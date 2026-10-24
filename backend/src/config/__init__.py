"""Configuration loader.

Reads `config.yaml` from the user data directory, then applies environment
variable overrides. All code reads settings through `config.get()`.

**The data directory is this app's own, never the FOREX Trader's.** FOREX
Trader keeps everything in a folder called `ForexTrader`; this app uses
`CryptoTrader`. The two apps are designed to run on the same machine at the
same time, and the only thing that makes that safe is that they share nothing
on disk: not the config, not a database, not the single-instance lock. See
docs/system/rules/80-running-beside-forex-gold.md.

`CRYPTO_TRADER_DATA_DIR` (a full path) or `CRYPTO_TRADER_DATA_DIR_NAME` (a
folder name in the platform's usual place) separate an install deliberately.
The test suite sets the first before anything imports this module, which is
what keeps a test run away from a real install's wallet and database.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover - PyYAML is a declared dependency
    _YAML_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parents[3]  # project root, code only

_APP_DATA_FOLDER = os.environ.get("CRYPTO_TRADER_DATA_DIR_NAME", "CryptoTrader")
if sys.platform == "win32":
    USER_DATA_DIR = Path.home() / "AppData" / "Roaming" / _APP_DATA_FOLDER
elif sys.platform == "darwin":
    USER_DATA_DIR = Path.home() / "Library" / "Application Support" / _APP_DATA_FOLDER
else:
    USER_DATA_DIR = Path.home() / ".config" / _APP_DATA_FOLDER
if os.environ.get("CRYPTO_TRADER_DATA_DIR"):
    USER_DATA_DIR = Path(os.environ["CRYPTO_TRADER_DATA_DIR"])

CONFIG_FILE = USER_DATA_DIR / "config.yaml"
DATA_DIR = USER_DATA_DIR / "data"
MODELS_DIR = USER_DATA_DIR / "models"
LOG_FILE = DATA_DIR / "crypto_trader.log"

#: The three places an order can go. `paper` simulates fills against live
#: public prices and needs no wallet; `testnet` is Hyperliquid's test exchange
#: (this app's "demo account"); `mainnet` is real money.
NETWORKS = ("paper", "testnet", "mainnet")

#: 8890, not 8888: 8888 is FOREX Trader's dashboard, and its launchers kill
#: whatever listens there. 9000/9010/9101/9111/8443/8444/8765 are its bridge,
#: EA, admin and sync ports. Nothing in this app binds any of them.
DEFAULT_DASHBOARD_PORT = 8890

DEFAULTS: dict[str, Any] = {
    "network": "paper",
    "dashboard_host": "127.0.0.1",
    "dashboard_port": DEFAULT_DASHBOARD_PORT,
    # The main Hyperliquid account (the address that holds the funds). The
    # signing key is an API wallet ("agent") approved for it; it lives in the
    # OS keyring, never in this file. See config/secrets.py.
    "account_address": "",
    # Paper account starting balance, in USDC.
    "paper_starting_balance": 10_000.0,
    # Connect to the shared admin console as a client. On by default because
    # the owner wants to see every install; turning it off sends nothing.
    "admin_console_enabled": True,
    "admin_console_nickname": "",
    "log_level": "INFO",
}

_cfg: dict = {}

#: The network this process started on. Once pinned, reloading config.yaml
#: never changes it: the database, the engines' research and the exchange
#: client were all chosen for it at startup. Without this, saving any other
#: setting after choosing a new network would reload the new network into a
#: process still holding the old one's database -- a paper trade record
#: written while orders went to mainnet.
_pinned_network: str | None = None


def _load_yaml() -> dict:
    if not _YAML_AVAILABLE or not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _coerce(default: Any, raw: Any) -> Any:
    """Cast an env/yaml value to the type of its default."""
    if isinstance(default, bool):
        return str(raw).strip().lower() not in ("0", "false", "no", "off", "")
    if isinstance(default, int):
        return int(raw)
    if isinstance(default, float):
        return float(raw)
    return raw


def load() -> dict:
    """Read config.yaml + environment into the module cache and return it."""
    global _cfg
    base = _load_yaml()
    merged: dict[str, Any] = {}
    for key, default in DEFAULTS.items():
        env = os.environ.get(f"CRYPTO_TRADER_{key.upper()}")
        raw = env if env is not None else base.get(key, default)
        try:
            merged[key] = _coerce(default, raw)
        except (TypeError, ValueError):
            merged[key] = default
    for key, value in base.items():
        merged.setdefault(key, value)
    if merged["network"] not in NETWORKS:
        merged["network"] = DEFAULTS["network"]
    if _pinned_network is not None:
        merged["network"] = _pinned_network
    _cfg = merged
    return dict(_cfg)


def pin_network() -> str:
    """Fix the running network for the life of this process (called at startup)."""
    global _pinned_network
    _pinned_network = None
    _pinned_network = load()["network"]
    return _pinned_network


def get(key: str, default: Any = None) -> Any:
    if not _cfg:
        load()
    return _cfg.get(key, default)


def all_settings() -> dict:
    if not _cfg:
        load()
    return dict(_cfg)


def stored() -> dict:
    """What config.yaml says now, which may differ from the running values."""
    return _load_yaml()


def write_yaml(updates: dict, reload: bool = True) -> None:
    """Merge `updates` into config.yaml. `reload=False` leaves the running
    values alone -- used for settings that only take effect on restart."""
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    current = _load_yaml()
    current.update(updates)
    tmp = CONFIG_FILE.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(current, f, sort_keys=True)
    os.replace(tmp, CONFIG_FILE)
    if reload:
        load()


def save_to_yaml(updates: dict) -> None:
    """Merge `updates` into config.yaml and reload."""
    write_yaml(updates, reload=True)


def db_path(name: str) -> Path:
    """Where database `name` lives. One file per network for the main DB so a
    paper or testnet history can never be mistaken for a mainnet one."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / name


def main_db_path() -> Path:
    return db_path(f"crypto_trader_{get('network')}.db")
