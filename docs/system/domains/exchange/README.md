# Exchange

**Living file.** Covers `backend/src/services/exchange/`.

## What it is

The only code that knows Hyperliquid exists. Everything else speaks
`ExchangeClient` (`types.py`).

- `hyperliquid_client.py`: testnet/mainnet through `hyperliquid-python-sdk`
  **0.24.0** (pinned exactly). Reads via `Info(skip_ws=True)`, writes via
  `Exchange(api_wallet, url, account_address=main_account)`, built lazily.
- `paper_exchange.py`: live mainnet prices, simulated account, persisted in
  `app_config['paper_state']`.
- `rounding.py`: tick and lot rules.
- `provider.py`: picks the client from the network once.

## Constraints

- Prices: at most 5 significant figures and `6 - szDecimals` decimals; integer
  prices always valid. Sizes: at most `szDecimals` decimals, rounded **down**.
- Minimum order value $10.
- Trigger (stop/TP) orders are `{"trigger": {"triggerPx", "isMarket": True,
  "tpsl": "sl"|"tp"}}`, reduce-only, with a limit price 10% beyond the trigger
  as the worst acceptable fill (`TRIGGER_SLIPPAGE`).
- Order responses: `response.data.statuses[0]` is `{"resting": {oid}}`,
  `{"filled": {totalSz, avgPx, oid}}` or `{"error": str}`.

## Known things and gotchas

- **Paper flatters live.** No funding, no liquidation, fills at mid +/- 0.05%
  with no depth, triggers checked only when polled (every ~10 s). Quote a paper
  number with that caveat.
- **Paper fill prices are not on the tick grid** (mid x slippage). Harmless for
  paper; never copy a paper price into a real order unrounded.
- `market_close` in the SDK reads the position itself to choose the side; the
  client passes our rounded size.
- `all_mids` also returns spot pairs as `@<index>`; they are filtered out.
- Delisted perps stay in `meta` with `isDelisted: true` (e.g. MATIC, FTM);
  they are excluded from snapshots and the universe.

## Open questions

- Builder-deployed perp dexes (HIP-3) are not scanned; only the main dex.
