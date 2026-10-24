"""The admin console's WebSocket protocol, client side only.

Message names are copied from FOREX Trader
(`backend/src/services/cluster/remote/protocol.py`), which runs the admin
server this app connects to. They must stay byte-identical: the server is
FOREX Trader's code and this app does not change it.
"""

# Client -> server
MSG_HELLO = "hello"
MSG_PONG = "pong"
MSG_STATUS = "status"
MSG_DIAGNOSTICS = "diagnostics"
MSG_UPDATE_STATUS = "update_status"
MSG_REGISTER = "register"

# Server -> client
MSG_WELCOME = "welcome"
MSG_REJECT = "reject"
MSG_REVOKE = "revoke"
MSG_LICENCE = "licence"
MSG_PING = "ping"
MSG_GET_DIAG = "get_diagnostics"
MSG_GIT_UPDATE = "git_update"
MSG_VERSION_INFO = "version_info"


def make(type_: str, **kwargs) -> dict:
    return {"type": type_, **kwargs}
