"""One engine's cycle, the same shape for every engine.

    scan universe -> closed candles -> generator -> features -> ML score
        -> store (always) -> executor (only if this engine's live toggle is on)
    then: track every open virtual signal to its outcome under the live exit
          plan (and re-score labels an older rule wrote, while their bars last)
    and: retrain the model once a day

An engine's generator is a pure function from candles to zero or more
`Setup`s; everything else (storage, tracking, ML, the live hand-off) is here,
so the three engines cannot drift apart in how they treat money.

Toggles, per engine, in app_config:

* `engine_enabled:<name>` -- generate and track signals (default ON: this
  is research, no money moves);
* `engine_live:<name>` -- hand signals to the executor (default OFF). Even
  then nothing executes unless the master `trading_enabled` risk setting is
  also on.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from backend.src.db import database
from backend.src.services.engines import tracker
from backend.src.services.engines.base import Signal
from backend.src.services.engines.signal_repo import LIVE_EXECUTED, LIVE_REFUSED, SignalStore
from backend.src.services.events import calendar
from backend.src.services.exchange.paper_exchange import PAPER_TAKER_FEE
from backend.src.services.exchange.types import Candle, ExchangeClient
from backend.src.services.market import candles as candle_src
from backend.src.services.market import universe
from backend.src.services.market.candles import INTERVAL_MS
from backend.src.services.ml import features as feat
from backend.src.services.ml.model import EngineModel
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings as risk_settings
from backend.src.services.trading import executor
from backend.src.utils import clock

log = logging.getLogger(__name__)

HISTORY_BARS = 260
RETRAIN_EVERY_S = 24 * 3600
#: Don't repeat a signal for the same coin and direction within this many bars.
DEDUPE_BARS = 8


@dataclass
class Setup:
    """What a generator found: direction, levels, and its own extra features."""
    direction: str
    entry: float
    stop: float
    reason: str
    extra: dict = field(default_factory=dict)


Generator = Callable[[Sequence[Candle], Sequence[Candle]], list[Setup]]


class EngineService:
    def __init__(self, name: str, interval: str, generator: Generator, extra_features: Sequence[str],
                 store: SignalStore, model: EngineModel, htf_interval: Optional[str] = None) -> None:
        self.name = name
        self.interval = interval
        self.htf_interval = htf_interval
        self.generator = generator
        self.extra_features = tuple(extra_features)
        self.store = store
        self.model = model
        self.last_cycle: Optional[float] = None
        self.last_error: str = ""
        self.last_retrain: float = 0.0
        self.last_train_report: dict = {}

    # ── toggles ──────────────────────────────────────────────────────────────
    def enabled(self) -> bool:
        return (database.get_app_config(f"engine_enabled:{self.name}") or "1") == "1"

    def live(self) -> bool:
        return (database.get_app_config(f"engine_live:{self.name}") or "0") == "1"

    def set_enabled(self, on: bool) -> None:
        database.set_app_config(f"engine_enabled:{self.name}", "1" if on else "0")

    def set_live(self, on: bool) -> None:
        database.set_app_config(f"engine_live:{self.name}", "1" if on else "0")

    # ── cycle ────────────────────────────────────────────────────────────────
    def _features(self, setup: Setup, bars, snapshot, btc_bars, coin: str) -> dict:
        v = feat.base_vector(setup.direction, setup.entry, setup.stop, bars, snapshot, btc_bars,
                             calendar.proximity_hours(coin))
        for name in self.extra_features:
            v[name] = float(setup.extra.get(name, feat.NEUTRAL))
        return v

    def scan(self, client: ExchangeClient) -> list[Signal]:
        settings = risk_settings.get()
        snapshots = {s.coin: s for s in client.snapshots()}
        coins = universe.select(list(snapshots.values()), settings)
        try:
            btc_bars = candle_src.closed(client, "BTC", self.interval, HISTORY_BARS) \
                if "BTC" in snapshots else []
        except candle_src.CandleBudgetExceeded:
            log.info("[%s] candle budget used up; scanning next cycle", self.name)
            return []
        step_s = INTERVAL_MS[self.interval] / 1000
        made: list[Signal] = []
        deferred = 0
        for coin in coins:
            try:
                bars = candle_src.closed(client, coin, self.interval, HISTORY_BARS)
                htf = candle_src.closed(client, coin, self.htf_interval, HISTORY_BARS) \
                    if self.htf_interval else []
                if len(bars) < 60:
                    continue
                for setup in self.generator(bars, htf):
                    created = bars[-1].t / 1000 + step_s   # the bar's close
                    if self.store.exists_since(coin, setup.direction, created - DEDUPE_BARS * step_s):
                        continue
                    features = self._features(setup, bars, snapshots.get(coin), btc_bars, coin)
                    sig = Signal(engine=self.name, coin=coin, direction=setup.direction,
                                 entry=setup.entry, stop=setup.stop, created_at=created,
                                 interval=self.interval, reason=setup.reason, features=features,
                                 ml_score=self.model.score(features))
                    sig.id = self.store.insert(sig)
                    made.append(sig)
            except candle_src.CandleBudgetExceeded:
                deferred += 1          # within the request budget next cycle
            except Exception as exc:
                log.warning("[%s] %s scan failed: %s", self.name, coin, exc)
        if deferred:
            log.info("[%s] %d coin(s) deferred to the next cycle (candle budget)", self.name, deferred)
        return made

    def hand_to_executor(self, client: ExchangeClient, signals: list[Signal]) -> None:
        for sig in signals:
            outcome = executor.execute(client, sig, self.model.has_model)
            if outcome.placed:
                self.store.set_live(sig.id, LIVE_EXECUTED, outcome.trade_id)
            else:
                self.store.set_live(sig.id, f"{LIVE_REFUSED}:{outcome.reason}"[:200], None)

    def track(self, client: ExchangeClient) -> int:
        settings = risk_settings.get()
        plan = {"tp_ladder": settings["tp_ladder"], "breakeven_after_tp": settings["breakeven_after_tp"],
                "fee_rate": PAPER_TAKER_FEE}
        resolved = 0
        for row in self.store.tracking() + self.store.stale(tracker.LABEL_VERSION):
            try:
                rescore = row["status"] != "tracking"
                bars = candle_src.closed(client, row["coin"], row["interval"], HISTORY_BARS)
                if rescore and (not bars or bars[0].t / 1000 > row["created_at"]):
                    continue           # its first bars are gone: keep the old label, never train on it
                after = [c for c in bars if c.t / 1000 >= row["created_at"]]
                sig = dict(row)
                trade = trades_repo.get(row["trade_id"]) if row.get("trade_id") else None
                if trade:
                    sig["fill"] = trade["entry_price"]
                out = tracker.evaluate(sig, after, plan)
                if out["status"] == "tracking":
                    if rescore:
                        self.store.reopen(row["id"], out["mfe_r"], out["mae_r"])
                    else:
                        self.store.update_excursion(row["id"], out["mfe_r"], out["mae_r"])
                else:
                    self.store.resolve(row["id"], out["status"], out["label"], out["r_final"],
                                       out["mfe_r"], out["mae_r"], out["resolved_at"])
                    resolved += 1
            except Exception as exc:
                log.debug("[%s] tracking #%s failed: %s", self.name, row["id"], exc)
        return resolved

    def maybe_retrain(self, force: bool = False) -> Optional[dict]:
        if not force and clock.now() - self.last_retrain < RETRAIN_EVERY_S:
            return None
        self.last_retrain = clock.now()
        self.last_train_report = self.model.train(self.store.labelled())
        return self.last_train_report

    def cycle(self, client: ExchangeClient) -> dict:
        if not self.enabled():
            return {"engine": self.name, "skipped": "disabled"}
        try:
            signals = self.scan(client)
            if self.live() and signals:
                self.hand_to_executor(client, signals)
            resolved = self.track(client)
            self.maybe_retrain()
            self.last_error = ""
            return {"engine": self.name, "signals": len(signals), "resolved": resolved}
        except Exception as exc:
            self.last_error = str(exc)
            log.exception("[%s] cycle failed", self.name)
            return {"engine": self.name, "error": str(exc)}
        finally:
            self.last_cycle = clock.now()

    def status(self) -> dict:
        return {
            "name": self.name, "interval": self.interval, "enabled": self.enabled(),
            "live": self.live(), "last_cycle": self.last_cycle, "last_error": self.last_error,
            "stats": self.store.stats(), "model": {
                "trained": self.model.has_model, "meta": self.model.meta,
                "last_report": self.last_train_report,
            },
        }
