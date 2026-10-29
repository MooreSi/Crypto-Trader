from fastapi.testclient import TestClient

from backend.src.api.server import create_app

H = {"X-Crypto-Trader": "1"}


def _c():
    return TestClient(create_app(), base_url="http://127.0.0.1:8890")


def test_strategy_crud_and_activate(fake_exchange):
    c = _c()
    first = c.get("/api/strategies").json()
    assert len(first["items"]) == 1 and first["active"] == first["items"][0]["id"]  # the default
    assert "stop_lock_r" in first["keys"]
    made = c.post("/api/strategies", json={"name": "Mine", "params": {"max_leverage": 2}},
                  headers=H).json()
    assert made["params"]["max_leverage"] == 2
    c.put(f"/api/strategies/{made['id']}", json={"name": "Mine 2", "params": {"max_leverage": 4},
                                                 "notes": ""}, headers=H)
    on = c.post(f"/api/strategies/{made['id']}/activate", headers=H).json()
    assert on["active"] == made["id"]
    assert c.get("/api/risk").json()["max_leverage"] == 4
    assert c.delete(f"/api/strategies/{made['id']}", headers=H).status_code == 400   # active
    assert c.post("/api/strategies", json={"name": "x", "params": {"nope": 1}},
                  headers=H).status_code == 400
    assert c.post("/api/strategies/missing/activate", headers=H).status_code == 404
