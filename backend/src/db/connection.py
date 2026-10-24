"""One SQLite file, one connection, one lock.

Every database in this app (the main one and each engine's own) is a
`Database`. A single connection per file, shared across threads behind an
`RLock`, is deliberate: the app is one process with a handful of asyncio
tasks and worker threads, and SQLite serialises writers anyway. One handle
also means one thing to close -- which matters on Windows, where a file with
an open handle cannot be deleted (FOREX Trader's first Windows CI run produced
50 teardown errors from exactly that).

Schemas are lists of statements applied in order and tracked with
`PRAGMA user_version`. A migration is appended, never edited: an install
that already ran statement N must never see N change under it.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional, Sequence


class Database:
    def __init__(self, path: Path | str, migrations: Sequence[str] = ()) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = sqlite3.connect(
            str(self.path), check_same_thread=False, isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._migrate(migrations)

    # ── lifecycle ────────────────────────────────────────────────────────────
    def _migrate(self, migrations: Sequence[str]) -> None:
        with self._lock:
            current = self._conn.execute("PRAGMA user_version").fetchone()[0]
            for index, statement in enumerate(migrations, start=1):
                if index <= current:
                    continue
                self._conn.execute("BEGIN")
                try:
                    self._conn.execute(statement)  # one statement per migration
                    self._conn.execute(f"PRAGMA user_version = {index}")
                    self._conn.execute("COMMIT")
                except Exception:
                    self._conn.execute("ROLLBACK")
                    raise

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def closed(self) -> bool:
        return self._conn is None

    def _c(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError(f"database {self.path.name} is closed")
        return self._conn

    # ── queries ──────────────────────────────────────────────────────────────
    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        """Run one write; returns lastrowid (inserts) or rowcount."""
        with self._lock:
            cur = self._c().execute(sql, tuple(params))
            return cur.lastrowid if sql.lstrip().upper().startswith("INSERT") else cur.rowcount

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._c().execute(sql, tuple(params)).fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
        with self._lock:
            row = self._c().execute(sql, tuple(params)).fetchone()
            return dict(row) if row is not None else None

    @contextmanager
    def transaction(self) -> Iterator["Database"]:
        """Several writes that must land together or not at all."""
        with self._lock:
            conn = self._c()
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield self
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
