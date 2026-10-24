"""Settings page: network, Hyperliquid account, API wallet key, admin console."""
from __future__ import annotations

from backend.src.services.health import app_settings


def get() -> dict:
    return app_settings.get()


def set_network(network: str) -> dict:
    return app_settings.set_network(network)


def set_account_address(address: str) -> dict:
    return app_settings.set_account_address(address)


def set_agent_key(network: str, key: str) -> dict:
    return app_settings.set_agent_key(network, key)


def clear_agent_key(network: str) -> dict:
    return app_settings.clear_agent_key(network)


def set_admin_console(enabled: bool, nickname: str) -> dict:
    return app_settings.set_admin_console(enabled, nickname)
