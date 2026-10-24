"""The open path: no position is ever left without a stop."""
import pytest

from backend.src.services.engines.base import Signal
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings, sizing
from backend.src.services.trading import order_service


def _setup(fx, entry=3000.0, stop=2970.0):
    sig = Signal(engine="breakout", coin="ETH", direction="long", entry=entry, stop=stop,
                 created_at=0, interval="15m", reason="test")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    s = settings.defaults()
    decision = sizing.compute(market, 10_000, 10_000, entry, stop, s)
    return sig, market, s, decision


def test_entry_places_stop_and_full_tp_ladder(fake_exchange, fixed_clock):
    fx = fake_exchange
    sig, market, s, decision = _setup(fx)
    trade_id = order_service.open_trade(fx, market, sig, decision, s, [])
    kinds = [c for c in fx.calls if c[0] == "trigger"]
    stop = [c for c in kinds if c[5] == "stop"]
    tps = [c for c in kinds if c[5] == "take_profit"]
    assert len(stop) == 1 and stop[0][3] == decision.size and stop[0][2] is False
    assert len(tps) == 3
    assert sum(c[3] for c in tps) == pytest.approx(decision.size)    # ladder covers the position
    assert [c[4] for c in tps] == [3030.0, 3060.0, 3090.0]          # 1R, 2R, 3R
    t = trades_repo.get(trade_id)
    assert t["status"] == "open" and t["sl_oid"] and len(t["tp_oids"]) == 3
    assert trades_repo.events_for(trade_id)[0]["kind"] == "opened"


def test_refused_stop_closes_the_position_at_once(fake_exchange, fixed_clock):
    fx = fake_exchange
    fx.refuse_stop = True
    sig, market, s, decision = _setup(fx)
    with pytest.raises(order_service.OrderRefused):
        order_service.open_trade(fx, market, sig, decision, s, [])
    assert fx.positions == {}
    assert ("market", "ETH", False, decision.size, True) in fx.calls
    assert trades_repo.open_trades() == []


def test_fill_beyond_the_stop_is_closed_not_protected(fake_exchange, fixed_clock):
    fx = fake_exchange
    fx.entry_fill_price = 2960.0      # slipped below the 2970 stop
    sig, market, s, decision = _setup(fx)
    with pytest.raises(order_service.OrderRefused):
        order_service.open_trade(fx, market, sig, decision, s, [])
    assert fx.positions == {}
    assert not [c for c in fx.calls if c[0] == "trigger"]


def test_unfilled_entry_places_nothing_else(fake_exchange, fixed_clock):
    fx = fake_exchange
    fx.refuse_entry = True
    sig, market, s, decision = _setup(fx)
    with pytest.raises(order_service.OrderRefused):
        order_service.open_trade(fx, market, sig, decision, s, [])
    assert [c[0] for c in fx.calls] == ["leverage", "market"]


def test_move_stop_places_new_before_cancelling_old(fake_exchange, fixed_clock):
    fx = fake_exchange
    sig, market, s, decision = _setup(fx)
    tid = order_service.open_trade(fx, market, sig, decision, s, [])
    t = trades_repo.get(tid)
    fx.calls.clear()
    assert order_service.move_stop(fx, t, 3000.0, t["size"], "breakeven")
    assert fx.calls[0][0] == "trigger" and fx.calls[1] == ("cancel", "ETH", t["sl_oid"])
    assert trades_repo.get(tid)["stop_loss"] == 3000.0


def test_refused_stop_move_keeps_the_old_stop(fake_exchange, fixed_clock):
    fx = fake_exchange
    sig, market, s, decision = _setup(fx)
    tid = order_service.open_trade(fx, market, sig, decision, s, [])
    t = trades_repo.get(tid)
    fx.refuse_stop = True
    assert not order_service.move_stop(fx, t, 3000.0, t["size"], "breakeven")
    assert not [c for c in fx.calls if c[0] == "cancel"]
    assert trades_repo.get(tid)["stop_loss"] == t["stop_loss"]
