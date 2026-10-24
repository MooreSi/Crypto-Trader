import pytest

from backend.src.services.exchange import rounding

from backend.src.services.engines.base import Signal
from backend.src.services.exchange.types import Position
from backend.src.services.positions import manager, trades_repo
from backend.src.services.risk import day, settings, sizing
from backend.src.services.trading import order_service


@pytest.fixture
def trade(fake_exchange, fixed_clock):
    fx = fake_exchange
    sig = Signal(engine="trend_pa", coin="ETH", direction="long", entry=3000.0, stop=2970.0,
                 created_at=0, interval="1h")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    s = settings.defaults()
    d = sizing.compute(market, 10_000, 10_000, 3000.0, 2970.0, s)
    tid = order_service.open_trade(fx, market, sig, d, s, [])
    return fx, trades_repo.get(tid)


def test_stop_hit_on_exchange_is_recorded_from_fills(trade, fixed_clock):
    fx, t = trade
    fx.fire(t["sl_oid"], 2970.0, int(fixed_clock.now() * 1000) + 1000, fee=1.0)
    manager.manage(fx)
    closed = trades_repo.get(t["id"])
    assert closed["status"] == "closed" and closed["close_reason"] == "stop loss"
    assert closed["realised_pnl"] == pytest.approx(-30.0 * t["size"])
    assert {c[2] for c in fx.calls if c[0] == "cancel"} >= set(t["tp_oids"])
    assert trades_repo.realised_since(day.start_ts()) == pytest.approx(
        -30.0 * t["size"] - 1.0 - t["fees"])


def test_tp1_fill_books_partial_and_moves_stop_to_breakeven(trade, fixed_clock):
    fx, t = trade
    fx.fire(t["tp_oids"][0], 3030.0, int(fixed_clock.now() * 1000) + 1000)
    manager.manage(fx)
    after = trades_repo.get(t["id"])
    assert after["status"] == "open" and after["tp_hit"] == 1
    assert after["stop_loss"] == rounding.round_price(after["entry_price"], 4)
    live = fx.positions["ETH"].size
    assert after["size"] == pytest.approx(live)
    stops = [o for o in fx.orders if o.kind == "stop"]
    assert len(stops) == 1 and stops[0].size == pytest.approx(live)


def test_positions_the_app_did_not_open_are_listed_not_touched(trade):
    fx, t = trade
    fx.positions["SOL"] = Position("SOL", 5.0, 150.0, 0.0, 2, None, 0.0)
    fx.calls.clear()
    summary = manager.manage(fx)
    assert summary["unmanaged_positions"] == ["SOL"]
    assert not [c for c in fx.calls if c[1] == "SOL"]
