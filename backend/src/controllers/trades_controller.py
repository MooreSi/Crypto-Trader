"""Trades page: open trades, history, audit trail, gate decisions, manual close."""
from __future__ import annotations

from backend.src.services.positions import trades_repo_view
from backend.src.services.trading import manual


def open_trades() -> list[dict]:
    return trades_repo_view.open_trades()


def history(limit: int, offset: int) -> list[dict]:
    return trades_repo_view.history(limit, offset)


def trade_events(trade_id: int) -> list[dict]:
    return trades_repo_view.events_for(trade_id)


def gate_decisions(limit: int) -> list[dict]:
    return trades_repo_view.recent_gate_decisions(limit)


def stats() -> dict:
    return trades_repo_view.stats()


def close(trade_id: int) -> bool:
    return manual.close(trade_id)
