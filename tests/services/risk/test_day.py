"""The day's starting equity belongs to one account.

Changing the account mid-day kept the old account's start: from $1000 to a
$45 account the loss limit read a $955 loss; from $45 to $1000 it read a $955
profit and would not trip until that was lost too.
"""
from backend.src import config
from backend.src.db import database
from backend.src.services.risk import day


def test_each_account_has_its_own_start(fresh_db, fixed_clock, monkeypatch):
    monkeypatch.setattr(config, "account_key", lambda: "mainnet:0xold")
    assert day.start_equity(1000.0) == 1000.0
    monkeypatch.setattr(config, "account_key", lambda: "mainnet:0xnew")
    assert day.start_equity(45.0) == 45.0
    assert day.start_equity(40.0) == 45.0
    monkeypatch.setattr(config, "account_key", lambda: "mainnet:0xold")
    assert day.start_equity(900.0) == 1000.0


def test_a_start_recorded_before_the_upgrade_still_counts_today(fresh_db, fixed_clock):
    legacy = "day_start_equity:" + fixed_clock.utcnow().strftime("%Y-%m-%d")
    database.set_app_config(legacy, "500.0")
    assert day.start_equity(400.0) == 500.0
