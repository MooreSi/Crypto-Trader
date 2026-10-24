"""Market regime from ADX and volatility: trend, range, or volatile.

A feature and a filter. The engines use it to stand down where their edge
does not apply (a breakout in a dead range, a reversal into a strong trend).
"""
from __future__ import annotations

from typing import Sequence

from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind

TREND_ADX = 25.0
RANGE_ADX = 18.0
VOLATILE_ATR_PCT_RANK = 0.9


def detect(candles: Sequence[Candle]) -> str:
    a = ind.adx(candles, 14)
    if a is None:
        return "unknown"
    atrs = [ind.atr(candles[: i + 1], 14) for i in range(len(candles) - 50, len(candles))
            if i >= 15]
    atrs = [x for x in atrs if x is not None]
    if atrs and ind.pct_rank(atrs, atrs[-1]) >= VOLATILE_ATR_PCT_RANK and a < TREND_ADX:
        return "volatile"
    if a >= TREND_ADX:
        return "trend"
    if a <= RANGE_ADX:
        return "range"
    return "transition"


REGIME_CODES = {"unknown": 0.0, "range": 1.0, "transition": 2.0, "trend": 3.0, "volatile": 4.0}
