"""The main database: trades, their audit trail, gate decisions, events, config.

One file per network (`crypto_trader_<network>.db`), opened by `init()`.
Each engine keeps its own separate database for its signals and models --
see the engines domain README -- so nothing here belongs to an engine.

The schema lives here and nowhere else. Repos (`services/**/*_repo.py`) hold
the SQL that reads and writes it.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from backend.src.db.connection import Database

MIGRATIONS: tuple[str, ...] = (
    """CREATE TABLE app_config (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
    """CREATE TABLE trades (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        engine         TEXT NOT NULL,
        coin           TEXT NOT NULL,
        direction      TEXT NOT NULL CHECK (direction IN ('long','short')),
        status         TEXT NOT NULL CHECK (status IN ('open','closed')),
        network        TEXT NOT NULL,
        signal_id      INTEGER,
        entry_price    REAL NOT NULL,
        size           REAL NOT NULL,
        initial_size   REAL NOT NULL,
        stop_loss      REAL NOT NULL,
        initial_stop   REAL NOT NULL,
        take_profits   TEXT NOT NULL,
        tp_hit         INTEGER NOT NULL DEFAULT 0,
        leverage       INTEGER NOT NULL,
        risk_usd       REAL NOT NULL,
        sl_oid         INTEGER,
        tp_oids        TEXT NOT NULL DEFAULT '[]',
        opened_at      REAL NOT NULL,
        closed_at      REAL,
        close_price    REAL,
        close_reason   TEXT,
        realised_pnl   REAL NOT NULL DEFAULT 0,
        fees           REAL NOT NULL DEFAULT 0
    )""",
    "CREATE INDEX idx_trades_status ON trades(status)",
    """CREATE TABLE trade_events (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id  INTEGER NOT NULL REFERENCES trades(id),
        ts        REAL NOT NULL,
        kind      TEXT NOT NULL,
        detail    TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE gate_decisions (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        REAL NOT NULL,
        engine    TEXT NOT NULL,
        coin      TEXT NOT NULL,
        direction TEXT NOT NULL,
        signal_id INTEGER,
        passed    INTEGER NOT NULL,
        decisions TEXT NOT NULL
    )""",
    """CREATE TABLE events (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        uid       TEXT NOT NULL UNIQUE,
        ts        REAL NOT NULL,
        title     TEXT NOT NULL,
        kind      TEXT NOT NULL,
        impact    TEXT NOT NULL CHECK (impact IN ('low','medium','high')),
        coins     TEXT NOT NULL DEFAULT '',
        source    TEXT NOT NULL
    )""",
    "CREATE INDEX idx_events_ts ON events(ts)",
    """CREATE TABLE equity_snapshots (
        ts      REAL PRIMARY KEY,
        equity  REAL NOT NULL
    )""",
    # The account a snapshot was read from (config.account_key()); '' for rows
    # written before this column existed.
    "ALTER TABLE equity_snapshots ADD COLUMN account TEXT NOT NULL DEFAULT ''",
    # The Calendar's day journal: the owner's note on one UTC trading day, per
    # account (config.account_key()), so demo and live notes stay apart.
    """CREATE TABLE day_journal (
        account    TEXT NOT NULL,
        day        TEXT NOT NULL,
        note       TEXT NOT NULL DEFAULT '',
        tags       TEXT NOT NULL DEFAULT '[]',
        mood       INTEGER,
        updated_at REAL NOT NULL,
        PRIMARY KEY (account, day)
    )""",
)

_lock = threading.Lock()
_db: Optional[Database] = None


def init(path: Path) -> Database:
    """Open (and migrate) the main database. Closes any previous one first."""
    global _db
    with _lock:
        if _db is not None:
            _db.close()
        _db = Database(path, MIGRATIONS)
        return _db


def get() -> Database:
    if _db is None or _db.closed:
        raise RuntimeError("main database not initialised; call database.init()")
    return _db


def close() -> None:
    global _db
    with _lock:
        if _db is not None:
            _db.close()
            _db = None


def get_app_config(key: str) -> Optional[str]:
    row = get().query_one("SELECT value FROM app_config WHERE key = ?", (key,))
    return row["value"] if row else None


def set_app_config(key: str, value: str) -> None:
    get().execute(
        "INSERT INTO app_config(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
