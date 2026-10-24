"""Breakout: price leaves a tight range with volume, or breaks then retests it.

Ported in spirit from FOREX Trader's breakout engine (break-and-go and
break-and-retest on XAUUSD M5), rebuilt for any perpetual on 15m bars:

* **range** -- the `RANGE_BARS` closed bars before the trigger bar; it counts
  as consolidation when its height is at most `MAX_RANGE_ATR` ATRs.
* **break-and-go** -- the trigger bar closes beyond the range by at least
  `BREAK_ATR` ATR on volume at least `MIN_VOL_Z` standard deviations above
  normal.
* **break-and-retest** -- a break happened within the last `RETEST_WINDOW`
  bars, and the trigger bar comes back to touch the broken edge and closes
  back on the breakout side.

Stop: the range midpoint, but at least `MIN_STOP_ATR` ATRs from entry.
Stands down in the `volatile` regime, where ranges are noise.

ATR and regime are measured on the bars BEFORE the trigger. Measured with
it, the breakout bar's own range inflates ATR into the top decile and every
genuine breakout reads as "volatile" -- the filter would drop exactly what
the engine exists to find.
"""
from __future__ import annotations

from typing import Sequence

from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind
from backend.src.services.market import regime

RANGE_BARS = 24
MAX_RANGE_ATR = 4.0
BREAK_ATR = 0.1
MIN_VOL_Z = 1.0
RETEST_WINDOW = 8
RETEST_TOLERANCE_ATR = 0.25
MIN_STOP_ATR = 1.0

EXTRA_FEATURES = ("bo_range_atr", "bo_break_atr", "bo_vol_z", "bo_retest")


def _range(bars: Sequence[Candle]) -> tuple[float, float]:
    return max(c.high for c in bars), min(c.low for c in bars)


def _stop(direction: str, entry: float, mid: float, atr: float) -> float:
    if direction == "long":
        return min(mid, entry - MIN_STOP_ATR * atr)
    return max(mid, entry + MIN_STOP_ATR * atr)


def generate(bars: Sequence[Candle], htf: Sequence[Candle]) -> list[Setup]:
    if len(bars) < RANGE_BARS + RETEST_WINDOW + 30:
        return []
    before = bars[:-1]
    atr = ind.atr(before, 14)
    if not atr or regime.detect(before) == "volatile":
        return []
    trigger = bars[-1]
    vol_z = ind.zscore([c.volume for c in bars], 20) or 0.0

    # break-and-go
    hi, lo = _range(bars[-RANGE_BARS - 1:-1])
    height = (hi - lo) / atr
    if height <= MAX_RANGE_ATR and vol_z >= MIN_VOL_Z:
        mid = (hi + lo) / 2
        for direction, edge, beyond in (("long", hi, trigger.close - hi),
                                         ("short", lo, lo - trigger.close)):
            if beyond >= BREAK_ATR * atr:
                return [Setup(direction, trigger.close, _stop(direction, trigger.close, mid, atr),
                              f"break-and-go of a {height:.1f} ATR range on vol z {vol_z:.1f}",
                              {"bo_range_atr": height, "bo_break_atr": beyond / atr,
                               "bo_vol_z": vol_z, "bo_retest": 0.0})]

    # break-and-retest: range ends RETEST_WINDOW bars before the trigger
    base = bars[-RANGE_BARS - RETEST_WINDOW - 1:-RETEST_WINDOW - 1]
    hi, lo = _range(base)
    height = (hi - lo) / atr
    if height > MAX_RANGE_ATR:
        return []
    since = bars[-RETEST_WINDOW - 1:-1]
    mid = (hi + lo) / 2
    tol = RETEST_TOLERANCE_ATR * atr
    if any(c.close > hi + BREAK_ATR * atr for c in since) and \
            abs(trigger.low - hi) <= tol and trigger.close > hi and trigger.close > trigger.open:
        return [Setup("long", trigger.close, _stop("long", trigger.close, mid, atr),
                      "break-and-retest of range high",
                      {"bo_range_atr": height, "bo_break_atr": (trigger.close - hi) / atr,
                       "bo_vol_z": vol_z, "bo_retest": 1.0})]
    if any(c.close < lo - BREAK_ATR * atr for c in since) and \
            abs(trigger.high - lo) <= tol and trigger.close < lo and trigger.close < trigger.open:
        return [Setup("short", trigger.close, _stop("short", trigger.close, mid, atr),
                      "break-and-retest of range low",
                      {"bo_range_atr": height, "bo_break_atr": (lo - trigger.close) / atr,
                       "bo_vol_z": vol_z, "bo_retest": 1.0})]
    return []
