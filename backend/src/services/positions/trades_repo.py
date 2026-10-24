"""SQL for trades and their audit trail (main database).

Every state change of a trade writes a `trade_events` row in the same
transaction, so any trade can be explained afterwards: why it opened, every
stop move, every partial, why it closed.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.src.db import database
from backend.src.utils import clock

_JSON_COLS = ("take_profits", "tp_oids")


def _decode(row: Optional[dict]) -> Optional[dict]:
    if row is None:
        return None
    for col in _JSON_COLS:
        row[col] = json.loads(row[col]) if row.get(col) else []
    return row


def insert(trade: dict, event_detail: dict) -> int:
    cols = ("engine", "coin", "direction", "status", "network", "signal_id", "entry_price",
            "size", "initial_size", "stop_loss", "initial_stop", "take_profits", "leverage",
            "risk_usd", "sl_oid", "tp_oids", "opened_at", "fees")
    values = [json.dumps(trade[c]) if c in _JSON_COLS else trade.get(c) for c in cols]
    db = database.get()
    with db.transaction():
        trade_id = db.execute(
            f"INSERT INTO trades({','.join(cols)}) VALUES({','.join('?' * len(cols))})", values)
        _event(trade_id, "opened", event_detail)
    return trade_id


def _event(trade_id: int, kind: str, detail: dict) -> None:
    database.get().execute(
        "INSERT INTO trade_events(trade_id, ts, kind, detail) VALUES(?,?,?,?)",
        (trade_id, clock.now(), kind, json.dumps(detail, default=str)))


def add_event(trade_id: int, kind: str, detail: dict) -> None:
    _event(trade_id, kind, detail)


def update(trade_id: int, fields: dict[str, Any], event_kind: str, detail: dict) -> None:
    allowed = {"size", "stop_loss", "tp_hit", "sl_oid", "tp_oids", "realised_pnl", "fees",
               "status", "closed_at", "close_price", "close_reason"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"not updatable: {sorted(bad)}")
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = [json.dumps(v) if k in _JSON_COLS else v for k, v in fields.items()]
    db = database.get()
    with db.transaction():
        db.execute(f"UPDATE trades SET {sets} WHERE id = ?", (*values, trade_id))
        _event(trade_id, event_kind, detail)


def get(trade_id: int) -> Optional[dict]:
    return _decode(database.get().query_one("SELECT * FROM trades WHERE id = ?", (trade_id,)))


def open_trades() -> list[dict]:
    rows = database.get().query("SELECT * FROM trades WHERE status = 'open' ORDER BY opened_at")
    return [_decode(r) for r in rows]


def open_for_coin(coin: str) -> Optional[dict]:
    return _decode(database.get().query_one(
        "SELECT * FROM trades WHERE status = 'open' AND coin = ?", (coin,)))


def history(limit: int = 200, offset: int = 0) -> list[dict]:
    rows = database.get().query(
        "SELECT * FROM trades ORDER BY opened_at DESC LIMIT ? OFFSET ?", (limit, offset))
    return [_decode(r) for r in rows]


def events_for(trade_id: int) -> list[dict]:
    rows = database.get().query(
        "SELECT ts, kind, detail FROM trade_events WHERE trade_id = ? ORDER BY id", (trade_id,))
    for r in rows:
        r["detail"] = json.loads(r["detail"])
    return rows


def realised_since(ts: float) -> float:
    """Net realised P&L booked at or after `ts`: every partial and final close.

    Read from the audit trail rather than the trades table, so a partial taken
    today on a trade opened yesterday counts today, and the final close of
    that trade counts only its own remainder. `opened` carries the entry fee;
    each `partial` / `closed` / `reconciled` event carries `{"pnl": gross,
    "fee": fee}` for exactly the size it closed.
    """
    row = database.get().query_one(
        "SELECT COALESCE(SUM(COALESCE(json_extract(detail, '$.pnl'), 0) "
        "- COALESCE(json_extract(detail, '$.fee'), 0)), 0) AS pnl FROM trade_events "
        "WHERE kind IN ('opened', 'partial', 'closed', 'reconciled') AND ts >= ?", (ts,))
    return float(row["pnl"]) if row else 0.0


def closed_stats() -> dict:
    row = database.get().query_one(
        "SELECT COUNT(*) AS n, COALESCE(SUM(realised_pnl - fees), 0) AS pnl, "
        "COALESCE(SUM(CASE WHEN realised_pnl - fees > 0 THEN 1 ELSE 0 END), 0) AS wins "
        "FROM trades WHERE status = 'closed'")
    return dict(row) if row else {"n": 0, "pnl": 0.0, "wins": 0}


def record_gate_decision(engine: str, coin: str, direction: str, signal_id: Optional[int],
                         passed: bool, decisions: list[dict]) -> None:
    database.get().execute(
        "INSERT INTO gate_decisions(ts, engine, coin, direction, signal_id, passed, decisions) "
        "VALUES(?,?,?,?,?,?,?)",
        (clock.now(), engine, coin, direction, signal_id, int(passed), json.dumps(decisions)))


def recent_gate_decisions(limit: int = 100) -> list[dict]:
    rows = database.get().query(
        "SELECT * FROM gate_decisions ORDER BY id DESC LIMIT ?", (limit,))
    for r in rows:
        r["decisions"] = json.loads(r["decisions"])
    return rows


def snapshot_equity(equity: float) -> None:
    database.get().execute(
        "INSERT OR REPLACE INTO equity_snapshots(ts, equity) VALUES(?, ?)", (clock.now(), equity))


def equity_curve(since_ts: float) -> list[dict]:
    return database.get().query(
        "SELECT ts, equity FROM equity_snapshots WHERE ts >= ? ORDER BY ts", (since_ts,))
