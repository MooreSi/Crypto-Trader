"""Events page: the calendar and your own events."""
from __future__ import annotations

from backend.src.services.events import calendar


def upcoming(days: int) -> list[dict]:
    return calendar.upcoming(days)


def add(ts: float, title: str, impact: str, kind: str, coins: list[str]) -> dict:
    return calendar.add_user_event(ts, title, impact, kind, coins)


def delete(event_id: int) -> bool:
    return calendar.delete_user_event(event_id)


def refresh() -> int:
    return calendar.refresh()


def kinds() -> dict:
    return {"impacts": list(calendar.IMPACTS), "kinds": list(calendar.USER_KINDS)}
