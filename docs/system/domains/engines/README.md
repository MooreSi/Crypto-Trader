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
