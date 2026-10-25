"""Defects found in the position manager on 2026-10-25, each pinned by a test.

1. **A trailed stop was moved back to breakeven.** With `trail_atr_mult` on,
   the stop trails above entry after TP1. When TP2 then filled,
   `_reconcile_partial` set the stop to the entry price again because
   `tp_hit >= breakeven_after_tp` was still true: a stop in profit was
   loosened back to breakeven. A stop the manager moves must only tighten.
2. **The exit reason always named the last rung.** A position closed by TP1
   (one merged TP for the whole size, `order_service._tp_plan`) was recorded
   as "TP3".
"""
import pytest

from backend.src.services.engines.base import Signal
from backend.src.services.positions import manager, trades_repo
from backend.src.services.risk import settings, sizing
from backend.src.services.risk.sizing import SizeDecision
from backend.src.services.trading import order_service


def _open_default(fx):
    sig = Signal(engine="trend_pa", coin="ETH", direction="long", entry=3000.0, stop=2970.0,
                 created_at=0, interval="1h")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    s = settings.defaults()
    d = sizing.compute(market, 10_000, 10_000, 3000.0, 2970.0, s)
    return trades_repo.get(order_service.open_trade(fx, market, sig, d, s, []))


def test_tp2_fill_does_not_move_a_trailed_stop_back_to_breakeven(fake_exchange, fixed_clock):
    fx = fake_exchange
    t = _open_default(fx)
    now_ms = int(fixed_clock.now() * 1000)
    fx.fire(t["tp_oids"][0], 3030.0, now_ms + 1000)
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 3000.0
    # the trail (or a manual move) has since tightened the stop into profit
    order_service.move_stop(fx, trades_repo.get(t["id"]), 3015.0, fx.positions["ETH"].size, "trail")
    fx.fire(t["tp_oids"][1], 3060.0, now_ms + 2000)
    manager.manage(fx)
    after = trades_repo.get(t["id"])
    assert after["tp_hit"] == 2
    assert after["stop_loss"] == 3015.0
    stops = [o for o in fx.orders if o.kind == "stop"]
    assert len(stops) == 1 and stops[0].trigger_price == 3015.0
    assert stops[0].size == pytest.approx(fx.positions["ETH"].size)


def test_short_tp2_fill_does_not_loosen_a_trailed_stop(fake_exchange, fixed_clock):
    fx = fake_exchange
    sig = Signal(engine="trend_pa", coin="ETH", direction="short", entry=3000.0, stop=3030.0,
                 created_at=0, interval="1h")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    s = settings.defaults()
    d = sizing.compute(market, 10_000, 10_000, 3000.0, 3030.0, s)
    t = trades_repo.get(order_service.open_trade(fx, market, sig, d, s, []))
    now_ms = int(fixed_clock.now() * 1000)
    fx.fire(t["tp_oids"][0], 2970.0, now_ms + 1000)
    manager.manage(fx)
    order_service.move_stop(fx, trades_repo.get(t["id"]), 2985.0, abs(fx.positions["ETH"].size),
                            "trail")
    fx.fire(t["tp_oids"][1], 2940.0, now_ms + 2000)
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 2985.0


def test_a_position_closed_by_its_only_tp_is_recorded_as_tp1(fake_exchange, fixed_clock):
    fx = fake_exchange
    sig = Signal(engine="reversal", coin="ETH", direction="long", entry=3000.0, stop=2970.0,
                 created_at=0, interval="15m")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    d = SizeDecision(True, size=0.0066, leverage=1, risk_usd=0.198, notional=19.8, margin=19.8)
    t = trades_repo.get(order_service.open_trade(fx, market, sig, d, settings.defaults(), []))
    assert t["tp_oids"][0] and t["tp_oids"][1:] == [None, None]
    fx.fire(t["tp_oids"][0], 3030.0, int(fixed_clock.now() * 1000) + 1000)
    manager.manage(fx)
    closed = trades_repo.get(t["id"])
    assert closed["status"] == "closed" and closed["close_reason"] == "TP1"


def test_last_rung_still_named_by_its_own_number(fake_exchange, fixed_clock):
    fx = fake_exchange
    t = _open_default(fx)
    now_ms = int(fixed_clock.now() * 1000)
    for i, price in enumerate((3030.0, 3060.0, 3090.0)):
        fx.fire(t["tp_oids"][i], price, now_ms + 1000 * (i + 1))
        manager.manage(fx)
    assert trades_repo.get(t["id"])["close_reason"] == "TP3"
