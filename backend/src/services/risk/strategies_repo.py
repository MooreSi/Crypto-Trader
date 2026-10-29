"""Strategies persistence: one JSON blob in app_config."""
from __future__ import annotations

from typing import Optional

from backend.src.db import database

_KEY = "strategies"


def load() -> Optional[str]:
    return database.get_app_config(_KEY)


def save(blob: str) -> None:
    database.set_app_config(_KEY, blob)
