"""One command that runs everything before a commit.

    python -m tools.checks all      # the suite, every gate, the boot smoke
    python -m tools.checks gates    # just the gates (fast, no test run)

ONE thing to remember. CI runs exactly this, so local-green and CI-green
cannot disagree. Exit code is non-zero if anything fails.
"""
from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass

from tools.refactor_audit.coverage_gate import COVERAGE_JSON

PY = sys.executable


@dataclass
class Check:
    name: str
    argv: list[str]
    why: str


GATES = [
    Check("structure gates", [PY, "-m", "tools.refactor_audit.structure_gates", "--check"],
          "file size, SQL outside the data layer"),
    Check("import contracts", [PY, "-m", "tools.refactor_audit.import_contracts", "--check"],
          "the layering rules and the single real-money surface"),
    Check("orphan modules", [PY, "-m", "tools.refactor_audit.orphan_modules", "--check"],
          "whole modules nothing imports"),
    Check("boot smoke", [PY, "-c", "import backend.src.app"], "the composition root imports"),
    Check("doc links", [PY, "tools/check_doc_links.py"], "every relative markdown link resolves"),
]

SUITE = Check("test suite", [PY, "-m", "pytest", "tests/", "-q", "--cov=backend",
                             f"--cov-report=json:{COVERAGE_JSON.name}"],
              "every behaviour anyone bothered to pin")
COVERAGE = Check("coverage ratchet", [PY, "-m", "tools.refactor_audit.coverage_gate", "--check"],
                 "coverage may rise, never fall")


def run(check: Check) -> bool:
    print(f"  {check.name:<20} ", end="", flush=True)
    started = time.time()
    res = subprocess.run(check.argv, capture_output=True, text=True)
    elapsed = time.time() - started
    if res.returncode == 0:
        print(f"ok   ({elapsed:.1f}s)")
        return True
    print(f"FAIL ({elapsed:.1f}s)  -- {check.why}")
    for line in (res.stdout + res.stderr).strip().splitlines()[-30:]:
        print(f"      {line}")
    return False


def main(argv: list[str]) -> int:
    what = argv[0] if argv else "all"
    checks = list(GATES)
    if what == "all":
        COVERAGE_JSON.unlink(missing_ok=True)
        checks += [SUITE, COVERAGE]
    elif what != "gates":
        print(__doc__)
        return 2
    results = [run(c) for c in checks]
    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
