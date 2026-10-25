"""Reports this install to the shared admin console, labelled as Crypto Trader.

The admin console is FOREX Trader's (its server runs inside FOREX Trader on
the owner's admin machine, its UI is `MooreSi/forex-admin`). This app speaks
the same protocol as a FOREX Trader client so it appears in the same Remote
Clients list, and changes NOTHING on the server side.

**How the console tells the two apps apart.** The server stores and shows a
client's `nickname` (as its name), `hostname` and `version`. This client
fills all three so no column can be mistaken for a FOREX Trader install:

    name      "Crypto Trader - <machine>"    (unless the user set a nickname,
                                              which still gets the prefix)
    hostname  "<machine> [Crypto Trader]"
    version   "Crypto Trader 0.2.0"

It also sends `app: "crypto-trader"` and `app_name`, which today's server
ignores and a future console can show as its own column.

What it deliberately does NOT do, because the server is not ours to steer:

* send `machine_uuid` -- the server grants remote-ADMIN rights by machine
  UUID, and a trading bot has no business holding them;
* act on `git_update` -- that pushes FOREX Trader's code. It is refused with
  an `update_status` saying so;
* store a licence -- this app has none (`licence_required: False` in the
  registration, which the server admits without approval);
* listen on UDP 8444 for the LAN beacon -- FOREX Trader's client binds that
  port, and a second listener could take the beacon from it. This client
  tries localhost, then the internet address, then a LAN scan.

Nothing here can stop the app: every failure is logged and retried.
"""
from __future__ import annotations

import asyncio
import json
import logging
import platform
import secrets
import socket
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from backend.src import config
from backend.src.services.remote import tls
from backend.src.services.remote.protocol import (
    MSG_DIAGNOSTICS, MSG_GET_DIAG, MSG_GIT_UPDATE, MSG_HELLO, MSG_PING, MSG_PONG, MSG_REGISTER,
    MSG_REJECT, MSG_REVOKE, MSG_STATUS, MSG_UPDATE_STATUS, MSG_VERSION_INFO, MSG_WELCOME, make,
)
from backend.src.utils.os_utils import scrub_log_secrets
from backend.src.utils.version_history import APP_ID, APP_NAME, __version__

log = logging.getLogger(__name__)

STATUS_EVERY_S = 30
RETRY_S = 30
SCAN_TIMEOUT_S = 0.5

_START = time.time()
_status: dict = {"connected": False, "host": "", "last_error": "", "admitted": False}

#: Supplied by the runtime: () -> dict with "positions" and "exchange_ok".
StatusProvider = Callable[[], dict]


def _remote_dir() -> Path:
    d = Path(config.USER_DATA_DIR) / "remote"
    d.mkdir(parents=True, exist_ok=True)
    return d


def token() -> str:
    """This install's 64-hex token, created on first use. Never FOREX Trader's."""
    path = _remote_dir() / "client_token.txt"
    if path.exists():
        tok = path.read_text(encoding="utf-8").strip()
        if len(tok) == 64:
            return tok
    tok = secrets.token_hex(32)
    path.write_text(tok, encoding="utf-8")
    return tok


def machine() -> str:
    return platform.node() or "unknown"


def display_name() -> str:
    nick = str(config.get("admin_console_nickname") or "").strip()
    return f"{APP_NAME} - {nick or machine()}"


def labelled_hostname() -> str:
    return f"{machine()} [{APP_NAME}]"


def labelled_version() -> str:
    return f"{APP_NAME} {__version__}"


def _identity() -> dict:
    return {"version": labelled_version(), "hostname": labelled_hostname(),
            "platform": sys.platform, "app": APP_ID, "app_name": APP_NAME,
            "commit_note": APP_NAME}


def build_hello() -> dict:
    return make(MSG_HELLO, token=token(), ts=time.time(), **_identity())


def build_register() -> dict:
    return make(MSG_REGISTER, token=token(), nickname=display_name(), email="",
                licence_required=False, ts=time.time(), **_identity())


def build_status(provider: Optional[StatusProvider]) -> dict:
    info = provider() if provider else {}
    extra = {}
    try:
        import psutil
        vm = psutil.virtual_memory()
        extra = {"cpu_percent": psutil.cpu_percent(interval=None),
                 "mem_percent": vm.percent}
    except Exception:
        pass
    return make(MSG_STATUS, uptime_s=int(time.time() - _START),
                trades_open=info.get("positions"), bridge_connected=bool(info.get("exchange_ok")),
                bridge_native=True, network=config.get("network"), **_identity(), **extra)


