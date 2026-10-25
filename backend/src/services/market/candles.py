"""Candles, fetched from the exchange and cached briefly in memory.

Every engine asks for the same few (coin, interval) pairs each cycle; the
cache keeps that to one request per pair per `CACHE_TTL_S`. Hyperliquid's
info endpoint is rate-limited by weight per IP, and a cycle over twenty
markets and three engines would otherwise send sixty identical requests.

Only CLOSED candles are returned by `closed()`: the last element of a
snapshot is the bar still forming, and a signal computed on it can vanish by
the bar's close. Engines decide on closed bars only.

**Request budget** (2026-10-25). Hyperliquid allows an IP 1200 weight a
minute; `candleSnapshot` weighs 20 plus 1 per 60 bars returned. With a 20 s
cache the engines spent ~2000 a minute on candles alone, and every info call
failed with 429, the positions loop's account reads included. So:

* a closed series is kept until its next bar closes (nothing new can exist
  before then): a 4h series is fetched once every 4 hours, not every minute;
* closed-series fetches share `WEIGHT_BUDGET_PER_MIN`, half the allowance,
  leaving the rest for the account, orders and the dashboard. Over budget,
  `closed()` raises `CandleBudgetExceeded` without a request; the engine
  skips that coin and scans it on a later cycle.
"""
from __future__ import annotations

import math
import threading
from collections import deque

from backend.src.services.exchange.types import Candle, ExchangeClient, ExchangeError
from backend.src.utils import clock

CACHE_TTL_S = 20.0
#: Candle weight the engines and the Lab may spend per rolling minute (of 1200).
WEIGHT_BUDGET_PER_MIN = 600

INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}

_lock = threading.Lock()
_cache: dict[tuple[str, str, int], tuple[float, list[Candle]]] = {}
_closed_cache: dict[tuple[str, str, int], tuple[float, list[Candle]]] = {}
_spent: deque[tuple[float, int]] = deque()      # (time, weight) of recent fetches


class CandleBudgetExceeded(ExchangeError):
    """The minute's candle budget is used up; try again on a later cycle."""


def request_weight(bars: int) -> int:
    """Hyperliquid's weight for a candleSnapshot returning `bars` candles."""
    return 20 + math.ceil(bars / 60)


def _spend(weight: int, enforce: bool) -> None:
    now = clock.now()
    with _lock:
        while _spent and now - _spent[0][0] >= 60.0:
            _spent.popleft()
        used = sum(w for _, w in _spent)
        if enforce and used + weight > WEIGHT_BUDGET_PER_MIN:
            raise CandleBudgetExceeded(
                f"candle budget used up ({used}/{WEIGHT_BUDGET_PER_MIN} this minute); "
                "try again in a minute")
        _spent.append((now, weight))


def _request(client: ExchangeClient, coin: str, interval: str, bars: int, enforce: bool) -> list[Candle]:
    _spend(request_weight(bars), enforce)
    end = clock.now_ms()
    start = end - INTERVAL_MS[interval] * (bars + 1)
    return client.candles(coin, interval, start, end)[-bars:]


def fetch(client: ExchangeClient, coin: str, interval: str, bars: int) -> list[Candle]:
    """The last `bars` candles (including the forming one), oldest first. For charts:
    counted against the budget but never refused, since the owner asked for it."""
    key = (coin, interval, bars)
    now = clock.now()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL_S:
            return hit[1]
    rows = _request(client, coin, interval, bars, enforce=False)
    with _lock:
        _cache[key] = (now, rows)
    return rows


def closed(client: ExchangeClient, coin: str, interval: str, bars: int) -> list[Candle]:
    """Closed candles only, kept until the next bar closes; within the request budget."""
    step = INTERVAL_MS[interval]
    key = (coin, interval, bars)
    now_ms = clock.now_ms()
    with _lock:
        hit = _closed_cache.get(key)
    if hit:
        fetched_at, rows = hit
        fresh = now_ms < rows[-1].t + 2 * step if rows else clock.now() - fetched_at < CACHE_TTL_S
        if fresh:
            return rows
    raw = _request(client, coin, interval, bars + 1, enforce=True)
    rows = [c for c in raw if c.t + step <= now_ms][-bars:]
    with _lock:
        _closed_cache[key] = (clock.now(), rows)
    return rows


def clear_cache() -> None:
    with _lock:
        _cache.clear()
        _closed_cache.clear()
        _spent.clear()


