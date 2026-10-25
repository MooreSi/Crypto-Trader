"""Market pulse: one glance at what the whole perp market is doing.

From the exchange's market snapshots only (no candles, one request):

* **breadth** -- the share of the `top_n` most traded markets up on 24h;
* **funding** -- volume-weighted hourly funding: positive means longs pay,
  i.e. the market leans long;
* **crowded longs / shorts** -- the highest and most negative funding rates.
  Extreme funding marks a crowded side; crowded sides are what squeezes and
  liquidation cascades unwind (a widely used contrarian input);
* **mood** -- `risk-on` when breadth is at least `ON_BREADTH`% and BTC is up,
  `risk-off` when breadth is at most `OFF_BREADTH`% and BTC is down, else
  `mixed`.

Information for the dashboard; no gate reads it.
"""
from __future__ import annotations

from backend.src.services.exchange.types import MarketSnapshot

ON_BREADTH = 60.0
OFF_BREADTH = 40.0
LIST_N = 5


def _row(s: MarketSnapshot) -> dict:
    return {"coin": s.coin, "price": s.mark_price, "change_pct": s.change_24h_pct,
            "funding_pct_h": s.funding_rate * 100.0, "volume_usd": s.day_notional_volume}


def summarise(snapshots: list[MarketSnapshot], top_n: int = 30) -> dict:
    top = sorted(snapshots, key=lambda s: s.day_notional_volume, reverse=True)[:top_n]
    n = len(top)
    vol = sum(s.day_notional_volume for s in top)
    breadth = 100.0 * sum(1 for s in top if s.change_24h_pct > 0) / n if n else 0.0
    btc = next((s for s in snapshots if s.coin == "BTC"), None)
    btc_change = btc.change_24h_pct if btc else 0.0
    if breadth >= ON_BREADTH and btc_change > 0:
        mood = "risk-on"
    elif n and breadth <= OFF_BREADTH and btc_change < 0:
        mood = "risk-off"
    else:
        mood = "mixed"
    by_funding = sorted(top, key=lambda s: s.funding_rate, reverse=True)
    by_change = sorted(top, key=lambda s: s.change_24h_pct, reverse=True)
    return {
        "markets": n, "breadth_pct": breadth, "mood": mood, "btc_change_pct": btc_change,
        "avg_change_pct": sum(s.change_24h_pct for s in top) / n if n else 0.0,
        "funding_pct_h": (sum(s.funding_rate * s.day_notional_volume for s in top) / vol * 100.0
                          if vol else 0.0),
        "open_interest_usd": sum(s.open_interest * s.mark_price for s in top),
        "volume_usd": vol,
        "crowded_longs": [_row(s) for s in by_funding[:LIST_N] if s.funding_rate > 0],
        "crowded_shorts": [_row(s) for s in by_funding[::-1][:LIST_N] if s.funding_rate < 0],
        "gainers": [_row(s) for s in by_change[:LIST_N] if s.change_24h_pct > 0],
        "losers": [_row(s) for s in by_change[::-1][:LIST_N] if s.change_24h_pct < 0],
    }
