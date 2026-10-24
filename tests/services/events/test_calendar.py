from datetime import datetime, timezone

from backend.src.services.events import calendar, macro_feed, recurring
from backend.src.services.risk import settings


def _utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


def test_options_expiry_classification():
    ev = {e["uid"]: e for e in recurring.options_expiries(_utc(2026, 9, 1), 60)}
    assert ev["opex:2026-09-25"]["impact"] == "high"        # last Friday of September
    assert ev["opex:2026-10-30"]["impact"] == "medium"      # last Friday of October
    assert ev["opex:2026-10-09"]["impact"] == "low"
    assert datetime.fromtimestamp(ev["opex:2026-10-09"]["ts"], timezone.utc).hour == 8


def test_cme_gap_follows_chicago_time():
    ev = {e["uid"]: e for e in recurring.cme_gap(_utc(2026, 10, 19), 7)}
    close = datetime.fromtimestamp(ev["cme_close:2026-10-23"]["ts"], timezone.utc)
    assert (close.hour, close.minute) == (21, 0)            # 16:00 CDT


def test_macro_feed_keeps_usd_and_promotes_cpi():
    rows = [
        {"title": "CPI m/m", "country": "USD", "date": "2026-10-27T08:30:00-04:00", "impact": "Medium"},
        {"title": "German PMI", "country": "EUR", "date": "2026-10-27T04:30:00-04:00", "impact": "High"},
        {"title": "Bank Holiday", "country": "USD", "date": "2026-10-27T00:00:00-04:00", "impact": "Holiday"},
    ]
    out = macro_feed.parse(rows)
    assert len(out) == 1 and out[0]["impact"] == "high" and out[0]["coins"] == ""


def test_blackout_window_and_coin_scoping(fresh_db, fixed_clock):
    s = settings.defaults()
    now = fixed_clock.now()
    calendar.add_user_event(now + 20 * 60, "SOL unlock", "high", "token_unlock", ["sol"])
    assert calendar.blackout("SOL", s)["title"] == "SOL unlock"
    assert calendar.blackout("ETH", s) is None                # coin-scoped
    s["blackout_minutes_before"] = 10
    assert calendar.blackout("SOL", s) is None                # outside the window


def test_macro_event_blocks_every_coin_and_medium_is_opt_in(fresh_db, fixed_clock):
    from backend.src.services.events import events_repo
    now = fixed_clock.now()
    events_repo.upsert_many([{"uid": "m1", "ts": now + 600, "title": "USD PPI", "kind": "macro",
                              "impact": "medium", "coins": "", "source": "test"}])
    s = settings.defaults()
    assert calendar.blackout("DOGE", s) is None
    s["blackout_include_medium"] = True
    assert calendar.blackout("DOGE", s)["title"] == "USD PPI"


def test_user_events_validate_and_only_user_events_delete(fresh_db, fixed_clock):
    import pytest
    with pytest.raises(ValueError):
        calendar.add_user_event(0, "x", "huge")
    calendar.refresh(fetch_macro=False)
    timetable = calendar.upcoming(30)[0]
    assert not calendar.delete_user_event(timetable["id"])
