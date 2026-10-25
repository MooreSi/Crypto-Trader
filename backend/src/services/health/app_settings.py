"""App-level settings the dashboard can change: network, account, API key, admin console.

A network change is written to config.yaml and takes effect on restart: the
main database, the engines' research databases and the exchange client are
all chosen by network at startup, and swapping them under running loops is
the kind of cleverness that loses a trade record.
"""
from __future__ import annotations

import re

from backend.src import config
from backend.src.config import secrets
from backend.src.services.exchange import provider
from backend.src.services.notify import notifier

_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


def get() -> dict:
    running = config.get("network")
    stored = config.stored().get("network", running)
    return {
        "network": running,
        "network_on_restart": stored if stored in config.NETWORKS else running,
        "networks": list(config.NETWORKS),
        "account_address": config.get("account_address", ""),
        "has_agent_key": {n: secrets.has_agent_key(n) for n in ("testnet", "mainnet")},
        "admin_console_enabled": bool(config.get("admin_console_enabled", True)),
        "admin_console_nickname": config.get("admin_console_nickname", ""),
        "paper_starting_balance": config.get("paper_starting_balance"),
        "dashboard_port": config.get("dashboard_port"),
        "data_dir": str(config.USER_DATA_DIR),
        "telegram_enabled": bool(config.get("telegram_enabled", False)),
        "telegram_chat_id": str(config.get("telegram_chat_id", "") or ""),
        "has_telegram_token": secrets.get_telegram_token() is not None,
    }


def set_network(network: str) -> dict:
    if network not in config.NETWORKS:
        raise ValueError(f"network must be one of {config.NETWORKS}")
    config.write_yaml({"network": network}, reload=False)
    return get()


def set_account_address(address: str) -> dict:
    address = address.strip()
    if address and not _ADDRESS.match(address):
        raise ValueError("an account address is 0x followed by 40 hex characters")
    config.save_to_yaml({"account_address": address})
    provider.reset()
    return get()


def set_agent_key(network: str, key: str) -> dict:
    if network not in ("testnet", "mainnet"):
        raise ValueError("API wallet keys are stored for testnet or mainnet")
    secrets.set_agent_key(network, key)
    provider.reset()
    return get()


def clear_agent_key(network: str) -> dict:
    secrets.clear_agent_key(network)
    provider.reset()
    return get()


def set_admin_console(enabled: bool, nickname: str) -> dict:
    config.save_to_yaml({"admin_console_enabled": bool(enabled),
                         "admin_console_nickname": nickname.strip()[:40]})
    return get()



def set_telegram(enabled: bool, chat_id: str, token: str) -> dict:
    """Trade alerts. A blank token keeps the stored one."""
    chat_id = chat_id.strip()
    if chat_id and not chat_id.lstrip("-").isdigit():
        raise ValueError("a Telegram chat id is a number (send /start to @userinfobot to find it)")
    if token.strip():
        secrets.set_telegram_token(token)
    config.save_to_yaml({"telegram_enabled": bool(enabled), "telegram_chat_id": chat_id})
    return get()


def test_telegram() -> dict:
    notifier.send_test()
    return {"sent": True}
