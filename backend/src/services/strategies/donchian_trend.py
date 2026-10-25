"""Donchian trend: a fresh break of the 20-bar channel, confirmed by an ensemble.

Time-series momentum is the best-documented systematic edge in crypto: a
Donchian-channel ensemble across several lookbacks with volatility-based
sizing ("Catching Crypto Trends", Zarattini et al.) and the Turtle rules
before it. On 4h bars:

* **entry** -- the trigger bar closes beyond the prior `ENTRY_N`-bar channel,
  and the bar before it did not (a fresh break, not a running trend);
* **ensemble** -- at least `MIN_AGREE` of the `ENSEMBLE` lookbacks have price
  on the breakout side of their channel midpoint;
* **stop** -- `STOP_ATR` x ATR(20) from entry (the Turtles' 2N).

Strategy Lab only: it runs in the backtester and never reaches the executor.
"""
from __future__ import annotations

from typing import Optional, Sequence

from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind

ENTRY_N = 20
ENSEMBLE = (20, 55, 100)
MIN_AGREE = 2 / 3
STOP_ATR = 2.0

EXTRA_FEATURES = ("dc_agree", "dc_break_atr", "dc_width_atr")

#: The tunable constants and their values as above; `generate(..., p)` overrides them.
DEFAULTS = {"ENTRY_N": ENTRY_N, "STOP_ATR": STOP_ATR}


def _agreement(bars: Sequence[Candle], direction: str) -> float:
    close = bars[-1].close
    votes = []
    for n in ENSEMBLE:
        hi, lo = ind.donchian(bars, n)
        mid = (hi + lo) / 2
        votes.append(1.0 if (close > mid if direction == "long" else close < mid) else 0.0)
    return sum(votes) / len(votes)


def generate(bars: Sequence[Candle], htf: Sequence[Candle], p: Optional[dict] = None) -> list[Setup]:
    k = {**DEFAULTS, **(p or {})}
    entry_n, stop_atr = int(k["ENTRY_N"]), float(k["STOP_ATR"])
    if len(bars) < max(ENSEMBLE) + 2:
        return []
    atr = ind.atr(bars[:-1], 20)
    now, prev = ind.donchian(bars, entry_n), ind.donchian(bars[:-1], entry_n)
    if not atr or now is None or prev is None:
        return []
    c, p = bars[-1], bars[-2]
    hi, lo = now
    for direction, broke, fresh, beyond in (
            ("long", c.close > hi, p.close <= prev[0], c.close - hi),
            ("short", c.close < lo, p.close >= prev[1], lo - c.close)):
        if not (broke and fresh):
            continue
        agree = _agreement(bars, direction)
        if agree < MIN_AGREE:
            continue
        stop = c.close - stop_atr * atr if direction == "long" else c.close + stop_atr * atr
        return [Setup(direction, c.close, stop,
                      f"fresh {entry_n}-bar {'high' if direction == 'long' else 'low'} break, "
                      f"ensemble {agree:.0%}",
                      {"dc_agree": agree, "dc_break_atr": beyond / atr,
                       "dc_width_atr": (hi - lo) / atr})]
    return []
