# Start here

You are working on a **crypto trading application that can trade real money**
on Hyperliquid. That single fact drives everything else on this page.

## Read these, in this order

| | Document | Read it when |
|---|---|---|
| 0 | [../vision/000-goal.md](../vision/000-goal.md) | to understand what this system is for |
| 1 | **[10-golden-rules.md](10-golden-rules.md)** | **always, before touching anything** |
| 2 | [20-trading-safety.md](20-trading-safety.md) | before any change near orders, sizing or the exchange |
| 3 | [30-architecture.md](30-architecture.md) | before adding a file or an import |
| 4 | [40-testing.md](40-testing.md) | before writing a test, i.e. before writing code |
| 5 | [50-workflow.md](50-workflow.md) | how a change gets made, end to end |
| 6 | [60-adding-a-tunable.md](60-adding-a-tunable.md) | when a constant should be user-editable |
| 7 | [70-file-organisation.md](70-file-organisation.md) | when a file is too big |
| 8 | [80-running-beside-forex-gold.md](80-running-beside-forex-gold.md) | when touching startup, ports, data paths or the admin console |

Plain Markdown on purpose: any agent or human reads the same rules.

## The thirty-second version

- **Never** place, close or modify a trade on **mainnet** as a test. Testnet is
  the demo account and is allowed, but never from the automated suite.
- **Never** edit a test to make a change pass.
- Write the test first, and **watch it fail**.
- Run `.venv/bin/python -m tools.checks all` before committing.
- Report what you actually did, including what you skipped.

## Why the rules are this strict

They are inherited from FOREX Trader, where an earlier refactor was declared
complete and was not: ~3,000 lines of code nothing called, duplicates that had
diverged, and a guardrail that scanned a deleted directory and printed "all
good" for months. Green output is not evidence.

## If you are unsure

Stop and ask. Specifically stop if the change touches order placement, closing
or sizing; a test would need modifying to pass; a baseline would need raising;
or verifying it needs **mainnet** (testnet does not need asking).

## Where everything lives

```
docs/system/vision/   why the system exists
docs/system/rules/    these rules
docs/system/domains/  one living README per part of the system
```

Read the affected domain's README before designing a change; update it when a
change teaches you something. If a domain file and the code disagree, the code
is the fact: fix the file and say so.
