"""Telegram settings: token to the keyring, chat id and switch to config.yaml."""
import pytest

from backend.src import config
from backend.src.config import secrets
from backend.src.runtime import TradingRuntime
from backend.src.services.health import app_settings
from backend.src.services.notify import notifier


class _Ring:
    def __init__(self):
        self.store = {}

    def get_password(self, s, u): return self.store.get((s, u))
    def set_password(self, s, u, p): self.store[(s, u)] = p
    def delete_password(self, s, u): self.store.pop((s, u), None)


@pytest.fixture
def env(tmp_path, monkeypatch, fresh_db):
    ring = _Ring()
    monkeypatch.setattr(secrets, "_keyring", lambda: ring)
    monkeypatch.setattr(config, "USER_DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.yaml")
    config.load()
    yield ring
    config.load()


def test_token_goes_to_the_keyring_not_the_config_file(env, tmp_path):
    out = app_settings.set_telegram(True, "12345", "123456789:" + "A" * 30)
    assert out["telegram_enabled"] and out["telegram_chat_id"] == "12345"
    assert out["has_telegram_token"] and "telegram_token" not in out
    assert "123456789:" not in (tmp_path / "config.yaml").read_text()
    assert secrets.get_telegram_token() == "123456789:" + "A" * 30


def test_blank_token_keeps_the_stored_one(env):
    app_settings.set_telegram(True, "1", "123456789:" + "B" * 30)
    app_settings.set_telegram(False, "1", "")
    assert secrets.get_telegram_token() == "123456789:" + "B" * 30
    assert not app_settings.get()["telegram_enabled"]


def test_malformed_token_is_refused(env):
    with pytest.raises(ValueError):
        app_settings.set_telegram(True, "1", "not a token")


def test_positions_pass_runs_the_notifier_and_survives_its_failure(fake_exchange, monkeypatch):
    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError("down")
    monkeypatch.setattr(notifier, "notify_pass", boom)
    rt = TradingRuntime()
    rt.positions_pass()
    assert calls == [1] and rt.health["exchange_ok"] is True
