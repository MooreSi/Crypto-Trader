"""Routes added with the Strategy Lab, analytics and market pulse."""
from fastapi.testclient import TestClient

from backend.src.api.server import create_app
from backend.src.services.exchange.types import Candle

H = {"X-Crypto-Trader": "1"}


def _c():
    return TestClient(create_app(), base_url="http://127.0.0.1:8890")


def test_strategy_catalogue(fake_exchange):
    rows = _c().get("/api/backtest/strategies").json()
    assert {"breakout", "donchian_trend"} <= {r["name"] for r in rows}


def test_backtest_runs_and_places_nothing(fake_exchange, fixed_clock):
    now_ms = int(fixed_clock.now() * 1000)
    fake_exchange.candle_rows[("ETH", "15m")] = [
        Candle(now_ms - (700 - i) * 900_000, 100, 100.4, 99.6, 100.1, 1.0) for i in range(700)]
    r = _c().post("/api/backtest", json={"strategy": "bb_rsi_revert", "coin": "ETH", "bars": 600},
                  headers=H)
    assert r.status_code == 200 and r.json()["summary"]["trades"] >= 0
    assert not fake_exchange.calls


def test_backtest_unknown_strategy_is_400(fake_exchange):
    r = _c().post("/api/backtest", json={"strategy": "x", "coin": "ETH", "bars": 600}, headers=H)
    assert r.status_code == 400


def test_backtest_needs_the_write_header(fake_exchange):
    r = _c().post("/api/backtest", json={"strategy": "breakout", "coin": "ETH", "bars": 600})
    assert r.status_code == 403


def test_market_pulse(fake_exchange):
    p = _c().get("/api/markets/pulse").json()
    assert p["markets"] == 3 and 0 <= p["breadth_pct"] <= 100
    assert p["mood"] in ("risk-on", "risk-off", "mixed")


def test_trade_analytics_empty(fake_exchange):
    a = _c().get("/api/trades/analytics").json()
    assert a["closed"] == 0 and a["by_engine"] == {}


def test_tune_route_is_read_only(fake_exchange, fixed_clock):
    now_ms = int(fixed_clock.now() * 1000)
    fake_exchange.candle_rows[("ETH", "15m")] = [
        Candle(now_ms - (1300 - i) * 900_000, 100, 100.4, 99.6, 100.1, 1.0) for i in range(1300)]
    r = _c().post("/api/backtest/tune", json={"strategy": "breakout", "coin": "ETH", "bars": 1200, "folds": 3},
                  headers=H)
    assert r.status_code == 200 and len(r.json()["folds"]) == 3
    assert not fake_exchange.calls
