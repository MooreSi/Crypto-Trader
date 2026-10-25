# Positions

**Living file.** Covers `services/positions/` and `services/trading/order_service.py`.

## What it is

`order_service.py` places every order (see rules/20). `manager.py` runs every
10 s and reconciles each open trade with the exchange: position gone (stop, last
TP, liquidation or manual close on the exchange), position smaller (a TP
filled), then breakeven and trailing.

## Constraints

- Close path frozen: `close_trade`, `partial_close_trade`, `record_close`.
- A stop move places the new stop first, then cancels the old one.
- Positions the app did not open are reported, never touched.

## Known things and gotchas

- **The breakeven move only tightens** (2026-10-25). With `trail_atr_mult`
  on, TP2 filling re-applied "breakeven after TP1" and moved a stop already
  trailed into profit back to entry. `_reconcile_partial` now moves to
  breakeven only if that is tighter (`_tighter`). Pinned by
  `tests/services/positions/test_manager_defects.py`.
- **Exit reason names the rung that filled** (2026-10-25), the highest TP oid
  among the exit fills, not the ladder's length.
- **Analytics** (`analytics.py`) are pure over closed trades and equity
  snapshots. Sharpe uses daily last-equity returns x sqrt(365) and cannot tell
  a deposit from a return.
- **No take-profit below $11.20** (2026-10-25). Hyperliquid accepts a TP
  trigger under its $10 minimum and rejects it only when it fires
  (`minTradeNtlRejected`). On live ~$20 positions every TP of the 50/25/25
  ladder was under $10, so trades could only exit at the stop; a UNI long
  ran past all three TPs and came back to the stop. `_tp_plan` now merges an
  undersized rung into the rung before it (nearer price). A $20 position gets
  one TP at 1R; a full three-rung ladder needs roughly $35 or more. The
  $11.20 covers the case that the fired order is valued at its limit price
  (10% past the trigger); which price the exchange uses is not verified.
- **The breakeven stop is rounded to a valid tick** (2026-10-24). The fill
  price is an average and rarely on the grid; sent raw, the exchange would
  refuse the stop move. Found in the end-to-end paper run on BTC
  (fill 79839.39975).
- Exit P&L is booked from the exchange's own fills (`closedPnl`, `fee`) when
  they can be read back, newest fills first, else estimated at the base taker
  fee and corrected by nothing (the estimate stays). An estimated row is the
  exception, not the rule.
- `move_stop` after a partial resizes the stop to the remaining size; the
  exchange would otherwise hold a reduce-only stop larger than the position.

## Open questions

- Not yet run against testnet with real fills (needs an API wallet).
