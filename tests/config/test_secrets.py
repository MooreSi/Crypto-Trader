import pytest

from backend.src.config import secrets


class MemoryKeyring:
    def __init__(self):
        self.store = {}

    def get_password(self, service, user):
        return self.store.get((service, user))

    def set_password(self, service, user, value):
        self.store[(service, user)] = value

    def delete_password(self, service, user):
        self.store.pop((service, user), None)


@pytest.fixture
def ring(monkeypatch):
    kr = MemoryKeyring()
    monkeypatch.setattr(secrets, "_keyring", lambda: kr)
    return kr


def test_keys_are_per_network_under_this_apps_service(ring):
    secrets.set_agent_key("testnet", "AB" * 32)
    assert secrets.get_agent_key("testnet") == "0x" + "ab" * 32
    assert secrets.get_agent_key("mainnet") is None
    assert all(service == "CryptoTrader" for service, _ in ring.store)


def test_malformed_keys_are_refused(ring):
    for bad in ("", "0x1234", "zz" * 32, "ab" * 33):
        with pytest.raises(ValueError):
            secrets.set_agent_key("testnet", bad)
    assert ring.store == {}


def test_clear(ring):
    secrets.set_agent_key("mainnet", "0x" + "1" * 64)
    secrets.clear_agent_key("mainnet")
    assert not secrets.has_agent_key("mainnet")
