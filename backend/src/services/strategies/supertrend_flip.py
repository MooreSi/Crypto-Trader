"""Supertrend flip: trade the first bar of a new Supertrend direction, with EMA200.

The most widely copied trend strategy on TradingView and in freqtrade's
community repository. On 1h bars:

* **trigger** -- Supertrend(`ST_PERIOD`, `ST_MULT`) flips on the latest bar;
* **filter** -- the close is on the same side of EMA(`EMA_N`) (trade with the
  long-term trend only);
* **stop** -- the Supertrend line, at least `MIN_STOP_ATR` ATRs from entry.

The 4h Supertrend agreeing is a feature, not a filter. Strategy Lab only:
never reaches the executor.
"""
from __future__ import annotations

from typing import Optional, Sequence

from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind

ST_PERIOD = 10
ST_MULT = 3.0
EMA_N = 200
MIN_STOP_ATR = 1.0

EXTRA_FEATURES = ("st_line_atr", "st_ema_dist_atr", "st_htf_agree")

#: The tunable constants and their values as above; `generate(..., p)` overrides them.
DEFAULTS = {"ST_PERIOD": ST_PERIOD, "ST_MULT": ST_MULT}


def generate(bars: Sequence[Candle], htf: Sequence[Candle], p: Optional[dict] = None) -> list[Setup]:
    k = {**DEFAULTS, **(p or {})}
    period, mult = int(k["ST_PERIOD"]), float(k["ST_MULT"])
    if len(bars) < EMA_N + 2:
        return []
    st = ind.supertrend(bars, period, mult)
    (line, now), (_, before) = st[-1], st[-2]
    if line is None or now == before or before == 0:
        return []
    ema = ind.ema([c.close for c in bars], EMA_N)[-1]
    atr = ind.atr(bars, 14)
    if ema is None or not atr:
        return []
    c = bars[-1]
    direction = "long" if now == 1 else "short"
    if (direction == "long") != (c.close > ema):
        return []
    hst = ind.supertrend(htf, period, mult) if len(htf) > period + 1 else []
    htf_dir = hst[-1][1] if hst else 0
    if direction == "long":
        stop = min(line, c.close - MIN_STOP_ATR * atr)
    else:
        stop = max(line, c.close + MIN_STOP_ATR * atr)
    return [Setup(direction, c.close, stop,
                  f"Supertrend flipped {'up' if now == 1 else 'down'} "
                  f"{'above' if direction == 'long' else 'below'} EMA{EMA_N}",
                  {"st_line_atr": abs(c.close - line) / atr,
                   "st_ema_dist_atr": abs(c.close - ema) / atr,
                   "st_htf_agree": float(htf_dir * now)})]
