"""Bollinger + RSI reversion: fade an oversold / overbought flush in a range.

The staple mean-reversion strategy of open-source crypto bots (freqtrade's
BB-RSI family). On 15m bars:

* **range** -- ADX(14) at most `MAX_ADX`, measured BEFORE the flush (a flush
  raises ADX on its own, which would hide exactly the setup);
* **flush** -- within the last `LOOKBACK` bars, a close below the lower
  Bollinger band (20, 2) with RSI(14) at most `RSI_BAND` (at least 100 - band for shorts);
* **trigger** -- the latest bar closes back inside the band, in the reversal
  direction.

Stop beyond the flush's extreme by `STOP_PAD_ATR`, at least `MIN_STOP_ATR`
ATRs from entry. Strategy Lab only: never reaches the executor.
"""
from __future__ import annotations

from typing import Optional, Sequence

from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind

MAX_ADX = 25.0
RSI_BAND = 30.0          # oversold at RSI <= band, overbought at RSI >= 100 - band
LOOKBACK = 4
STOP_PAD_ATR = 0.25
MIN_STOP_ATR = 1.0

EXTRA_FEATURES = ("bb_rsi_extreme", "bb_depth_atr", "bb_width")

#: The tunable constants and their values as above; `generate(..., p)` overrides them.
DEFAULTS = {"RSI_BAND": RSI_BAND, "MAX_ADX": MAX_ADX}


def generate(bars: Sequence[Candle], htf: Sequence[Candle], p: Optional[dict] = None) -> list[Setup]:
    k = {**DEFAULTS, **(p or {})}
    rsi_low, rsi_high, max_adx = float(k["RSI_BAND"]), 100.0 - float(k["RSI_BAND"]), float(k["MAX_ADX"])
    if len(bars) < 60:
        return []
    adx = ind.adx(bars[:-LOOKBACK - 1], 14)
    atr = ind.atr(bars[:-1], 14)
    if adx is None or adx > max_adx or not atr:
        return []
    closes = [c.close for c in bars]
    bands = ind.bollinger_bands(closes)
    if bands is None:
        return []
    lower, mid, upper = bands
    c = bars[-1]
    recent = range(len(bars) - 1 - LOOKBACK, len(bars) - 1)
    flushes = []
    for j in recent:
        b = ind.bollinger_bands(closes[:j + 1])
        r = ind.rsi(closes[:j + 1], 14)
        if b is None or r is None:
            continue
        if closes[j] < b[0] and r <= rsi_low:
            flushes.append(("long", r, b[0] - closes[j]))
        elif closes[j] > b[2] and r >= rsi_high:
            flushes.append(("short", r, closes[j] - b[2]))
    window = bars[-LOOKBACK - 1:]
    for direction, r, depth in flushes[::-1]:
        if direction == "long" and lower < c.close < mid and c.close > c.open:
            stop = min(min(b.low for b in window) - STOP_PAD_ATR * atr, c.close - MIN_STOP_ATR * atr)
        elif direction == "short" and mid < c.close < upper and c.close < c.open:
            stop = max(max(b.high for b in window) + STOP_PAD_ATR * atr, c.close + MIN_STOP_ATR * atr)
        else:
            continue
        return [Setup(direction, c.close, stop,
                      f"{'oversold' if direction == 'long' else 'overbought'} flush (RSI {r:.0f}) "
                      f"back inside the band",
                      {"bb_rsi_extreme": r, "bb_depth_atr": depth / atr,
                       "bb_width": (upper - lower) / mid if mid else 0.0})]
    return []
