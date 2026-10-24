"""Dashboard-initiated actions on trades this app opened."""
from __future__ import annotations

from backend.src.services.exchange import provider
from backend.src.services.positions import trades_repo
from backend.src.services.trading import order_service


def close(trade_id: int) -> bool:
    trade = trades_repo.get(trade_id)
    if trade is None or trade["status"] != "open":
        raise ValueError(f"trade #{trade_id} is not open")
    return order_service.close_trade(provider.get(), trade, "closed from dashboard")
