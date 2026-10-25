"""Telegram: turn a trade event into one line and send it to the owner's chat.

Uses the Bot API's `sendMessage` (https://core.telegram.org/bots/api). The bot
token lives in the OS keyring (config/secrets.py), never in config.yaml, a
log line or a message. Text is plain (no parse mode), so a coin name or a
reason can never break the formatting.
"""
from __future__ import annotations

from typing import Optional

import httpx

API = "https://api.telegram.org"
TIMEOUT_S = 10.0


def _p(x) -> str:
    return f"{float(x):.6g}" if x is not None else "-"


def _money(x) -> str:
    return f"{float(x or 0.0):+.2f}"


def format_event(trade: dict, ev: dict) -> Optional[str]:
    """One message per event worth a phone buzz, or None for bookkeeping noise."""
    d, kind = ev.get("detail") or {}, ev["kind"]
    tag = f"[{str(trade.get('network') or '').upper()}]"
    who = f"#{trade['id']} {trade['direction']} {trade['coin']}"
    if kind == "opened":
        return (f"{tag} OPENED {who} @ {_p(d.get('fill'))} size {_p(d.get('size'))}, "
                f"risk ${float(d.get('risk_usd') or 0):.2f} ({trade.get('engine')})")
    if kind == "partial":
        return (f"{tag} {d.get('reason') or 'Partial'} {who}: closed {_p(d.get('size'))} "
                f"@ {_p(d.get('price'))}, P&L {_money((d.get('pnl') or 0) - (d.get('fee') or 0))}")
    if kind == "stop_moved":
        if d.get("from") == d.get("to"):
            return None
        return f"{tag} Stop moved {who}: {_p(d.get('from'))} -> {_p(d.get('to'))} ({d.get('reason')})"
    if kind in ("closed", "reconciled"):
        return (f"{tag} CLOSED {who} @ {_p(d.get('price'))}: {d.get('reason')}, "
                f"P&L {_money((d.get('pnl') or 0) - (d.get('fee') or 0))}")
    return None


def send(token: str, chat_id: str, text: str) -> None:
    """Send one message; raises on any failure so the caller can retry later."""
    r = httpx.post(f"{API}/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text},
                   timeout=TIMEOUT_S)
    if r.status_code != 200 or not r.json().get("ok"):
        # The URL holds the token: report the status only.
        raise RuntimeError(f"telegram refused the message (HTTP {r.status_code})")
