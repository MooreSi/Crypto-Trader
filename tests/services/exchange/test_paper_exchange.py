import pytest

from backend.src.services.exchange.paper_exchange import PAPER_SLIPPAGE, PAPER_TAKER_FEE, PaperExchange
from tests.fakes import FakeExchange


@pytest.fixture
def paper(fresh_db):
    src = FakeExchange()
    return PaperExchange(src, 10_000.0), src


def test_long_round_trip_books_pnl_and_fees(paper):
    px, src = paper
    res = px.place_market("ETH", True, 1.0, 0.01)
    entry = 3000.0 * (1 + PAPER_SLIPPAGE)
    assert res.ok and res.avg_price == pytest.approx(entry)
    src.mid["ETH"] = 3100.0
    out = px.place_market("ETH", False, 1.0, 0.01, reduce_only=True)
    exit_ = 3100.0 * (1 - PAPER_SLIPPAGE)
    fees = (entry + exit_) * PAPER_TAKER_FEE
    assert out.ok
    assert px.account().equity == pytest.approx(10_000.0 + (exit_ - entry) - fees)
    assert px.account().positions == ()


def test_stop_trigger_fires_when_price_crosses(paper):
    px, src = paper
    px.place_market("SOL", True, 10.0, 0.01)
    px.place_trigger("SOL", False, 10.0, 140.0, "stop")
    src.mid["SOL"] = 141.0
    assert px.account().position("SOL") is not None
    src.mid["SOL"] = 139.0          # gapped through the stop
    acc = px.account()
    assert acc.position("SOL") is None
    fills = px.fills_since(0)
    assert fills[-1].price == 139.0  # worse of trigger and mid
    assert px.open_orders() == []


def test_reduce_only_cannot_open_or_flip(paper):
    px, _ = paper
    assert not px.place_market("BTC", False, 0.1, 0.01, reduce_only=True).ok
    px.place_market("BTC", True, 0.01, 0.01)
    res = px.place_market("BTC", False, 1.0, 0.01, reduce_only=True)
    assert res.ok and res.filled_size == 0.01
    assert px.account().position("BTC") is None


def test_state_survives_restart(paper):
    px, src = paper
    px.place_market("ETH", True, 2.0, 0.01)
    again = PaperExchange(src, 10_000.0)
    assert again.account().position("ETH").size == 2.0
