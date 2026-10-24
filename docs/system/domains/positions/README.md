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
