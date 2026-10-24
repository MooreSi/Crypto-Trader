"""SQL for the events table (main database)."""
from __future__ import annotations

from typing import Optional

from backend.src.db import database


def upsert_many(events: list[dict]) -> int:
    db = database.get()
    with db.transaction():
        for e in events:
            db.execute(
                "INSERT INTO events(uid, ts, title, kind, impact, coins, source) "
                "VALUES(?,?,?,?,?,?,?) ON CONFLICT(uid) DO UPDATE SET ts=excluded.ts, "
                "title=excluded.title, impact=excluded.impact, coins=excluded.coins",
                (e["uid"], e["ts"], e["title"], e["kind"], e["impact"], e["coins"], e["source"]),
            )
    return len(events)


def between(start_ts: float, end_ts: float) -> list[dict]:
    return database.get().query(
        "SELECT * FROM events WHERE ts BETWEEN ? AND ? ORDER BY ts", (start_ts, end_ts))


def get(event_id: int) -> Optional[dict]:
    return database.get().query_one("SELECT * FROM events WHERE id = ?", (event_id,))


def delete_user_event(event_id: int) -> bool:
    return database.get().execute(
        "DELETE FROM events WHERE id = ? AND source = 'user'", (event_id,)) > 0
