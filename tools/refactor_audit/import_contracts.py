"""Import contracts: layers point downward, and one file holds the money.

    python -m tools.refactor_audit.import_contracts --check

    frontend (HTTP) -> api/ -> controllers/ -> services/ -> db/
                                       utils/, config/ -> nothing above them

Enforced at zero, no baseline:

1. `api/` never imports `services` or `db` (named exemption: api/server.py,
   which maps the exchange's error type to an HTTP status).
2. `controllers/` never import `db`, a `*_repo` module, or `api`.
3. `services/` never import `controllers` or `api`.
4. `db/` imports only `db`; `config/` only `config`; `utils/` only `utils`
   and `config`.
5. **The real-money surface.** Outside `services/exchange/` (where the
   clients are implemented), only `services/trading/order_service.py` may
   call `.place_market(`, `.place_trigger(`, `.cancel(` or `.set_leverage(`.
6. `order_service` is imported only by the executor, the manual-close
   service and the position manager.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

from tools.refactor_audit._scan import ROOT, python_files

PKG = "backend.src"
MONEY_CALLS = {"place_market", "place_trigger", "cancel", "set_leverage"}
MONEY_FILE = "backend/src/services/trading/order_service.py"
ORDER_SERVICE_IMPORTERS = {
    "backend/src/services/trading/executor.py",
    "backend/src/services/trading/manual.py",
    "backend/src/services/positions/manager.py",
}
API_EXEMPT = {"backend/src/api/server.py"}


def imports_of(tree: ast.AST) -> list[tuple[int, str]]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append((node.lineno, node.module))
            out += [(node.lineno, f"{node.module}.{a.name}") for a in node.names]
    return out


def _layer(rel: str) -> str:
    parts = rel.split("/")
    return parts[2] if len(parts) > 3 and parts[:2] == ["backend", "src"] else ""


def _forbidden(rel: str, mod: str) -> str:
    if not mod.startswith(PKG + "."):
        return ""
    target = mod[len(PKG) + 1:].split(".")[0]
    layer = _layer(rel)
    if layer == "api" and rel not in API_EXEMPT and target in ("services", "db"):
        return "api imports services/db"
    if layer == "controllers" and (target in ("db", "api") or mod.endswith("_repo")):
        return "controller imports db/api/repo"
    if layer == "services" and target in ("controllers", "api"):
        return "service imports controllers/api"
    if layer == "db" and target != "db":
        return "db imports above itself"
    if layer == "config" and target != "config":
        return "config imports above itself"
    if layer == "utils" and target not in ("utils", "config"):
        return "utils imports above itself"
    if mod.endswith("trading.order_service") or ".order_service." in mod:
        if layer == "services" and rel not in ORDER_SERVICE_IMPORTERS and rel != MONEY_FILE:
            return "order_service imported outside its allowed callers"
    return ""


def money_calls(tree: ast.AST) -> list[int]:
    """Lines calling an order-placing method. `.cancel` counts only with two or
    more arguments: the exchange's is `cancel(coin, oid)`, while asyncio's
    `Task.cancel()` takes none and is everywhere."""
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        name = n.func.attr
        if name in MONEY_CALLS and (name != "cancel" or len(n.args) + len(n.keywords) >= 2):
            out.append(n.lineno)
    return out


def check_file(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = [f"{rel}:{line}: {why} ({mod})" for line, mod in imports_of(tree)
           if (why := _forbidden(rel, mod))]
    if not rel.startswith("backend/src/services/exchange/") and rel != MONEY_FILE:
        out += [f"{rel}:{line}: order-placing call outside order_service" for line in money_calls(tree)]
    return out


def run(root: Path = ROOT) -> list[str]:
    out = []
    for p in python_files("backend", root=root):
        out += check_file(p, root)
    return out


def main() -> int:
    problems = run()
    for p in problems:
        print(p)
    print(f"import contracts: {len(problems)} violation(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
