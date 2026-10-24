"""Candles, fetched from the exchange and cached briefly in memory.

Every engine asks for the same few (coin, interval) pairs each cycle; the
cache keeps that to one request per pair per `CACHE_TTL_S`. Hyperliquid's
info endpoint is rate-limited by weight per IP, and a cycle over twenty
markets and three engines would otherwise send sixty identical requests.

Only CLOSED candles are returned by `closed()`: the last element of a
snapshot is the bar still forming, and a signal computed on it can vanish by
the bar's close. Engines decide on closed bars only.
"""
from __future__ import annotations

import threading


from backend.src.services.exchange.types import Candle, ExchangeClient
from backend.src.utils import clock

CACHE_TTL_S = 20.0

INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}

_lock = threading.Lock()
_cache: dict[tuple[str, str, int], tuple[float, list[Candle]]] = {}


def fetch(client: ExchangeClient, coin: str, interval: str, bars: int) -> list[Candle]:
    """The last `bars` candles (including the forming one), oldest first."""
    step = INTERVAL_MS[interval]
    key = (coin, interval, bars)
    now = clock.now()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL_S:
            return hit[1]
    end = clock.now_ms()
    start = end - step * (bars + 1)
    rows = client.candles(coin, interval, start, end)[-bars:]
    with _lock:
        _cache[key] = (now, rows)
    return rows


def closed(client: ExchangeClient, coin: str, interval: str, bars: int) -> list[Candle]:
    """Closed candles only: drops the bar whose close time is still ahead."""
    rows = fetch(client, coin, interval, bars + 1)
    step = INTERVAL_MS[interval]
    now_ms = clock.now_ms()
    return [c for c in rows if c.t + step <= now_ms][-bars:]


def clear_cache() -> None:
    with _lock:
        _cache.clear()


