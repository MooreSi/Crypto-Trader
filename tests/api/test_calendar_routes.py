from fastapi.testclient import TestClient

from backend.src.api.server import create_app

H = {"X-Crypto-Trader": "1"}


def _c():
    return TestClient(create_app(), base_url="http://127.0.0.1:8890")


def test_calendar_trades_and_events(fake_exchange, fixed_clock):
    c = _c()
    out = c.get("/api/calendar/trades?days=30").json()
    assert out == {"today": "2026-10-24", "rows": []}
    assert c.get("/api/calendar/trades?days=0").status_code == 422
    assert c.get("/api/calendar/events?start=2026-10-01&end=2026-10-31").json() == {"events": []}
    assert c.get("/api/calendar/events?start=oct&end=2026-10-31").status_code == 422


def test_journal_round_trip(fake_exchange, fixed_clock):
    c = _c()
    body = {"note": "quiet day", "tags": ["patience"], "mood": 4}
    assert c.post("/api/calendar/journal/2026-10-22", json=body).status_code == 403   # no CSRF header
    saved = c.post("/api/calendar/journal/2026-10-22", json=body, headers=H).json()["entry"]
    assert saved["note"] == "quiet day"
    listed = c.get("/api/calendar/journal?start=2026-10-01&end=2026-10-31").json()["entries"]
    assert listed == [saved]
    bad = c.post("/api/calendar/journal/2026-02-30", json=body, headers=H)
    assert bad.status_code == 400
