"""A network change waits for restart, whatever else is saved meanwhile."""
import pytest

from backend.src import config
from backend.src.services.health import app_settings


@pytest.fixture
def pinned(tmp_path, monkeypatch, fresh_db):
    monkeypatch.setattr(config, "USER_DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.yaml")
    config.pin_network()
    yield
    monkeypatch.setattr(config, "_pinned_network", None)
    config.load()


def test_choosing_mainnet_does_not_switch_the_running_process(pinned):
    out = app_settings.set_network("mainnet")
    assert out["network"] == "paper" and out["network_on_restart"] == "mainnet"
    # saving an unrelated setting reloads config.yaml; the network must hold
    app_settings.set_account_address("0x" + "ab" * 20)
    assert config.get("network") == "paper"
    assert config.stored()["network"] == "mainnet"


def test_bad_address_and_network_are_refused(pinned):
    with pytest.raises(ValueError):
        app_settings.set_account_address("0x123")
    with pytest.raises(ValueError):
        app_settings.set_network("devnet")
