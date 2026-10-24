# Crypto Trader

Automated trading of **Hyperliquid perpetual futures**, 24 hours a day, 7 days
a week, from your own computer.

Three research engines watch the most liquid markets on Hyperliquid (or your
own watchlist), track every signal they find to its outcome, and learn which
ones work. When you switch an engine **live**, its signals go through a
deterministic risk governor and are traded with an **exchange-side stop-loss
and take-profit ladder**, so positions stay protected even when the app is
closed.

Sister project of [FOREX Trader](https://github.com/MooreSi/forex-gold) (XAUUSD
on MetaTrader 5), built from its rules and engines, and designed to run on the
same machine at the same time.

> **Version 0.1.** Starts in **paper** mode (simulated account on live prices,
> no wallet). Trading is **off** until you turn it on. Not financial advice.
> Leveraged crypto can lose money very quickly.

---

## Features

**Markets**
- Any perpetual listed on Hyperliquid. Scans the top 20 by 24h volume, or your
  watchlist; blocklist anything.
- Live price, funding, open interest and volume for every market; candle charts.

**Three engines, each with its own model**
| Engine | Timeframe | Looks for |
|---|---|---|
| Breakout | 15m | a tight range broken on volume, or broken and retested |
| Reversal (ICT) | 15m + daily | a liquidity sweep of a key level followed by a market structure shift (FVG / "unicorn" noted) |
| Trend PA | 1h + 4h | a pullback to EMA20 in an established EMA20/50/200 trend, with a rejection candle |

Every signal is tracked virtually to "+1R or stop first". Each engine retrains
daily on its own outcomes, and a new model is only accepted if it beats chance
on recent data it has never seen.

**Risk governor** (defaults in brackets)
- Risk per trade from the stop distance (0.5% of equity); positions rounded
  down to the exchange's lot size.
- Leverage cap (3x) and isolated margin, with liquidation kept well beyond the stop.
- Max open positions (3), max positions in one direction (2), funding-cost
  limit, daily loss limit (3%), optional daily profit target.
- Event blackout around high-impact events (30 min either side).
- Take-profit ladder (1R 50%, 2R 25%, 3R 25%), breakeven after TP1, optional ATR trailing.
- Every decision, placed or refused, is recorded with the reason.

**Crypto event calendar**: US macro releases (FOMC, CPI, NFP, PCE), Deribit
options expiries, the CME Bitcoin futures weekend gap, and your own token
unlocks, listings and upgrades, optionally tied to specific coins.

**Three networks**: `paper` (default), `testnet` (Hyperliquid's test exchange)
and `mainnet`.

**Dashboard** at `http://127.0.0.1:8890`: account, positions, resting orders,
equity curve, markets, engines, trades with a full audit trail, risk settings,
events, settings.

**Admin console**: reports to the shared FOREX Trader admin console, clearly
labelled **Crypto Trader**. Can be turned off in Settings.

## Install and run

Needs **Python 3.11+**. Runs locally only (no VPS mode in this build).

**macOS**: double-click `Crypto Start.command` (first run creates `.venv` and
installs everything). Stop with `Crypto Stop.command`.

**Windows**: double-click `Setup & Start Crypto.bat`. Stop with `Stop Crypto.bat`.

**By hand**:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

The dashboard opens at <http://127.0.0.1:8890>.

## Going from paper to real trading

1. Watch the **Engines** page in paper mode until an engine's tracked results
   show an edge. Paper does not charge funding or model liquidation, so it
   flatters live results.
2. In Hyperliquid, create an **API wallet** (More > API). It can trade but
   **cannot withdraw**. Never give this app your main wallet's private key.
3. **Settings**: enter your account address and the API wallet key (stored in
   your OS keychain), choose **testnet**, restart.
4. **Risk**: review every limit, then turn **Trading enabled** on; on
   **Engines**, switch one engine **Live**.
5. Only after testnet behaves as expected, repeat on **mainnet**.

## Running beside FOREX Trader

| | FOREX Trader | Crypto Trader |
|---|---|---|
| Dashboard | 8888 | **8890** |
| Data folder | `ForexTrader` | `CryptoTrader` |
| Lock, keychain, admin token | its own | its own |

Neither app's start or stop scripts can stop the other.

Data folder: `~/Library/Application Support/CryptoTrader` (macOS),
`%APPDATA%\CryptoTrader` (Windows), `~/.config/CryptoTrader` (Linux).

## For developers

Read [CLAUDE.md](CLAUDE.md) and [docs/system/rules/](docs/system/rules/00-start-here.md)
first. Everything is checked with one command:

```bash
.venv/bin/python -m tools.checks all     # tests, structural gates, coverage, boot
cd frontend && npm install && npm test && npm run build
```

Layout:

```
run.py                     start-up: lock, port check, server
backend/src/app.py         composition root
backend/src/runtime.py     24x7 loops: positions, engines, events, admin console
backend/src/api/           FastAPI routers (127.0.0.1 only, CSRF-protected)
backend/src/controllers/   one thin controller per page
backend/src/services/      exchange, market, engines, ml, risk, trading, positions, events, remote
frontend/                  React dashboard (dist/ is committed)
tests/                     pytest suite (never touches an exchange)
tools/                     checks and structural gates
docs/system/               vision, rules, domain knowledge
```

## Licence

[GNU Affero General Public License v3.0](LICENSE), the same as FOREX Trader.
