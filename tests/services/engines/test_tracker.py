from backend.src.services.engines import tracker
from backend.src.services.exchange.types import Candle

SIG = {"direction": "long", "entry": 100.0, "stop": 98.0}


def _bar(t, hi, lo, close=None):
    return Candle(t, 100.0, hi, lo, close if close is not None else (hi + lo) / 2, 1.0)


def test_win_when_one_r_reached_first():
    out = tracker.evaluate(SIG, [_bar(1, 101, 99.5), _bar(2, 102.1, 100.5)])
    assert out["status"] == "win" and out["label"] == 1 and out["mfe_r"] >= 1


def test_loss_when_stop_reached_first():
    out = tracker.evaluate(SIG, [_bar(1, 100.5, 97.9)])
    assert out["status"] == "loss" and out["label"] == 0 and out["r_final"] == -1.0


def test_bar_touching_both_is_a_loss():
    out = tracker.evaluate(SIG, [_bar(1, 102.5, 97.5)])
    assert out["status"] == "loss"


def test_short_mirrors_long():
    short = {"direction": "short", "entry": 100.0, "stop": 102.0}
    assert tracker.evaluate(short, [_bar(1, 100.5, 97.9)])["status"] == "win"


def test_expires_after_max_bars_with_label_zero():
    bars = [_bar(i, 100.5, 99.5, 100.2) for i in range(tracker.MAX_BARS)]
    out = tracker.evaluate(SIG, bars)
    assert out["status"] == "expired" and out["label"] == 0
    assert abs(out["r_final"] - 0.1) < 1e-9


def test_still_tracking_reports_excursions():
    out = tracker.evaluate(SIG, [_bar(1, 101.0, 99.0)])
    assert out["status"] == "tracking" and out["mfe_r"] == 0.5 and out["mae_r"] == -0.5
