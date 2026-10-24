"""Pinned admin-server certificate fingerprints, per host (app_config)."""
from __future__ import annotations

from typing import Optional

from backend.src.db import database


def _key(host: str) -> str:
    return f"admin_pinned_fp_{host}"


def get(host: str) -> Optional[str]:
    return database.get_app_config(_key(host))


def set(host: str, fingerprint: str) -> None:  # noqa: A001 - mirrors get()
    database.set_app_config(_key(host), fingerprint)
