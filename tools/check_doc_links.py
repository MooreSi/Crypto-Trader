"""Every relative markdown link in the docs resolves.

    python tools/check_doc_links.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(#[^)]*)?\)")
SKIP = {".git", ".venv", "node_modules", ".claude", "dist"}


def markdown_files(root: Path = ROOT) -> list[Path]:
    return [p for p in root.rglob("*.md") if not any(s in p.relative_to(root).parts for s in SKIP)]


def broken(root: Path = ROOT) -> list[str]:
    out = []
    for md in markdown_files(root):
        for target, _ in LINK.findall(md.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+:", target):
                continue
            if not (md.parent / target).resolve().exists():
                out.append(f"{md.relative_to(root)}: {target}")
    return out


def main() -> int:
    problems = broken()
    for p in problems:
        print(p)
    print(f"doc links: {len(problems)} broken")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
