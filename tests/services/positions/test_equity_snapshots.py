"""The equity curve belongs to one account.

Defect (2026-10-27): snapshots carried no account, and an empty or
unconfigured account read as $0. Changing the account address put $0 points
in the mainnet curve and the dashboard reported a 100% drawdown.
"""
from backend.src import config
from backend.src.runtime import TradingRuntime
from backend.src.services.health import account_view
from backend.src.services.positions import trades_repo, trades_repo_view
from backend.src.utils import clock


def test_a_zero_equity_reading_is_not_recorded(fake_exchange, fixed_clock):
    fake_exchange.equity = 0.0
    TradingRuntime().positions_pass()
    assert trades_repo.equity_curve(0.0, config.account_key()) == []


def test_a_positive_reading_is_recorded(fake_exchange, fixed_clock):
    fake_exchange.equity = 45.0
    TradingRuntime().positions_pass()
    assert [p["equity"] for p in trades_repo.equity_curve(0.0, config.account_key())] == [45.0]


def test_the_curve_is_the_current_accounts_only(fresh_db, fixed_clock):
    trades_repo.snapshot_equity(1000.0, "mainnet:0xold")
    clock.set_fixed(clock.now() + 300)
    trades_repo.snapshot_equity(45.0, "mainnet:0xnew")
    clock.set_fixed(clock.now() + 300)
    trades_repo.snapshot_equity(44.0, "mainnet:0xnew")
    assert [p["equity"] for p in trades_repo.equity_curve(0.0, "mainnet:0xnew")] == [45.0, 44.0]
    assert [p["equity"] for p in trades_repo.equity_curve(0.0, "mainnet:0xold")] == [1000.0]


def test_rows_from_before_the_account_column_still_count_but_not_zeros(fresh_db, fixed_clock):
    fresh_db.execute("INSERT INTO equity_snapshots(ts, equity) VALUES(?, ?)", (clock.now(), 45.0))
    fresh_db.execute("INSERT INTO equity_snapshots(ts, equity) VALUES(?, ?)", (clock.now() + 1, 0.0))
    assert [p["equity"] for p in trades_repo.equity_curve(0.0, "mainnet:0xabc")] == [45.0]


def test_switching_account_shows_no_drawdown(fake_exchange, fixed_clock, monkeypatch):
    monkeypatch.setattr(config, "account_key", lambda: "mainnet:0xold")
    trades_repo.snapshot_equity(1000.0, config.account_key())
    monkeypatch.setattr(config, "account_key", lambda: "mainnet:0xnew")
    clock.set_fixed(clock.now() + 300)
    trades_repo.snapshot_equity(45.0, config.account_key())
    assert trades_repo_view.analytics()["max_drawdown_pct"] == 0.0
    assert [p["equity"] for p in account_view.equity_curve(30)] == [45.0]
