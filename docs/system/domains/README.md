# Domains

One living README per part of the system: what it is, where the code lives,
what must not change, and what we have learned. Read the affected one before a
change; update it when a change teaches you something.

| Domain | Code |
|---|---|
| [exchange](exchange/README.md) | `services/exchange/` |
| [engines](engines/README.md) | `services/engines/`, `breakout/`, `reversal/`, `trend_pa/`, `ml/` |
| [risk](risk/README.md) | `services/risk/`, `services/trading/executor.py` |
| [positions](positions/README.md) | `services/positions/`, `services/trading/order_service.py` |
| [market](market/README.md) | `services/market/` |
| [events](events/README.md) | `services/events/` |
| [platform](platform/README.md) | `run.py`, `app.py`, `runtime.py`, `config/`, `db/`, `remote/`, launchers |
| [frontend](frontend/README.md) | `frontend/` |
