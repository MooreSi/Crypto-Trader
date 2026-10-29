"""Replay one setup bar by bar with the live exit plan, in R multiples.

The exit plan is the one `order_service` places and `positions/manager.py`
manages: a stop, a TP ladder of `[R, fraction of the original size]` rungs,
and the stop moved to entry (or `stop_lock_r` R past it) after
`breakeven_after_tp` TPs. A ladder adding up to less than 1 leaves a runner;
the live trail is not modelled, so a runner the stop does not take is marked
to the last close at `max_bars`. Rules, chosen to flatter nothing:

* a bar that touches the stop AND a target is scored as the stop for
  whatever is still open (from OHLC the order inside the bar is unknown; the
  tracker uses the same rule);
* a breakeven move takes effect from the NEXT bar, never inside the bar that
  earned it;
* a round-trip taker fee is charged in R: `2 x fee_rate x entry / risk`;
* after `max_bars` the rest is marked to the last close (`expired`); if the
  bars run out first the trade is `open` and the runner leaves it out.

Pure: no I/O, no clock.
"""
from __future__ import annotations

from typing import Sequence

from backend.src.services.exchange.types import Candle
from backend.src.services.risk.sizing import r_multiple, tp_price


def simulate(direction: str, entry: float, stop: float, bars_after: Sequence[Candle],
             ladder: list[list[float]], breakeven_after_tp: int, fee_rate: float,
             max_bars: int, stop_lock_r: float = 0.0) -> dict:
    long = direction == "long"
    risk = abs(entry - stop)
    fee_r = 2.0 * fee_rate * entry / risk if risk else 0.0
    rungs = [(tp_price(direction, entry, stop, r), r, f) for r, f in ladder]
    lock = tp_price(direction, entry, stop, stop_lock_r) if stop_lock_r > 0 else entry
    hit = [False] * len(rungs)
    open_frac, booked, tp_hits, cur_stop = 1.0, 0.0, 0, stop
    moved = False

    def done(exit_: str, i: int, gross: float) -> dict:
        return {"r": gross - fee_r, "gross_r": gross, "fee_r": fee_r, "exit": exit_,
                "exit_index": i, "tp_hits": tp_hits}

    for i, c in enumerate(bars_after[:max_bars]):
        stopped = c.low <= cur_stop if long else c.high >= cur_stop
        if stopped:
            at_entry = cur_stop == entry
            return done("breakeven" if at_entry else "stop", i,
                        booked + open_frac * r_multiple(direction, entry, stop, cur_stop))
        new_hits = 0
        for k, (price, r, frac) in enumerate(rungs):
            if hit[k] or not (c.high >= price if long else c.low <= price):
                continue
            hit[k] = True
            take = min(frac, open_frac)
            booked += take * r
            open_frac -= take
            new_hits += 1
        tp_hits += new_hits
        if open_frac <= 1e-9:
            return done("tp", i, booked)
        if breakeven_after_tp and tp_hits >= breakeven_after_tp and not moved:
            # As live: a lock past the price would fire at once, so it is entry.
            safe = lock == entry or (lock < c.close if long else lock > c.close)
            target = lock if safe else entry
            cur_stop = max(cur_stop, target) if long else min(cur_stop, target)
            moved = True
        if i + 1 >= max_bars:
            return done("expired", i, booked + open_frac * r_multiple(direction, entry, stop, c.close))
    last = bars_after[min(len(bars_after), max_bars) - 1].close if bars_after else entry
    return done("open", len(bars_after) - 1,
                booked + open_frac * r_multiple(direction, entry, stop, last))


def summarise(trades: list[dict], risk_pct: float) -> dict:
    """Headline metrics of closed simulated trades (`{"t", "r"}`, oldest first)."""
    n = len(trades)
    rs = [float(t["r"]) for t in trades]
    gains = sum(r for r in rs if r > 0)
    losses = -sum(r for r in rs if r < 0)
    cum, peak, max_dd, growth = 0.0, 0.0, 0.0, 1.0
    curve = []
    for t, r in zip(trades, rs):
        cum += r
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
        growth *= 1 + r * risk_pct / 100.0
        curve.append({"t": t["t"], "r": cum})
    wins = sum(1 for r in rs if r > 0)
    return {
        "trades": n, "wins": wins, "win_rate": wins / n if n else None,
        "total_r": cum, "avg_r": cum / n if n else None,
        "profit_factor": gains / losses if losses > 0 and gains > 0 else None,
        "best_r": max(rs) if rs else None, "worst_r": min(rs) if rs else None,
        "max_drawdown_r": max_dd, "risk_pct": risk_pct,
        "compounded_return_pct": (growth - 1.0) * 100.0, "curve": curve,
    }
