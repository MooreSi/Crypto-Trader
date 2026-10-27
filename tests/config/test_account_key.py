"""Which account a figure belongs to: the network plus the address."""
from backend.src import config


def test_paper_is_one_account(monkeypatch):
    monkeypatch.setattr(config, "get", lambda k, d=None: {"network": "paper",
                                                          "account_address": "0xAB"}.get(k, d))
    assert config.account_key() == "paper"


def test_a_real_network_is_keyed_by_address(monkeypatch):
    monkeypatch.setattr(config, "get", lambda k, d=None: {"network": "mainnet",
                                                          "account_address": "0xAbC"}.get(k, d))
    assert config.account_key() == "mainnet:0xabc"
