"""Each generator fires on the pattern it describes and stays quiet without it."""
from backend.src.services.breakout import generator as breakout
from backend.src.services.exchange.types import Candle
from backend.src.services.reversal import generator as reversal
from backend.src.services.trend_pa import generator as trend_pa


def _c(i, o, h, lo, c, v=100.0, step=900_000):
    return Candle(1_700_000_000_000 + i * step, o, h, lo, c, v)


def _flat(n, price=100.0, wiggle=0.3, vol=100.0):
    out = []
    for i in range(n):
        d = wiggle if i % 2 else -wiggle
        out.append(_c(i, price, price + abs(d) + 0.2, price - abs(d) - 0.2, price + d, vol))
    return out


def test_breakout_fires_long_on_a_volume_break_of_a_tight_range():
    bars = _flat(80)
    n = len(bars)
    bars.append(_c(n, 100.2, 103.5, 100.1, 103.0, 1000.0))
    setups = breakout.generate(bars, [])
    assert len(setups) == 1 and setups[0].direction == "long"
    assert setups[0].stop < setups[0].entry == 103.0
    assert set(setups[0].extra) == set(breakout.EXTRA_FEATURES)


def test_breakout_quiet_without_volume():
    bars = _flat(80)
    bars.append(_c(80, 100.2, 103.5, 100.1, 103.0, 100.0))
    assert breakout.generate(bars, []) == []


def test_trend_pa_long_on_rejection_of_ema20_in_uptrend():
    bars, price = [], 100.0
    for i in range(240):
        price *= 1.004
        bars.append(_c(i, price * 0.998, price * 1.003, price * 0.996, price, step=3_600_000))
    last = bars[-1].close
    # pull back to EMA20 (a few % below in a steady 0.4%/bar trend) and reject it
    from backend.src.services.market import indicators as ind
    e20 = ind.ema([b.close for b in bars], 20)[-1]
    bars.append(_c(240, e20 * 1.004, e20 * 1.012, e20 * 0.995, e20 * 1.010, step=3_600_000))
    setups = trend_pa.generate(bars, [])
    assert len(setups) == 1 and setups[0].direction == "long"
    assert setups[0].stop < setups[0].entry
    assert last > e20


def test_trend_pa_quiet_in_a_range():
    assert trend_pa.generate(_flat(260), []) == []


def test_reversal_sweep_of_low_then_structure_shift_goes_long():
    bars = _flat(90, 100.0, 0.3)
    n = len(bars)
    # a swing low at 98 inside the level window, and a minor swing high at
    # 100.9 just before the sweep for the structure shift to break
    bars[60] = _c(60, 99.5, 99.6, 98.0, 99.4)
    bars[n - 3] = _c(n - 3, 100.0, 100.9, 99.7, 100.2)
    bars += [
        _c(n, 99.6, 99.8, 99.2, 99.4),
        _c(n + 1, 99.4, 99.5, 97.6, 98.6),     # sweeps 98.0, closes back above
        _c(n + 2, 98.6, 101.2, 98.5, 101.0),   # closes above the last minor swing high
        _c(n + 3, 100.8, 101.5, 100.6, 101.4),  # trigger: bullish close
    ]
    setups = reversal.generate(bars, [])
    assert len(setups) == 1 and setups[0].direction == "long"
    assert setups[0].stop < 97.6


def test_reversal_quiet_without_a_sweep():
    assert reversal.generate(_flat(120), []) == []


# ── 2026-10-27: entry filters, chosen on 12 coins' history (first 60%) and
# checked on the last 40%; see the engines domain README.

def _daily(n, start, step_pct):
    out, price = [], start
    for i in range(n):
        nxt = price * (1 + step_pct)
        out.append(_c(i, price, max(price, nxt) * 1.002, min(price, nxt) * 0.998, nxt,
                      step=86_400_000))
        price = nxt
    return out


def _reversal_long_bars():
    bars = _flat(90, 100.0, 0.3)
    n = len(bars)
    bars[60] = _c(60, 99.5, 99.6, 98.0, 99.4)
    bars[n - 3] = _c(n - 3, 100.0, 100.9, 99.7, 100.2)
    bars += [
        _c(n, 99.6, 99.8, 99.2, 99.4),
        _c(n + 1, 99.4, 99.5, 97.6, 98.6),
        _c(n + 2, 98.6, 101.2, 98.5, 101.0),
        _c(n + 3, 100.8, 101.5, 100.6, 101.4),
    ]
    return bars


def test_reversal_takes_a_sweep_with_the_daily_trend():
    setups = reversal.generate(_reversal_long_bars(), _daily(60, 60.0, 0.004))
    assert len(setups) == 1 and setups[0].direction == "long"


def test_reversal_skips_a_sweep_against_the_daily_trend():
    # Out of sample, sweeps against the daily EMA10/20 lost; with it they won.
    assert reversal.generate(_reversal_long_bars(), _daily(60, 200.0, -0.004)) == []


def test_breakout_skips_a_break_that_closes_mid_bar():
    bars = _flat(80)
    # breaks the range on volume but closes in the middle of its own bar:
    # the buyers did not hold it
    bars.append(_c(80, 100.2, 105.0, 100.1, 102.6, 1000.0))
    assert breakout.generate(bars, []) == []


def _trend_bars():
    bars, price = [], 100.0
    for i in range(240):
        price *= 1.004
        bars.append(_c(i, price * 0.998, price * 1.003, price * 0.996, price, step=3_600_000))
    from backend.src.services.market import indicators as ind
    e20 = ind.ema([b.close for b in bars], 20)[-1]
    bars.append(_c(240, e20 * 1.004, e20 * 1.012, e20 * 0.995, e20 * 1.010, step=3_600_000))
    return bars


def _h4(n, start, step_pct):
    return [_c(i, x.open, x.high, x.low, x.close, step=14_400_000)
            for i, x in enumerate(_daily(n, start, step_pct))]


def test_trend_pa_takes_the_pullback_when_the_4h_trend_agrees():
    setups = trend_pa.generate(_trend_bars(), _h4(80, 50.0, 0.004))
    assert len(setups) == 1 and setups[0].direction == "long"


def test_trend_pa_skips_the_pullback_when_the_4h_trend_disagrees():
    assert trend_pa.generate(_trend_bars(), _h4(80, 200.0, -0.004)) == []


def test_trend_pa_skips_a_long_with_rsi_already_stretched(monkeypatch):
    monkeypatch.setattr(trend_pa.ind, "rsi", lambda closes, period=14: 72.0)
    assert trend_pa.generate(_trend_bars(), []) == []
    monkeypatch.setattr(trend_pa.ind, "rsi", lambda closes, period=14: 55.0)
    assert len(trend_pa.generate(_trend_bars(), [])) == 1
