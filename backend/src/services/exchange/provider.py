"""Which exchange the app talks to, chosen once from the configured network.

`paper` reads mainnet market data with no key and simulates the account.
`testnet` and `mainnet` read and trade the real Hyperliquid endpoints with
the API wallet key stored for that network.

`set_for_tests` exists so the suite can install a fake. Nothing in the app
calls it; tests/conftest.py also replaces the SDK's `Exchange` constructor
with one that raises, so a test that reached the real signing path would fail
loudly instead of signing anything.
"""
from __future__ import annotations

import threading
from typing import Optional

from backend.src import config
from backend.src.config import secrets
from backend.src.services.exchange.types import ExchangeClient

_lock = threading.Lock()
_client: Optional[ExchangeClient] = None


def build(network: str) -> ExchangeClient:
    from backend.src.services.exchange.hyperliquid_client import HyperliquidClient
    if network == "paper":
        from backend.src.services.exchange.paper_exchange import PaperExchange
        source = HyperliquidClient("mainnet", "", None)
        return PaperExchange(source, float(config.get("paper_starting_balance", 10_000.0)))
    return HyperliquidClient(network, str(config.get("account_address", "")),
                             secrets.get_agent_key(network))


def get() -> ExchangeClient:
    global _client
    with _lock:
        if _client is None:
            _client = build(str(config.get("network", "paper")))
        return _client


def reset() -> None:
    """Drop the cached client so the next `get()` rebuilds it (network or key changed)."""
    global _client
    with _lock:
        _client = None


def set_for_tests(client: Optional[ExchangeClient]) -> None:
    global _client
    with _lock:
        _client = client
