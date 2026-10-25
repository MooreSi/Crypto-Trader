"""Release history: the single source of truth for the version number.

`RELEASES[0]` is the running version. The About page lists these, the admin
console reads `__version__` through the hello handshake, and `VERSION` at the
repo root is kept equal to it (pinned by tests/test_version.py).

A version bump adds a new entry at the top, a `CHANGELOG.md` section and an
updated pin test, in the same commit. See docs/system/rules/50-workflow.md.
"""
from __future__ import annotations

RELEASES: list[dict] = [
    {
        "version": "0.2.0",
        "date": "2026-10-25",
        "title": "Strategy Lab, analytics and a new dashboard",
        "notes": [
            "Strategy Lab: backtest any engine, or three research strategies (Donchian trend "
            "ensemble, Bollinger + RSI reversion, Supertrend flip), with the app's own exit plan.",
            "Walk-forward tuning: settings chosen on one stretch of history are scored only on "
            "the next, against your defaults. A proposal only; nothing changes by itself.",
            "Performance analytics: profit factor, expectancy in R, Sharpe, max drawdown, "
            "losing streak and a per-engine breakdown.",
            "Market pulse: breadth, funding, crowded longs and shorts, top movers.",
            "Telegram trade alerts for opens, take-profits, stop moves and closes.",
            "Each engine shows the features its ML model learned most from.",
            "A redesigned dashboard with a sidebar, new cards and charts that resize.",
            "Fixed: a trailed stop was moved back to breakeven when a later TP filled; "
            "take-profits below Hyperliquid's minimum were rejected when they fired; "
            "mixed-case coins (kPEPE) on the watchlist were never scanned; the daily loss "
            "limit could count from a figure taken after a loss.",
        ],
    },
    {
        "version": "0.1.0",
        "date": "2026-10-24",
        "title": "First release",
        "notes": [
            "Trades any perpetual listed on Hyperliquid, 24 hours a day, 7 days a week.",
            "Three networks: paper (simulated, no wallet), testnet and mainnet.",
            "Three research engines ported from FOREX Trader and retuned for crypto: "
            "Breakout, Reversal (ICT) and Trend PA, each with its own ML model.",
            "Risk governor: per-trade risk, leverage cap, isolated margin, daily loss "
            "limit, max open positions, correlation cap and a daily profit target.",
            "Exchange-native stop-loss and take-profit orders, so a position stays "
            "protected while the app is closed.",
            "Crypto event calendar: US macro releases, options expiries, CME weekend "
            "gap and your own token-unlock or listing events.",
            "Reports to the shared admin console, labelled as Crypto Trader.",
        ],
    },
]

__version__: str = RELEASES[0]["version"]

#: How this app names itself to the shared admin console and in logs.
APP_NAME = "Crypto Trader"
APP_ID = "crypto-trader"
