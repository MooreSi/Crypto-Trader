import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _names(lines):
    return {re.split(r"[<>=!;\[ ]", ln.strip(), maxsplit=1)[0].lower() for ln in lines
            if ln.strip() and not ln.strip().startswith(("#", "-"))}


def test_requirements_and_pyproject_declare_the_same_packages():
    req = _names((ROOT / "requirements.txt").read_text().splitlines())
    text = (ROOT / "pyproject.toml").read_text()
    block = text.split("dependencies = [", 1)[1].split("]", 1)[0]
    py = _names(x.strip().strip('",') for x in block.splitlines())
    assert req == py
