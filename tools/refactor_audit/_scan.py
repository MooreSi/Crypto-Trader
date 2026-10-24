"""Shared file discovery for the gates: what counts as source, and what never does.

Every scanner excludes the same directories. `.claude/` matters most: an
agent worktree there is a complete second checkout, and FOREX Trader once saw
four gates go red at once from ~370 duplicated files that were not real.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".claude", "node_modules", ".pytest_cache",
                 "dist", "docs/reviews"}


def excluded(path: Path, root: Path = ROOT) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = rel.split("/")
    return any(p in EXCLUDED_DIRS for p in parts) or any(rel.startswith(d + "/") for d in EXCLUDED_DIRS)


def python_files(*subdirs: str, root: Path = ROOT) -> list[Path]:
    out = []
    for sub in subdirs:
        base = root / sub
        if base.is_file():
            out.append(base)
            continue
        out += [p for p in base.rglob("*.py") if not excluded(p, root)]
    return sorted(out)


def module_name(path: Path, root: Path = ROOT) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)
