# Changelog

All notable changes to Crypto Trader. Newest first.

## [Unreleased]

### Added
- Restart and Stop buttons next to Pause in the dashboard header. Both shut
  the app down cleanly; Restart starts the same checkout again and the page
  reloads when it is back.

### Fixed
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
