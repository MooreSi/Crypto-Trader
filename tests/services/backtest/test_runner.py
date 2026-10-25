"""The backtest runner: walks history bar by bar with no look-ahead.

The things a backtester most often gets wrong, each pinned here:

* the generator must only see bars that had CLOSED at the decision time;
* a higher-timeframe bar is visible only once it has closed too;
* one trade per coin at a time (the live "one per coin" gate);
* entry is the signal bar's close and the exit plan starts on the NEXT bar.
"""
import pytest

from backend.src.services.backtest import catalogue, runner
from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.risk import settings

STEP = 900_000
HTF = 3_600_000


def _bars(n, price=100.0):
    return [Candle(i * STEP, price, price + 0.2, price - 0.2, price, 1.0) for i in range(n)]


def test_no_look_ahead_and_closed_htf_only():
    bars = _bars(400)
    htf = [Candle(i * HTF, 100, 101, 99, 100, 1.0) for i in range(100)]
    seen = []

    def gen(window, h):
        seen.append((window[-1].t, len(window), h[-1].t if h else None))
        return []

    runner.run_on_bars(bars, htf, gen, "15m", "1h", settings.defaults(), window=260)
    assert seen and all(n <= 260 for _, n, _ in seen)
    first_t = seen[0][0]
    assert first_t == bars[259].t
    for last_t, _, htf_t in seen:
        assert htf_t is None or htf_t + HTF <= last_t + STEP


def test_one_trade_at_a_time_and_exit_starts_next_bar():
    bars = _bars(300)
    # bar 270 signals long at 100 stop 99; bar 271 runs to 103.5 (full ladder)
    bars[271] = Candle(271 * STEP, 100, 103.5, 99.5, 103, 1.0)

    def gen(window, h):
        if window[-1].t in (270 * STEP, 271 * STEP):
            return [Setup("long", window[-1].close, 99.0, "test")]
        return []

    trades = runner.run_on_bars(bars, [], gen, "15m", None, settings.defaults(), window=260)
    assert len(trades) == 1
    t = trades[0]
    assert t["entry"] == 100.0 and t["opened_at"] == pytest.approx((270 * STEP + STEP) / 1000)
    assert t["exit"] == "tp" and t["r"] == pytest.approx(1.75 - t["fee_r"])


def test_catalogue_lists_engines_and_lab_strategies():
    names = [s["name"] for s in catalogue.describe()]
    assert {"breakout", "reversal", "trend_pa"} <= set(names)
    assert {"donchian_trend", "bb_rsi_revert", "supertrend_flip"} <= set(names)
    assert all(s["interval"] and s["about"] for s in catalogue.describe())


def test_backtest_through_the_exchange_reads_candles_only(fake_exchange, fixed_clock):
    fx = fake_exchange
    now_ms = int(fixed_clock.now() * 1000)
    rows = [Candle(now_ms - (600 - i) * STEP, 100, 100.4, 99.6, 100 + (0.1 if i % 2 else -0.1), 1.0)
            for i in range(600)]
    fx.candle_rows[("BTC", "15m")] = rows
    out = runner.backtest(fx, "breakout", "BTC", 500)
    assert out["strategy"] == "breakout" and out["coin"] == "BTC"
    assert out["bars"] >= 400 and "summary" in out
    assert not fx.calls          # nothing but reads


def test_unknown_strategy_is_refused(fake_exchange):
    with pytest.raises(ValueError):
        runner.backtest(fake_exchange, "nope", "BTC", 500)
