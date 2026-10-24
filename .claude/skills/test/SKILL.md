---
name: test
description: Write or review tests for Crypto Trader. Use when creating tests, reviewing tests for correctness, or improving coverage. Enforces red-first, negative controls, no exchange access, and the anti-patterns that make tests pass without proving anything.
---

# Writing and reviewing tests

Full protocol: docs/system/rules/40-testing.md.

## The loop

1. Write the test. 2. Run it and **watch it fail for the reason you expect**.
3. Make the smallest change. 4. Watch it pass. 5. `tools.checks all`.

## Fixtures (tests/conftest.py)

| Fixture | Gives |
|---|---|
| `fresh_db` | a migrated main database in tmp, closed after |
| `fake_exchange` | `tests/fakes.py::FakeExchange` installed as the provider (+ `fresh_db`) |
| `fixed_clock` | `clock.now()` pinned to 2026-10-24 13:53:20 UTC (a Saturday) |

The SDK's `Exchange` and `Info` constructors raise in every test. If your test
hits `ExchangeSentinel`, it reached for the real exchange: use the fake.

## Layout

Mirror `backend/src/`: `services/risk/gates.py` -> `tests/services/risk/test_gates.py`.
Every test directory has `__init__.py`.

## Anti-patterns (reject in review)

| Pattern | Why it is wrong |
|---|---|
| Asserting the mock was called, not the outcome | proves wiring, not behaviour |
| Expected value computed with the same code under test | tautology |
| `>=` / `in` where the exact value is known | hides regressions |
| A zero-violations assertion with no planted violation | blind scanner passes |
| Building "now" at import time | stale by the time the test runs |
| One test asserting ten unrelated things | the first failure hides the rest |
| Editing an existing test so a change passes | golden rule 4 |

## For money paths, mutate

Break the line on purpose, watch the test fail, restore, delete `__pycache__`.
