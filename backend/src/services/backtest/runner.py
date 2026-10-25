"""Walk a strategy over history, bar by bar, and score it with the live exit plan.

At each closed bar the strategy's generator sees exactly what an engine would
have seen at that bar's close: the last `window` closed bars and the
higher-timeframe bars that had closed by then. Nothing later. A setup enters
at the bar's close; `simulator.simulate` replays the exit plan from the next
bar. One trade at a time per coin, like the live "one per coin" gate.

Reads candles only. Nothing here can place an order: the runner never sees
an order method, and the import-contract gate would refuse one.

What a backtest does NOT include, so it flatters live results: funding,
slippage beyond the fee, the risk gates (ML, funding, blackout, daily
limits), and the minimum order size. Say so whenever a number is quoted.
"""
from __future__ import annotations

import bisect
from typing import Optional, Sequence

from backend.src.services.backtest import catalogue, simulator
from backend.src.services.engines import tracker
from backend.src.services.engines.service import HISTORY_BARS, Generator, Setup
from backend.src.services.exchange import provider
from backend.src.services.exchange.paper_exchange import PAPER_TAKER_FEE
from backend.src.services.exchange.types import Candle, ExchangeClient
from backend.src.services.market import candles as candle_src
from backend.src.services.market.candles import INTERVAL_MS
from backend.src.services.risk import settings as risk_settings

MIN_BARS, MAX_BARS = 300, 5000


def signals(bars: Sequence[Candle], htf: Sequence[Candle], generate: Generator, interval: str,
            htf_interval: Optional[str], window: int = HISTORY_BARS, start: int = 0,
            end: Optional[int] = None) -> dict[int, Setup]:
    """The first setup at each bar index in [start, end), from closed history only.

    A setup depends only on bars up to its own, so computing them once and
    simulating many exit plans over them cannot leak the future.
    """
    step = INTERVAL_MS[interval]
    htf_step = INTERVAL_MS[htf_interval] if htf_interval else 0
    htf_close = [h.t + htf_step for h in htf]
    out: dict[int, Setup] = {}
    for i in range(max(window - 1, start), len(bars) if end is None else end):
        decided_at = bars[i].t + step                     # the bar's close
        visible_htf = htf[:bisect.bisect_right(htf_close, decided_at)][-window:]
        setups = generate(bars[i - window + 1:i + 1], visible_htf)
        if setups:
            out[i] = setups[0]
    return out


def trades_from_signals(bars: Sequence[Candle], sigs: dict[int, Setup], interval: str,
                        settings: dict, start: int, end: int) -> list[dict]:
    """Simulate the setups in [start, end) one at a time, using bars before `end` only.

    A trade still open at `end` is left out, and nothing after it is taken
    (the one-per-coin rule would have blocked them).
    """
    step = INTERVAL_MS[interval]
    ladder, be = settings["tp_ladder"], int(settings["breakeven_after_tp"])
    trades: list[dict] = []
    busy_until = -1
    for i in sorted(k for k in sigs if start <= k < end):
        if i <= busy_until:
            continue
        s = sigs[i]
        out = simulator.simulate(s.direction, s.entry, s.stop, bars[i + 1:end], ladder, be,
                                 PAPER_TAKER_FEE, tracker.MAX_BARS)
        if out["exit"] == "open":
            break
        exit_i = i + 1 + out["exit_index"]
        decided_at = bars[i].t + step
        trades.append({"t": decided_at / 1000, "opened_at": decided_at / 1000,
                       "closed_at": (bars[exit_i].t + step) / 1000, "direction": s.direction,
                       "entry": s.entry, "stop": s.stop, "reason": s.reason, **out})
        busy_until = exit_i
    return trades


def run_on_bars(bars: Sequence[Candle], htf: Sequence[Candle], generate: Generator,
                interval: str, htf_interval: Optional[str], settings: dict,
                window: int = HISTORY_BARS) -> list[dict]:
    sigs = signals(bars, htf, generate, interval, htf_interval, window)
    return trades_from_signals(bars, sigs, interval, settings, window - 1, len(bars))


def history(client: ExchangeClient, strat: catalogue.Strategy,
            coin: str, bars: int) -> tuple[list[Candle], list[Candle]]:
    """Closed bars on the strategy's interval, and its higher timeframe's to match."""
    rows = candle_src.closed(client, coin, strat.interval, bars)
    htf: list[Candle] = []
    if strat.htf:
        n_htf = bars * INTERVAL_MS[strat.interval] // INTERVAL_MS[strat.htf] + HISTORY_BARS
        htf = candle_src.closed(client, coin, strat.htf, int(min(n_htf, MAX_BARS)))
    return rows, htf


def backtest(client: ExchangeClient, strategy: str, coin: str, bars: int) -> dict:
    strat = catalogue.get(strategy)
    bars = int(min(max(bars, MIN_BARS), MAX_BARS))
    settings = risk_settings.get()
    rows, htf = history(client, strat, coin, bars)
    trades = run_on_bars(rows, htf, strat.generate, strat.interval, strat.htf, settings) \
        if len(rows) >= HISTORY_BARS + 10 else []
    summary = simulator.summarise(trades, float(settings["risk_per_trade_pct"]))
    return {"strategy": strat.name, "coin": coin, "interval": strat.interval, "bars": len(rows),
            "from": rows[0].t / 1000 if rows else None, "to": rows[-1].t / 1000 if rows else None,
            "ladder": settings["tp_ladder"], "summary": summary,
            "trades": [{k: t[k] for k in ("opened_at", "closed_at", "direction", "entry", "stop",
                                           "r", "exit", "tp_hits", "reason")} for t in trades]}


def run(strategy: str, coin: str, bars: int) -> dict:
    """Backtest against the running network's market data (read-only)."""
    return backtest(provider.get(), strategy, coin, bars)
