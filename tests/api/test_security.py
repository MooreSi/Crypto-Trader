from fastapi.testclient import TestClient

from backend.src.api.server import create_app


def _client(host="localhost"):
    return TestClient(create_app(), base_url=f"http://{host}:8890")


def test_writes_need_the_csrf_header(fake_exchange):
    c = _client()
    assert c.post("/api/system/pause", json={"paused": True}).status_code == 403
    ok = c.post("/api/system/pause", json={"paused": True}, headers={"X-Crypto-Trader": "1"})
    assert ok.status_code == 200 and ok.json()["paused"] is True
    c.post("/api/system/pause", json={"paused": False}, headers={"X-Crypto-Trader": "1"})


def test_reads_do_not_need_it(fake_exchange):
    assert _client().get("/api/system/version").status_code == 200


def test_foreign_host_is_refused_even_for_reads(fake_exchange):
    assert _client("evil.example").get("/api/system/version").status_code == 403
