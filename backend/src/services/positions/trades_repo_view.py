"""Read-only trade queries for the dashboard, with stats derived from them.

The controller layer may not import a repo, so the dashboard reads trades
through this service, which adds what a page needs (win rate, R achieved)
and nothing that writes.
"""
from __future__ import annotations

from backend.src import config
from backend.src.services.positions import analytics as perf
from backend.src.services.positions import trades_repo
from backend.src.utils import clock


def _with_r(t: dict) -> dict:
    risk = t.get("risk_usd") or 0.0
    net = (t.get("realised_pnl") or 0.0) - (t.get("fees") or 0.0)
    return t | {"net_pnl": net, "r_achieved": net / risk if risk else None}


def open_trades() -> list[dict]:
    return [_with_r(t) for t in trades_repo.open_trades()]


def history(limit: int, offset: int) -> list[dict]:
    return [_with_r(t) for t in trades_repo.history(limit, offset)]


def events_for(trade_id: int) -> list[dict]:
    return trades_repo.events_for(trade_id)


def recent_gate_decisions(limit: int) -> list[dict]:
    return trades_repo.recent_gate_decisions(limit)


def stats() -> dict:
    s = trades_repo.closed_stats()
    n = s.get("n") or 0
    return {"closed": n, "net_pnl": s.get("pnl") or 0.0,
            "win_rate": (s.get("wins") or 0) / n if n else None}


def analytics() -> dict:
    """Performance over every closed trade and the last year of equity."""
    return perf.compute(trades_repo.history(5000, 0), trades_repo.equity_curve(clock.now() - 365 * 86400,
                                                                     config.account_key()))
