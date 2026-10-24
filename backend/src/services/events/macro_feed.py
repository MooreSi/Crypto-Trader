"""US macro releases from the ForexFactory weekly JSON feed.

The same public feed FOREX Trader uses
(`https://nfs.faireconomy.media/ff_calendar_thisweek.json`, no key). For
crypto only the US dollar matters: FOMC, CPI, NFP, PCE and their kin move
BTC and the whole market with it, and nothing else on the feed reliably
does. Rows are `{"title", "country", "date" (ISO-8601 with offset),
"impact": "High"|"Medium"|"Low"|"Holiday"}`.

The feed answers 429 when asked too often and publishes weekly, so a failure
backs off (doubling, capped at an hour) instead of retrying every cycle.
"""
from __future__ import annotations

import logging
from datetime import datetime

from backend.src.utils import clock

log = logging.getLogger(__name__)

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
REFRESH_S = 6 * 3600
RETRY_S = 300
RETRY_MAX_S = 3600

#: Titles that move crypto harder than the feed's own impact rating implies.
#: A match is promoted to high impact.
PROMOTE_TO_HIGH = ("fomc", "federal funds", "rate decision", "powell", "cpi",
                   "non-farm", "nonfarm", "core pce")

_next_fetch = 0.0
_fail_streak = 0


def parse(rows: list) -> list[dict]:
    """Feed rows -> event dicts (USD only, holidays dropped)."""
    out = []
    for r in rows if isinstance(rows, list) else []:
        if str(r.get("country", "")).upper() != "USD":
            continue
        impact = str(r.get("impact", "")).lower()
        if impact not in ("high", "medium", "low"):
            continue
        try:
            ts = datetime.fromisoformat(str(r["date"]).replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            continue
        title = str(r.get("title", "")).strip()
        if any(k in title.lower() for k in PROMOTE_TO_HIGH):
            impact = "high"
        out.append({"uid": f"macro:{int(ts)}:{title}", "ts": ts, "title": f"USD {title}",
                    "kind": "macro", "impact": impact, "coins": "", "source": "forexfactory"})
    return out


def due() -> bool:
    return clock.now() >= _next_fetch


def fetch() -> list[dict]:
    """Fetch and parse, or [] on failure (with backoff). Never raises."""
    global _next_fetch, _fail_streak
    import httpx
    try:
        resp = httpx.get(FEED_URL, timeout=15.0, headers={"User-Agent": "CryptoTrader"})
        resp.raise_for_status()
        events = parse(resp.json())
        _fail_streak = 0
        _next_fetch = clock.now() + REFRESH_S
        return events
    except Exception as exc:
        _fail_streak += 1
        delay = min(RETRY_S * 2 ** (_fail_streak - 1), RETRY_MAX_S)
        _next_fetch = clock.now() + delay
        log.warning("[Events] macro feed fetch failed (%s); retry in %ds", exc, delay)
        return []
