"""A whole engine cycle against the fake exchange: scan, store, live hand-off."""
import dataclasses

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


def _signal_at(engine, bar, entry, stop):
    from backend.src.services.engines.base import Signal
    return engine.store.insert(Signal(engine=engine.name, coin="ETH", direction="long", entry=entry,
                                      stop=stop, created_at=bar.t / 1000 + STEP / 1000,
                                      interval="15m", features={"x": 1.0}))


def test_tracking_labels_by_the_exit_plan_and_stamps_the_version(engines, fake_exchange):
    from backend.src.services.engines import tracker
    eng = engines["breakout"]
    bars = fake_exchange.candle_rows[("ETH", "15m")]
    b = bars[10]
    # the chop after bar 10 swings about 0.5% a bar: a 0.2% stop is hit long before 3R
    sid = _signal_at(eng, b, b.close, b.close * 0.998)
    eng.track(fake_exchange)
    row = eng.store.db.query_one("SELECT * FROM signals WHERE id = ?", (sid,))
    assert row["status"] == "loss" and row["label_v"] == tracker.LABEL_VERSION
    assert row["r_final"] < -1.0                     # fees on top of the full stop


def test_old_labels_are_rescored_while_their_bars_are_still_held(engines, fake_exchange):
    from backend.src.services.engines import tracker
    eng = engines["breakout"]
    b = fake_exchange.candle_rows[("ETH", "15m")][10]
    sid = _signal_at(eng, b, b.close, b.close * 0.998)
    eng.store.resolve(sid, "win", 1, 1.0, 1.0, -0.5, 1.0, label_v=1)
    eng.track(fake_exchange)
    row = eng.store.db.query_one("SELECT * FROM signals WHERE id = ?", (sid,))
    assert row["status"] == "loss" and row["label"] == 0 and row["label_v"] == tracker.LABEL_VERSION


def test_an_old_label_whose_bars_are_gone_stays_out_of_training(engines, fake_exchange):
    eng = engines["breakout"]
    first = fake_exchange.candle_rows[("ETH", "15m")][0]
    early = dataclasses.replace(first, t=first.t - 50 * STEP)   # before the held window starts
    sid = _signal_at(eng, early, early.close, early.close * 0.998)
    eng.store.resolve(sid, "win", 1, 1.0, 1.0, -0.5, 1.0, label_v=1)
    eng.track(fake_exchange)
    row = eng.store.db.query_one("SELECT * FROM signals WHERE id = ?", (sid,))
    assert row["label_v"] == 1 and eng.store.labelled() == []


def test_an_executed_signal_is_tracked_from_its_trade_fill(engines, fake_exchange, monkeypatch):
    from backend.src.services.engines import service, tracker
    eng = engines["breakout"]
    b = fake_exchange.candle_rows[("ETH", "15m")][10]
    sid = _signal_at(eng, b, b.close, b.close * 0.9)
    eng.store.set_live(sid, "executed", 42)
    seen = []
    real = tracker.evaluate
    monkeypatch.setattr(service.trades_repo, "get",
                        lambda tid: {"id": tid, "entry_price": b.close * 1.01} if tid == 42 else None)
    monkeypatch.setattr(tracker, "evaluate", lambda sig, bars, plan: seen.append(sig) or real(sig, bars, plan))
    eng.track(fake_exchange)
    assert seen and seen[0]["fill"] == b.close * 1.01
