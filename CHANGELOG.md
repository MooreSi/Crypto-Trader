# Changelog

All notable changes to Crypto Trader. Newest first.

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
