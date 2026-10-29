"""A TP ladder that adds up to less than 1 leaves a runner with no take-profit.

Added 2026-10-29 for the "TP1 80% at 1.5R + trailed runner" strategy
(docs/specs/001-strategies.md). Before, the last rung always took the
remainder, so `[[1.5, 0.8]]` closed 100% at TP1 and nothing was left to
trail. A runner too small for Hyperliquid's $10 minimum is added to the last
rung instead, the same rule as a small rung.
"""
import pytest

from backend.src.services.engines.base import Signal
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings
from backend.src.services.risk.sizing import SizeDecision
from backend.src.services.trading import order_service

RUNNER = [[1.5, 0.8]]


def _open(fx, size, ladder, direction="long", entry=3000.0, stop=2970.0):
    sig = Signal(engine="reversal", coin="ETH", direction=direction, entry=entry, stop=stop,
                 created_at=0, interval="15m", reason="test")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    decision = SizeDecision(True, size=size, leverage=1, risk_usd=abs(entry - stop) * size,
                            notional=size * entry, margin=size * entry)
    s = dict(settings.defaults(), tp_ladder=ladder)
    trade_id = order_service.open_trade(fx, market, sig, decision, s, [])
    tps = [c for c in fx.calls if c[0] == "trigger" and c[5] == "take_profit"]
    return trades_repo.get(trade_id), [(c[3], c[4]) for c in tps]


def test_a_ladder_under_100_percent_leaves_a_runner(fake_exchange, fixed_clock):
    t, tps = _open(fake_exchange, 0.1, RUNNER)          # $300 notional
    assert tps == [(pytest.approx(0.08), 3045.0)]
    stop = next(c for c in fake_exchange.calls if c[0] == "trigger" and c[5] == "stop")
    assert stop[3] == pytest.approx(0.1)                 # the stop still covers everything
    assert t["take_profits"] == [3045.0]


def test_a_short_runner(fake_exchange, fixed_clock):
    _, tps = _open(fake_exchange, 0.1, RUNNER, direction="short", entry=3000.0, stop=3030.0)
    assert tps == [(pytest.approx(0.08), 2955.0)]


def test_a_runner_under_the_exchange_minimum_goes_to_the_last_rung(fake_exchange, fixed_clock):
    # $19.80 position: the 20% runner would be about $4, which Hyperliquid
    # may refuse when its stop fires. TP1 takes it all, as before.
    _, tps = _open(fake_exchange, 0.0066, RUNNER)
    assert tps == [(pytest.approx(0.0066), 3045.0)]


def test_a_ladder_of_100_percent_is_unchanged(fake_exchange, fixed_clock):
    _, tps = _open(fake_exchange, 0.1, [[1.0, 0.5], [2.0, 0.25], [3.0, 0.25]])
    assert [s for s, _ in tps] == [pytest.approx(0.05), pytest.approx(0.025), pytest.approx(0.025)]


def test_a_runner_behind_several_rungs(fake_exchange, fixed_clock):
    _, tps = _open(fake_exchange, 0.1, [[1.0, 0.5], [2.0, 0.3]])
    assert [s for s, _ in tps] == [pytest.approx(0.05), pytest.approx(0.03)]