def build_diagnostics() -> dict:
    lines: list[str] = []
    try:
        if config.LOG_FILE.exists():
            raw = config.LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            lines = [scrub_log_secrets(ln) for ln in raw[-500:]]
    except Exception:
        pass
    data = {"platform": sys.platform, "hostname": labelled_hostname(), "python": sys.version,
            "version": labelled_version(), "uptime_s": int(time.time() - _START),
            "network": config.get("network"), "log_lines": lines,
            "log_raw": "\n".join(lines)}
    return make(MSG_DIAGNOSTICS, data=data)


def status() -> dict:
    return dict(_status)


# ── finding the server ────────────────────────────────────────────────────────

def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return ""


async def _port_open(host: str) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, tls.SERVER_PORT),
                                           timeout=SCAN_TIMEOUT_S)
        writer.close()
        return True
    except Exception:
        return False


async def candidate_hosts() -> list[str]:
    hosts = ["127.0.0.1", tls.SERVER_HOST]
    ip = _local_ip()
    parts = ip.split(".")
    if len(parts) == 4 and (ip.startswith("192.168.") or ip.startswith("10.")
                            or ip.startswith("172.")):
        prefix = ".".join(parts[:3])
        probes = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != ip]
        found = await asyncio.gather(*[_port_open(h) for h in probes])
        hosts += [h for h, ok in zip(probes, found) if ok]
    return hosts


# ── the connection ────────────────────────────────────────────────────────────

async def _session(ws, host: str, provider: Optional[StatusProvider]) -> None:
    await ws.send(json.dumps(build_hello()))
    first = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    if first.get("type") == MSG_REJECT:
        if first.get("reason") == "invalid_token":
            await ws.send(json.dumps(build_register()))
            _status["last_error"] = "registered; waiting to be admitted"
        else:
            _status["last_error"] = f"rejected: {first.get('reason')}"
        return
    if first.get("type") != MSG_WELCOME:
        _status["last_error"] = f"unexpected reply {first.get('type')}"
        return
    _status.update(connected=True, host=host, last_error="", admitted=True)
    log.info("[Admin] connected to admin console at %s as %s", host, display_name())
    await ws.send(json.dumps(build_status(provider)))
    last = time.time()
    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=STATUS_EVERY_S)
        except asyncio.TimeoutError:
            raw = None
        if time.time() - last >= STATUS_EVERY_S:
            await ws.send(json.dumps(build_status(provider)))
            last = time.time()
        if raw is None or isinstance(raw, bytes):
            continue
        msg = json.loads(raw)
        kind = msg.get("type")
        if kind == MSG_PING:
            await ws.send(json.dumps(make(MSG_PONG)))
        elif kind == MSG_GET_DIAG:
            await ws.send(json.dumps(build_diagnostics()))
        elif kind == MSG_GIT_UPDATE:
            await ws.send(json.dumps(make(
                MSG_UPDATE_STATUS, status="failed",
                error=f"{APP_NAME} does not take FOREX Trader updates")))
        elif kind == MSG_REVOKE:
            (_remote_dir() / "client_token.txt").unlink(missing_ok=True)
            _status.update(connected=False, admitted=False, last_error="revoked by administrator")
            return
        elif kind == MSG_VERSION_INFO:
            pass   # FOREX Trader's version: not ours to compare against


async def run(provider: Optional[StatusProvider] = None) -> None:
    """Connect forever; returns only when cancelled."""
    import websockets
    while True:
        for host in await candidate_hosts():
            try:
                async with websockets.connect(f"wss://{host}:{tls.SERVER_PORT}",
                                              ssl=tls.client_ssl_context(host),
                                              open_timeout=8, close_timeout=3,
                                              max_size=8 * 1024 * 1024) as ws:
                    ok, why = tls.peer_is_acceptable(host, tls.peer_fingerprint(ws))
                    if not ok:
                        log.warning("[Admin] refusing %s: %s", host, why)
                        continue
                    await _session(ws, host, provider)
                    break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _status["last_error"] = f"{host}: {exc}"
            finally:
                _status["connected"] = False
        await asyncio.sleep(RETRY_S)
