"""The runtime: the loops that keep the app trading, 24 hours a day.

Four loops, each independent so one failing never starves another:

| loop      | every  | does                                                   |
|-----------|--------|--------------------------------------------------------|
| positions | 10 s   | reconcile open trades with the exchange, move stops    |
| engines   | 60 s   | each engine scans, tracks, maybe trades, maybe retrains|
| events    | 1 h    | refresh the event calendar                             |
| admin     | always | report to the shared admin console (if enabled)        |

There is no session gate and no weekend shutdown: crypto never closes. The
only things that stop new entries are the risk gates and the pause switch.

**Pause** stops the engines (no new signals, no new trades). It never stops
the positions loop: an open trade's stop still moves and an exchange-side
exit is still recorded while paused.

The exchange SDK is synchronous, so every call into services runs in a
worker thread (`asyncio.to_thread`); the event loop only schedules.

**Shutdown waits for a pass already running.** Cancelling a task stops its
await, not its thread, so `stop()` waits for the in-flight threads before
returning; only then does app.py close the databases. Otherwise a pass
caught between placing an order and recording it would hit a closed
database and leave the position unrecorded.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from backend.src import config
from backend.src.services.engines import registry
from backend.src.services.events import calendar
from backend.src.services.exchange import provider
from backend.src.services.notify import notifier
from backend.src.services.positions import manager, trades_repo
from backend.src.services.remote import client as admin_client
from backend.src.services.risk import day, strategies
from backend.src.utils import clock

log = logging.getLogger(__name__)

POSITIONS_EVERY_S = 10
ENGINES_EVERY_S = 60
EVENTS_EVERY_S = 3600
EQUITY_SNAPSHOT_EVERY_S = 300


class TradingRuntime:
    def __init__(self) -> None:
        self.paused = False
        self.started_at = clock.now()
        self.health: dict = {"exchange_ok": False, "last_error": "", "positions_at": None,
                             "engines_at": None, "events_at": None, "unmanaged_positions": [],
                             "open_positions": 0}
        self._tasks: list[asyncio.Task] = []
        self._inflight: set[asyncio.Future] = set()
        self._last_equity_snapshot = 0.0

    # ── loops ────────────────────────────────────────────────────────────────
    def positions_pass(self) -> None:
        client = provider.get()
        try:
            account = client.account() if (config.get("network") == "paper"
                                           or config.get("account_address")) else None
            summary = manager.manage(client, account)
            self.health.update(exchange_ok=True, positions_at=clock.now(), last_error="",
                               unmanaged_positions=summary["unmanaged_positions"],
                               open_positions=len(account.positions) if account else 0)
            if account:
                # Record the UTC day's starting equity as soon as the day
                # begins, not when the dashboard or a signal first asks.
                day.start_equity(account.equity)
            if (account and account.equity > 0
                    and clock.now() - self._last_equity_snapshot >= EQUITY_SNAPSHOT_EVERY_S):
                trades_repo.snapshot_equity(account.equity, config.account_key())
                self._last_equity_snapshot = clock.now()
        except Exception as exc:
            self.health.update(exchange_ok=False, last_error=str(exc))
            log.warning("[Runtime] positions pass failed: %s", exc)
        try:
            notifier.notify_pass()
        except Exception as exc:
            log.warning("[Runtime] trade alerts failed: %s", exc)

    def engines_pass(self) -> list[dict]:
        if self.paused:
            return []
        client = provider.get()
        results = [eng.cycle(client) for eng in registry.get().values()]
        self.health["engines_at"] = clock.now()
        return results

    def events_pass(self) -> None:
        try:
            calendar.refresh()
            self.health["events_at"] = clock.now()
        except Exception as exc:
            log.warning("[Runtime] events refresh failed: %s", exc)

    async def _every(self, seconds: float, fn) -> None:
        while True:
            try:
                work = asyncio.ensure_future(asyncio.to_thread(fn))
                self._inflight.add(work)
                work.add_done_callback(self._inflight.discard)
                await asyncio.shield(work)     # a cancel stops the wait, never the pass
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("[Runtime] %s crashed; continuing", getattr(fn, "__name__", fn))
            await asyncio.sleep(seconds)

    def admin_status(self) -> dict:
        return {"positions": self.health.get("open_positions"),
                "exchange_ok": self.health.get("exchange_ok")}

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            if strategies.ensure_default():
                log.info("[Runtime] default strategy %r created and activated",
                         strategies.DEFAULT_NAME)
        except Exception as exc:
            log.warning("[Runtime] default strategy not created: %s", exc)
        self._tasks = [
            loop.create_task(self._every(EVENTS_EVERY_S, self.events_pass)),
            loop.create_task(self._every(POSITIONS_EVERY_S, self.positions_pass)),
            loop.create_task(self._every(ENGINES_EVERY_S, self.engines_pass)),
        ]
        if config.get("admin_console_enabled", True):
            self._tasks.append(loop.create_task(admin_client.run(self.admin_status)))
        log.info("[Runtime] started on %s (paper=%s)", config.get("network"),
                 config.get("network") == "paper")

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        if self._inflight:
            log.info("[Runtime] waiting for %d running pass(es) to finish", len(self._inflight))
            await asyncio.gather(*list(self._inflight), return_exceptions=True)

    def status(self) -> dict:
        return {"paused": self.paused, "network": config.get("network"),
                "started_at": self.started_at, "uptime_s": clock.now() - self.started_at,
                **self.health, "admin_console": admin_client.status()}


_runtime: Optional[TradingRuntime] = None


def get() -> TradingRuntime:
    global _runtime
    if _runtime is None:
        _runtime = TradingRuntime()
    return _runtime
