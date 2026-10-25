"""Candles and Hyperliquid's request budget.

Defect (2026-10-25, live on mainnet): the engines refetched every series
every minute (a 20 s cache): about 80 candle requests a minute for 20
coins, ~2000 of the 1200 weight per minute Hyperliquid allows an IP
(candleSnapshot weighs 20, plus 1 per 60 bars returned). Every info call
then failed with HTTP 429, including the positions loop's account reads, so
stops could not be moved and exits were not recorded.

Two fixes, pinned here:
1. a closed series is kept until its next bar has closed (nothing new can
   exist before then), so a 4h series is fetched once every 4 hours;
2. candle fetches share a per-minute weight budget, leaving the rest of the
   allowance for the account, orders and the dashboard. Over budget, a fetch
   is refused without a request and the coin is scanned next cycle.
"""
import pytest

from backend.src.services.exchange.types import Candle
from backend.src.services.market import candles
from backend.src.utils import clock

STEP = 900_000


class Counting:
    def __init__(self, now_ms):
        self.requests = 0
        self.now_ms = now_ms

    def candles(self, coin, interval, start_ms, end_ms):
        self.requests += 1
        first = (self.now_ms // STEP) * STEP - 300 * STEP
        return [Candle(first + i * STEP, 1, 1, 1, 1, 1) for i in range(301) if first + i * STEP <= end_ms]


@pytest.fixture
def at():
    def set_ms(ms):
        clock.set_fixed(ms / 1000)
    yield set_ms
    clock.set_fixed(None)


def test_request_weight_follows_the_docs():
    assert candles.request_weight(60) == 21 and candles.request_weight(261) == 25


def test_closed_series_is_reused_until_the_next_bar_closes(at):
    t0 = 1_792_000_000_000 - (1_792_000_000_000 % STEP) + 60_000     # 1 min into a bar
    at(t0)
    src = Counting(t0)
    first = candles.closed(src, "BTC", "15m", 260)
    at(t0 + 13 * 60_000)                                              # same bar still forming
    assert candles.closed(src, "BTC", "15m", 260) == first and src.requests == 1
    at(t0 + 15 * 60_000)                                              # a new bar has closed
    src.now_ms = t0 + 15 * 60_000
    again = candles.closed(src, "BTC", "15m", 260)
    assert src.requests == 2 and again[-1].t == first[-1].t + STEP


def test_fetches_over_the_budget_are_refused_without_a_request(at, monkeypatch):
    t0 = 1_792_000_000_000
    at(t0)
    src = Counting(t0)
    monkeypatch.setattr(candles, "WEIGHT_BUDGET_PER_MIN", 3 * candles.request_weight(261))
    for coin in ("A", "B", "C"):
        candles.closed(src, coin, "15m", 260)
    with pytest.raises(candles.CandleBudgetExceeded):
        candles.closed(src, "D", "15m", 260)
    assert src.requests == 3
    at(t0 + 61_000)                                                   # the window has moved on
    candles.closed(src, "D", "15m", 260)
    assert src.requests == 4


def test_a_cached_series_needs_no_budget(at, monkeypatch):
    t0 = 1_792_000_000_000
    at(t0)
    src = Counting(t0)
    monkeypatch.setattr(candles, "WEIGHT_BUDGET_PER_MIN", candles.request_weight(261))
    candles.closed(src, "A", "15m", 260)
    assert candles.closed(src, "A", "15m", 260)      # served from cache, no refusal


def test_an_engine_defers_coins_over_budget_instead_of_failing(fake_exchange, fixed_clock, monkeypatch):
    from backend.src.services.engines.service import EngineService
    from backend.src.services.engines.signal_repo import SignalStore
    from backend.src.services.ml.model import EngineModel
    import tempfile
    from pathlib import Path
    monkeypatch.setattr(candles, "WEIGHT_BUDGET_PER_MIN", 0)
    d = Path(tempfile.mkdtemp())
    eng = EngineService("breakout", "15m", lambda b, h: [], (), SignalStore(d / "x.db"),
                        EngineModel("breakout", ("a",), d))
    out = eng.cycle(fake_exchange)
    assert "error" not in out and eng.last_error == ""
