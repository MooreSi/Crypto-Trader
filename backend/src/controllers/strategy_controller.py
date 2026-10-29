"""Strategy page: named sets of risk settings, one of them active."""
from __future__ import annotations

from backend.src.services.risk import strategies


def list_all() -> dict:
    strategies.ensure_default()
    return strategies.list_all()


def create(name: str, params: dict, notes: str) -> dict:
    return strategies.create(name, params, notes)


def update(sid: str, name: str, params: dict, notes: str) -> dict:
    return strategies.update(sid, name, params, notes)


def delete(sid: str) -> dict:
    strategies.delete(sid)
    return strategies.list_all()


def activate(sid: str) -> dict:
    return strategies.activate(sid)
