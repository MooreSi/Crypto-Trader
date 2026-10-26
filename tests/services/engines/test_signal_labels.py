"""Labels carry the version of the rule that wrote them; only current ones train a model."""
from backend.src.services.engines import tracker
from backend.src.services.engines.base import Signal
from backend.src.services.engines.signal_repo import SignalStore


def _sig(t):
    return Signal(engine="breakout", coin="BTC", direction="long", entry=100.0, stop=98.0,
                  created_at=t, interval="15m", features={"x": t})


def test_old_rule_labels_are_left_out_of_training(tmp_path):
    s = SignalStore(tmp_path / "x.db")
    try:
        old, new = s.insert(_sig(1.0)), s.insert(_sig(2.0))
        s.resolve(old, "win", 1, 1.0, 1.0, -0.2, 5.0, label_v=1)
        s.resolve(new, "loss", 0, -1.045, 0.4, -1.1, 6.0)
        assert [f["x"] for _, f, _ in s.labelled()] == [2.0]
    finally:
        s.close()


def test_stale_lists_resolved_rows_written_by_an_older_rule(tmp_path):
    s = SignalStore(tmp_path / "x.db")
    try:
        old, new, open_ = s.insert(_sig(1.0)), s.insert(_sig(2.0)), s.insert(_sig(3.0))
        s.resolve(old, "win", 1, 1.0, 1.0, -0.2, 5.0, label_v=1)
        s.resolve(new, "win", 1, 2.955, 3.0, -0.2, 6.0)
        assert [r["id"] for r in s.stale(tracker.LABEL_VERSION)] == [old]
        assert [r["id"] for r in s.tracking()] == [open_]
    finally:
        s.close()


def test_reopen_puts_a_row_back_to_tracking_without_a_label(tmp_path):
    s = SignalStore(tmp_path / "x.db")
    try:
        sid = s.insert(_sig(1.0))
        s.resolve(sid, "win", 1, 1.0, 1.0, -0.2, 5.0, label_v=1)
        s.reopen(sid, 1.2, -0.3)
        row = s.tracking()[0]
        assert row["id"] == sid and row["label"] is None and row["r_final"] is None
        assert row["mfe_r"] == 1.2 and not s.stale(tracker.LABEL_VERSION)
    finally:
        s.close()
