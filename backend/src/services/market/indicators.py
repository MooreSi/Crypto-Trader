"""Price indicators as pure functions over candle lists.

No I/O and no state: every engine computes its own features from these, so
a change here moves every engine at once. Keep them boring and pinned by
tests (tests/services/market/test_indicators.py).

Conventions: input oldest first; output aligned to the input (same length)
for series functions, with leading values that cannot be computed set to
None, or a single float for "latest value" functions.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

from backend.src.services.exchange.types import Candle


def ema(values: Sequence[float], period: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def true_ranges(candles: Sequence[Candle]) -> list[float]:
    trs = []
    for i, c in enumerate(candles):
        if i == 0:
            trs.append(c.high - c.low)
        else:
            pc = candles[i - 1].close
            trs.append(max(c.high - c.low, abs(c.high - pc), abs(c.low - pc)))
    return trs


def atr(candles: Sequence[Candle], period: int = 14) -> Optional[float]:
    """Wilder's ATR of the latest bar."""
    if len(candles) < period + 1:
        return None
    trs = true_ranges(candles)[1:]
    value = sum(trs[:period]) / period
    for tr in trs[period:]:
        value = (value * (period - 1) + tr) / period
    return value


def rsi(closes: Sequence[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    avg_g, avg_l = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (period - 1) + max(d, 0)) / period
        avg_l = (avg_l * (period - 1) + max(-d, 0)) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100.0 - 100.0 / (1 + rs)


def adx(candles: Sequence[Candle], period: int = 14) -> Optional[float]:
    """Wilder's ADX of the latest bar."""
    n = len(candles)
    if n < period * 2 + 1:
        return None
    plus_dm, minus_dm = [], []
    for i in range(1, n):
        up = candles[i].high - candles[i - 1].high
        down = candles[i - 1].low - candles[i].low
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    trs = true_ranges(candles)[1:]

    def smooth(xs: list[float]) -> list[float]:
        s = sum(xs[:period])
        out = [s]
        for x in xs[period:]:
            s = s - s / period + x
            out.append(s)
        return out

    tr_s, p_s, m_s = smooth(trs), smooth(plus_dm), smooth(minus_dm)
    dxs = []
    for tr_v, p_v, m_v in zip(tr_s, p_s, m_s):
        if tr_v == 0:
            dxs.append(0.0)
            continue
        pdi, mdi = 100 * p_v / tr_v, 100 * m_v / tr_v
        dxs.append(0.0 if pdi + mdi == 0 else 100 * abs(pdi - mdi) / (pdi + mdi))
    if len(dxs) < period:
        return None
    value = sum(dxs[:period]) / period
    for dx in dxs[period:]:
        value = (value * (period - 1) + dx) / period
    return value


def macd_hist(closes: Sequence[float], fast: int = 12, slow: int = 26,
              signal: int = 9) -> Optional[float]:
    ef, es = ema(closes, fast), ema(closes, slow)
    line = [f - s for f, s in zip(ef, es) if f is not None and s is not None]
    sig = ema(line, signal)
    if not line or sig[-1] is None:
        return None
    return line[-1] - sig[-1]


def bollinger_width(closes: Sequence[float], period: int = 20, k: float = 2.0) -> Optional[float]:
    """(upper - lower) / middle of the latest bar."""
    if len(closes) < period:
        return None
    window = closes[-period:]
    mean = sum(window) / period
    if mean == 0:
        return None
    sd = math.sqrt(sum((x - mean) ** 2 for x in window) / period)
    return (2 * k * sd) / mean


def zscore(values: Sequence[float], period: int = 20) -> Optional[float]:
    if len(values) < period:
        return None
    window = values[-period:]
    mean = sum(window) / period
    sd = math.sqrt(sum((x - mean) ** 2 for x in window) / period)
    if sd == 0:
        return 0.0
    return (values[-1] - mean) / sd


def swing_points(candles: Sequence[Candle], strength: int = 3) -> tuple[list[int], list[int]]:
    """Indices of swing highs and swing lows (fractals of `strength` bars each side)."""
    highs, lows = [], []
    for i in range(strength, len(candles) - strength):
        h, lo = candles[i].high, candles[i].low
        left, right = candles[i - strength:i], candles[i + 1:i + 1 + strength]
        if all(h > c.high for c in left) and all(h >= c.high for c in right):
            highs.append(i)
        if all(lo < c.low for c in left) and all(lo <= c.low for c in right):
            lows.append(i)
    return highs, lows


def pct_rank(values: Sequence[float], value: float) -> float:
    """Fraction of `values` below `value` (0..1)."""
    if not values:
        return 0.5
    return sum(1 for v in values if v < value) / len(values)


def donchian(candles: Sequence[Candle], period: int) -> Optional[tuple[float, float]]:
    """(highest high, lowest low) of the `period` bars BEFORE the latest one.

    The latest bar is left out so "close above the channel" means a break of
    the channel as it stood when the bar opened (the Turtle rule).
    """
    if len(candles) < period + 1:
        return None
    window = candles[-period - 1:-1]
    return max(c.high for c in window), min(c.low for c in window)


def bollinger_bands(closes: Sequence[float], period: int = 20,
                    k: float = 2.0) -> Optional[tuple[float, float, float]]:
    """(lower, middle, upper) of the latest bar, population standard deviation."""
    if len(closes) < period:
        return None
    window = closes[-period:]
    mean = sum(window) / period
    sd = math.sqrt(sum((x - mean) ** 2 for x in window) / period)
    return mean - k * sd, mean, mean + k * sd


def supertrend(candles: Sequence[Candle], period: int = 10,
               mult: float = 3.0) -> list[tuple[Optional[float], int]]:
    """(line, direction) per bar: direction 1 = up (line below price), -1 = down.

    The standard definition: ATR (Wilder) bands around (high + low) / 2, each
    band only allowed to move in the trend's favour, and the direction flips
    when a close crosses the active band. Bars before the first ATR are
    `(None, 0)`.
    """
    n = len(candles)
    out: list[tuple[Optional[float], int]] = [(None, 0)] * n
    if n < period + 1:
        return out
    trs = true_ranges(candles)
    atr_v = sum(trs[1:period + 1]) / period
    upper = lower = 0.0
    direction = 1
    for i in range(period, n):
        if i > period:
            atr_v = (atr_v * (period - 1) + trs[i]) / period
        c = candles[i]
        mid = (c.high + c.low) / 2
        basic_up, basic_lo = mid + mult * atr_v, mid - mult * atr_v
        prev_close = candles[i - 1].close
        if i == period:
            upper, lower = basic_up, basic_lo
            direction = 1 if c.close >= mid else -1
        else:
            upper = basic_up if basic_up < upper or prev_close > upper else upper
            lower = basic_lo if basic_lo > lower or prev_close < lower else lower
            if direction == -1 and c.close > upper:
                direction = 1
            elif direction == 1 and c.close < lower:
                direction = -1
        out[i] = (lower if direction == 1 else upper, direction)
    return out
