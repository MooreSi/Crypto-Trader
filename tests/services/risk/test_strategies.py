"""Strategies: named sets of risk settings, one of them active.

Activating a strategy writes its values into the risk settings, which is
what the executor and the position manager read. See
docs/specs/001-strategies.md.
"""
import pytest

from backend.src.services.risk import settings, strategies


def test_the_default_is_created_once_and_activated(fresh_db):
    settings.update({"risk_per_trade_pct": 5.0, "max_leverage": 1})
    out = strategies.ensure_default()
    assert out is not None
    listing = strategies.list_all()
    assert len(listing["items"]) == 1
    default = listing["items"][0]
    assert listing["active"] == default["id"]
    p = default["params"]
    assert p["tp_ladder"] == [[1.5, 0.8]]
    assert p["stop_lock_r"] == 1.5 and p["trail_atr_mult"] == 1.5
    assert p["breakeven_after_tp"] == 1
    # everything else is the owner's current settings: only the exits change
    assert p["risk_per_trade_pct"] == 5.0 and p["max_leverage"] == 1
    live = settings.get()
    assert live["tp_ladder"] == [[1.5, 0.8]] and live["stop_lock_r"] == 1.5
    assert live["trail_atr_mult"] == 1.5 and live["risk_per_trade_pct"] == 5.0
    # a second call (next boot) does nothing, even after the owner deletes it
    assert strategies.ensure_default() is None
    assert len(strategies.list_all()["items"]) == 1


def test_seeding_never_touches_the_master_switch_or_lists(fresh_db):
    settings.update({"trading_enabled": True, "watchlist": ["BTC"], "isolated_margin": True})
    strategies.ensure_default()
    live = settings.get()
    assert live["trading_enabled"] is True and live["watchlist"] == ["BTC"]
    assert "trading_enabled" not in strategies.KEYS and "watchlist" not in strategies.KEYS


def test_create_fills_missing_values_from_current_settings(fresh_db):
    s = strategies.create("Scalp", {"tp_ladder": [[1.0, 1.0]], "max_leverage": 2}, "fast")
    assert s["name"] == "Scalp" and s["notes"] == "fast"
    assert s["params"]["max_leverage"] == 2
    assert s["params"]["risk_per_trade_pct"] == settings.get()["risk_per_trade_pct"]
    assert set(s["params"]) == set(strategies.KEYS)
    assert settings.get()["max_leverage"] == 3          # creating does not apply it


def test_values_are_clamped_like_risk_settings(fresh_db):
    s = strategies.create("Wild", {"max_leverage": 500})
    assert s["params"]["max_leverage"] == 50


@pytest.mark.parametrize("params", [{"trading_enabled": True}, {"watchlist": ["BTC"]},
                                    {"nope": 1}, {"tp_ladder": [[1.0, 0.9], [2.0, 0.9]]}])
def test_refuses_keys_a_strategy_does_not_own_and_bad_values(fresh_db, params):
    with pytest.raises(ValueError):
        strategies.create("Bad", params)


@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
def test_refuses_a_bad_name(fresh_db, name):
    with pytest.raises(ValueError):
        strategies.create(name, {})


def test_refuses_a_duplicate_name(fresh_db):
    strategies.create("A", {})
    with pytest.raises(ValueError):
        strategies.create(" a ", {})


def test_activate_applies_and_editing_the_active_one_reapplies(fresh_db):
    s = strategies.create("Two TPs", {"tp_ladder": [[1.0, 0.5], [2.0, 0.5]], "max_leverage": 2})
    strategies.activate(s["id"])
    assert settings.get()["max_leverage"] == 2
    assert strategies.list_all()["active"] == s["id"]
    strategies.update(s["id"], "Two TPs", {"max_leverage": 4}, "")
    assert settings.get()["max_leverage"] == 4
    assert settings.get()["tp_ladder"] == [[1.0, 0.5], [2.0, 0.5]]


def test_editing_an_inactive_one_does_not_apply(fresh_db):
    a = strategies.create("A", {"max_leverage": 2})
    b = strategies.create("B", {"max_leverage": 5})
    strategies.activate(a["id"])
    strategies.update(b["id"], "B", {"max_leverage": 6}, "")
    assert settings.get()["max_leverage"] == 2


def test_the_active_one_cannot_be_deleted(fresh_db):
    a = strategies.create("A", {})
    b = strategies.create("B", {})
    strategies.activate(a["id"])
    with pytest.raises(ValueError):
        strategies.delete(a["id"])
    strategies.delete(b["id"])
    assert [x["id"] for x in strategies.list_all()["items"]] == [a["id"]]


def test_unknown_id_is_a_key_error(fresh_db):
    with pytest.raises(KeyError):
        strategies.activate("missing")


def test_listing_shows_where_settings_drifted_from_the_active_strategy(fresh_db):
    a = strategies.create("A", {"max_leverage": 2})
    strategies.activate(a["id"])
    assert strategies.list_all()["drift"] == []
    settings.update({"max_leverage": 3})                # changed on the Risk page
    assert strategies.list_all()["drift"] == ["max_leverage"]
