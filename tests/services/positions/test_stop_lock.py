"""After TP1 the stop can lock in profit (`stop_lock_r`), then trail the runner.

Added 2026-10-29 for the "TP1 80% at 1.5R + trailed runner" strategy
(docs/specs/001-strategies.md). `stop_lock_r` = 0 (the default) is the old
breakeven move to entry. A lock price that is no longer on the safe side of
the mid would fire at once, so the stop goes to entry instead and the trail
tightens it later.
"""
import pytest

from backend.src.services.engines.base import Signal
from backend.src.services.positions import manager, trades_repo
from backend.src.services.risk import settings
from backend.src.services.risk.sizing import SizeDecision
from backend.src.services.trading import order_service
from tests.fakes import make_candles

RUNNER = [[1.5, 0.8]]


def _open(fx, direction="long", entry=3000.0, stop=2970.0, size=0.1, **plan):
    s = settings.update({"tp_ladder": RUNNER, **plan})
    sig = Signal(engine="reversal", coin="ETH", direction=direction, entry=entry, stop=stop,
                 created_at=0, interval="15m", reason="test")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    d = SizeDecision(True, size=size, leverage=1, risk_usd=abs(entry - stop) * size,
                     notional=size * entry, margin=size * entry)
    return trades_repo.get(order_service.open_trade(fx, market, sig, d, s, []))


def _stops(fx):
    return [o for o in fx.orders if o.kind == "stop"]


def _flat_candles(fx, clock, price=3000.0):
    # constant closes with a 0.2% spread: every true range is 12, so ATR(14) = 12
    start = clock.now_ms() - 61 * 900_000
    fx.candle_rows[("ETH", "15m")] = make_candles([price] * 60, start_ms=start)


def test_stop_locks_at_tp1_for_the_runner(fake_exchange, fixed_clock):
    fx = fake_exchange
    t = _open(fx, stop_lock_r=1.5)
    fx.mid["ETH"] = 3046.0
    fx.fire(t["tp_oids"][0], 3045.0, fixed_clock.now_ms() + 1000)
    manager.manage(fx)
    after = trades_repo.get(t["id"])
    assert after["status"] == "open" and after["tp_hit"] == 1
    assert after["size"] == pytest.approx(0.02)
    assert after["stop_loss"] == 3045.0
    stops = _stops(fx)
    assert len(stops) == 1 and stops[0].trigger_price == 3045.0
    assert stops[0].size == pytest.approx(0.02)


def test_short_stop_locks_at_tp1(fake_exchange, fixed_clock):
    fx = fake_exchange
    t = _open(fx, direction="short", entry=3000.0, stop=3030.0, stop_lock_r=1.5)
    fx.mid["ETH"] = 2954.0
    fx.fire(t["tp_oids"][0], 2955.0, fixed_clock.now_ms() + 1000)
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 2955.0


def test_lock_falls_back_to_entry_when_price_is_back_through_it(fake_exchange, fixed_clock):
    fx = fake_exchange
    t = _open(fx, stop_lock_r=1.5)
    fx.mid["ETH"] = 3040.0                      # below the 3045 lock: a stop there fires at once
    fx.fire(t["tp_oids"][0], 3045.0, fixed_clock.now_ms() + 1000)
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 3000.0


def test_no_lock_by_default_moves_to_entry(fake_exchange, fixed_clock):
    fx = fake_exchange
    t = _open(fx)
    fx.mid["ETH"] = 3046.0
    fx.fire(t["tp_oids"][0], 3045.0, fixed_clock.now_ms() + 1000)
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 3000.0


def test_the_trail_raises_the_locked_stop_and_never_lowers_it(fake_exchange, fixed_clock):
    fx = fake_exchange
    _flat_candles(fx, fixed_clock)
    t = _open(fx, stop_lock_r=1.5, trail_atr_mult=1.5)
    fx.mid["ETH"] = 3050.0                      # trail candidate 3050 - 18 = 3032, below the lock
    fx.fire(t["tp_oids"][0], 3045.0, fixed_clock.now_ms() + 1000)
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 3045.0
    fx.mid["ETH"] = 3100.0                      # candidate 3082
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 3082.0
    fx.mid["ETH"] = 3060.0                      # candidate 3042: looser, ignored
    manager.manage(fx)
    assert trades_repo.get(t["id"])["stop_loss"] == 3082.0
    stops = _stops(fx)
    assert len(stops) == 1 and stops[0].size == pytest.approx(0.02)


def test_a_runner_stopped_in_profit_is_named_so(fake_exchange, fixed_clock):
    fx = fake_exchange
    t = _open(fx, stop_lock_r=1.5)
    fx.mid["ETH"] = 3046.0
    fx.fire(t["tp_oids"][0], 3045.0, fixed_clock.now_ms() + 1000)
    manager.manage(fx)
    fx.fire(_stops(fx)[0].oid, 3045.0, fixed_clock.now_ms() + 2000)
    manager.manage(fx)
    closed = trades_repo.get(t["id"])
    assert closed["status"] == "closed" and closed["close_reason"] == "stop in profit"
