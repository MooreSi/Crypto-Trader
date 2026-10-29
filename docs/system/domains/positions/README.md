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

- **Runner and stop lock** (2026-10-29). A TP ladder whose shares add up to
  less than 1 leaves a runner with no TP (`_tp_plan`); a runner under $11.20
  at the last rung's price is added to the last rung. `stop_lock_r` (default
  0) makes the breakeven move go to entry + n x initial risk; if that price
  is not strictly on the safe side of the mid, the stop goes to entry. A
  runner stopped beyond entry after a TP is recorded as "stop in profit".
  **Not yet watched on testnet**: needs one trade of $60+ notional so the
  runner is not merged (spec 001). At ~$20 positions the runner is merged
  and the orders are the same as a 100% TP1.

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
- **The equity curve is one account's** (2026-10-27). Changing the account
  address recorded two $0 snapshots between ~$45 ones on mainnet and the
  dashboard showed a 100% drawdown. Snapshots now carry `account`
  (`config.account_key()`: `paper`, or `<network>:<address>`); the curve,
  drawdown and Sharpe read the current account's rows plus untagged rows from
  before the column. A $0 reading is never recorded and never read: it is an
  unfunded or just-changed account, not a value. The cost: a real wipe-out to
  exactly $0 would not show as a 100% drawdown.
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

## The Calendar (`services/calendar/`, 2026-10-29)

Read-only views of closed trades for the Calendar page, ported from FOREX
Trader's Analysis calendar. Nothing here trades.

- A trade is filed whole under the **UTC date it closed on**, the risk
  governor's trading day (`risk/day.py`). Partials booked before midnight on
  a trade that closed after it show on the later day here, while the loss
  limit counted them on the day they were booked.
- Net is `realised_pnl - fees`, as everywhere else; R is net over `risk_usd`.
- The % figures are of the day's derived opening balance (equity now minus
  everything realised from that day on). Deposits, withdrawals and open
  positions' float are not in the rows, so they shift these figures.
- Target and loss-limit marks apply TODAY's settings to the day's realised
  closes; the real loss limit also counts open float. They are hints, not a
  record of what the governor did.
- The day journal (`day_journal` table) is keyed by `(account, day)` with
  `config.account_key()`, so paper, testnet and mainnet notes never mix.

## Open questions

- Not yet run against testnet with real fills (needs an API wallet).
