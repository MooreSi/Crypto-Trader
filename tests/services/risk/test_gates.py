import pytest

from backend.src.services.engines.base import Signal
from backend.src.services.risk import gates, settings

NOW = 1_792_850_000.0


def _sig(**over):
    base = dict(engine="breakout", coin="ETH", direction="long", entry=3000.0, stop=2970.0,
                created_at=NOW - 60, interval="15m", ml_score=0.7)
    base.update(over)
    return Signal(**base)


def _ctx(**over):
    s = settings.defaults()
    s["trading_enabled"] = True
    s.update(over.pop("settings", {}))
    base = dict(now=NOW, settings=s, open_trades=[], interval_seconds=900, funding_rate=0.00001,
                blackout_event=None, day_start_equity=10_000, equity=10_000, realised_today=0.0,
                ml_has_model=True)
    base.update(over)
    return gates.GateContext(**base)


def test_all_pass_records_every_gate():
    r = gates.evaluate(_sig(), _ctx())
    assert r.passed and len(r.decisions) == 11 and all(d["passed"] for d in r.decisions)


@pytest.mark.parametrize("ctx_over,sig_over,gate", [
    ({"settings": {"trading_enabled": False}}, {}, "trading enabled"),
    ({}, {"created_at": NOW - 3600}, "fresh"),
    ({}, {"ml_score": 0.3}, "ML"),
    ({"settings": {"min_reward_risk": 3.0}}, {}, "reward:risk"),
    ({"open_trades": [{"coin": "ETH", "direction": "short"}]}, {}, "one per coin"),
    ({"open_trades": [{"coin": c, "direction": "short"} for c in "ABC"]}, {}, "max positions"),
    ({"open_trades": [{"coin": c, "direction": "long"} for c in "AB"]}, {}, "correlation cap"),
    ({"funding_rate": 0.001}, {}, "funding"),
    ({"blackout_event": {"title": "USD CPI"}}, {}, "event blackout"),
    ({"equity": 9_600}, {}, "daily loss limit"),
    ({"settings": {"daily_profit_target_usd": 100}, "realised_today": 150}, {}, "daily target"),
])
def test_each_gate_refuses_on_its_own(ctx_over, sig_over, gate):
    r = gates.evaluate(_sig(**sig_over), _ctx(**ctx_over))
    assert not r.passed
    assert r.decisions[-1]["gate"] == gate
    assert all(d["passed"] for d in r.decisions[:-1])


def test_short_pays_negative_funding():
    r = gates.evaluate(_sig(direction="short", stop=3030.0), _ctx(funding_rate=-0.001))
    assert not r.passed and r.decisions[-1]["gate"] == "funding"
    ok = gates.evaluate(_sig(direction="short", stop=3030.0), _ctx(funding_rate=0.001))
    assert ok.passed


def test_no_model_passes_unless_required():
    assert gates.evaluate(_sig(ml_score=None), _ctx(ml_has_model=False)).passed
    r = gates.evaluate(_sig(ml_score=None),
                       _ctx(ml_has_model=False, settings={"ml_require_model": True}))
    assert not r.passed and r.decisions[-1]["gate"] == "ML"


def test_signal_rejects_a_stop_on_the_wrong_side():
    with pytest.raises(ValueError):
        _sig(stop=3010.0)
