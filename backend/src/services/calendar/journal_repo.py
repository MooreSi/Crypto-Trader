"""SQL for the Calendar's day journal (main database, table `day_journal`)."""
from __future__ import annotations

from typing import Optional

from backend.src.db import database


def between(account: str, start: str, end: str) -> list[dict]:
    return database.get().query(
        "SELECT day, note, tags, mood, updated_at FROM day_journal "
        "WHERE account = ? AND day >= ? AND day <= ? ORDER BY day", (account, start, end))


def upsert(account: str, day: str, note: str, tags: str, mood: Optional[int], ts: float) -> None:
    database.get().execute(
        "INSERT INTO day_journal(account, day, note, tags, mood, updated_at) "
        "VALUES(?, ?, ?, ?, ?, ?) ON CONFLICT(account, day) DO UPDATE SET "
        "note = excluded.note, tags = excluded.tags, mood = excluded.mood, "
        "updated_at = excluded.updated_at", (account, day, note, tags, mood, ts))


def delete(account: str, day: str) -> None:
    database.get().execute("DELETE FROM day_journal WHERE account = ? AND day = ?", (account, day))
