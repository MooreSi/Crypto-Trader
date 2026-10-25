# Running beside FOREX Trader

The owner runs FOREX Trader (`~/Forex-Gold`) on the same machine. Crypto Trader
must start, run and stop **without touching it**, and FOREX Trader's
launchers must not be able to hurt Crypto Trader.

## What is separate, and where it is pinned

| Shared by nothing | FOREX Trader | Crypto Trader | Pinned by |
|---|---|---|---|
| Data folder | `.../ForexTrader` | `.../CryptoTrader` | `test_default_data_folder_is_not_forex_traders` |
| Env var prefix | `FOREX_TRADER_*` | `CRYPTO_TRADER_*` | `test_env_vars_have_their_own_prefix` |
| Dashboard port | 8888 | **8890** | `test_dashboard_port_is_not_one_forex_trader_uses` |
| Other ports | 9000, 9010, 9101, 9111, 8443, 8444, 8765 | none bound | same |
| Single-instance lock | `forex_trader.lock` | `crypto_trader.lock` | `test_lock_file_has_its_own_name` |
| Keyring service | FOREX's | `CryptoTrader` | `test_keyring_service_is_its_own` |
| Admin-console token | FOREX's `remote/client_token.txt` | its own, in its own data folder | `test_token_is_this_apps_own` |

FOREX Trader's Stop scripts kill whatever listens on 8888 and 9000; nothing of
Crypto Trader's is there. Crypto Trader's Stop scripts kill only the pid in
its own lock file, after checking it is a `run.py` process; `run.py` never
kills anything and refuses to start if its port is taken
(`test_launchers_never_kill_by_name`).

## The admin console

The console's server runs inside FOREX Trader; its UI is `MooreSi/forex-admin`.
Crypto Trader is a **client** only, and changes nothing on the server side. It
identifies itself in every column the console already shows:

| Column | Value |
|---|---|
| name (nickname) | `Crypto Trader - <machine or nickname>` |
| hostname | `<machine> [Crypto Trader]` |
| version | `Crypto Trader 0.2.0` |

It also sends `app: "crypto-trader"`, which a future console version can show
as its own column. It never sends `machine_uuid` (the server grants admin
rights by it), refuses `git_update` (that is FOREX Trader's code), stores no
licence, and does **not** listen on UDP 8444 (FOREX Trader's client does; a
second listener could take its beacon). It finds the server at localhost, then
the public address, then by LAN scan.

## Never

- change anything in `~/Forex-Gold`, `~/Forex-Update`, `~/forex-admin` from here;
- read FOREX Trader's data folder, database or keyring entries;
- bind one of its ports.
