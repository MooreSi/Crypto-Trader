"""The crypto feature vector every engine starts from.

FOREX Trader's engines were built for one instrument; these features are
built for any perpetual on Hyperliquid, so everything is **scale-free**:
returns and distances are fractions of price, volume is a z-score or a log,
and funding is in basis points per hour. A model trained on BTC and SOL
signals together can then score a new listing without seeing it before.

Crypto-only inputs FOREX Trader had no equivalent for:

* funding rate (what longs pay shorts each hour) and open interest,
* BTC as the cross-asset peer: most of the market moves with it, so its
  short-term return and trend are features for every other coin,
* weekend flag: liquidity is thinner Saturday and Sunday,
* hours to the nearest high-impact event for this coin.

**Append-only.** `BASE_FEATURES` is the order models were trained on. A new
feature goes on the END and bumps nothing else; an engine's model then hands
over from the narrower version (ml/model.py) until it retrains. Reordering or
removing one silently scrambles every stored vector.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional, Sequence

from backend.src.services.exchange.types import Candle, MarketSnapshot
from backend.src.services.market import indicators as ind
from backend.src.services.market import levels, regime, sessions

BASE_FEATURES: tuple[str, ...] = (
    "direction", "risk_pct", "ret_1", "ret_4", "ret_24", "atr_pct", "adx", "rsi",
    "macd_hist_pct", "bb_width", "vol_z", "regime_code", "funding_bps", "log_oi_usd",
    "log_day_volume", "change_24h_pct", "btc_ret_4", "btc_trend", "dist_round_pct",
    "dist_swing_pct", "sess_asia", "sess_europe", "sess_us", "sess_overlap", "weekend",
    "hour_sin", "hour_cos", "event_hours",
)

NEUTRAL = 0.0


def _ret(closes: Sequence[float], n: int) -> float:
    if len(closes) <= n or closes[-1 - n] == 0:
        return 0.0
    return (closes[-1] - closes[-1 - n]) / closes[-1 - n]


def _num(x: Optional[float]) -> float:
    return float(x) if x is not None and math.isfinite(x) else NEUTRAL


def base_vector(direction: str, entry: float, stop: float, bars: Sequence[Candle],
                snapshot: Optional[MarketSnapshot], btc_bars: Sequence[Candle],
                event_hours: float) -> dict[str, float]:
    closes = [c.close for c in bars]
    price = closes[-1] if closes else entry
    atr = ind.atr(bars, 14)
    swing_hi, swing_lo = levels.swing_levels(bars[-100:], 3)
    btc_closes = [c.close for c in btc_bars]
    btc_e20, btc_e50 = ind.ema(btc_closes, 20), ind.ema(btc_closes, 50)
    btc_trend = NEUTRAL
    if btc_e20 and btc_e50 and btc_e20[-1] is not None and btc_e50[-1] is not None:
        btc_trend = 1.0 if btc_e20[-1] > btc_e50[-1] else -1.0
    ts = datetime.fromtimestamp(bars[-1].t / 1000, tz=timezone.utc) if bars else \
        datetime.now(tz=timezone.utc)
    hour = ts.hour + ts.minute / 60
    oi_usd = (snapshot.open_interest * snapshot.mark_price) if snapshot else 0.0
    v = {
        "direction": 1.0 if direction == "long" else -1.0,
        "risk_pct": abs(entry - stop) / entry * 100 if entry else NEUTRAL,
        "ret_1": _ret(closes, 1) * 100,
        "ret_4": _ret(closes, 4) * 100,
        "ret_24": _ret(closes, 24) * 100,
        "atr_pct": (atr / price * 100) if atr and price else NEUTRAL,
        "adx": _num(ind.adx(bars, 14)),
        "rsi": _num(ind.rsi(closes, 14)),
        "macd_hist_pct": (_num(ind.macd_hist(closes)) / price * 100) if price else NEUTRAL,
        "bb_width": _num(ind.bollinger_width(closes)),
        "vol_z": _num(ind.zscore([c.volume for c in bars], 20)),
        "regime_code": regime.REGIME_CODES.get(regime.detect(bars), NEUTRAL),
        "funding_bps": snapshot.funding_rate * 1e4 if snapshot else NEUTRAL,
        "log_oi_usd": math.log10(oi_usd + 1),
        "log_day_volume": math.log10(snapshot.day_notional_volume + 1) if snapshot else NEUTRAL,
        "change_24h_pct": snapshot.change_24h_pct if snapshot else NEUTRAL,
        "btc_ret_4": _ret(btc_closes, 4) * 100,
        "btc_trend": btc_trend,
        "dist_round_pct": levels.distance_to_nearest(price, [levels.nearest_round(price)]) * 100,
        "dist_swing_pct": levels.distance_to_nearest(price, swing_hi + swing_lo) * 100,
        **sessions.session_flags(ts),
        "hour_sin": math.sin(2 * math.pi * hour / 24),
        "hour_cos": math.cos(2 * math.pi * hour / 24),
        "event_hours": float(event_hours),
    }
    return {k: _num(v[k]) for k in BASE_FEATURES}


def to_row(features: dict, names: Sequence[str]) -> list[float]:
    """Ordered row for a model; a missing feature is NEUTRAL (older stored vectors)."""
    return [_num(features.get(n)) for n in names]
