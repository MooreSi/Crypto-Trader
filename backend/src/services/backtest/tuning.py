"""Walk-forward tuning: choose parameters on the past, judge them on the future.

The safe form of a "self-improving" bot. Tuning on all of history and
reporting the best result measures only how well the grid fits noise; here a
parameter set is only ever scored on bars it was not chosen on:

    | warm-up | seg 1 | seg 2 | seg 3 | ... | seg k+1 |
    fold 1:    train   test
    fold 2:            train   test
    ...

In each fold every candidate (the strategy's own `grid` x the exit plans in
`LADDERS` x breakeven on/off) is backtested on the train segment; the best by
profit factor, among candidates with at least `min_trades` trades, is then
backtested on the NEXT segment, which it never saw. The out-of-sample result
is all test segments joined, set against the untuned defaults on the same
segments. A fold where no candidate has `min_trades` train trades keeps the
defaults and says so (`fallback`); `profitable` is reported apart from
`beats_default`, because losing less than the defaults is still losing.

**A proposal, never a change.** Nothing here writes a risk setting, a
strategy constant or an engine toggle. The owner reads the report and
decides; golden rule 3 (defaults never change silently) stands.

Setups are computed once per strategy-parameter set over the whole history
(each depends only on bars up to its own) and every exit plan is simulated
over them, so the grid costs one generator pass per strategy-parameter set.
"""
from __future__ import annotations

import functools
import itertools
import math
from collections import Counter
from typing import Optional, Sequence

from backend.src.services.backtest import catalogue, runner, simulator
from backend.src.services.engines.service import HISTORY_BARS
from backend.src.services.exchange import provider
from backend.src.services.exchange.types import Candle, ExchangeClient
from backend.src.services.risk import settings as risk_settings

#: Exit plans tried besides the owner's own ladder ("yours").
LADDERS: dict[str, list[list[float]]] = {
    "trend": [[2.0, 0.3], [4.0, 0.3], [8.0, 0.4]],     # let winners run
    "single_2r": [[2.0, 1.0]],
    "quick": [[1.0, 0.5], [1.5, 0.5]],
}
BREAKEVEN = (0, 1)
MIN_SEGMENT_BARS = 100
DEFAULT_FOLDS = 4
DEFAULT_MIN_TRADES = 8


def folds(n_bars: int, warmup: int, k: int) -> list[tuple[int, int, int, int]]:
    """(train_start, train_end, test_start, test_end) per fold, rolling forward."""
    seg = (n_bars - warmup) // (k + 1)
    if k < 1 or seg < MIN_SEGMENT_BARS:
        raise ValueError(f"not enough history for {k} folds: need {(k + 1) * MIN_SEGMENT_BARS} bars "
                         f"after the {warmup}-bar warm-up, have {max(n_bars - warmup, 0)}")
    return [(warmup + i * seg, warmup + (i + 1) * seg, warmup + (i + 1) * seg, warmup + (i + 2) * seg)
            for i in range(k)]


def _exits(settings: dict, ladders: bool) -> list[tuple[str, list[list[float]], int]]:
    own = ("yours", settings["tp_ladder"], int(settings["breakeven_after_tp"]))
    if not ladders:
        return [own]
    plans = [("yours", settings["tp_ladder"])] + list(LADDERS.items())
    return [(name, ladder, be) for name, ladder in plans for be in BREAKEVEN]


def _score(s: dict, min_trades: int) -> Optional[tuple[float, float]]:
    """Higher is better; None when there are too few trades to judge."""
    if s["trades"] < min_trades:
        return None
    pf = s["profit_factor"]
    if pf is None:                       # no losers (or no winners)
        pf = math.inf if s["total_r"] > 0 else 0.0
    return pf, s["total_r"]


def _brief(s: dict) -> dict:
    return {k: v for k, v in s.items() if k != "curve"}


def _key(params: dict, exit_name: str, be: int) -> str:
    return repr((sorted(params.items()), exit_name, be))


