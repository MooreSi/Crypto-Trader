from fastapi.testclient import TestClient

from backend.src.api.server import create_app

H = {"X-Crypto-Trader": "1"}


def _c():
    return TestClient(create_app(), base_url="http://127.0.0.1:8890")


def test_account_and_markets(fake_exchange):
    c = _c()
    acc = c.get("/api/account").json()
    assert acc["equity"] == 10_000 and acc["network"] == "paper"
    markets = c.get("/api/markets").json()
    assert {m["coin"] for m in markets} == {"BTC", "ETH", "SOL"}
    assert all(m["scanned"] for m in markets)


def test_risk_round_trip_and_validation(fake_exchange):
    c = _c()
    assert c.post("/api/risk", json={"fields": {"max_leverage": 2}}, headers=H).json()["max_leverage"] == 2
    bad = c.post("/api/risk", json={"fields": {"nope": 1}}, headers=H)
    assert bad.status_code == 400


def test_engines_toggle_live(fake_exchange, monkeypatch):
    from backend.src.services.engines import registry
    try:
        c = _c()
        names = [e["name"] for e in c.get("/api/engines").json()]
        assert names == ["breakout", "reversal", "trend_pa"]
        assert all(not e["live"] for e in c.get("/api/engines").json())   # default OFF
        on = c.post("/api/engines/breakout/live", json={"on": True}, headers=H).json()
        assert on["live"] is True
        assert c.post("/api/engines/nope/live", json={"on": True}, headers=H).status_code == 404
    finally:
        registry.close()


def test_user_event_crud(fake_exchange, fixed_clock):
    c = _c()
    ev = c.post("/api/events", json={"ts": fixed_clock.now() + 3600, "title": "ARB unlock",
                                     "impact": "high", "kind": "token_unlock", "coins": ["ARB"]},
                headers=H).json()
    listed = c.get("/api/events").json()
    row = next(e for e in listed if e["uid"] == ev["uid"])
    assert c.delete(f"/api/events/{row['id']}", headers=H).json()["deleted"] is True


def test_closing_a_trade_that_is_not_open_is_a_400(fake_exchange):
    assert _c().post("/api/trades/999/close", headers=H).status_code == 400
