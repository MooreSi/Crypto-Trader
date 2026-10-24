"""Trend PA: trade the pullback in an established trend, on 1h bars.

Trend: EMA20 > EMA50 > EMA200 (long) or the reverse (short), with ADX at
least `MIN_ADX`. Pullback: the trigger bar's low (long) reaches EMA20 within
`TOUCH_ATR` ATRs, and the bar rejects it -- closes in the trend's direction
with a wick at least `MIN_WICK` of its range on the pullback side.

Stop: beyond the trigger bar's extreme by `STOP_PAD_ATR`, at least
`MIN_STOP_ATR` ATRs from entry. The 4h trend agreeing is a feature, not a
filter, so the model can learn whether it matters per market.
"""
from __future__ import annotations

from typing import Sequence

from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind

MIN_ADX = 20.0
TOUCH_ATR = 0.25
MIN_WICK = 0.4
STOP_PAD_ATR = 0.2
MIN_STOP_ATR = 1.0

EXTRA_FEATURES = ("tp_ema_spread_atr", "tp_wick", "tp_htf_agree", "tp_adx")


def _htf_trend(htf: Sequence[Candle]) -> float:
    closes = [c.close for c in htf]
    e20, e50 = ind.ema(closes, 20), ind.ema(closes, 50)
    if not closes or e20[-1] is None or e50[-1] is None:
        return 0.0
    return 1.0 if e20[-1] > e50[-1] else -1.0


def generate(bars: Sequence[Candle], htf: Sequence[Candle]) -> list[Setup]:
    if len(bars) < 210:
        return []
    closes = [c.close for c in bars]
    e20, e50, e200 = ind.ema(closes, 20)[-1], ind.ema(closes, 50)[-1], ind.ema(closes, 200)[-1]
    atr, adx = ind.atr(bars, 14), ind.adx(bars, 14)
    if None in (e20, e50, e200) or not atr or adx is None or adx < MIN_ADX:
        return []
    c = bars[-1]
    rng = c.high - c.low
    if rng <= 0:
        return []
    htf_trend = _htf_trend(htf)
    if e20 > e50 > e200:
        wick = (min(c.open, c.close) - c.low) / rng
        if c.low <= e20 + TOUCH_ATR * atr and c.close > e20 and c.close > c.open and wick >= MIN_WICK:
            stop = min(c.low - STOP_PAD_ATR * atr, c.close - MIN_STOP_ATR * atr)
            return [Setup("long", c.close, stop, f"pullback to EMA20 in uptrend, ADX {adx:.0f}",
                          {"tp_ema_spread_atr": (e20 - e50) / atr, "tp_wick": wick,
                           "tp_htf_agree": 1.0 if htf_trend > 0 else -1.0 if htf_trend < 0 else 0.0,
                           "tp_adx": adx})]
    if e20 < e50 < e200:
        wick = (c.high - max(c.open, c.close)) / rng
        if c.high >= e20 - TOUCH_ATR * atr and c.close < e20 and c.close < c.open and wick >= MIN_WICK:
            stop = max(c.high + STOP_PAD_ATR * atr, c.close + MIN_STOP_ATR * atr)
            return [Setup("short", c.close, stop, f"pullback to EMA20 in downtrend, ADX {adx:.0f}",
                          {"tp_ema_spread_atr": (e50 - e20) / atr, "tp_wick": wick,
                           "tp_htf_agree": 1.0 if htf_trend < 0 else -1.0 if htf_trend > 0 else 0.0,
                           "tp_adx": adx})]
    return []
