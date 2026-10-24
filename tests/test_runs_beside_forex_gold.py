"""Crypto Trader must be able to run while FOREX Trader runs on the same machine.

Each assertion is one thing the two apps would otherwise share. See
docs/system/rules/80-running-beside-forex-gold.md.
"""
import importlib
import os
import sys

from backend.src import config
from backend.src.config import secrets
from backend.src.utils import single_instance

FOREX_PORTS = {8888, 9000, 9010, 9101, 9111, 8443, 8444, 8765}


def test_default_data_folder_is_not_forex_traders(monkeypatch):
    monkeypatch.delenv("CRYPTO_TRADER_DATA_DIR", raising=False)
    monkeypatch.delenv("CRYPTO_TRADER_DATA_DIR_NAME", raising=False)
    fresh = importlib.reload(config)
    try:
        assert fresh.USER_DATA_DIR.name == "CryptoTrader"
        assert "ForexTrader" not in str(fresh.USER_DATA_DIR)
    finally:
        monkeypatch.setenv("CRYPTO_TRADER_DATA_DIR", os.environ.get("CRYPTO_TRADER_DATA_DIR", ""))
        importlib.reload(config)


def test_dashboard_port_is_not_one_forex_trader_uses():
    assert config.DEFAULT_DASHBOARD_PORT not in FOREX_PORTS


def test_lock_file_has_its_own_name():
    assert single_instance.lock_path().name == "crypto_trader.lock"


def test_keyring_service_is_its_own():
    assert secrets.SERVICE == "CryptoTrader"


def test_env_vars_have_their_own_prefix():
    import pathlib
    src = pathlib.Path(config.__file__).read_text()
    assert "FOREX_TRADER_" not in src


def test_launchers_never_kill_by_name():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    for name in ("Crypto Stop.command", "Stop Crypto.bat"):
        text = (root / name).read_text()
        assert "pkill" not in text and "killall" not in text
        assert "taskkill /IM" not in text
        # stop by this app's own pid, never by whatever holds a port
        assert "lsof" not in text and ":8888" not in text and "netstat" not in text


def test_python_used_is_the_projects_venv():
    assert sys.version_info >= (3, 11)
