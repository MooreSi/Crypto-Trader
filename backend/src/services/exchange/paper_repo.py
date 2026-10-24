"""Persistence for the paper account: one JSON blob in the main database."""
from __future__ import annotations

import json
from typing import Optional

from backend.src.db import database

_KEY = "paper_state"


def load() -> Optional[dict]:
    raw = database.get_app_config(_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def save(state: dict) -> None:
    database.set_app_config(_KEY, json.dumps(state))
