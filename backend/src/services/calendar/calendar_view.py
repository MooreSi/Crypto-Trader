"""The Calendar page's reads: closed trades filed by trading day, and the
events that fell on each day.

The trading day is the risk governor's (services/risk/day.py): 00:00 to
24:00 UTC. A trade belongs to the day it CLOSED on, whole, partials
included; the Trades page and the daily loss limit count partials on the
day they were booked, so a trade that took a partial before midnight and
closed after it shows its whole result on the later day here.
"""
from __future__ import annotations

import calendar as _cal
from datetime import date, datetime, timedelta, timezone

from backend.src.services.events import events_repo
from backend.src.services.market import sessions
from backend.src.services.positions import trades_repo
from backend.src.utils import clock

MAX_DAYS = 730


def _utc(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)


def _row(t: dict) -> dict:
    net = (t.get("realised_pnl") or 0.0) - (t.get("fees") or 0.0)
    risk = t.get("risk_usd") or 0.0
    closed = _utc(t["closed_at"])
    return {
        "id": t["id"], "engine": t["engine"], "coin": t["coin"], "direction": t["direction"],
        "opened_at": t["opened_at"], "closed_at": t["closed_at"],
        "day": closed.strftime("%Y-%m-%d"), "net_pnl": net, "fees": t.get("fees") or 0.0,
        "risk_usd": risk, "r": net / risk if risk else None,
        "close_reason": t.get("close_reason"), "session": sessions.session_name(closed),
    }


def closed_trades(days: int) -> dict:
    """Trades closed in the last `days` days, newest first, and today's date."""
    if not 1 <= days <= MAX_DAYS:
        raise ValueError(f"days must be 1 to {MAX_DAYS}")
    rows = trades_repo.closed_since(clock.now() - days * 86400)
    return {"today": clock.utcnow().strftime("%Y-%m-%d"), "rows": [_row(t) for t in rows]}


def _day(text: str) -> date:
    """YYYY-MM-DD, with a day past the month's end clamped to it (YYYY-MM-31)."""
    y, m, d = (int(p) for p in text.split("-"))
    return date(y, m, min(d, _cal.monthrange(y, m)[1]))


def events_between(start: str, end: str) -> list[dict]:
    """Events from the start of `start` to the end of `end`, UTC, each with its day."""
    first, last = _day(start), _day(end)
    if last < first:
        raise ValueError("end is before start")
    lo = datetime(first.year, first.month, first.day, tzinfo=timezone.utc).timestamp()
    hi = (datetime(last.year, last.month, last.day, tzinfo=timezone.utc)
          + timedelta(days=1)).timestamp()
    return [e | {"day": _utc(e["ts"]).strftime("%Y-%m-%d")}
            for e in events_repo.between(lo, hi) if e["ts"] < hi]
