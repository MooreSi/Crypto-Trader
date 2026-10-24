"""Golden rule 7: every gate is shown to find a planted violation.

A green gate from a broken scanner is worse than no gate. Each test builds a
tiny tree with exactly one violation and asserts the gate reports it, then
asserts the real repository is clean.
"""
from pathlib import Path

from tools import check_doc_links
from tools.refactor_audit import import_contracts, orphan_modules, structure_gates


def _write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def test_structure_gate_finds_sql_outside_a_repo(tmp_path):
    _write(tmp_path, "backend/src/services/x/thing.py", 'Q = "SELECT a FROM b"\n')
    _write(tmp_path, "backend/src/services/x/thing_repo.py", 'Q = "SELECT a FROM b"\n')
    found = structure_gates.stray_sql(list((tmp_path / "backend").rglob("*.py")), tmp_path)
    assert len(found) == 1 and "thing.py" in found[0]


def test_structure_gate_finds_an_oversized_file(tmp_path):
    p = _write(tmp_path, "backend/big.py", "x = 1\n" * (structure_gates.MAX_LINES + 1))
    assert structure_gates.oversized([p])


def test_import_contracts_find_a_controller_reading_a_repo(tmp_path):
    p = _write(tmp_path, "backend/src/controllers/bad_controller.py",
               "from backend.src.services.positions import trades_repo\n"
               "from backend.src.services.positions.trades_repo import get\n")
    assert import_contracts.check_file(p, tmp_path)


def test_import_contracts_find_an_order_outside_order_service(tmp_path):
    p = _write(tmp_path, "backend/src/services/engines/sneaky.py",
               "def go(client):\n    client.place_market('BTC', True, 1, 0.01)\n"
               "    client.cancel('BTC', 5)\n")
    assert len(import_contracts.check_file(p, tmp_path)) == 2


def test_import_contracts_ignore_asyncio_task_cancel(tmp_path):
    p = _write(tmp_path, "backend/src/services/x.py", "def f(t):\n    t.cancel()\n")
    assert import_contracts.check_file(p, tmp_path) == []


def test_import_contracts_find_api_reaching_into_db(tmp_path):
    p = _write(tmp_path, "backend/src/api/routers/bad.py", "from backend.src.db import database\n")
    assert import_contracts.check_file(p, tmp_path)


def test_orphan_gate_fails_closed_without_entrypoints(tmp_path):
    _write(tmp_path, "backend/src/x.py", "")
    assert "missing" in orphan_modules.run(tmp_path)[0]


def test_orphan_gate_finds_an_unimported_module(tmp_path):
    _write(tmp_path, "run.py", "import backend.src.app\n")
    _write(tmp_path, "backend/__init__.py", "")
    _write(tmp_path, "backend/src/__init__.py", "")
    _write(tmp_path, "backend/src/app.py", "from backend.src import used\n")
    _write(tmp_path, "backend/src/used.py", "")
    _write(tmp_path, "backend/src/dead.py", "")
    found = orphan_modules.run(tmp_path)
    assert len(found) == 1 and "dead.py" in found[0]


def test_doc_link_checker_finds_a_broken_link(tmp_path):
    _write(tmp_path, "docs/a.md", "[ok](b.md) [bad](missing.md) [web](https://x.y)\n")
    _write(tmp_path, "docs/b.md", "")
    found = check_doc_links.broken(tmp_path)
    assert len(found) == 1 and "missing.md" in found[0]


def test_the_real_repository_is_clean():
    assert structure_gates.run() == []
    assert import_contracts.run() == []
    assert orphan_modules.run() == []
