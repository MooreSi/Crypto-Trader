"""From an engine's signal to an order: gates, sizing, then the order service.

The executor is the only caller of `order_service.open_trade`. It is reached
only when the engine's own live toggle is on (checked by the engine service)
AND the master `trading_enabled` switch is on (checked by the first gate).
Every decision -- placed or refused -- is written to `gate_decisions`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from backend.src.services.engines.base import Signal
from backend.src.services.events import calendar
from backend.src.services.exchange.types import ExchangeClient
from backend.src.services.market.candles import INTERVAL_MS
from backend.src.services.positions import trades_repo
from backend.src.services.risk import day, gates, settings as risk_settings, sizing
from backend.src.services.trading import order_service
from backend.src.utils import clock

log = logging.getLogger(__name__)


@dataclass
class Outcome:
    placed: bool
    reason: str = ""
    trade_id: Optional[int] = None


def _funding(client: ExchangeClient, coin: str) -> Optional[float]:
    for snap in client.snapshots():
        if snap.coin == coin:
            return snap.funding_rate
    return None


def execute(client: ExchangeClient, sig: Signal, ml_has_model: bool) -> Outcome:
    settings = risk_settings.get()
    account = client.account()
    ctx = gates.GateContext(
        now=clock.now(), settings=settings, open_trades=trades_repo.open_trades(),
        interval_seconds=INTERVAL_MS[sig.interval] / 1000.0,
        funding_rate=_funding(client, sig.coin),
        blackout_event=calendar.blackout(sig.coin, settings),
        day_start_equity=day.start_equity(account.equity), equity=account.equity,
        realised_today=trades_repo.realised_since(day.start_ts()), ml_has_model=ml_has_model,
    )
    result = gates.evaluate(sig, ctx)
    if not result.passed:
        trades_repo.record_gate_decision(sig.engine, sig.coin, sig.direction, sig.id, False,
                                         result.decisions)
        return Outcome(False, result.reason)

    market = next((m for m in client.markets() if m.coin == sig.coin), None)
    if market is None or market.delisted:
        reason = f"{sig.coin} is not tradable"
        result.decisions.append({"gate": "market", "passed": False, "detail": reason})
        trades_repo.record_gate_decision(sig.engine, sig.coin, sig.direction, sig.id, False,
                                         result.decisions)
        return Outcome(False, reason)

    decision = sizing.compute(market, account.equity, account.available, sig.entry, sig.stop,
                              settings)
    result.decisions.append({"gate": "sizing", "passed": decision.ok, "detail": decision.reason})
    if not decision.ok:
        trades_repo.record_gate_decision(sig.engine, sig.coin, sig.direction, sig.id, False,
                                         result.decisions)
        return Outcome(False, f"sizing: {decision.reason}")

    trades_repo.record_gate_decision(sig.engine, sig.coin, sig.direction, sig.id, True,
                                     result.decisions)
    try:
        trade_id = order_service.open_trade(client, market, sig, decision, settings,
                                            result.decisions)
    except order_service.OrderRefused as exc:
        log.warning("[Executor] %s %s %s refused: %s", sig.engine, sig.direction, sig.coin, exc)
        return Outcome(False, str(exc))
    return Outcome(True, trade_id=trade_id)
