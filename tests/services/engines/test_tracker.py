"""The tracker labels a signal by what the real exit plan would have made.

Entry 100, stop 98 (R = 2): with a single 3R take-profit the target is 106,
and a 0.045% taker fee each way costs 2 x 0.00045 x 100 / 2 = 0.045 R.
"""
import pytest

from backend.src.services.engines import tracker
from backend.src.services.exchange.types import Candle

SIG = {"direction": "long", "entry": 100.0, "stop": 98.0}
PLAN = {"tp_ladder": [[3.0, 1.0]], "breakeven_after_tp": 1, "fee_rate": 0.00045}
FEE_R = 0.045


def _bar(t, hi, lo, close=None):
    return Candle(t, 100.0, hi, lo, close if close is not None else (hi + lo) / 2, 1.0)


def test_one_r_is_not_a_win_when_the_plan_takes_profit_at_three_r():
    out = tracker.evaluate(SIG, [_bar(1, 101, 99.5), _bar(2, 102.1, 100.5)], PLAN)
    assert out["status"] == "tracking"


def test_win_when_the_take_profit_is_reached_first_net_of_fees():
    out = tracker.evaluate(SIG, [_bar(1, 102.1, 99.5), _bar(2, 106.1, 101.0)], PLAN)
    assert out["status"] == "win" and out["label"] == 1
    assert out["r_final"] == pytest.approx(3.0 - FEE_R)


def test_loss_when_stop_reached_first_includes_the_fees():
    out = tracker.evaluate(SIG, [_bar(1, 100.5, 97.9)], PLAN)
    assert out["status"] == "loss" and out["label"] == 0
    assert out["r_final"] == pytest.approx(-1.0 - FEE_R)


def test_bar_touching_both_is_a_loss():
    out = tracker.evaluate(SIG, [_bar(1, 106.5, 97.5)], PLAN)
    assert out["status"] == "loss"


def test_short_mirrors_long():
    short = {"direction": "short", "entry": 100.0, "stop": 102.0}
    assert tracker.evaluate(short, [_bar(1, 100.5, 93.9)], PLAN)["status"] == "win"


def test_a_partial_then_breakeven_that_fees_eat_is_a_loss():
    # stop 0.1% away: fees cost 0.9 R; half off at +1R books 0.5 R gross, the rest stops at entry
    tight = {"direction": "long", "entry": 100.0, "stop": 99.9}
    plan = dict(PLAN, tp_ladder=[[1.0, 0.5], [3.0, 0.5]])
    out = tracker.evaluate(tight, [_bar(1, 100.15, 99.95), _bar(2, 100.1, 99.95)], plan)
    assert out["status"] == "loss" and out["label"] == 0
    assert out["r_final"] == pytest.approx(0.5 - 0.9)


def test_a_traded_signal_is_judged_from_its_real_fill():
    # filled at 100.5: R is 2.5 and the 3R target moves from 106 to 108
    bars = [_bar(1, 106.5, 99.0)]
    assert tracker.evaluate(SIG, bars, PLAN)["status"] == "win"
    assert tracker.evaluate(dict(SIG, fill=100.5), bars, PLAN)["status"] == "tracking"


def test_expires_after_max_bars_with_label_zero_and_net_r():
    bars = [_bar(i, 100.5, 99.5, 100.2) for i in range(tracker.MAX_BARS)]
    out = tracker.evaluate(SIG, bars, PLAN)
    assert out["status"] == "expired" and out["label"] == 0
    assert out["r_final"] == pytest.approx(0.1 - FEE_R)


def test_still_tracking_reports_excursions():
    out = tracker.evaluate(SIG, [_bar(1, 101.0, 99.0)], PLAN)
    assert out["status"] == "tracking" and out["mfe_r"] == 0.5 and out["mae_r"] == -0.5


def test_label_version_moved_past_the_one_r_rule():
    assert tracker.LABEL_VERSION >= 2
