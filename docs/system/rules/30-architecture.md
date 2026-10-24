# Architecture: layers and boundaries

```
frontend/ (React, compiled to frontend/dist, served by the app)
    | HTTP/JSON on 127.0.0.1:8890
backend/src/api/routers/  ->  controllers/  ->  services/  ->  db/
                                     utils/, config/  ->  nothing above them
backend/src/app.py        composition root (may import anything)
backend/src/runtime.py    the loops (positions 10s, engines 60s, events 1h, admin)
```

- **Routers forward.** One controller call plus a response; no logic.
- **Controllers route.** A flat `<name>_controller.py` that names an operation
  and forwards it to one service. No loops, merges, formatting or fallbacks.
- **Services decide.** Grouped by domain under `services/<domain>/`.
- **Repos hold the SQL.** `*_repo.py` files and `backend/src/db/` are the only
  places a SQL string may appear (structure gate).

## Enforced at zero (tools/refactor_audit/import_contracts.py)

1. `api/` never imports `services` or `db` (named exemption: `api/server.py`,
   which maps the exchange error type to HTTP 502).
2. Controllers never import `db`, a `*_repo` module or `api`.
3. Services never import `controllers` or `api`.
4. `db/` imports only `db`; `config/` only `config`; `utils/` only `utils` and
   `config`.
5. Outside `services/exchange/`, only `services/trading/order_service.py` calls
   `place_market`, `place_trigger`, `cancel(coin, oid)` or `set_leverage`.
6. `order_service` is imported only by the executor, the manual-close service
   and the position manager.

## The exchange abstraction

Everything above `services/exchange/` speaks `ExchangeClient`
(`services/exchange/types.py`). Three implementations: `HyperliquidClient`
(testnet/mainnet), `PaperExchange` (live prices, simulated account) and the
test `FakeExchange`. No `if paper:` anywhere in trading code.

## Databases

| File | Holds | Keyed by |
|---|---|---|
| `crypto_trader_<network>.db` | trades, trade_events, gate_decisions, events, app_config, equity | network |
| `<engine>_<source>.db` | one engine's signals and outcomes | market data source (`mainnet` for paper+mainnet, `testnet`) |
| `models/<source>/<engine>/` | one engine's model files | same |

Engines never share a database, a row or a label.

## Security of the local dashboard

Binds 127.0.0.1 only, no login (single-user local app). Every write needs the
`X-Crypto-Trader` header (blocks CSRF) and the `Host` must be localhost
(blocks DNS rebinding). `backend/src/api/security.py`.
