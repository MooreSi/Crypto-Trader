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

- **Fees vs stop distance** (2026-10-25). A round trip pays ~0.09% of price in
  taker fees, plus slippage on a triggered stop, whatever the stop. Live
  mainnet losses on ~$20 positions with 0.2-0.5% stops closed at -1.16R to
  -1.48R. `min_stop_pct` (sizing, default off) refuses such signals.
- **At ~$20 a position the TP ladder is one TP.** Rungs under $11.20 are merged
  (`order_service._tp_plan`), so 1R/2R/3R becomes 100% at 1R. A one-rung
  ladder must still pass `min_reward_risk` (1.5): 1R alone would refuse all.
- **Research behind the owner's settings of 2026-10-25** (19 most traded
  perps, 52 days of 15m / 125 days of 1h history, fee 0.06% a side including
  slippage, ladder as placed at $20, first 60% of each coin vs last 40%):

  | setup | first 60% avg R | last 40% avg R | trades |
  |---|---|---|---|
  | all engines, 1R/2R/3R, no stop filter (before) | -0.166 | -0.044 | 3632 |
  | breakout + trend_pa, 3R, stop >= 1.5% | -0.058 | +0.184 | 809 |
  | trend_pa only, 3R, stop >= 1.5% (chosen) | -0.011 | +0.251 | 295 |

  Reversal was negative in the first period under every setting tried, and
  all five of its live trades lost. Nothing here was positive in both periods;
  re-run before trusting it on a new regime.
- **A $0 equity is never the day's start** (2026-10-27). An unfunded or
  just-changed account reads $0; recorded as the start, it put the loss-limit
  floor at $0 and every later equity read as profit, so the limit could not
  trip that day. The first positive reading is recorded instead.
- **The day's start is per account** (2026-10-27), keyed
  `day_start_equity:<date>:<account_key>`. Before, a mid-day change of
  account address kept the old account's figure: from a bigger account the
  limit read a phantom loss, from a smaller one a phantom profit it would not
  trip on. A date-only key written before the change still counts for its day.
- The daily loss limit uses **equity** (includes unrealised), the profit target
  uses **realised** P&L. On purpose: a loss limit must see an open loser; a
  target must not stop trading on a winner that has not been banked.
- The correlation cap counts direction only. Crypto majors move together, so
  "2 longs" is already a large BTC bet.

## Open questions

- Per-coin risk scaling for very volatile small caps (not in v0.1).
