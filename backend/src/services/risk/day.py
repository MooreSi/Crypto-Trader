"""The trading day, for a market that never closes: 00:00 to 24:00 UTC.

The daily loss limit and the daily profit target both reset at midnight
UTC. The equity at the first check of each day is remembered so the loss
limit is a fraction of where the day started, not of a balance that has
already fallen.
"""
from __future__ import annotations

from datetime import datetime, timezone

from backend.src.db import database
from backend.src.utils import clock


def start_ts() -> float:
    now = clock.utcnow()
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp()


def _key() -> str:
    return "day_start_equity:" + clock.utcnow().strftime("%Y-%m-%d")


def start_equity(current_equity: float) -> float:
    """Equity at the start of today (UTC); records it on the first call of the day.

    A $0 reading (an unfunded or just-changed account) is not recorded: as the
    start it would put the loss-limit floor at $0 for the rest of the day."""
    raw = database.get_app_config(_key())
    if raw is not None:
        return float(raw)
    if current_equity <= 0:
        return float(current_equity)
    database.set_app_config(_key(), repr(float(current_equity)))
    return float(current_equity)
