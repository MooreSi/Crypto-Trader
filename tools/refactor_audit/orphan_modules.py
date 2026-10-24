"""Orphan modules: every backend module must be reachable from an entrypoint.

    python -m tools.refactor_audit.orphan_modules --check

Walks imports from `run.py` and `backend/src/app.py`. A module nothing
reaches is dead code that looks live -- FOREX Trader once carried ~3,000
lines of it. Fails CLOSED if an entrypoint is missing, so a renamed
entrypoint cannot turn this gate into a check that passes on nothing.
An intentional orphan goes in orphan_module_allowlist.json WITH a reason.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from tools.refactor_audit._scan import ROOT, module_name, python_files

ENTRYPOINTS = ("run.py", "backend/src/app.py")
ALLOWLIST = Path(__file__).with_name("orphan_module_allowlist.json")


def _imports(path: Path, known: set[str]) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        for n in names:
            parts = n.split(".")
            for i in range(1, len(parts) + 1):
                cand = ".".join(parts[:i])
                if cand in known:
                    found.add(cand)
    return found


def run(root: Path = ROOT) -> list[str]:
    for ep in ENTRYPOINTS:
        if not (root / ep).exists():
            return [f"entrypoint {ep} is missing; refusing to report on nothing"]
    files = {module_name(p, root): p for p in python_files("backend", root=root)}
    known = set(files)
    reached: set[str] = set()
    todo = [root / ep for ep in ENTRYPOINTS]
    seen_paths: set[Path] = set()
    while todo:
        path = todo.pop()
        if path in seen_paths:
            continue
        seen_paths.add(path)
        for mod in _imports(path, known):
            if mod not in reached:
                reached.add(mod)
                todo.append(files[mod])
    allow = json.loads(ALLOWLIST.read_text()) if ALLOWLIST.exists() else {}
    return [f"{files[m].relative_to(root)}: nothing imports this module"
            for m in sorted(known - reached - set(allow))
            if not files[m].name == "__init__.py"]


def main() -> int:
    problems = run()
    for p in problems:
        print(p)
    print(f"orphan modules: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
