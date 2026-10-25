"""Which markets the engines scan.

Hyperliquid lists 200+ perpetuals. Scanning them all every cycle would hit
the info endpoint's rate limit and spend most of the time on markets too thin
to trade. So the engines scan:

* the user's **watchlist**, if they set one (any listed perpetual), else
* the top `auto_top_n` markets by 24h notional volume,

always excluding delisted markets, markets under `min_day_volume_usd`, and
anything in the user's **blocklist**. Settings live in the risk settings
(`services/risk/settings.py`) so one page controls what may be traded.
"""
from __future__ import annotations

from backend.src.services.exchange.types import ExchangeClient, MarketSnapshot


def select(snapshots: list[MarketSnapshot], settings: dict) -> list[str]:
    block = {c.upper() for c in settings.get("blocklist", [])}
    min_vol = float(settings.get("min_day_volume_usd", 0))
    eligible = {s.coin: s for s in snapshots
                if s.coin.upper() not in block and s.day_notional_volume >= min_vol}
    # The settings store coins upper-cased; the exchange names some in mixed
    # case (kPEPE), so match without case and return the exchange's name.
    by_upper = {c.upper(): c for c in eligible}
    watch = [by_upper[c.upper()] for c in settings.get("watchlist", []) if c.upper() in by_upper]
    if watch:
        return watch
    ranked = sorted(eligible.values(), key=lambda s: s.day_notional_volume, reverse=True)
    return [s.coin for s in ranked[: int(settings.get("auto_top_n", 20))]]


def scan(client: ExchangeClient, settings: dict) -> list[str]:
    return select(client.snapshots(), settings)
