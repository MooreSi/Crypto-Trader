"""Liquidity sessions for a market that never closes.

Crypto has no session open or close, but liquidity and volatility still
follow the clock: Asia, Europe and the US each bring their own volume, and
weekends are thinner. These are FEATURES for the engines, not gates -- the
app trades 24x7. (FOREX Trader's sessions gated trading entirely; that rule
was dropped on purpose for crypto. See docs/system/domains/market/README.md.)

All times UTC.
"""
from __future__ import annotations

from datetime import datetime

ASIA = (0, 8)
EUROPE = (7, 16)
US = (13, 21)


def _in(hour: int, window: tuple[int, int]) -> bool:
    return window[0] <= hour < window[1]


def session_flags(ts: datetime) -> dict[str, float]:
    h = ts.hour
    return {
        "sess_asia": float(_in(h, ASIA)),
        "sess_europe": float(_in(h, EUROPE)),
        "sess_us": float(_in(h, US)),
        "sess_overlap": float(_in(h, EUROPE) and _in(h, US)),
        "weekend": float(is_weekend(ts)),
    }


def is_weekend(ts: datetime) -> bool:
    """Saturday or Sunday UTC."""
    return ts.weekday() >= 5


def session_name(ts: datetime) -> str:
    h = ts.hour
    if _in(h, EUROPE) and _in(h, US):
        return "EU/US overlap"
    if _in(h, US):
        return "US"
    if _in(h, EUROPE):
        return "Europe"
    if _in(h, ASIA):
        return "Asia"
    return "Late US"
