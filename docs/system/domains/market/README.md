# Market

**Living file.** Covers `services/market/`.

`candles.py` (fetch + 20 s cache, `closed()` drops the forming bar),
`indicators.py` (pure: EMA, ATR, ADX, RSI, MACD, Bollinger width, z-score,
swings), `levels.py` (swings, prior day, round numbers scaled to price),
`regime.py`, `sessions.py`, `universe.py`.


- **Watchlist matching ignores case** (2026-10-25). Settings store coins
  upper-cased; Hyperliquid names some in mixed case (`kPEPE`). `universe.select`
  maps back to the exchange's name. The dashboard compares with `sameCoin`.
- **`pulse.py`** summarises snapshots only (no candles): breadth of the top 30
  by volume, volume-weighted funding, crowded sides by funding, movers, and a
  mood label. Information only; no gate reads it.
- `indicators.py` gained `donchian` (excludes the latest bar), `bollinger_bands`
  and `supertrend` for the Strategy Lab, pinned in `test_indicators.py`.
## Constraints

- Engines decide on **closed** candles only.
- **No session gate.** FOREX Trader blocked trading outside its sessions and on
  weekends; crypto trades 24x7, so sessions and the weekend are ML features
  only. Asia 00-08, Europe 07-16, US 13-21 UTC.
- The universe is the watchlist if set, else the top `auto_top_n` (20) by 24h
  notional volume above `min_day_volume_usd`, minus the blocklist. Scanning
  all ~180 live perps every minute would hit the info endpoint's rate limit.
