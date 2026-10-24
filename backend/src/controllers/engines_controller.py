"""Engines page: status, toggles, signals, retrain."""
from __future__ import annotations

from backend.src.services.engines import registry


def _engine(name: str):
    engines = registry.get()
    if name not in engines:
        raise KeyError(name)
    return engines[name]


def list_status() -> list[dict]:
    return [e.status() for e in registry.get().values()]


def set_enabled(name: str, on: bool) -> dict:
    _engine(name).set_enabled(on)
    return _engine(name).status()


def set_live(name: str, on: bool) -> dict:
    _engine(name).set_live(on)
    return _engine(name).status()


def signals(name: str, limit: int) -> list[dict]:
    return _engine(name).store.recent(limit)


def retrain(name: str) -> dict:
    return _engine(name).maybe_retrain(force=True) or {}
