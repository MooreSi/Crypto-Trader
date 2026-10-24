"""Coverage ratchet: total line coverage may rise, never fall.

    python -m tools.refactor_audit.coverage_gate --check     # compare
    python -m tools.refactor_audit.coverage_gate --record    # raise the baseline

Reads the JSON report the suite writes (`--cov-report=json:.coverage.json`).
No report is a FAILURE ("no coverage data"), never a pass: a ratchet with
nothing to read must not go green. The baseline only moves up, and only by
`--record`, in a commit that says why.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COVERAGE_JSON = ROOT / ".coverage.json"
BASELINE = Path(__file__).with_name("coverage_baseline.json")
TOLERANCE = 0.1


def total(path: Path = COVERAGE_JSON) -> float | None:
    if not path.exists():
        return None
    return float(json.loads(path.read_text())["totals"]["percent_covered"])


def main(argv: list[str]) -> int:
    now = total()
    if now is None:
        print("coverage ratchet: no coverage data (run the suite with --cov first)")
        return 1
    base = json.loads(BASELINE.read_text())["percent"] if BASELINE.exists() else 0.0
    if "--record" in argv:
        if now < base:
            print(f"coverage ratchet: {now:.2f}% is below the baseline {base:.2f}%; not lowering it")
            return 1
        BASELINE.write_text(json.dumps({"percent": round(now, 2)}, indent=2) + "\n")
        print(f"coverage ratchet: baseline recorded at {now:.2f}%")
        return 0
    if now + TOLERANCE < base:
        print(f"coverage ratchet: {now:.2f}% fell below the baseline {base:.2f}%")
        return 1
    print(f"coverage ratchet: {now:.2f}% (baseline {base:.2f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
