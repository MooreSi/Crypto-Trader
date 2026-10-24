"""A whole engine cycle against the fake exchange: scan, store, live hand-off."""
import pytest

from backend.src.services.engines import registry
from backend.src.services.exchange.types import Candle
from backend.src.services.positions import trades_repo
from backend.src.services.risk import settings

STEP = 900_000


def _breakout_bars(end_ms: int, base: float) -> list[Candle]:
    n = 120
    start = end_ms - n * STEP          # the last bar closes at end_ms
    bars = []
    for i in range(n - 1):
        d = 0.003 * base if i % 2 else -0.003 * base
        bars.append(Candle(start + i * STEP, base, base + abs(d) + 0.002 * base,
                           base - abs(d) - 0.002 * base, base + d, 100.0))
    bars.append(Candle(start + (n - 1) * STEP, base * 1.002, base * 1.035, base * 1.001,
                       base * 1.03, 1000.0))
    return bars


@pytest.fixture
def engines(fake_exchange, fixed_clock, monkeypatch, tmp_path):
    from backend.src import config
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(config, "db_path", lambda name: tmp_path / name)
    end = int(fixed_clock.now() * 1000) // STEP * STEP
    fake_exchange.candle_rows[("ETH", "15m")] = _breakout_bars(end, 3000.0)
    fake_exchange.mid["ETH"] = fake_exchange.candle_rows[("ETH", "15m")][-1].close
    fake_exchange.market_list = [m for m in fake_exchange.market_list if m.coin == "ETH"]
    registry.close()
    yield registry.get()
    registry.close()


def test_research_mode_stores_the_signal_and_places_nothing(engines, fake_exchange):
    out = engines["breakout"].cycle(fake_exchange)
    assert out["signals"] == 1
    sig = engines["breakout"].store.recent(1)[0]
    assert sig["coin"] == "ETH" and sig["direction"] == "long" and sig["live_status"] is None
    assert not [c for c in fake_exchange.calls if c[0] in ("market", "trigger")]


def test_same_setup_is_not_stored_twice(engines, fake_exchange):
    engines["breakout"].cycle(fake_exchange)
    assert engines["breakout"].cycle(fake_exchange)["signals"] == 0


def test_live_engine_with_trading_on_opens_a_trade(engines, fake_exchange):
    settings.update({"trading_enabled": True})
    engines["breakout"].set_live(True)
    engines["breakout"].cycle(fake_exchange)
    sig = engines["breakout"].store.recent(1)[0]
    assert sig["live_status"] == "executed" and sig["trade_id"]
    assert trades_repo.get(sig["trade_id"])["engine"] == "breakout"


def test_live_engine_with_master_switch_off_records_a_refusal(engines, fake_exchange):
    engines["breakout"].set_live(True)
    engines["breakout"].cycle(fake_exchange)
    sig = engines["breakout"].store.recent(1)[0]
    assert sig["live_status"].startswith("refused:trading enabled")
    assert trades_repo.open_trades() == []


def test_disabled_engine_does_nothing(engines, fake_exchange):
    engines["breakout"].set_enabled(False)
    assert engines["breakout"].cycle(fake_exchange) == {"engine": "breakout", "skipped": "disabled"}
