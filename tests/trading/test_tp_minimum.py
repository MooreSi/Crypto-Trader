"""No take-profit order below Hyperliquid's minimum.

Found live on mainnet, 2026-10-25: on ~$20 positions the 50/25/25 ladder
made TP orders of ~$10, $5 and $5. Hyperliquid accepts such a trigger and
rejects it only when it fires (`minTradeNtlRejected`), so a UNI long that
went past all three TPs closed at the stop instead.

The fix merges an undersized rung into the rung before it (the nearer
price), so profit is taken sooner rather than later. TP1 takes whatever is
left, even if that is still small: it is the best exit available.
"""
import pytest

from backend.src.services.engines.base import Signal
from backend.src.services.exchange import hyperliquid_client
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings
from backend.src.services.risk.sizing import SizeDecision
from backend.src.services.trading import order_service


def _open(fx, size, direction="long", entry=3000.0, stop=2970.0):
    sig = Signal(engine="reversal", coin="ETH", direction=direction, entry=entry, stop=stop,
                 created_at=0, interval="15m", reason="test")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    decision = SizeDecision(True, size=size, leverage=1, risk_usd=abs(entry - stop) * size,
                            notional=size * entry, margin=size * entry)
    trade_id = order_service.open_trade(fx, market, sig, decision, settings.defaults(), [])
    tps = [c for c in fx.calls if c[0] == "trigger" and c[5] == "take_profit"]
    return trade_id, [(c[3], c[4]) for c in tps]


def test_minimum_covers_the_trigger_slippage():
    # The exchange may value a triggered market order at its limit price,
    # which is TRIGGER_SLIPPAGE worse than the trigger.
    worst = 1 - hyperliquid_client.TRIGGER_SLIPPAGE
    assert order_service.TP_MIN_NOTIONAL_USD * worst >= 10.0


def test_a_20_dollar_position_gets_one_tp_at_1r_for_the_whole_size(fake_exchange, fixed_clock):
    trade_id, tps = _open(fake_exchange, 0.0066)          # $19.80
    assert tps == [(0.0066, 3030.0)]
    t = trades_repo.get(trade_id)
    assert t["take_profits"] == [3030.0, 3060.0, 3090.0]
    assert t["tp_oids"][0] and t["tp_oids"][1:] == [None, None]


def test_a_40_dollar_position_merges_only_the_small_last_rung(fake_exchange, fixed_clock):
    _, tps = _open(fake_exchange, 0.0133)                 # $39.90: 0.0066 / 0.0033 / 0.0034
    assert tps == [(0.0066, 3030.0), (0.0067, 3060.0)]


def test_every_tp_placed_meets_the_minimum_and_covers_the_position(fake_exchange, fixed_clock):
    for size in (0.0040, 0.0066, 0.0100, 0.0133, 0.0200, 0.0400):
        fake_exchange.calls.clear()
        fake_exchange.positions.clear()
        _, tps = _open(fake_exchange, size)
        assert sum(s for s, _ in tps) == pytest.approx(size)
        if size * 3030.0 >= order_service.TP_MIN_NOTIONAL_USD:
            assert all(s * p >= order_service.TP_MIN_NOTIONAL_USD for s, p in tps), (size, tps)


def test_a_large_position_keeps_the_full_three_rung_ladder(fake_exchange, fixed_clock):
    _, tps = _open(fake_exchange, 0.0400)                 # $120
    assert tps == [(0.02, 3030.0), (0.01, 3060.0), (0.01, 3090.0)]


def test_short_too_small_even_whole_at_tp1_still_gets_one_tp(fake_exchange, fixed_clock):
    # $10.50 short: worth less than the minimum at TP1. One full-size TP1 is still the best exit.
    _, tps = _open(fake_exchange, 0.0035, direction="short", stop=3030.0)
    assert tps == [(0.0035, 2970.0)]


def test_a_refused_tp_leaves_the_stop_in_place(fake_exchange, fixed_clock):
    fake_exchange.refuse_tp = True
    trade_id, _ = _open(fake_exchange, 0.0066)
    t = trades_repo.get(trade_id)
    assert t["status"] == "open" and t["sl_oid"] and t["tp_oids"] == [None, None, None]
    assert any(o.kind == "stop" for o in fake_exchange.orders)
