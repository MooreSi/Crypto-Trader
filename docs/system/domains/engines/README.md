# Engines

**Living file.** Covers `services/engines/`, `breakout/`, `reversal/`,
`trend_pa/`, `ml/`.

## What it is

Three research engines ported in spirit from FOREX Trader and rebuilt for any
Hyperliquid perpetual. Each produces `Setup`s from closed candles; the shared
`EngineService` stores, tracks, scores and (only when live) hands them on.

| Engine | Bars | Idea |
|---|---|---|
| Breakout | 15m | tight range (<= 4 ATR, 24 bars) broken on volume (z >= 1), or broken then retested |
| Reversal | 15m (+1d) | liquidity sweep of a swing / prior-day level, then market structure shift; FVG and "unicorn" as features |
| Trend PA | 1h (+4h) | pullback to EMA20 in an EMA20>50>200 trend with ADX >= 20 and a rejection wick |

## Constraints

- **Total isolation**: each engine has its own signal DB and model directory;
  one vocabulary for "traded" (`signal_repo.LIVE_EXECUTED`) shared on purpose,
  after FOREX Trader's engines used two words and a copied query matched zero
  rows for months.
- Research is keyed by **market data source**: paper and mainnet share
  `<engine>_mainnet.db`; testnet is kept apart (its prices are its own market).
- The label is "+1R before -1R" (`tracker.py`). A bar touching both is a loss.
  Expiry after 192 bars is label 0.
- Features are **append-only** (`ml/features.py`). The model file name carries
  the width; a narrower model hands over until the next accepted retrain.
- **ML fails open**: no model means `ml_score=None`, which passes the ML gate
  unless `ml_require_model` is on. Kept deliberately so a fresh install can
  trade; never mistake "no model" for a filter that is running.

## Known things and gotchas

- **Strategy Lab** (2026-10-25): `services/strategies/` holds research
  generators (`donchian_trend`, `bb_rsi_revert`, `supertrend_flip`) with the
  same `Setup` interface as the engines. They are listed only in
  `services/backtest/catalogue.py` and are NOT in `registry.py`: no signal DB,
  no model, no live toggle. Promoting one to an engine is an owner decision
  (it also changes the engine list pinned by `tests/api/test_routes.py`).
- **The backtester** (`services/backtest/`) walks closed bars with the
  generator seeing only the last 260 closed bars and closed higher-timeframe
  bars, one trade per coin at a time, entry at the signal bar's close. The
  simulator applies the live exit plan (ladder, breakeven from the next bar),
  scores a bar touching stop and target as the stop, and charges a round-trip
  taker fee in R. It leaves out funding, slippage and the risk gates.
- First Lab results, BTC, 3000 bars each, 2026-10-25, default ladder and no
  ML filter: every strategy negative. Profit factor breakout 0.54, reversal
  0.58, trend_pa 0.53, donchian_trend 0.82 (89 trades on 4h since 2025-06),
  bb_rsi_revert 0.37, supertrend_flip 0.51. The 1R/2R/3R ladder caps trend
  followers' winners, which is what they live on; worth testing a trend
  ladder before judging donchian_trend.
- **Walk-forward tuning** (`backtest/tuning.py`, 2026-10-25): k+1 equal
  segments after the 260-bar warm-up; each fold picks the best candidate by
  profit factor (at least `min_trades` train trades) on segment i and scores
  it on segment i+1 only. Candidates: the strategy's `grid` (Lab strategies
  take an optional `p` dict; `DEFAULTS` equal the old constants) x 4 exit
  ladders x breakeven 0/1. Setups are computed once per parameter set
  (`runner.signals`) and every exit plan is simulated over them
  (`runner.trades_from_signals`, which ignores bars after the window end).
  It writes nothing. Negative control: making the selection score the test
  window fails `test_choice_is_made_on_train_bars_only`.
- First walk-forward runs, BTC, 3000 bars, 4 folds, 2026-10-25: donchian_trend
  tuned -7.2R (45 trades, PF 0.73) vs defaults -12.1R (74, PF 0.72), 25%
  stable; supertrend_flip tuned -5.6R vs -11.3R, 50% stable; bb_rsi_revert
  tuned -11.8R vs defaults -4.2R. Tuning lost less in two of three, but
  nothing was profitable out of sample, and the choices were unstable
  across folds: no edge found on BTC.
 (feature importances of the accepted
  model) so the dashboard can show what each engine learned from.
- Running a second instance (the preview) on the same IP doubles Hyperliquid
  info requests; the preview hit HTTP 429 within a minute of starting. Pause a
  preview's engines when the real app is running.
- **Breakout measures ATR and regime on the bars BEFORE the trigger**
  (2026-10-24). Measured with it, the breakout bar's own range pushed ATR into
  the top decile and every genuine breakout read as "volatile" and was dropped.
  Found by `test_breakout_fires_long_on_a_volume_break_of_a_tight_range`.
- **Model acceptance is a significance test** (2026-10-24): holdout AUC must
  beat 0.5 + 1.645 x SE (Mann-Whitney null). A fixed 0.53 margin was tried
  first; pure noise cleared it about a third of the time on a 60-signal
  holdout. Measured after the change: 1 of 60 noise seeds accepted.
- Firing rates on 2026-10 data (BTC, ETH, SOL, HYPE; ~21 days of 15m, ~62 days
  of 1h): Breakout 34-47, Reversal 54-78, Trend PA 13-24 per coin. That is
  frequency, not edge: no engine has yet shown an edge on crypto.
- Retraining runs once a day per engine; needs 60 labelled signals.

## Open questions

- Which engines, if any, have an edge on crypto. Decide from tracked research
  before switching any engine live on mainnet.
