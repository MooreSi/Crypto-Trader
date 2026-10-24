"""The one place the app reads the time.

Every service that branches on the time of day takes it from here, so a test
can pin it (`set_fixed`) and mean the same thing on a Saturday night as on a
Tuesday afternoon. FOREX Trader learned this the expensive way: its session
gates passed all week and failed every weekend with no code change. Crypto
trades 24x7, but the schedule windows, the event blackouts and the daily
profit cap all still depend on the clock.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

_fixed: Optional[float] = None


def now() -> float:
    """Unix seconds."""
    return _fixed if _fixed is not None else time.time()


def now_ms() -> int:
    return int(now() * 1000)


def utcnow() -> datetime:
    return datetime.fromtimestamp(now(), tz=timezone.utc)


def set_fixed(ts: Optional[float]) -> None:
    """Pin the clock (tests only). None restores the real clock."""
    global _fixed
    _fixed = ts
