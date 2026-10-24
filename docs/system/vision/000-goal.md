# 000: What this system is and what it is for

**Status:** Living document
**Touches money:** yes, the whole system does
**Created:** 2026-10-24 (v0.1)

This is the plain-English answer to "what is this thing?". If anything else in
`docs/system/` conflicts with this document, this document wins or must be
updated.

---

## What it is

Crypto Trader is an automated trading application for **Hyperliquid
perpetual futures**. It can trade **any perpetual listed on Hyperliquid**,
around the clock: crypto never closes, so neither does the bot. It runs
**locally only**, on the owner's own computer, and shows everything it does on
a dashboard at `http://127.0.0.1:8890`.

It is the sister app of FOREX Trader (`MooreSi/forex-gold`, XAUUSD on
MetaTrader 5). It was built from that app's rules, structure and research
engines, re-aimed at crypto, and it is designed to **run at the same time** as
FOREX Trader on the same machine without either touching the other.

It is a personal/family trading tool, not a hosted product.

## What it does, in one paragraph

Three research engines: **Breakout**, **Reversal (ICT)** and **Trend PA** -
scan the most liquid Hyperliquid markets (or the owner's watchlist) on closed
candles. Every signal is stored and tracked virtually to its outcome, and each
engine trains its own model on those outcomes. When the owner switches an
engine **live** and the master **trading enabled** switch is on, its signals go
through the risk gates; a signal that passes is sized from its stop, entered at
market, and immediately protected by an **exchange-side stop-loss and
take-profit ladder**. The app then manages the trade: breakeven after TP1,
optional ATR trailing: and records every change.

## How it makes decisions

A signal becomes a trade only if it passes, in order: master switch,
freshness, ML score, reward:risk, one-per-coin, max positions, correlation cap,
funding cost, event blackout, daily loss limit, daily profit target. Then it is
sized deterministically: `equity x risk% / stop distance`, capped, rounded down
to the exchange's lot size, at a leverage low enough that liquidation sits well
beyond the stop. See [../rules/20-trading-safety.md](../rules/20-trading-safety.md).

## Where orders can go

| Network | What it is | Money |
|---|---|---|
| `paper` (default) | live mainnet prices, simulated account | none |
| `testnet` | Hyperliquid's test exchange: this app's **demo account** | test USDC |
| `mainnet` | Hyperliquid | **real** |

## What "safe" means here

- Nothing in the automated suite reaches any exchange, testnet included.
- No position is ever left without a stop: if the stop cannot be placed, the
  position is closed at once.
- Exits live on the exchange, so a crash, sleep or closed laptop does not
  leave a position unprotected.
- The close path is frozen from v0.1: moved verbatim only, never reshaped
  without owner sign-off and a testnet session.
- Positions the app did not open are never touched.

## What success looks like

- The bot runs unattended 24x7, and a closed laptop never costs a stop.
- On losing days the daily loss limit keeps the damage small and pre-decided.
- Every trade can be explained afterwards: which engine and signal, which gates
  it passed, how it was sized, every stop move, why it closed.
- Engines are only switched live once their tracked research shows an edge.

## Non-goals (v0.1)

- Running on a VPS or any remote host. Local only.
- Spot trading, or venues other than Hyperliquid.
- Copy-trading Telegram signal channels (FOREX Trader's main feature; not
  ported: its parser is gold-specific).
- A licence key. This build has none.
- High-frequency or latency-sensitive trading.
