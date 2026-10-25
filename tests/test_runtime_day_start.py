"""The daily loss limit counts from the equity at the START of the UTC day.

Defect (2026-10-25): the day's starting equity was recorded only by the
first caller of `day.start_equity`: the dashboard or the executor. With the
dashboard closed and no signal until the afternoon, a morning loss was
already inside the "start" figure, and the loss limit allowed that much more
loss again. The positions pass runs every 10 seconds from startup, so it
records the figure as soon as the day begins.
"""
from backend.src.db import database
from backend.src.runtime import TradingRuntime
from backend.src.services.risk import day


def test_positions_pass_records_the_days_starting_equity(fake_exchange, fixed_clock):
    fake_exchange.equity = 1234.5
    assert database.get_app_config(day._key()) is None
    TradingRuntime().positions_pass()
    assert float(database.get_app_config(day._key())) == 1234.5


def test_a_later_lower_equity_does_not_replace_it(fake_exchange, fixed_clock):
    rt = TradingRuntime()
    fake_exchange.equity = 1000.0
    rt.positions_pass()
    fake_exchange.equity = 900.0
    rt.positions_pass()
    assert day.start_equity(900.0) == 1000.0
