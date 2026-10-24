"""Key price levels: swing highs/lows, prior-day high/low, round numbers.

Round numbers are scaled to the price: BTC at 80,000 respects 1,000s, a coin
at 0.5 respects 0.05s. `round_step` picks the step from the price's order of
magnitude so the same rule works for every market on the exchange.
"""
from __future__ import annotations

import math
from typing import Sequence

from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind


def round_step(price: float) -> float:
    if price <= 0:
        return 1.0
    return 10 ** (math.floor(math.log10(price)) - 1) * 5


def nearest_round(price: float) -> float:
    step = round_step(price)
    return round(price / step) * step


def swing_levels(candles: Sequence[Candle], strength: int = 3) -> tuple[list[float], list[float]]:
    highs, lows = ind.swing_points(candles, strength)
    return [candles[i].high for i in highs], [candles[i].low for i in lows]


def prior_day(daily: Sequence[Candle]) -> tuple[float, float] | None:
    """(high, low) of the last CLOSED daily candle."""
    if len(daily) < 2:
        return None
    d = daily[-2]
    return d.high, d.low


def distance_to_nearest(price: float, levels: Sequence[float]) -> float:
    """Distance to the nearest level as a fraction of price (1.0 if none)."""
    if not levels or price <= 0:
        return 1.0
    return min(abs(price - lv) for lv in levels) / price
