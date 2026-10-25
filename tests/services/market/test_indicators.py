"""Indicators added for the Strategy Lab, pinned against hand-worked values."""
import pytest

from backend.src.services.exchange.types import Candle
from backend.src.services.market import indicators as ind


def _c(i, h, lo, c, o=None):
    return Candle(i * 60_000, c if o is None else o, h, lo, c, 1.0)


def test_donchian_excludes_the_latest_bar():
    bars = [_c(0, 10, 5, 7), _c(1, 12, 6, 8), _c(2, 11, 4, 9), _c(3, 20, 1, 15)]
    assert ind.donchian(bars, 3) == (12, 4)


def test_donchian_needs_enough_bars():
    assert ind.donchian([_c(0, 1, 0, 1)], 3) is None


def test_bollinger_bands_mean_plus_minus_k_population_sd():
    closes = [1.0, 2.0, 3.0, 4.0, 5.0]
    lower, mid, upper = ind.bollinger_bands(closes, 5, 2.0)
    sd = 2.0 ** 0.5        # population sd of 1..5
    assert mid == pytest.approx(3.0)
    assert upper == pytest.approx(3.0 + 2 * sd) and lower == pytest.approx(3.0 - 2 * sd)


def test_bollinger_bands_none_when_short():
    assert ind.bollinger_bands([1.0, 2.0], 5) is None


def _trend(n, start, step):
    out, p = [], start
    for i in range(n):
        out.append(_c(i, p + 0.5, p - 0.5, p + step * 0.8, o=p))
        p += step
    return out


def test_supertrend_is_up_in_a_steady_rise_and_down_in_a_steady_fall():
    up = ind.supertrend(_trend(60, 100.0, 1.0), 10, 3.0)
    down = ind.supertrend(_trend(60, 200.0, -1.0), 10, 3.0)
    assert up[-1][1] == 1 and up[-1][0] < 160
    assert down[-1][1] == -1 and down[-1][0] > 140


def test_supertrend_flips_after_a_reversal():
    bars = _trend(60, 100.0, 1.0) + [
        _c(60 + i, 160 - 4 * i + 0.5, 160 - 4 * i - 0.5, 160 - 4 * i - 3) for i in range(15)]
    dirs = [d for _, d in ind.supertrend(bars, 10, 3.0)]
    assert dirs[59] == 1 and dirs[-1] == -1


def test_supertrend_series_is_aligned_with_none_padding():
    bars = _trend(30, 100.0, 1.0)
    st = ind.supertrend(bars, 10, 3.0)
    assert len(st) == 30 and st[0] == (None, 0)
