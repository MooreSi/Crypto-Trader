# 001: Strategies, and a TP1-plus-runner default

Asked by the owner on 2026-10-29.

## What changes

A **Strategy** page in the sidebar. A strategy is a named set of the settings
that decide how a trade is sized, filtered and exited (risk per trade,
leverage, reward:risk, the TP ladder, breakeven, the stop lock, the trail,
position and daily limits, the event blackout). The owner can create, edit,
copy, delete and activate strategies. Activating one writes its values into
the risk settings, which is what the engines, the executor and the position
manager already read. Editing the active strategy re-applies it.

A built-in strategy, **TP1 80% at 1.5R + trailed runner**, is created once per
account database and activated:

- TP ladder `[[1.5, 0.8]]`: one take-profit closes 80% at 1.5R.
- The other 20% has no take-profit (a *runner*).
- After TP1 the stop moves to the TP1 price (`stop_lock_r` = 1.5).
- The stop then trails the runner at 1.5 x ATR(15m) (`trail_atr_mult`),
  only ever tightening.
- Every other value (risk %, leverage, limits) is copied from the settings in
  force when it is created, so activating it changes only the exits.

Two engine changes make the strategy possible:

1. **Runner** (`order_service._tp_plan`): when the ladder's fractions add up
   to less than 1, the remainder is left with no take-profit instead of being
   added to the last rung. A runner worth less than $11.20 (valued at the
   last rung's price) is added to the last rung, the same rule as a small
   rung, because Hyperliquid may refuse an order under $10 when it fires.
2. **Stop lock** (`manager._reconcile_partial`, new setting `stop_lock_r`,
   default 0): when the breakeven move is due, the stop goes to entry plus
   `stop_lock_r` x the initial risk instead of entry. If that price is not on
   the safe side of the current mid (price has already fallen back through
   it), the stop goes to entry as before, and the trail tightens it later.

The tracker and the Strategy Lab replay (`backtest/simulator.py`) apply the
stop lock too, so labels match the live plan. The simulator does not model the
trail; a runner that is not stopped is marked to the last close as before.

## What must not change

- Defaults: `stop_lock_r` defaults to 0 (stop to entry, as today). A ladder
  adding up to 1 places exactly the same orders as before.
- The close path is not touched.
- FOREX Trader isolation: nothing here reads or writes outside this app.

## Touches money?

Yes: order placement (the TP sizes) and stop movement. Mitigation:

- At the owner's current size (about $20 notional per trade) the 20% runner
  is about $4, under the $11.20 floor, so it is merged into TP1: the orders
  placed are the same as today (100% at 1.5R). The runner, lock and trail
  engage from roughly $56 notional.
- **Testnet session still owed** before relying on the runner path: open one
  trade of at least $60 notional on testnet, watch TP1 close 80%, the stop
  move to the TP1 price for the remaining 20%, and a trail move.

## Trail distance

Chosen from a replay of the 358 resolved mainnet signals (reversal, breakout,
trend PA) on Hyperliquid 15m candles. 126 reached 1.5R before their stop.
Runner result after TP1 with the stop locked at 1.5R:

| trail | runner avg R | runners past 1.5R | runners at 3R+ |
|---|---|---|---|
| 0.5 x ATR | 1.64 | 13 | 7 |
| 1.0 x ATR | 1.64 | 11 | 7 |
| 1.5 x ATR | 1.63 | 10 | 5 |
| 2.0 x ATR | 1.61 | 10 | 5 |
| 3.0 x ATR | 1.55 | 9 | 1 |

(trailing from the bar close; trailing from the bar extreme is within 0.03R.)
About 90% of runners came straight back to the locked stop at 1.5R, so the
runner adds roughly +0.03R per winning trade and the trail distance matters
little between 0.5 and 2 ATR. 1.5 x ATR sits in the middle of that flat
range, which is the least likely to be an artefact of a small sample.

## Open questions

- Should a strategy also carry the engines' Live switches and the watchlist?
  Provisional: no; those stay on their own pages.
