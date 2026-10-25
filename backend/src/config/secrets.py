"""The API wallet's private key: stored in the OS keyring, nowhere else.

Hyperliquid lets an account approve an **API wallet** (an "agent") that may
place and cancel orders but can never withdraw. This app only ever holds an
agent key. The account's own key -- the one that can move funds -- must never
be entered here, and the Settings page says so.

Keyring service names are this app's own (`CryptoTrader`), so FOREX Trader's
stored credentials are never read or overwritten.

One key per network: a testnet agent and a mainnet agent are different
wallets, and keeping them apart means switching network can never sign a
mainnet order with a key the owner thought was for testing.
"""
from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

SERVICE = "CryptoTrader"


def _username(network: str) -> str:
    return f"hyperliquid_agent_key_{network}"


def _keyring():
    import keyring
    return keyring


def get_agent_key(network: str) -> Optional[str]:
    try:
        return _keyring().get_password(SERVICE, _username(network)) or None
    except Exception as exc:
        log.warning("[Secrets] keyring read failed: %s", exc)
        return None


def set_agent_key(network: str, key: str) -> None:
    key = key.strip()
    if key.startswith("0x"):
        key = key[2:]
    if len(key) != 64 or any(c not in "0123456789abcdefABCDEF" for c in key):
        raise ValueError("an API wallet private key is 64 hex characters")
    _keyring().set_password(SERVICE, _username(network), "0x" + key.lower())


def clear_agent_key(network: str) -> None:
    try:
        _keyring().delete_password(SERVICE, _username(network))
    except Exception:
        pass


def has_agent_key(network: str) -> bool:
    return get_agent_key(network) is not None


# ── Telegram bot token (trade alerts) ────────────────────────────────────────
# Not a trading credential, but anyone holding it can post as the bot, so it
# lives in the keyring too, never in config.yaml.
_TELEGRAM = "telegram_bot_token"


def get_telegram_token() -> Optional[str]:
    try:
        return _keyring().get_password(SERVICE, _TELEGRAM) or None
    except Exception as exc:
        log.warning("[Secrets] keyring read failed: %s", exc)
        return None


def set_telegram_token(token: str) -> None:
    token = token.strip()
    if ":" not in token or len(token) < 20 or any(c.isspace() for c in token):
        raise ValueError("a Telegram bot token looks like 123456789:AA... (from @BotFather)")
    _keyring().set_password(SERVICE, _TELEGRAM, token)


def clear_telegram_token() -> None:
    try:
        _keyring().delete_password(SERVICE, _TELEGRAM)
    except Exception:
        pass
