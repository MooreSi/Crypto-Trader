"""The backtest trade simulator, against hand-worked R multiples.

The simulator replays one setup bar by bar with the SAME exit plan the live
app uses (stop, TP ladder of R multiples, breakeven after TP n) and the same
conservative rule as the tracker: a bar that touches both the stop and a
target is a loss for whatever is still open.
"""
import pytest

from backend.src.services.backtest import simulator as sim
from backend.src.services.exchange.types import Candle

LADDER = [[1.0, 0.5], [2.0, 0.25], [3.0, 0.25]]


def _b(i, h, lo, c=None):
    return Candle(i * 900_000, lo, h, lo, c if c is not None else (h + lo) / 2, 1.0)


def run(bars, direction="long", entry=100.0, stop=99.0, ladder=LADDER, be=1, fee=0.0, max_bars=192):
    return sim.simulate(direction, entry, stop, bars, ladder, be, fee, max_bars)


def test_stop_first_is_minus_one():
    r = run([_b(0, 100.5, 98.9)])
    assert r["r"] == pytest.approx(-1.0) and r["exit"] == "stop" and r["exit_index"] == 0


def test_tp1_then_breakeven_stop_books_half_an_r():
    r = run([_b(0, 101.1, 99.5), _b(1, 100.8, 99.9)])
    assert r["r"] == pytest.approx(0.5) and r["exit"] == "breakeven" and r["tp_hits"] == 1


def test_full_ladder_pays_the_weighted_r():
    r = run([_b(0, 101.2, 99.6), _b(1, 102.1, 100.5), _b(2, 103.5, 101.5)])
    assert r["r"] == pytest.approx(0.5 * 1 + 0.25 * 2 + 0.25 * 3) and r["exit"] == "tp"


def test_a_bar_touching_stop_and_target_is_a_loss():
    r = run([_b(0, 101.5, 98.5)])
    assert r["r"] == pytest.approx(-1.0) and r["exit"] == "stop"


def test_breakeven_takes_effect_from_the_next_bar():
    # TP1 and a dip under entry in the same bar: the dip does not stop out at BE
    r = run([_b(0, 101.1, 99.5), _b(1, 102.2, 100.2), _b(2, 101.0, 99.9)])
    assert r["tp_hits"] == 2 and r["exit"] == "breakeven"
    assert r["r"] == pytest.approx(0.5 + 0.5)


def test_expiry_marks_the_rest_to_the_last_close():
    bars = [_b(i, 100.6, 99.6, 100.4) for i in range(5)]
    r = run(bars, max_bars=5)
    assert r["exit"] == "expired" and r["r"] == pytest.approx(0.4)


def test_unresolved_when_bars_run_out():
    r = run([_b(0, 100.6, 99.6, 100.2)])
    assert r["exit"] == "open"


def test_round_trip_fee_is_charged_in_r():
    r = run([_b(0, 100.5, 98.9)], fee=0.0005)
    assert r["fee_r"] == pytest.approx(2 * 0.0005 * 100 / 1.0)
    assert r["r"] == pytest.approx(-1.0 - 0.1)


def test_short_mirrors_long():
    r = run([_b(0, 99.5, 98.9), _b(1, 100.1, 99.2)], direction="short", entry=100.0, stop=101.0)
    assert r["r"] == pytest.approx(0.5) and r["exit"] == "breakeven"


def test_a_partial_ladder_lets_the_rest_ride_to_the_stop():
    r = run([_b(0, 101.1, 99.5), _b(1, 100.5, 99.9)], ladder=[[1.0, 0.5]])
    assert r["r"] == pytest.approx(0.5)


def test_no_breakeven_when_switched_off():
    r = run([_b(0, 101.1, 99.5), _b(1, 100.5, 98.9)], be=0)
    assert r["r"] == pytest.approx(0.5 * 1 + 0.5 * -1)


def test_summary_metrics():
    trades = [{"t": float(i), "r": r} for i, r in enumerate([1.0, -1.0, 2.0, -1.0, -1.0, 0.5])]
    s = sim.summarise(trades, risk_pct=1.0)
    assert s["trades"] == 6 and s["wins"] == 3 and s["win_rate"] == pytest.approx(0.5)
    assert s["total_r"] == pytest.approx(0.5) and s["avg_r"] == pytest.approx(0.5 / 6)
    assert s["profit_factor"] == pytest.approx(3.5 / 3.0)
    assert s["max_drawdown_r"] == pytest.approx(2.0)
    growth = 1.01 * 0.99 * 1.02 * 0.99 * 0.99 * 1.005
    assert s["compounded_return_pct"] == pytest.approx((growth - 1) * 100)
    assert [p["r"] for p in s["curve"]] == pytest.approx([1, 0, 2, 1, 0, 0.5])


def test_summary_of_nothing():
    s = sim.summarise([], risk_pct=1.0)
    assert s["trades"] == 0 and s["profit_factor"] is None and s["win_rate"] is None


def test_profit_factor_without_losses_is_none_not_infinite():
    assert sim.summarise([{"t": 0.0, "r": 1.0}], 1.0)["profit_factor"] is None


def test_stop_lock_moves_the_stop_to_the_lock_price_not_entry():
    # 2026-10-29: TP1 80% at 1.5R, stop locked at 1.5R for the 20% runner.
    bars = [_b(0, 101.6, 99.5, 101.55), _b(1, 101.4, 101.0)]
    r = sim.simulate("long", 100.0, 99.0, bars, [[1.5, 0.8]], 1, 0.0, 192, stop_lock_r=1.5)
    assert r["r"] == pytest.approx(0.8 * 1.5 + 0.2 * 1.5) and r["exit"] == "stop"


def test_short_stop_lock():
    bars = [_b(0, 100.5, 98.4, 98.45), _b(1, 99.0, 98.6)]
    r = sim.simulate("short", 100.0, 101.0, bars, [[1.5, 0.8]], 1, 0.0, 192, stop_lock_r=1.5)
    assert r["r"] == pytest.approx(1.5)


def test_no_lock_by_default_is_breakeven():
    bars = [_b(0, 101.6, 99.5), _b(1, 101.4, 99.9)]
    r = sim.simulate("long", 100.0, 99.0, bars, [[1.5, 0.8]], 1, 0.0, 192)
    assert r["r"] == pytest.approx(0.8 * 1.5) and r["exit"] == "breakeven"


def test_a_lock_beyond_the_close_falls_back_to_entry():
    # As live: a stop past the price would fire at once, so it goes to entry.
    bars = [_b(0, 101.6, 99.5, 101.2), _b(1, 101.4, 99.9)]
    r = sim.simulate("long", 100.0, 99.0, bars, [[1.5, 0.8]], 1, 0.0, 192, stop_lock_r=1.5)
    assert r["r"] == pytest.approx(0.8 * 1.5) and r["exit"] == "breakeven"
