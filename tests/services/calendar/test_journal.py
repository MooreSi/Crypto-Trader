"""The day journal: a note, tags and a mood per trading day, per account."""
import pytest

from backend.src import config
from backend.src.services.calendar import journal


def test_save_then_read_back(fresh_db, fixed_clock):
    saved = journal.save("2026-10-22", "  chased the breakout  ", ["fomo", " fomo", "", "news"], 2)
    assert saved["note"] == "chased the breakout"
    assert saved["tags"] == ["fomo", "news"]
    assert saved["mood"] == 2 and saved["updated_at"] == fixed_clock.now()
    assert journal.between("2026-10-01", "2026-10-31") == [saved]


def test_saving_again_replaces_the_entry(fresh_db):
    journal.save("2026-10-22", "first", [], None)
    journal.save("2026-10-22", "second", ["x"], 4)
    rows = journal.between("2026-10-01", "2026-10-31")
    assert [(r["note"], r["tags"], r["mood"]) for r in rows] == [("second", ["x"], 4)]


def test_a_blank_save_clears_the_day(fresh_db):
    journal.save("2026-10-22", "note", [], 3)
    assert journal.save("2026-10-22", "   ", [], None) is None
    assert journal.between("2026-10-01", "2026-10-31") == []


def test_range_is_inclusive_and_takes_a_month_end_of_31(fresh_db):
    journal.save("2026-02-28", "end of feb", [], None)
    journal.save("2026-03-01", "march", [], None)
    assert [r["day"] for r in journal.between("2026-02-01", "2026-02-31")] == ["2026-02-28"]


def test_entries_belong_to_one_account(fresh_db, monkeypatch):
    journal.save("2026-10-22", "paper note", [], None)
    monkeypatch.setattr(config, "account_key", lambda: "testnet:0xabc")
    assert journal.between("2026-10-01", "2026-10-31") == []


@pytest.mark.parametrize("day, note, tags, mood", [
    ("2026-02-30", "x", [], None),          # not a real date
    ("2026-10-22", "x" * 4001, [], None),
    ("2026-10-22", "x", [str(i) for i in range(11)], None),
    ("2026-10-22", "x", ["t" * 41], None),
    ("2026-10-22", "x", [], 0),
    ("2026-10-22", "x", [], 6),
])
def test_bad_entries_are_refused(fresh_db, day, note, tags, mood):
    with pytest.raises(journal.BadJournalEntry):
        journal.save(day, note, tags, mood)