def walk_forward(bars: Sequence[Candle], htf: Sequence[Candle], strat: catalogue.Strategy,
                 settings: dict, k: int = DEFAULT_FOLDS, min_trades: int = DEFAULT_MIN_TRADES,
                 ladders: bool = True, window: int = HISTORY_BARS) -> dict:
    windows = folds(len(bars), window, k)
    names = sorted(strat.grid)
    param_sets = [dict(zip(names, combo)) for combo in itertools.product(*(strat.grid[n] for n in names))] \
        or [{}]
    default_params = dict(strat.defaults)
    if default_params not in param_sets:
        param_sets.append(default_params)
    exits = _exits(settings, ladders)
    risk = float(settings["risk_per_trade_pct"])

    lo, hi = windows[0][0], windows[-1][3]
    sigs = {}
    for params in param_sets:
        gen = functools.partial(strat.generate, p=params) if strat.grid else strat.generate
        sigs[repr(sorted(params.items()))] = runner.signals(bars, htf, gen, strat.interval, strat.htf,
                                                            window, lo, hi)

    def trades(params: dict, ladder: list[list[float]], be: int, a: int, b: int) -> list[dict]:
        plan = dict(settings, tp_ladder=ladder, breakeven_after_tp=be)
        return runner.trades_from_signals(bars, sigs[repr(sorted(params.items()))], strat.interval,
                                          plan, a, b)

    own_ladder, own_be = settings["tp_ladder"], int(settings["breakeven_after_tp"])
    out_folds, chosen_trades, default_trades, picks = [], [], [], []
    for (a, b, c, d) in windows:
        best, best_score = None, None
        for params in param_sets:
            for name, ladder, be in exits:
                sc = _score(simulator.summarise(trades(params, ladder, be, a, b), risk), min_trades)
                if sc is not None and (best_score is None or sc > best_score):
                    best, best_score = (params, name, ladder, be), sc
        fallback = best is None
        if fallback:                     # nothing traded enough: keep the defaults
            best = (default_params, "yours", own_ladder, own_be)
        params, name, ladder, be = best
        train = trades(params, ladder, be, a, b)
        test = trades(params, ladder, be, c, d)
        base = trades(default_params, own_ladder, own_be, c, d)
        chosen_trades += test
        default_trades += base
        picks.append(_key(params, name, be))
        out_folds.append({
            "train_from": bars[a].t / 1000, "test_from": bars[c].t / 1000, "test_to": bars[d - 1].t / 1000,
            "chosen": {**params, "ladder": name, "breakeven_after_tp": be}, "fallback": fallback,
            "train": _brief(simulator.summarise(train, risk)),
            "test": _brief(simulator.summarise(test, risk)),
            "test_default": _brief(simulator.summarise(base, risk)),
        })

    oos = simulator.summarise(chosen_trades, risk)
    oos_default = simulator.summarise(default_trades, risk)
    top, count = Counter(picks).most_common(1)[0]
    pick = next(f["chosen"] for f, p in zip(out_folds, picks) if p == top)
    ladder_name = pick["ladder"]
    proposal = {**{n: pick[n] for n in names}, "ladder": ladder_name,
                "tp_ladder": own_ladder if ladder_name == "yours" else LADDERS[ladder_name],
                "breakeven_after_tp": pick["breakeven_after_tp"]}
    return {
        "folds": out_folds, "oos": oos, "oos_default": oos_default, "proposal": proposal,
        "stability": count / len(picks),
        "beats_default": oos["trades"] >= min_trades and oos["total_r"] > oos_default["total_r"],
        # Beating the defaults while both lose is not a reason to trade it.
        "profitable": oos["trades"] >= min_trades and oos["total_r"] > 0,
        "candidates": len(param_sets) * len(exits), "min_trades": min_trades,
    }


def tune(client: ExchangeClient, strategy: str, coin: str, bars: int,
         k: int = DEFAULT_FOLDS, min_trades: int = DEFAULT_MIN_TRADES) -> dict:
    strat = catalogue.get(strategy)
    k = int(min(max(k, 1), 8))
    bars = int(min(max(bars, runner.MIN_BARS), runner.MAX_BARS))
    rows, htf = runner.history(client, strat, coin, bars)
    result = walk_forward(rows, htf, strat, risk_settings.get(), k=k, min_trades=min_trades)
    return {"strategy": strat.name, "coin": coin, "interval": strat.interval, "bars": len(rows),
            "from": rows[0].t / 1000 if rows else None, "to": rows[-1].t / 1000 if rows else None,
            "grid": strat.grid, "defaults": strat.defaults, **result}


def run(strategy: str, coin: str, bars: int, k: int = DEFAULT_FOLDS) -> dict:
    """Tune against the running network's market data (read-only)."""
    return tune(provider.get(), strategy, coin, bars, k)
