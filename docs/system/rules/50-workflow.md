# How to make a change, end to end

> spec -> failing test -> smallest change -> full checks -> commit

If a step is skipped, say which one and why, in the commit.

## 0. Understand before you type

Read the file and its tests. Comments here carry incident history; if a comment
explains why something is odd, it is odd on purpose.

## 1. Classify the change

| Kind | Needs |
|---|---|
| Bug fix | a test reproducing it first |
| New behaviour | a short spec in the PR/commit + tests |
| Refactor | characterization tests before moving anything |
| Tunable | [60-adding-a-tunable.md](60-adding-a-tunable.md) |
| Anything touching orders, sizing or the close path | **stop**: owner sign-off + testnet session |

## 2. Verify, all of it

```bash
.venv/bin/python -m tools.checks all
cd frontend && npm test && npm run build     # if frontend/src changed
```

**Use `.venv/bin/python`, never bare `python`.** FOREX Trader once reported
20 "pre-existing failures" that were a different interpreter missing packages.

**A `frontend/src` change that is not rebuilt is not shipped.** `frontend/dist`
is committed and is what the app serves.

## 3. Commit

Explain **why**, not what. Never mention which AI model produced the change.

## 4. Releasing a version

The same commit carries all of:

1. a new first entry in `backend/src/utils/version_history.py` `RELEASES`
   (the About page and the admin console read it);
2. `VERSION` and `pyproject.toml` / `frontend/package.json` versions;
3. a `## [x.y.z]` section at the top of `CHANGELOG.md`;
4. `tests/test_version.py` updated to the new number.

Then tag `vX.Y.Z` and create the GitHub release from the CHANGELOG section.
