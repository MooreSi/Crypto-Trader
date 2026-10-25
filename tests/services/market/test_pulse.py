"""Market pulse: breadth, funding and crowding across the most traded perps."""
import pytest

from backend.src.services.exchange.types import MarketSnapshot
from backend.src.services.market import pulse


def _s(coin, change_pct, funding, vol, price=100.0, oi=10.0):
    prev = price / (1 + change_pct / 100)
    return MarketSnapshot(coin, price, price, price, funding, oi, vol, prev)


def test_breadth_counts_only_the_top_n_by_volume():
    snaps = [_s("BTC", 2, 0.0001, 9e9), _s("ETH", 1, 0.0, 8e9), _s("SOL", -1, 0.0, 7e9),
             _s("TINY", -5, 0.0, 1.0)]
    p = pulse.summarise(snaps, top_n=3)
    assert p["markets"] == 3 and p["breadth_pct"] == pytest.approx(200 / 3)


def test_funding_is_volume_weighted_in_percent_per_hour():
    p = pulse.summarise([_s("A", 0, 0.0002, 3e9), _s("B", 0, -0.0001, 1e9)], top_n=10)
    assert p["funding_pct_h"] == pytest.approx((0.0002 * 3 - 0.0001 * 1) / 4 * 100)


def test_crowded_sides_and_movers():
    snaps = [_s("A", 5, 0.0005, 5e9), _s("B", -7, -0.0004, 4e9), _s("C", 1, 0.0001, 3e9),
             _s("BTC", 0.5, 0.0, 9e9)]
    p = pulse.summarise(snaps, top_n=10)
    assert p["crowded_longs"][0]["coin"] == "A" and p["crowded_shorts"][0]["coin"] == "B"
    assert all(c["funding_pct_h"] < 0 for c in p["crowded_shorts"])
    assert p["gainers"][0]["coin"] == "A" and p["losers"][0]["coin"] == "B"
    assert p["btc_change_pct"] == pytest.approx(0.5)


@pytest.mark.parametrize("changes,btc,mood", [
    ([3, 2, 1, 1, -1], 2, "risk-on"),
    ([-3, -2, -1, -1, 1], -2, "risk-off"),
    ([3, -2, 1, -1, 1], -0.5, "mixed"),
])
def test_mood(changes, btc, mood):
    snaps = [_s(f"C{i}", c, 0.0, 1e9 - i) for i, c in enumerate(changes)] + [_s("BTC", btc, 0, 1e10)]
    assert pulse.summarise(snaps, top_n=10)["mood"] == mood


def test_empty_market_list():
    p = pulse.summarise([], top_n=10)
    assert p["markets"] == 0 and p["breadth_pct"] == 0 and p["mood"] == "mixed"
