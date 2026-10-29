"""The day journal: the owner's note, tags and 1-5 mood for one trading day.

Words for review; nothing that trades reads them. Kept per account
(`config.account_key()`) so paper, testnet and mainnet notes never mix.
Saving a blank day (no note, no tags, no mood) clears it.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Optional

from backend.src import config
from backend.src.services.calendar import journal_repo
from backend.src.utils import clock

MAX_NOTE = 4000
MAX_TAGS = 10
MAX_TAG_LEN = 40


class BadJournalEntry(ValueError):
    pass


def _decode(row: dict) -> dict:
    return row | {"tags": json.loads(row["tags"] or "[]")}


def between(start: str, end: str) -> list[dict]:
    """Entries from `start` to `end` inclusive. Compared as strings, so an end
    of YYYY-MM-31 is a whole month for any month."""
    return [_decode(r) for r in journal_repo.between(config.account_key(), start, end)]


def save(day: str, note: str, tags: list[str], mood: Optional[int]) -> Optional[dict]:
    try:
        date.fromisoformat(day)
    except ValueError:
        raise BadJournalEntry(f"{day} is not a date") from None
    note = (note or "").strip()
    if len(note) > MAX_NOTE:
        raise BadJournalEntry(f"the note is longer than {MAX_NOTE} characters")
    clean = list(dict.fromkeys(t.strip() for t in tags if t and t.strip()))
    if len(clean) > MAX_TAGS:
        raise BadJournalEntry(f"at most {MAX_TAGS} tags")
    if any(len(t) > MAX_TAG_LEN for t in clean):
        raise BadJournalEntry(f"a tag is at most {MAX_TAG_LEN} characters")
    if mood is not None and not 1 <= mood <= 5:
        raise BadJournalEntry("mood is 1 to 5")
    account = config.account_key()
    if not note and not clean and mood is None:
        journal_repo.delete(account, day)
        return None
    now = clock.now()
    journal_repo.upsert(account, day, note, json.dumps(clean), mood, now)
    return {"day": day, "note": note, "tags": clean, "mood": mood, "updated_at": now}
