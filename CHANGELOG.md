# Changelog

All notable changes to Crypto Trader. Newest first.

## [Unreleased]

### Changed
- Signal tracking (and so what each engine's model learns) now replays every
  signal through the live exit plan: your TP ladder, the breakeven move and
  taker fees, from the real fill when it traded. A win is a signal that made
  money net of fees. The old "+1R before -1R" label called setups winners
  that the 3R take-profit never paid. Old labels are re-scored while their
  candles are still held, and are otherwise left out of training.

### Fixed
- The engines exceeded Hyperliquid's request limit (about 2000 of the 1200
  weight per minute an IP may use), so every info call, the account reads
  of the positions loop included, failed with HTTP 429 on mainnet. A closed
  candle series is now kept until its next bar closes, and candle fetches
  share a 600-per-minute budget; coins over budget are scanned next cycle.

### Added
- `min_stop_pct` (Risk page, default 0 = off): refuses a trade whose stop is
  closer than this % of price, where the round-trip fee is a large part of
  the risk.

## [0.2.0] - 2026-10-25 - Strategy Lab, analytics and a new dashboard

### Added
- Walk-forward tuning in the Strategy Lab: settings are chosen on one stretch
  of history and scored only on the next, against your defaults on the same
  bars. It shows a proposal and never changes a setting.
- Strategy Lab: backtest any engine, or one of three research strategies
  (Donchian trend ensemble, Bollinger + RSI reversion, Supertrend flip), on
  Hyperliquid history with the app's own exit plan. Read-only: Lab strategies
  have no live switch.
- Performance analytics on the Trades page and dashboard: profit factor,
  expectancy in R, Sharpe, max drawdown, losing streak, per-engine table.
- Market pulse on the dashboard: breadth, volume-weighted funding, crowded
  longs and shorts, top movers.
- Telegram trade alerts (Settings): opens, take-profits, stop moves, closes.
  The bot token is kept in the OS keychain.
- Each engine's model now reports the features it learned most from.
- A redesigned dashboard: sidebar navigation, new cards, charts that resize.
- Restart and Stop buttons next to Pause in the dashboard header. Both shut
  the app down cleanly; Restart starts the same checkout again and the page
  reloads when it is back.

### Fixed
- A trailed stop is no longer moved back to breakeven when a later TP fills.
  Before, with trailing on, TP2 filling loosened a stop that was already in
  profit back to the entry price.
- A trade closed by its only (merged) take-profit is recorded as TP1, not as
  the last rung of the ladder.
- A watched coin named in mixed case (kPEPE, kBONK) is scanned. Before, the
  watchlist stored it upper-cased and it never matched.
- The day's starting equity, which the daily loss limit counts from, is
  recorded from the first positions pass of the UTC day, not when the
  dashboard or a signal first asks.
- Clearing a number on the Risk page no longer saves the field's minimum.
- Take-profit orders are never smaller than $11.20. Smaller ladder rungs are
  merged into the rung before them, down to a single TP1 for the whole
  position. Before, on small positions Hyperliquid rejected every TP when it
  fired, so trades could only close at the stop.
- Shutting down (Stop, Restart, Ctrl+C, the Stop scripts) now waits for a
  pass already running. Before, it could close the databases under a running
  engine or positions pass, which then failed with "database is closed".

### Changed
- Risk per trade can now be set up to 100% of equity (was 5%). The default
  stays 0.5%. The max position size cap and free margin still limit how big
  a trade can get.

## [0.1.0] - 2026-10-24 - First release

### Added
- Hyperliquid perpetuals: any listed market, 24x7. Paper (default), testnet and
  mainnet networks; API wallet key per network in the OS keychain.
- Three research engines ported from FOREX Trader and rebuilt for crypto:
  Breakout (15m), Reversal / ICT (15m + daily), Trend PA (1h + 4h). Each has
  its own database and model; every signal tracked to "+1R or stop first".
- Per-engine ML (gradient boosting) on scale-free crypto features: funding,
  open interest, BTC as the cross-asset peer, sessions, weekend, event
  proximity. Daily retrain, accepted only if the holdout AUC beats chance at 95%.
- Risk governor with eleven gates, deterministic sizing from the stop, leverage
  chosen to keep liquidation beyond the stop, isolated margin, daily loss limit
  and optional daily profit target (UTC day).
- Exchange-side stop and take-profit ladder; breakeven after TP1; optional ATR
  trailing; an entry is closed at once if its stop cannot be placed.
- Crypto event calendar: US macro, options expiries, CME weekend gap, user
  events (token unlocks, listings, upgrades) per coin; blackout before/after.
- React dashboard on 127.0.0.1:8890 with CSRF and DNS-rebinding protection.
- Admin console client, labelled "Crypto Trader" in name, hostname and version.
- macOS and Windows start/stop scripts; runs beside FOREX Trader without sharing
  a port, folder, lock, keychain entry or process.
- Rules, structural gates and test protocol carried over from FOREX Trader.

### Not in this release
- VPS / remote node mode, Telegram signal channels, licence keys, spot trading.
