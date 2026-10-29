"""The Calendar's reads: closed trades filed by UTC day, and events by day."""
from datetime import datetime, timezone

import pytest

from backend.src.db import database
from backend.src.services.calendar import calendar_view


def _ts(*a):
    return datetime(*a, tzinfo=timezone.utc).timestamp()


def _trade(closed_at, pnl, fees=1.0, risk=10.0, status="closed", coin="BTC", engine="breakout"):
    database.get().execute(
        "INSERT INTO trades(engine, coin, direction, status, network, entry_price, size, "
        "initial_size, stop_loss, initial_stop, take_profits, leverage, risk_usd, opened_at, "
        "closed_at, close_price, close_reason, realised_pnl, fees) "
        "VALUES(?, ?, 'long', ?, 'paper', 100, 1, 1, 90, 90, '[]', 3, ?, ?, ?, 101, 'tp', ?, ?)",
        (engine, coin, status, risk, closed_at - 3600, closed_at if status == "closed" else None,
         pnl, fees))


def test_rows_are_filed_by_the_utc_day_of_the_close(fresh_db, fixed_clock):
    # 23:30 UTC on the 22nd and 00:30 UTC on the 23rd are different trading days.
    _trade(_ts(2026, 10, 22, 23, 30), 21.0)
    _trade(_ts(2026, 10, 23, 0, 30), -9.0)
    out = calendar_view.closed_trades(30)
    assert out["today"] == "2026-10-24"
    assert [r["day"] for r in out["rows"]] == ["2026-10-23", "2026-10-22"]   # newest first
    first = out["rows"][1]
    assert first["net_pnl"] == pytest.approx(20.0)
    assert first["r"] == pytest.approx(2.0)
    assert first["session"] == "Late US"


def test_open_trades_and_closes_outside_the_window_are_left_out(fresh_db, fixed_clock):
    _trade(fixed_clock.now() - 3600, 5.0, status="open")
    _trade(fixed_clock.now() - 40 * 86400, 5.0)
    _trade(fixed_clock.now() - 3600, 5.0)
    assert len(calendar_view.closed_trades(30)["rows"]) == 1


def test_a_trade_with_no_risk_has_no_r(fresh_db, fixed_clock):
    _trade(fixed_clock.now() - 60, 5.0, risk=0.0)
    assert calendar_view.closed_trades(1)["rows"][0]["r"] is None


def test_window_is_bounded():
    with pytest.raises(ValueError):
        calendar_view.closed_trades(0)
    with pytest.raises(ValueError):
        calendar_view.closed_trades(calendar_view.MAX_DAYS + 1)


def test_events_between_cover_whole_days_and_clamp_a_month_end(fresh_db):
    from backend.src.services.events import events_repo
    events_repo.upsert_many([
        {"uid": "a", "ts": _ts(2026, 2, 1, 0, 0), "title": "first", "kind": "macro",
         "impact": "high", "coins": "", "source": "feed"},
        {"uid": "b", "ts": _ts(2026, 2, 28, 23, 59), "title": "last", "kind": "macro",
         "impact": "low", "coins": "BTC", "source": "user"},
        {"uid": "c", "ts": _ts(2026, 3, 1, 0, 0), "title": "next month", "kind": "macro",
         "impact": "low", "coins": "", "source": "user"},
    ])
    out = calendar_view.events_between("2026-02-01", "2026-02-31")
    assert [(e["day"], e["title"]) for e in out] == [("2026-02-01", "first"), ("2026-02-28", "last")]


def test_events_between_refuses_a_backwards_range(fresh_db):
    with pytest.raises(ValueError):
        calendar_view.events_between("2026-03-01", "2026-02-01")
