"""ICT price-action patterns from plain OHLC, publicly documented definitions only.

Ported from FOREX Trader's reversal engine, which implemented the same
definitions for XAUUSD. No proprietary indicator code; every pattern here is
computable from candles alone.

* **Fair value gap (FVG)** -- three bars where bar 1's high is below bar 3's
  low (bullish) or bar 1's low above bar 3's high (bearish): price moved so
  fast it left a gap in traded prices.
* **Liquidity sweep** -- a bar trades beyond a level where stops rest (a
  swing high/low, the prior day's high/low) and closes back inside it.
* **Market structure shift (MSS)** -- after a sweep, price closes beyond the
  most recent minor swing in the opposite direction.
* **Breaker** -- the last opposite-colour candle before the move that made
  the MSS; its body is where a retrace is expected to turn.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind


@dataclass(frozen=True)
class Gap:
    index: int          # the third bar
    bullish: bool
    low: float
    high: float


@dataclass(frozen=True)
class Sweep:
    index: int
    bullish: bool       # a sweep of lows (bullish reversal) or of highs
    level: float
    extreme: float      # the wick's furthest price


def fair_value_gaps(bars: Sequence[Candle], lookback: int = 30) -> list[Gap]:
    out = []
    start = max(2, len(bars) - lookback)
    for i in range(start, len(bars)):
        a, c = bars[i - 2], bars[i]
        if a.high < c.low:
            out.append(Gap(i, True, a.high, c.low))
        elif a.low > c.high:
            out.append(Gap(i, False, c.high, a.low))
    return out


def find_sweep(bars: Sequence[Candle], levels_low: Sequence[float], levels_high: Sequence[float],
               within: int) -> Optional[Sweep]:
    """The most recent sweep in the last `within` bars."""
    for i in range(len(bars) - 1, max(len(bars) - 1 - within, 0), -1):
        b = bars[i]
        for lv in levels_low:
            if b.low < lv < b.close:
                return Sweep(i, True, lv, b.low)
        for lv in levels_high:
            if b.high > lv > b.close:
                return Sweep(i, False, lv, b.high)
    return None


def structure_shift(bars: Sequence[Candle], sweep: Sweep, strength: int = 2) -> bool:
    """Has price, since the sweep, closed beyond the last minor swing the other way?"""
    before = bars[max(0, sweep.index - 20):sweep.index]
    highs, lows = ind.swing_points(before, strength)
    after = bars[sweep.index + 1:]
    if not after:
        return False
    if sweep.bullish and highs:
        level = before[highs[-1]].high
        return any(c.close > level for c in after)
    if not sweep.bullish and lows:
        level = before[lows[-1]].low
        return any(c.close < level for c in after)
    return False


def breaker(bars: Sequence[Candle], sweep: Sweep) -> Optional[tuple[float, float]]:
    """(low, high) body of the last opposite candle before the sweep."""
    for i in range(sweep.index, max(sweep.index - 10, 0), -1):
        b = bars[i]
        if sweep.bullish and b.close < b.open:
            return b.close, b.open
        if not sweep.bullish and b.close > b.open:
            return b.open, b.close
    return None


def overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]
