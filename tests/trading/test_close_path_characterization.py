"""WITNESS for the frozen close path (golden rule 2).

This file pins what `close_trade`, `partial_close_trade` and `record_close`
do today. It must pass UNMODIFIED. If a change needs this file edited, the
change is not allowed without the owner's sign-off and a testnet session.
The one legitimate edit is a mock-target relocation, said so in the commit.
"""
import inspect

import pytest

from backend.src.services.engines.base import Signal
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings, sizing
from backend.src.services.trading import order_service


def test_signatures_are_frozen():
    assert str(inspect.signature(order_service.close_trade)) == \
        "(client: 'ExchangeClient', trade: 'dict', reason: 'str') -> 'bool'"
    assert str(inspect.signature(order_service.partial_close_trade)) == \
        "(client: 'ExchangeClient', trade: 'dict', fraction: 'float', market: 'Market', " \
        "reason: 'str') -> 'bool'"
    assert str(inspect.signature(order_service.record_close)) == \
        "(trade: 'dict', price: 'float', pnl: 'float', fee: 'float', reason: 'str') -> 'None'"


@pytest.fixture
def open_trade(fake_exchange, fixed_clock):
    fx = fake_exchange
    sig = Signal(engine="reversal", coin="ETH", direction="long", entry=3000.0, stop=2970.0,
                 created_at=0, interval="15m")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    s = settings.defaults()
    d = sizing.compute(market, 10_000, 10_000, 3000.0, 2970.0, s)
    tid = order_service.open_trade(fx, market, sig, d, s, [])
    return fx, market, trades_repo.get(tid)


def test_close_trade_market_closes_cancels_exits_and_records(open_trade):
    fx, _, t = open_trade
    fx.mid["ETH"] = 3060.0
    fx.calls.clear()
    assert order_service.close_trade(fx, t, "manual") is True
    assert fx.calls[0] == ("market", "ETH", False, t["size"], True)
    cancelled = {c[2] for c in fx.calls if c[0] == "cancel"}
    assert cancelled == {t["sl_oid"], *t["tp_oids"]}
    closed = trades_repo.get(t["id"])
    assert closed["status"] == "closed" and closed["close_reason"] == "manual"
    assert closed["close_price"] == 3060.0 and closed["size"] == 0.0
    expected_pnl = (3060.0 - 3000.0) * t["size"]
    assert closed["realised_pnl"] == pytest.approx(expected_pnl)
    assert closed["fees"] == pytest.approx(t["fees"] + 3060.0 * t["size"] * order_service.TAKER_FEE_ESTIMATE)
    assert trades_repo.events_for(t["id"])[-1]["kind"] == "closed"


def test_close_trade_refused_records_nothing(open_trade):
    fx, _, t = open_trade
    fx.place_market = lambda *a, **k: order_service.OrderResult(ok=False, error="nope")
    assert order_service.close_trade(fx, t, "manual") is False
    assert trades_repo.get(t["id"])["status"] == "open"


def test_partial_close_books_part_and_resizes_stop(open_trade):
    fx, market, t = open_trade
    fx.mid["ETH"] = 3030.0
    fx.calls.clear()
    assert order_service.partial_close_trade(fx, t, 0.5, market, "manual partial") is True
    half = round(t["size"] * 0.5, 4)
    assert fx.calls[0] == ("market", "ETH", False, half, True)
    after = trades_repo.get(t["id"])
    assert after["status"] == "open"
    assert after["size"] == pytest.approx(t["size"] - half)
    assert after["realised_pnl"] == pytest.approx(30.0 * half)
    new_stop = [c for c in fx.calls if c[0] == "trigger" and c[5] == "stop"][-1]
    assert new_stop[3] == pytest.approx(after["size"])


def test_partial_close_of_everything_is_a_close(open_trade):
    fx, market, t = open_trade
    assert order_service.partial_close_trade(fx, t, 1.0, market, "all") is True
    assert trades_repo.get(t["id"])["status"] == "closed"
