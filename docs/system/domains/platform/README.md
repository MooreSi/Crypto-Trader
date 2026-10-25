# Platform

**Living file.** Covers `run.py`, `backend/src/app.py`, `runtime.py`,
`config/`, `db/`, `services/remote/`, `services/health/`, the launchers.

## Startup

`run.py`: load config, take the single-instance lock, check port 8890 is free
(refuse, never kill), start uvicorn on 127.0.0.1. `app.py` lifespan: pin the
network, open the main DB, start the runtime loops.

## Constraints

- **Local only.** No VPS mode in this build; nothing binds a public interface.
- **The network is pinned at startup** (`config.pin_network`). Choosing another
  network writes config.yaml and takes effect on restart. Without the pin,
  saving any other setting reloaded the new network into a process still
  holding the old network's database (found 2026-10-24 while writing the
  Settings page).
- Runs beside FOREX Trader: see rules/80.

## Known things and gotchas

- **Telegram alerts** (`services/notify/`, 2026-10-25) read `trade_events`
  after each positions pass: no hook in the order path. The cursor
  (`telegram_last_event_id`) starts at the newest event when alerts are first
  on (no backlog), and moves only after a send succeeds. The bot token is in
  the keyring (`secrets.get_telegram_token`); the send error never includes
  the URL, which contains the token.
- The admin console's live end-to-end (register, appear in Remote Clients as
  "Crypto Trader - ...") has **not** been exercised: it would register a client
  on the owner's console and send a "New install" notification. Unit tests pin
  every field the console shows. First real run will confirm.
- The SDK is synchronous; the runtime runs every pass in a worker thread.
