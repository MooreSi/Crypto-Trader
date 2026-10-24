# Risk

**Living file.** Covers `services/risk/` and `services/trading/executor.py`.

## What it is

`settings.py` (every limit, clamped, defaults pinned), `gates.py` (eleven pure
gates over a `GateContext`), `sizing.py` (size and leverage from the stop),
`day.py` (the UTC trading day and its starting equity). The executor builds the
context, runs the gates, sizes, records the decision and calls the order service.

## Constraints

- Defaults are the owner's "conservative" choice (2026-10-24) and are pinned.
- Every decision, placed or refused, is written to `gate_decisions` with every
  gate's result up to the first refusal.
- The trading day is 00:00-24:00 **UTC**; the daily loss limit and profit target
  reset at midnight UTC.
- Daily realised P&L is read from the audit trail (`trade_events` `opened`,
  `partial`, `closed`, `reconciled`), so a partial today on a trade opened
  yesterday counts today.

## Known things and gotchas

- The daily loss limit uses **equity** (includes unrealised), the profit target
  uses **realised** P&L. On purpose: a loss limit must see an open loser; a
  target must not stop trading on a winner that has not been banked.
- The correlation cap counts direction only. Crypto majors move together, so
  "2 longs" is already a large BTC bet.

## Open questions

- Per-coin risk scaling for very volatile small caps (not in v0.1).
