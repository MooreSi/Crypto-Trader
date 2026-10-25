"""Trade alerts: forward new `trade_events` rows to Telegram, in order, once.

Runs after every positions pass. It reads the audit trail that every money
change already writes in the same transaction as the change, so alerts need
no hook in the order path and can never delay or alter an order.

* **Cursor** -- the id of the last event sent, in app_config. The first pass
  after alerts are switched on sets it to the newest event and sends nothing:
  switching on must not replay months of history.
* **At least once** -- the cursor moves only after a send succeeds; a failed
  send stops the pass and the same event is tried again next pass.
* **Off** unless enabled with a chat id and a bot token in the keyring.
"""
from __future__ import annotations

import logging
from typing import Optional

from backend.src import config
from backend.src.config import secrets
from backend.src.db import database
from backend.src.services.notify import telegram
from backend.src.services.positions import trades_repo

log = logging.getLogger(__name__)

CURSOR_KEY = "telegram_last_event_id"
BATCH = 20


def _credentials() -> Optional[tuple[str, str]]:
    if not config.get("telegram_enabled", False):
        return None
    chat = str(config.get("telegram_chat_id", "") or "").strip()
    token = secrets.get_telegram_token()
    return (token, chat) if token and chat else None


def notify_pass() -> int:
    """Send what is new; returns how many messages went out."""
    creds = _credentials()
    if creds is None:
        return 0
    raw = database.get_app_config(CURSOR_KEY)
    if raw is None:
        database.set_app_config(CURSOR_KEY, str(trades_repo.last_event_id()))
        return 0
    cursor, sent = int(raw), 0
    for ev in trades_repo.events_after(cursor, BATCH):
        trade = {"id": ev["trade_id"], "coin": ev["coin"], "direction": ev["direction"],
                 "engine": ev["engine"], "network": ev["network"]}
        text = telegram.format_event(trade, ev)
        if text:
            try:
                telegram.send(creds[0], creds[1], text)
            except Exception as exc:
                log.warning("[Notify] telegram send failed, will retry: %s", exc)
                break
            sent += 1
        database.set_app_config(CURSOR_KEY, str(ev["id"]))
    return sent


def send_test() -> None:
    """A test message, so the Settings page can prove the token and chat work."""
    token = secrets.get_telegram_token()
    chat = str(config.get("telegram_chat_id", "") or "").strip()
    if not token or not chat:
        raise ValueError("store a bot token and a chat id first")
    telegram.send(token, chat, f"Crypto Trader ({config.get('network')}) is connected. "
                               "Trade alerts will arrive here.")
