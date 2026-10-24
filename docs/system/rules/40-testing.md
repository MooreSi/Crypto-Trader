# Testing: the protocol

## Red, green, then commit

1. **Write the test first.**
2. **Run it. Watch it fail** for the reason you expected.
3. Implement the smallest change that passes.
4. Run it. Watch it pass.
5. Run `.venv/bin/python -m tools.checks all` before committing.

## Every green assertion needs a negative control

If you assert a set is empty, also assert your detector can find a member.
`tests/refactor/test_gates_catch_violations.py` plants one violation per gate.

## Where tests live

The tree mirrors `backend/src/`: `services/risk/gates.py` is tested by
`tests/services/risk/test_gates.py`. Every directory has `__init__.py`.

| Kind | Example |
|---|---|
| Characterization (frozen behaviour) | `tests/trading/test_close_path_characterization.py` |
| Pinned defaults | `tests/services/risk/test_settings.py` |
| Behaviour | `tests/services/positions/test_manager.py` |
| Structural / gates | `tests/refactor/` |
| Isolation from FOREX Trader | `tests/test_runs_beside_forex_gold.py` |
| Dashboard | `frontend/src/**/__tests__/*.test.ts` (vitest) |

## Never do this to a test

Delete it because it fails; skip/xfail it; loosen an assertion; widen a
tolerance; comment out the assert.

## Safety in tests

**No test may reach any exchange.** `tests/conftest.py`:

- sets `CRYPTO_TRADER_DATA_DIR` to a temp folder before the app is imported;
- replaces the SDK's `Exchange.__init__` and `Info.__init__` with functions
  that raise `ExchangeSentinel`;
- provides `fake_exchange` (installs `tests/fakes.py::FakeExchange` as the
  provider), `fresh_db` and `fixed_clock`.

## Determinism

Read the time through `backend/src/utils/clock.py`; tests pin it with
`fixed_clock`. Never build "now" at import time.

## Mutation spot-checks

For a test that guards money, break the code on purpose and watch the test
fail, then restore and delete `__pycache__`
(`find . -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +`). A stale
`.pyc` can make a killed mutant look like a survivor, never the reverse.

## Running

```bash
.venv/bin/python -m pytest tests/ -q        # the Python suite
.venv/bin/python -m tools.checks all        # suite + gates + coverage + boot
cd frontend && npm test                     # dashboard tests
```

**Never run two full suites at once.** Coverage is a ratchet
(`tools/refactor_audit/coverage_gate.py`): it may rise, never fall. Gates fail
closed: no data, no entrypoint, no baseline means FAIL.
