"""Risk page: every number that decides how much may be lost."""
from __future__ import annotations

from backend.src.services.risk import settings


def get() -> dict:
    return settings.get()


def defaults() -> dict:
    return settings.defaults()


def update(fields: dict) -> dict:
    return settings.update(fields)
