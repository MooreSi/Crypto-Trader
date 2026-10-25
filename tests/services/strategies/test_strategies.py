"""Each Strategy Lab generator fires on its pattern and stays quiet without it.

The strategies come from what has a public record of working on crypto:
time-series momentum / Donchian trend following (the most-cited systematic
edge in the literature), Bollinger + RSI mean reversion in ranges (a staple
of open-source bots such as freqtrade), and Supertrend flips (the most
common TradingView / freqtrade trend strategy). None trades: they run in the
backtester only.
"""
from backend.src.services.exchange.types import Candle
from backend.src.services.strategies import bb_rsi_revert, donchian_trend, supertrend_flip


def _c(i, o, h, lo, c, v=100.0, step=3_600_000):
    return Candle(1_700_000_000_000 + i * step, o, h, lo, c, v)


def _flat(n, price=100.0, wiggle=0.3, step=900_000):
    out = []
    for i in range(n):
        d = wiggle if i % 2 else -wiggle
        out.append(_c(i, price, price + abs(d) + 0.2, price - abs(d) - 0.2, price + d, step=step))
    return out


def _rise(n, start=100.0, pct=0.004, step=14_400_000):
    out, p = [], start
    for i in range(n):
        nxt = p * (1 + pct)
        out.append(_c(i, p, nxt * 1.002, p * 0.998, nxt, step=step))
        p = nxt
    return out


# ── Donchian trend ────────────────────────────────────────────────────────────

def test_donchian_long_on_a_fresh_20_bar_high_in_an_uptrend():
    bars = _rise(150)
    # a pause under the high, then a close through it
    top = max(b.high for b in bars[-20:])
    for i in range(8):
        bars.append(_c(150 + i, top * 0.99, top * 0.995, top * 0.985, top * 0.99, step=14_400_000))
    bars.append(_c(158, top * 0.99, top * 1.02, top * 0.989, top * 1.015, step=14_400_000))
    setups = donchian_trend.generate(bars, [])
    assert len(setups) == 1 and setups[0].direction == "long"
    assert setups[0].stop < setups[0].entry
    assert set(setups[0].extra) == set(donchian_trend.EXTRA_FEATURES)


def test_donchian_quiet_inside_the_channel():
    assert donchian_trend.generate(_flat(200, step=14_400_000), []) == []


def test_donchian_does_not_repeat_on_a_bar_that_was_already_above():
    bars = _rise(160)          # every bar is a new high: no FRESH break
    assert donchian_trend.generate(bars, []) == []


# ── Bollinger + RSI reversion ────────────────────────────────────────────────

def test_bb_rsi_long_when_an_oversold_flush_closes_back_inside_the_band():
    bars = _flat(80)
    n = len(bars)
    for i, p in enumerate((98.5, 97.0, 95.5, 94.0)):     # flush below the lower band, RSI < 30
        bars.append(_c(n + i, p + 1.5, p + 1.6, p - 0.2, p, step=900_000))
    bars.append(_c(n + 4, 94.0, 97.6, 93.8, 97.4, step=900_000))   # bullish close back inside
    setups = bb_rsi_revert.generate(bars, [])
    assert len(setups) == 1 and setups[0].direction == "long"
    assert setups[0].stop < setups[0].entry
    assert set(setups[0].extra) == set(bb_rsi_revert.EXTRA_FEATURES)


def test_bb_rsi_quiet_in_a_calm_range():
    assert bb_rsi_revert.generate(_flat(120), []) == []


def test_bb_rsi_stands_down_in_a_strong_trend():
    assert bb_rsi_revert.generate(_rise(150, step=900_000), []) == []


# ── Supertrend flip ──────────────────────────────────────────────────────────

def test_supertrend_long_on_the_flip_above_ema200():
    bars = _rise(230, pct=0.002, step=3_600_000)
    p = bars[-1].close
    for i in range(12):                     # a pullback that flips supertrend down
        q = p * (1 - 0.006 * (i + 1))
        bars.append(_c(230 + i, q * 1.006, q * 1.007, q * 0.999, q, step=3_600_000))
    from backend.src.services.market import indicators as ind
    flipped = None
    q = bars[-1].close
    for i in range(20):                     # then a recovery until it flips back up
        q *= 1.01
        bars.append(_c(242 + i, q / 1.01, q * 1.001, q / 1.011, q, step=3_600_000))
        st = ind.supertrend(bars, supertrend_flip.ST_PERIOD, supertrend_flip.ST_MULT)
        if st[-1][1] == 1 and st[-2][1] == -1:
            flipped = i
            break
    assert flipped is not None
    setups = supertrend_flip.generate(bars, [])
    assert len(setups) == 1 and setups[0].direction == "long"
    assert setups[0].stop < setups[0].entry


def test_supertrend_quiet_without_a_flip():
    assert supertrend_flip.generate(_rise(260, step=3_600_000), []) == []
