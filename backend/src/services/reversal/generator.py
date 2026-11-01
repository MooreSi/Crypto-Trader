"""Reversal: liquidity sweep of a key level, then a market structure shift.

On 15m bars, against levels from the same bars (swing highs/lows) and the
prior day's high/low (from the higher-timeframe series, daily bars):

1. a bar sweeps a level (`ict_patterns.find_sweep`) within `SWEEP_WINDOW`
   bars of the trigger;
2. price then shifts structure the other way (`structure_shift`);
3. the trigger bar closes in the new direction.

Entry at the trigger close; stop beyond the sweep's extreme by `STOP_PAD_ATR`
ATRs, at least `MIN_STOP_ATR` from entry. A fair value gap left by the shift
that overlaps the breaker -- the "unicorn" FOREX Trader's engine looked for --
is recorded as a feature, not required, so the model can weigh it.

Stands down when ADX shows a strong trend (`MAX_ADX`): reversals into a
trend are where this setup loses most.

Takes a sweep only in the direction of the daily trend (EMA`HTF_FAST` vs
EMA`HTF_SLOW` of the daily closes): a sweep of a low in a daily uptrend, of a
high in a downtrend. Measured 2026-10-27 on 12 coins with the live 1.5%
minimum stop, chosen on the first 60% of the history and checked on the
last 40%: sweeps against the daily trend lost under every exit plan, sweeps
with it made money at a 1.5R target. With too few daily bars to tell (a new
listing) the filter does not apply, which is how the engine behaved before.

`accept` adds a market-context filter the service applies after `generate`:
funding must agree with the trade. A long only while longs pay at least
`MIN_AGREE_FUNDING_8H` per 8 hours (perps at or above the resting premium),
a short only while shorts are paid that much. Measured 2026-11-01 on 2
years of 15m history for 12 coins (Binance USD-M perps, the closest long
public record) under the live exit plan with the 1% minimum stop: kept
+0.039R a trade over 1206 trades against -0.085R for the 2409 it drops;
kept beat dropped in 7 of 8 quarters, under every exit plan tried, and in
both the first 60% and the last 40% of the history (+0.026 vs -0.048,
+0.073 vs -0.074). Long-only, by contrast, lost -0.115R out of sample, so
this is not a long bias. With no snapshot (the backtester, a coin missing
from the market list) it does not apply.
"""
from __future__ import annotations

from typing import Optional, Sequence

from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle, MarketSnapshot
from backend.src.services.market import indicators as ind
from backend.src.services.market import levels
from backend.src.services.reversal import ict_patterns as ict

SWEEP_WINDOW = 6
STOP_PAD_ATR = 0.15
MIN_STOP_ATR = 0.8
MAX_ADX = 35.0
HTF_FAST = 10
HTF_SLOW = 20
#: Funding that counts as agreeing, as a fraction per 8 hours (0.7 bp). The
#: resting rate when perps trade at a premium is 1 bp per 8h (0.00125%/h on
#: Hyperliquid); below 0.7 bp the premium has turned to a discount.
MIN_AGREE_FUNDING_8H = 0.00007

EXTRA_FEATURES = ("rv_sweep_depth_atr", "rv_bars_since_sweep", "rv_fvg", "rv_unicorn",
                  "rv_prior_day_level")


def daily_bias(htf: Sequence[Candle]) -> int:
    """+1 daily uptrend, -1 downtrend, 0 too few daily bars to tell."""
    closes = [c.close for c in htf]
    fast, slow = ind.ema(closes, HTF_FAST), ind.ema(closes, HTF_SLOW)
    if not closes or fast[-1] is None or slow[-1] is None:
        return 0
    return 1 if fast[-1] > slow[-1] else -1


def accept(setup: Setup, snapshot: Optional[MarketSnapshot]) -> bool:
    """Does funding agree with the setup? True when there is no snapshot."""
    if snapshot is None:
        return True
    per_8h = snapshot.funding_rate * 8
    if setup.direction == "long":
        return per_8h >= MIN_AGREE_FUNDING_8H
    return per_8h <= -MIN_AGREE_FUNDING_8H


def generate(bars: Sequence[Candle], htf: Sequence[Candle]) -> list[Setup]:
    if len(bars) < 80:
        return []
    atr, adx = ind.atr(bars, 14), ind.adx(bars, 14)
    if not atr or (adx is not None and adx > MAX_ADX):
        return []
    window = bars[-100:-SWEEP_WINDOW - 1]
    swing_hi, swing_lo = levels.swing_levels(window, 3)
    pd = levels.prior_day(htf) if htf else None
    lows = swing_lo[-5:] + ([pd[1]] if pd else [])
    highs = swing_hi[-5:] + ([pd[0]] if pd else [])
    recent = list(bars[-SWEEP_WINDOW - 1:])
    sweep = ict.find_sweep(recent, lows, highs, SWEEP_WINDOW)
    if sweep is None or sweep.index == len(recent) - 1:
        return []
    offset = len(bars) - len(recent)
    abs_sweep = ict.Sweep(sweep.index + offset, sweep.bullish, sweep.level, sweep.extreme)
    if not ict.structure_shift(bars, abs_sweep):
        return []
    trigger = bars[-1]
    direction = "long" if sweep.bullish else "short"
    if (direction == "long") != (trigger.close > trigger.open):
        return []
    if daily_bias(htf) == (-1 if direction == "long" else 1):
        return []
    entry = trigger.close
    if direction == "long":
        stop = min(sweep.extreme - STOP_PAD_ATR * atr, entry - MIN_STOP_ATR * atr)
    else:
        stop = max(sweep.extreme + STOP_PAD_ATR * atr, entry + MIN_STOP_ATR * atr)
    gaps = [g for g in ict.fair_value_gaps(bars, 10) if g.bullish == sweep.bullish
            and g.index > abs_sweep.index]
    brk = ict.breaker(bars, abs_sweep)
    unicorn = any(brk and ict.overlaps((g.low, g.high), brk) for g in gaps)
    return [Setup(direction, entry, stop,
                  f"sweep of {'low' if sweep.bullish else 'high'} {sweep.level:.6g} + MSS"
                  + (" (unicorn)" if unicorn else ""),
                  {"rv_sweep_depth_atr": abs(sweep.extreme - sweep.level) / atr,
                   "rv_bars_since_sweep": float(len(recent) - 1 - sweep.index),
                   "rv_fvg": float(bool(gaps)), "rv_unicorn": float(unicorn),
                   "rv_prior_day_level": float(bool(pd) and sweep.level in pd)})]
