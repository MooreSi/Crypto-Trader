"""SQL for an engine's own signal database.

Each engine opens its OWN file (`breakout.db`, `reversal.db`, `trend_pa.db`)
through its own `SignalStore`. The class is shared; the data never is. Two
engines never read each other's rows, so one engine's labels can never leak
into another's model.

`live_status` uses ONE vocabulary for every engine: `executed`,
`refused:<reason>`, or NULL (virtual only). FOREX Trader's two engines used
two different words for "this one traded" and a query copied between them
matched zero rows for months (its bugs/062). Here the words are constants.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from backend.src.db.connection import Database
from backend.src.services.engines.base import Signal

LIVE_EXECUTED = "executed"
LIVE_REFUSED = "refused"

MIGRATIONS = (
    """CREATE TABLE signals (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at  REAL NOT NULL,
        coin        TEXT NOT NULL,
        interval    TEXT NOT NULL,
        direction   TEXT NOT NULL,
        entry       REAL NOT NULL,
        stop        REAL NOT NULL,
        reason      TEXT NOT NULL DEFAULT '',
        features    TEXT NOT NULL,
        ml_score    REAL,
        status      TEXT NOT NULL DEFAULT 'tracking'
                    CHECK (status IN ('tracking','win','loss','expired')),
        label       INTEGER,
        r_final     REAL,
        mfe_r       REAL,
        mae_r       REAL,
        resolved_at REAL,
        live_status TEXT,
        trade_id    INTEGER
    )""",
    "CREATE INDEX idx_signals_status ON signals(status)",
    "CREATE INDEX idx_signals_coin ON signals(coin, created_at)",
)


class SignalStore:
    def __init__(self, path: Path) -> None:
        self.db = Database(path, MIGRATIONS)

    def close(self) -> None:
        self.db.close()

    def insert(self, sig: Signal) -> int:
        return self.db.execute(
            "INSERT INTO signals(created_at, coin, interval, direction, entry, stop, reason, "
            "features, ml_score) VALUES(?,?,?,?,?,?,?,?,?)",
            (sig.created_at, sig.coin, sig.interval, sig.direction, sig.entry, sig.stop,
             sig.reason, json.dumps(sig.features), sig.ml_score))

    def exists_since(self, coin: str, direction: str, since_ts: float) -> bool:
        return self.db.query_one(
            "SELECT 1 FROM signals WHERE coin = ? AND direction = ? AND created_at >= ?",
            (coin, direction, since_ts)) is not None

    def tracking(self) -> list[dict]:
        return self.db.query("SELECT * FROM signals WHERE status = 'tracking' ORDER BY id")

    def resolve(self, signal_id: int, status: str, label: int, r_final: float,
                mfe_r: float, mae_r: float, resolved_at: float) -> None:
        self.db.execute(
            "UPDATE signals SET status=?, label=?, r_final=?, mfe_r=?, mae_r=?, resolved_at=? "
            "WHERE id = ?", (status, label, r_final, mfe_r, mae_r, resolved_at, signal_id))

    def update_excursion(self, signal_id: int, mfe_r: float, mae_r: float) -> None:
        self.db.execute("UPDATE signals SET mfe_r=?, mae_r=? WHERE id = ?",
                        (mfe_r, mae_r, signal_id))

    def set_live(self, signal_id: int, live_status: str, trade_id: Optional[int]) -> None:
        self.db.execute("UPDATE signals SET live_status=?, trade_id=? WHERE id = ?",
                        (live_status, trade_id, signal_id))

    def labelled(self) -> list[tuple[float, dict, int]]:
        rows = self.db.query(
            "SELECT created_at, features, label FROM signals WHERE label IS NOT NULL "
            "ORDER BY created_at")
        return [(r["created_at"], json.loads(r["features"]), int(r["label"])) for r in rows]

    def recent(self, limit: int = 100) -> list[dict]:
        rows = self.db.query("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,))
        for r in rows:
            r.pop("features", None)
        return rows

    def stats(self) -> dict:
        row = self.db.query_one(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status='tracking' THEN 1 ELSE 0 END) AS tracking, "
            "SUM(CASE WHEN status='win' THEN 1 ELSE 0 END) AS wins, "
            "SUM(CASE WHEN status='loss' THEN 1 ELSE 0 END) AS losses, "
            "SUM(CASE WHEN status='expired' THEN 1 ELSE 0 END) AS expired, "
            "AVG(r_final) AS avg_r, "
            "SUM(CASE WHEN live_status = ? THEN 1 ELSE 0 END) AS executed "
            "FROM signals", (LIVE_EXECUTED,))
        return {k: (v or 0) for k, v in (row or {}).items()}
