from backend.src.services.engines.base import Signal
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings
from backend.src.services.trading import executor


def _sig(fixed_clock, **over):
    base = dict(engine="breakout", coin="ETH", direction="long", entry=3000.0, stop=2970.0,
                created_at=fixed_clock.now() - 60, interval="15m", ml_score=None, id=1)
    base.update(over)
    return Signal(**base)


def test_master_switch_off_places_nothing_and_records_why(fake_exchange, fixed_clock):
    out = executor.execute(fake_exchange, _sig(fixed_clock), ml_has_model=False)
    assert not out.placed and out.reason.startswith("trading enabled")
    assert not [c for c in fake_exchange.calls if c[0] in ("market", "trigger")]
    d = trades_repo.recent_gate_decisions(1)[0]
    assert d["passed"] == 0 and d["decisions"][-1]["gate"] == "trading enabled"


def test_passing_signal_becomes_a_protected_trade(fake_exchange, fixed_clock):
    settings.update({"trading_enabled": True})
    out = executor.execute(fake_exchange, _sig(fixed_clock), ml_has_model=False)
    assert out.placed and out.trade_id
    t = trades_repo.get(out.trade_id)
    assert t["status"] == "open" and t["sl_oid"]
    assert trades_repo.recent_gate_decisions(1)[0]["passed"] == 1
    # risk is 0.5% of 10,000 at most
    assert t["risk_usd"] <= 50.0 + 1e-9


def test_sizing_refusal_is_recorded(fake_exchange, fixed_clock):
    settings.update({"trading_enabled": True})
    fake_exchange.equity = fake_exchange.available = 10.0      # 0.5% risk sizes to ~$5 notional
    out = executor.execute(fake_exchange, _sig(fixed_clock), ml_has_model=False)
    assert not out.placed and out.reason.startswith("sizing")
    assert trades_repo.recent_gate_decisions(1)[0]["decisions"][-1]["gate"] == "sizing"


def test_second_signal_on_same_coin_is_refused(fake_exchange, fixed_clock):
    settings.update({"trading_enabled": True})
    assert executor.execute(fake_exchange, _sig(fixed_clock), ml_has_model=False).placed
    again = executor.execute(fake_exchange, _sig(fixed_clock, id=2), ml_has_model=False)
    assert not again.placed and again.reason.startswith("one per coin")
