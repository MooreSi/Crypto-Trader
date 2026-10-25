import pytest

from backend.src.services.exchange.types import Market
from backend.src.services.risk import settings, sizing

ETH = Market("ETH", 4, 25)


def _s(**over):
    s = settings.defaults()
    s.update(over)
    return s


def test_risk_equals_equity_times_pct_over_stop_distance():
    d = sizing.compute(ETH, 10_000, 10_000, 3000.0, 2970.0, _s())
    # 0.5% of 10,000 = 50 USDC over a 30 dollar stop = 1.6666 ETH -> 1.6666 (4 dp, down)
    assert d.ok and d.size == 1.6666
    assert d.risk_usd == pytest.approx(1.6666 * 30)
    assert d.risk_usd <= 50.0


def test_notional_cap_only_ever_shrinks_the_position():
    tight = sizing.compute(ETH, 10_000, 10_000, 3000.0, 2999.0, _s())   # 1 dollar stop
    assert tight.ok and tight.notional <= 10_000 * 3.0 + 1e-6
    assert tight.risk_usd < 50.0


def test_leverage_keeps_liquidation_beyond_the_stop():
    # 10% stop: at 3x, liq distance ~ 1/3 - 1/50 = 0.313 >= 0.15
    d = sizing.compute(ETH, 10_000, 10_000, 100.0, 90.0, _s(max_leverage=25))
    assert d.ok
    mm = 1 / (2 * 25)
    assert 1 / d.leverage - mm >= 0.10 * sizing.LIQ_BUFFER
    assert d.leverage <= 25


def test_refuses_below_exchange_minimum():
    d = sizing.compute(ETH, 100, 100, 3000.0, 2000.0, _s())
    assert not d.ok and "minimum" in d.reason


def test_refuses_when_margin_does_not_fit():
    d = sizing.compute(ETH, 10_000, 5.0, 3000.0, 2970.0, _s())
    assert not d.ok and "margin" in d.reason


def test_r_multiple_and_tp_price_are_inverse():
    tp = sizing.tp_price("short", 100.0, 105.0, 2.0)
    assert tp == 90.0
    assert sizing.r_multiple("short", 100.0, 105.0, tp) == 2.0


def test_min_stop_distance_refuses_a_stop_too_close_for_fees():
    # 0.2% stop: a round-trip taker fee (2 x 0.045%) alone is 0.45R of the risk.
    d = sizing.compute(ETH, 10_000, 10_000, 3000.0, 2994.0, _s(min_stop_pct=0.5))
    assert not d.ok and "stop is 0.20%" in d.reason and "0.50%" in d.reason


def test_min_stop_distance_passes_at_and_beyond_the_minimum():
    at = sizing.compute(ETH, 10_000, 10_000, 3000.0, 2985.0, _s(min_stop_pct=0.5))   # exactly 0.5%
    wide = sizing.compute(ETH, 10_000, 10_000, 3000.0, 2970.0, _s(min_stop_pct=0.5))
    assert at.ok and wide.ok
    assert wide == sizing.compute(ETH, 10_000, 10_000, 3000.0, 2970.0, _s())   # size unchanged


def test_min_stop_distance_off_by_default_changes_nothing():
    assert settings.defaults()["min_stop_pct"] == 0.0
    assert sizing.compute(ETH, 10_000, 10_000, 3000.0, 2999.0, _s()).ok
