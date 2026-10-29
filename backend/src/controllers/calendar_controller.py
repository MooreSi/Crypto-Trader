"""Calendar page: closed trades by day, the day's events, the day journal.
Nothing here trades."""
from __future__ import annotations

from typing import Optional

from backend.src.services.calendar import calendar_view, journal


def trades(days: int) -> dict:
    return calendar_view.closed_trades(days)


def events(start: str, end: str) -> list[dict]:
    return calendar_view.events_between(start, end)


def journal_between(start: str, end: str) -> list[dict]:
    return journal.between(start, end)


def save_journal(day: str, note: str, tags: list[str], mood: Optional[int]) -> Optional[dict]:
    return journal.save(day, note, tags, mood)
