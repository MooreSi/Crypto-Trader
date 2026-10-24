"""Structure gates: file size, and SQL only in the data layer.

    python -m tools.refactor_audit.structure_gates --check

* **File size** -- no Python file under backend/ or tools/ over
  `MAX_LINES`. A file past that is split (docs/system/rules/70-file-organisation.md).
* **SQL lives in repos** -- a string literal that is a SQL statement may
  appear only in `backend/src/db/` or a `*_repo.py` file. Everything else asks
  a repo.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from tools.refactor_audit._scan import ROOT, python_files

MAX_LINES = 800
SQL = re.compile(r"^\s*(SELECT\b.+\bFROM\b|INSERT\s+(OR\s+\w+\s+)?INTO\b|UPDATE\s+\w+\s+SET\b|"
                 r"DELETE\s+FROM\b|CREATE\s+(TABLE|INDEX)\b|DROP\s+TABLE\b)",
                 re.IGNORECASE | re.DOTALL)


def sql_allowed(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    return rel.startswith("backend/src/db/") or path.name.endswith("_repo.py")


def oversized(files: list[Path], max_lines: int = MAX_LINES) -> list[str]:
    out = []
    for p in files:
        n = sum(1 for _ in p.open(encoding="utf-8"))
        if n > max_lines:
            out.append(f"{p}: {n} lines (max {max_lines})")
    return out


def stray_sql(files: list[Path], root: Path) -> list[str]:
    out = []
    for p in files:
        if sql_allowed(p, root):
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and SQL.match(node.value):
                out.append(f"{p.relative_to(root)}:{node.lineno}: SQL outside the data layer")
    return out


def run(root: Path = ROOT) -> list[str]:
    backend = python_files("backend", root=root)
    tools = python_files("tools", root=root)
    return oversized(backend + tools) + stray_sql(backend, root)


def main() -> int:
    problems = run()
    for p in problems:
        print(p)
    print(f"structure gates: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
