# Contributing

This is a trading application: a change merged here can place an order with
somebody's money. That is why some rules below are stricter than you will be
used to. This is the short version of [docs/system/rules/](docs/system/rules/00-start-here.md);
if the two disagree, the rules directory wins.

## Before you write code

1. Read [the golden rules](docs/system/rules/10-golden-rules.md).
2. Read the domain README for the part you are changing
   (`docs/system/domains/<domain>/README.md`).
3. For anything bigger than a one-line fix, write a half-page spec in the PR.

## Rules that will get a pull request rejected

- **A test that can reach an exchange.** The suite uses `tests/fakes.py`; the
  SDK constructors raise in tests on purpose.
- **Editing a test to make your change pass.**
- **No failing test first.** Show it red for the right reason.
- **Reshaping the close path** (`close_trade`, `partial_close_trade`,
  `record_close`).
- **Changing a default** in `services/risk/settings.py`.
- **Anything that touches FOREX Trader** (its ports, data folder, processes).
- A `frontend/src` change without the rebuilt `frontend/dist`.

## Checks

```bash
.venv/bin/python -m tools.checks all
cd frontend && npm test && npm run build
```

All of it must pass. A failing gate is not noise.

## Licence

By contributing you agree your contribution is licensed under the
[GNU AGPL v3](LICENSE).
