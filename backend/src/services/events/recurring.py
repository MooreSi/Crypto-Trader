"""Crypto-market events that follow a timetable, so need no feed.

* **Options expiry** -- Deribit, the venue where most crypto options trade,
  settles at 08:00 UTC every Friday. The last Friday of a month is the
  monthly expiry (medium impact) and the last Friday of March, June,
  September and December the quarterly (high impact): open interest there is
  large enough to pin and then release price around the settlement.
* **CME weekend gap** -- CME Bitcoin futures trade Sunday 17:00 to Friday
  16:00 America/Chicago. Spot trades through the weekend, so the futures
  reopen with a gap that price often trades back toward. Close and reopen
  are emitted as low-impact markers: useful context, not a blackout.
* **FOMC decision days** -- the same fallback dates FOREX Trader keeps,
  used only so a decision is never missed while the live feed is down.
  ADD NEXT YEAR'S DATES when the Fed publishes them; a missing year warns.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

CHICAGO = ZoneInfo("America/Chicago")
QUARTER_MONTHS = (3, 6, 9, 12)

#: FOMC statement days, (month, day), from FOREX Trader's fallback table.
FOMC_DATES: dict[int, set[tuple[int, int]]] = {
    2026: {(1, 29), (3, 19), (5, 7), (6, 18), (7, 29), (9, 17), (11, 5), (12, 16)},
}
#: The statement is released at 14:00 America/New_York.
FOMC_TIME_NY = time(14, 0)

_warned: set[int] = set()


def _last_friday(year: int, month: int) -> date:
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    d = nxt - timedelta(days=1)
    while d.weekday() != 4:
        d -= timedelta(days=1)
    return d


def options_expiries(start: datetime, days: int) -> list[dict]:
    out = []
    d = start.date()
    for _ in range(days + 1):
        if d.weekday() == 4:
            ts = datetime.combine(d, time(8, 0), tzinfo=timezone.utc).timestamp()
            last = _last_friday(d.year, d.month) == d
            if last and d.month in QUARTER_MONTHS:
                title, impact = "Quarterly options expiry (Deribit)", "high"
            elif last:
                title, impact = "Monthly options expiry (Deribit)", "medium"
            else:
                title, impact = "Weekly options expiry (Deribit)", "low"
            out.append({"uid": f"opex:{d.isoformat()}", "ts": ts, "title": title,
                        "kind": "options_expiry", "impact": impact, "coins": "BTC,ETH",
                        "source": "timetable"})
        d += timedelta(days=1)
    return out


def cme_gap(start: datetime, days: int) -> list[dict]:
    out = []
    d = start.date()
    for _ in range(days + 1):
        if d.weekday() == 4:
            ts = datetime.combine(d, time(16, 0), tzinfo=CHICAGO).timestamp()
            out.append({"uid": f"cme_close:{d.isoformat()}", "ts": ts,
                        "title": "CME Bitcoin futures weekend close", "kind": "cme_gap",
                        "impact": "low", "coins": "BTC", "source": "timetable"})
        if d.weekday() == 6:
            ts = datetime.combine(d, time(17, 0), tzinfo=CHICAGO).timestamp()
            out.append({"uid": f"cme_open:{d.isoformat()}", "ts": ts,
                        "title": "CME Bitcoin futures reopen (gap)", "kind": "cme_gap",
                        "impact": "low", "coins": "BTC", "source": "timetable"})
        d += timedelta(days=1)
    return out


def fomc(start: datetime, days: int) -> list[dict]:
    out = []
    ny = ZoneInfo("America/New_York")
    d = start.date()
    for _ in range(days + 1):
        dates = FOMC_DATES.get(d.year)
        if dates is None and d.year not in _warned:
            _warned.add(d.year)
            log.warning("[Events] no FOMC fallback dates for %d; add them to "
                        "services/events/recurring.py. The live feed is unaffected.", d.year)
        if dates and (d.month, d.day) in dates:
            ts = datetime.combine(d, FOMC_TIME_NY, tzinfo=ny).timestamp()
            out.append({"uid": f"fomc:{d.isoformat()}", "ts": ts,
                        "title": "USD FOMC Statement (fallback)", "kind": "macro",
                        "impact": "high", "coins": "", "source": "timetable"})
        d += timedelta(days=1)
    return out


def generate(start: datetime, days: int = 14) -> list[dict]:
    return options_expiries(start, days) + cme_gap(start, days) + fomc(start, days)
