"""The admin console must be able to tell this app from FOREX Trader."""
import asyncio
import json

from backend.src.services.remote import client
from backend.src.services.remote.protocol import MSG_GIT_UPDATE, MSG_UPDATE_STATUS


def test_every_visible_column_says_crypto_trader():
    hello = client.build_hello()
    assert hello["version"].startswith("Crypto Trader ")
    assert hello["hostname"].endswith("[Crypto Trader]")
    assert hello["app"] == "crypto-trader"
    reg = client.build_register()
    assert reg["nickname"].startswith("Crypto Trader - ")
    assert reg["licence_required"] is False


def test_never_claims_admin_rights_or_a_licence():
    for msg in (client.build_hello(), client.build_register()):
        assert "machine_uuid" not in msg and "machine_id" not in msg


def test_token_is_this_apps_own(tmp_path):
    from backend.src import config
    tok = client.token()
    assert len(tok) == 64
    assert str(config.USER_DATA_DIR) in str(client._remote_dir())
    assert "ForexTrader" not in str(client._remote_dir())


class _WS:
    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []

    async def send(self, raw):
        self.sent.append(json.loads(raw))

    async def recv(self):
        if not self.incoming:
            raise ConnectionError("closed")
        return json.dumps(self.incoming.pop(0))


def test_forex_updates_are_refused():
    ws = _WS([{"type": "welcome"}, {"type": MSG_GIT_UPDATE}])
    try:
        asyncio.run(client._session(ws, "127.0.0.1", None))
    except ConnectionError:
        pass
    replies = [m for m in ws.sent if m["type"] == MSG_UPDATE_STATUS]
    assert replies and replies[0]["status"] == "failed"


def test_unknown_token_registers_without_licence():
    ws = _WS([{"type": "reject", "reason": "invalid_token"}])
    asyncio.run(client._session(ws, "127.0.0.1", None))
    assert ws.sent[0]["type"] == "hello" and ws.sent[1]["type"] == "register"
