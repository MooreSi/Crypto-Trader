"""Walk-forward tuning: choose on the past, judge on the future, change nothing.

The point of walk-forward is that a parameter set is only ever scored on
bars it was NOT chosen on. The tests below build price paths where the
in-sample winner loses out of sample, so a tuner that peeked at the test
window would choose differently and the test would fail.
"""
import pytest

from backend.src.services.backtest import catalogue, tuning
from backend.src.services.engines.service import Setup
from backend.src.services.exchange.types import Candle
from backend.src.services.risk import settings
from backend.src.services.strategies import bb_rsi_revert, donchian_trend, supertrend_flip

STEP = 900_000


def test_folds_are_contiguous_and_test_follows_train():
    f = tuning.folds(n_bars=1260, warmup=260, k=4)
    assert len(f) == 4
    seg = 1000 // 5
    assert f[0] == (260, 260 + seg, 260 + seg, 260 + 2 * seg)
    for (a, b, c, d), nxt in zip(f, f[1:] + [None]):
        assert a < b == c < d
        if nxt:
            assert nxt[0] == c and nxt[2] == d     # rolling: this test window trains the next fold


def test_too_little_history_is_refused():
    with pytest.raises(ValueError):
        tuning.folds(n_bars=300, warmup=260, k=4)


def _path(segments):
    """Bars that rise by `drift` per bar within each segment, flat wicks of 0.6."""
    bars, p, i = [], 100.0, 0
    for n, drift in segments:
        for _ in range(n):
            nxt = p + drift
            bars.append(Candle(i * STEP, p, max(p, nxt) + 0.6, min(p, nxt) - 0.6, nxt, 1.0))
            p, i = nxt, i + 1
    return bars


def _side_strategy():
    """A strategy whose one parameter is the side it trades, every 10th bar."""
    def generate(bars, htf, p=None):
        side = (p or {}).get("side", "long")
        if (bars[-1].t // STEP) % 10:
            return []
        c = bars[-1].close
        return [Setup(side, c, c - 2.0 if side == "long" else c + 2.0, side)]
    return catalogue.Strategy("side_test", "15m", None, generate, "lab", "test",
                              {"side": ["long", "short"]}, {"side": "long"})


def test_choice_is_made_on_train_bars_only():
    # warm-up flat, train segment rises (longs win), test segment falls (longs lose)
    bars = _path([(260, 0.0), (400, 0.5), (400, -0.5)])
    out = tuning.walk_forward(bars, [], _side_strategy(), settings.defaults(), k=1, min_trades=5,
                              ladders=False)
    fold = out["folds"][0]
    assert fold["chosen"]["side"] == "long"            # what the PAST said
    assert fold["test"]["total_r"] < 0                 # and it is judged on the future
    assert out["oos"]["total_r"] == pytest.approx(fold["test"]["total_r"])


def test_a_choice_with_too_few_trades_is_never_picked():
    def generate(bars, htf, p=None):
        rare = (p or {}).get("rare", False)
        every = 200 if rare else 10
        if (bars[-1].t // STEP) % every:
            return []
        c = bars[-1].close
        return [Setup("long", c, c - 2.0, "x")]
    strat = catalogue.Strategy("rare_test", "15m", None, generate, "lab", "t",
                               {"rare": [False, True]}, {"rare": False})
    bars = _path([(260, 0.0), (400, 0.5), (400, 0.5)])
    out = tuning.walk_forward(bars, [], strat, settings.defaults(), k=1, min_trades=5, ladders=False)
    assert out["folds"][0]["chosen"]["rare"] is False


def test_report_compares_with_defaults_and_measures_stability():
    bars = _path([(260, 0.0), (300, 0.5), (300, 0.5), (300, 0.5)])
    out = tuning.walk_forward(bars, [], _side_strategy(), settings.defaults(), k=2, min_trades=3)
    assert set(out) >= {"folds", "oos", "oos_default", "proposal", "stability", "beats_default"}
    assert 0 < out["stability"] <= 1
    assert out["proposal"]["side"] in ("long", "short")
    assert "tp_ladder" in out["proposal"] and "breakeven_after_tp" in out["proposal"]


def test_lab_defaults_reproduce_the_untuned_strategy():
    for mod in (donchian_trend, bb_rsi_revert, supertrend_flip):
        assert set(mod.DEFAULTS) == set(catalogue.get(mod.__name__.rsplit(".", 1)[1]).grid)
        for name, values in catalogue.get(mod.__name__.rsplit(".", 1)[1]).grid.items():
            assert mod.DEFAULTS[name] in values, (mod.__name__, name)


def test_tune_reads_candles_only_and_changes_no_setting(fake_exchange, fixed_clock):
    now_ms = int(fixed_clock.now() * 1000)
    fake_exchange.candle_rows[("ETH", "15m")] = [
        Candle(now_ms - (1300 - i) * STEP, 100, 100.4, 99.6, 100 + (0.1 if i % 2 else -0.1), 1.0)
        for i in range(1300)]
    before = settings.get()
    out = tuning.tune(fake_exchange, "bb_rsi_revert", "ETH", 1200, k=3)
    assert out["strategy"] == "bb_rsi_revert" and len(out["folds"]) == 3
    assert not fake_exchange.calls
    assert settings.get() == before


def test_a_fold_where_nothing_qualifies_says_it_fell_back_to_the_defaults():
    bars = _path([(260, 0.0), (400, 0.5), (400, 0.5)])
    out = tuning.walk_forward(bars, [], _side_strategy(), settings.defaults(), k=1, min_trades=500,
                              ladders=False)
    fold = out["folds"][0]
    assert fold["fallback"] is True and fold["chosen"]["side"] == "long"   # the default


def test_beating_the_defaults_is_not_the_same_as_making_money():
    # both lose out of sample (falling test segment); "profitable" must say so
    bars = _path([(260, 0.0), (400, 0.5), (400, -0.5)])
    out = tuning.walk_forward(bars, [], _side_strategy(), settings.defaults(), k=1, min_trades=5,
                              ladders=False)
    assert out["profitable"] is False
    assert out["folds"][0]["fallback"] is False
