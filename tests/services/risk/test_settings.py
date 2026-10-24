"""The defaults are pinned. Golden rule 3: a default never changes silently.

If this test fails because a default changed, the change is wrong unless the
owner signed it off -- every existing install would start trading differently.
"""
import pytest

from backend.src.services.risk import settings


def test_conservative_defaults_are_pinned():
    d = settings.defaults()
    assert d["trading_enabled"] is False
    assert d["isolated_margin"] is True
    assert d["max_leverage"] == 3
    assert d["risk_per_trade_pct"] == 0.5
    assert d["max_open_positions"] == 3
    assert d["max_same_direction"] == 2
    assert d["daily_loss_limit_pct"] == 3.0
    assert d["daily_profit_target_usd"] == 0.0
    assert d["max_position_notional_pct"] == 300.0
    assert d["min_reward_risk"] == 1.5
    assert d["tp_ladder"] == [[1.0, 0.5], [2.0, 0.25], [3.0, 0.25]]
    assert d["blackout_enabled"] is True and d["blackout_minutes_before"] == 30
    assert d["breakeven_after_tp"] == 1 and d["trail_atr_mult"] == 0.0
    assert d["ml_require_model"] is False and d["ml_min_probability"] == 0.5
    assert d["auto_top_n"] == 20 and d["watchlist"] == [] and d["blocklist"] == []


def test_values_are_clamped_to_their_envelope(fresh_db):
    out = settings.update({"max_leverage": 500, "risk_per_trade_pct": -1})
    assert out["max_leverage"] == 50
    assert out["risk_per_trade_pct"] == 0.05


def test_risk_per_trade_may_go_up_to_100_pct_and_no_further(fresh_db):
    # Owner's decision 2026-10-24: the envelope goes up to 100%; the default stays 0.5.
    assert settings.update({"risk_per_trade_pct": 25})["risk_per_trade_pct"] == 25.0
    assert settings.update({"risk_per_trade_pct": 100})["risk_per_trade_pct"] == 100.0
    assert settings.update({"risk_per_trade_pct": 250})["risk_per_trade_pct"] == 100.0


def test_unknown_keys_and_bad_ladders_are_refused(fresh_db):
    with pytest.raises(ValueError):
        settings.update({"max_leverage_typo": 2})
    with pytest.raises(ValueError):
        settings.update({"tp_ladder": [[1.0, 0.8], [2.0, 0.5]]})   # 130% of the position


def test_update_persists(fresh_db):
    settings.update({"watchlist": ["btc", " eth "], "trading_enabled": True})
    again = settings.get()
    assert again["watchlist"] == ["BTC", "ETH"] and again["trading_enabled"] is True
