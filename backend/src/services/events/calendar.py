"""The event calendar: what is coming, and whether it blocks a new trade now.

Four sources, merged into the `events` table:

1. US macro releases (macro_feed.py, live feed),
2. options expiries, CME weekend gap and FOMC fallback (recurring.py),
3. **your own events** -- token unlocks, listings, network upgrades,
   exchange maintenance -- added from the Events page, optionally tied to
   specific coins.

`blackout(coin)` is what the risk gates ask. A **high**-impact event blocks
new automated entries from `blackout_minutes_before` to
`blackout_minutes_after` around it; **medium** does too when
`blackout_include_medium` is on. An event with coins blocks only those coins;
one without (macro) blocks every coin. Open positions are never touched by
a blackout; only new entries are refused.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from typing import Optional

from backend.src.services.events import events_repo, macro_feed, recurring
from backend.src.utils import clock

log = logging.getLogger(__name__)

IMPACTS = ("low", "medium", "high")
USER_KINDS = ("token_unlock", "listing", "upgrade", "maintenance", "other")


def refresh(fetch_macro: bool = True) -> int:
    """Regenerate the timetable and, when due, pull the macro feed."""
    events = recurring.generate(clock.utcnow() - timedelta(days=1), days=21)
    if fetch_macro and macro_feed.due():
        events += macro_feed.fetch()
    return events_repo.upsert_many(events)


def upcoming(days: int = 7, past_hours: int = 6) -> list[dict]:
    now = clock.now()
    return events_repo.between(now - past_hours * 3600, now + days * 86400)


def add_user_event(ts: float, title: str, impact: str, kind: str = "other",
                   coins: Optional[list[str]] = None) -> dict:
    if impact not in IMPACTS:
        raise ValueError(f"impact must be one of {IMPACTS}")
    if kind not in USER_KINDS:
        raise ValueError(f"kind must be one of {USER_KINDS}")
    title = title.strip()
    if not title:
        raise ValueError("title is required")
    coin_str = ",".join(sorted({c.strip().upper() for c in coins or [] if c.strip()}))
    uid = "user:" + hashlib.sha1(f"{ts}:{title}:{coin_str}".encode()).hexdigest()[:16]
    event = {"uid": uid, "ts": float(ts), "title": title, "kind": kind, "impact": impact,
             "coins": coin_str, "source": "user"}
    events_repo.upsert_many([event])
    return event


def delete_user_event(event_id: int) -> bool:
    return events_repo.delete_user_event(event_id)


def _applies(event: dict, coin: str) -> bool:
    coins = [c for c in (event.get("coins") or "").split(",") if c]
    return not coins or coin.upper() in coins


def blackout(coin: str, settings: dict) -> Optional[dict]:
    """The event blocking a new `coin` entry right now, or None."""
    if not settings.get("blackout_enabled", True):
        return None
    before = float(settings.get("blackout_minutes_before", 30)) * 60
    after = float(settings.get("blackout_minutes_after", 30)) * 60
    impacts = {"high"} | ({"medium"} if settings.get("blackout_include_medium") else set())
    now = clock.now()
    for e in events_repo.between(now - after, now + before):
        if e["impact"] in impacts and _applies(e, coin) and e["kind"] != "cme_gap":
            return e
    return None


def proximity_hours(coin: str, horizon_h: float = 48.0) -> float:
    """Hours to the nearest high-impact event for `coin` (capped at horizon). ML feature."""
    now = clock.now()
    rows = events_repo.between(now - 3600, now + horizon_h * 3600)
    hours = [abs(e["ts"] - now) / 3600 for e in rows if e["impact"] == "high" and _applies(e, coin)]
    return min(hours) if hours else horizon_h
