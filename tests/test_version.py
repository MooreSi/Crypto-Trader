from pathlib import Path

from backend.src.utils import version_history

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_0_1_0_everywhere():
    assert version_history.__version__ == "0.1.0"
    assert (ROOT / "VERSION").read_text().strip() == version_history.__version__
    assert f"## [{version_history.__version__}]" in (ROOT / "CHANGELOG.md").read_text()


def test_releases_newest_first_with_notes():
    assert version_history.RELEASES[0]["version"] == version_history.__version__
    assert all(r["notes"] for r in version_history.RELEASES)
