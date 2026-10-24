"""Engines never share rows: each SignalStore is its own file."""
from backend.src.services.engines.base import Signal
from backend.src.services.engines.signal_repo import LIVE_EXECUTED, SignalStore


def _sig(engine):
    return Signal(engine=engine, coin="BTC", direction="long", entry=100.0, stop=99.0,
                  created_at=1.0, interval="15m", features={"x": 1.0})


def test_two_stores_do_not_see_each_others_signals(tmp_path):
    a, b = SignalStore(tmp_path / "breakout.db"), SignalStore(tmp_path / "reversal.db")
    try:
        sid = a.insert(_sig("breakout"))
        a.resolve(sid, "win", 1, 1.0, 1.2, -0.3, 2.0)
        a.set_live(sid, LIVE_EXECUTED, 7)
        assert a.labelled() and not b.labelled()
        assert a.stats()["executed"] == 1 and b.stats()["total"] == 0
    finally:
        a.close()
        b.close()


def test_dedupe_window(tmp_path):
    s = SignalStore(tmp_path / "x.db")
    try:
        s.insert(_sig("trend_pa"))
        assert s.exists_since("BTC", "long", 0.5)
        assert not s.exists_since("BTC", "long", 1.5)
        assert not s.exists_since("BTC", "short", 0.5)
    finally:
        s.close()
