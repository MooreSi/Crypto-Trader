"""Stop and Restart, asked for from the dashboard.

A request never stops the server itself. It records what was asked and,
a moment later (so the HTTP reply gets out first), calls the handler that
run.py installed, which tells uvicorn to shut down the normal way: the
runtime's loops are cancelled, a worker thread already in an exchange call
is allowed to finish, the databases close and the lock is released. Only
then does run.py look at `requested()` and, for a restart, launch again.

Open positions are not touched by either. Their stop and take-profits are
exchange-side orders, so they stay protected while the app is down.

Under the test client or any server not started by run.py there is no
handler, and a request is refused with `NotAvailable`.
"""
from __future__ import annotations

import sys
import threading
from typing import Callable, Optional

ACTIONS = ("stop", "restart")
#: Seconds the relaunched process waits for the old one's lock and port.
RESTART_WAIT_S = 30

_handler: Optional[Callable[[], None]] = None
_delay_s = 0.5
_requested: Optional[str] = None


class NotAvailable(RuntimeError):
    pass


def install(handler: Callable[[], None], delay_s: float = 0.5) -> None:
    global _handler, _delay_s
    _handler, _delay_s = handler, delay_s


def reset() -> None:
    global _handler, _requested
    _handler, _requested = None, None


def requested() -> Optional[str]:
    return _requested


def request(action: str) -> dict:
    global _requested
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    if _handler is None:
        raise NotAvailable("this server was not started by run.py; stop it where it was started")
    _requested = action
    if _delay_s <= 0:
        _handler()
    else:
        threading.Timer(_delay_s, _handler).start()
    return {"action": action}


def restart_argv(script: str, argv: list[str]) -> list[str]:
    """The command line for the relaunch: the user's flags, minus any --wait,
    plus --no-browser (the dashboard tab is already open) and our --wait."""
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a == "--wait":
            skip = True
            continue
        if a.startswith("--wait=") or a == "--no-browser":
            continue
        out.append(a)
    return [sys.executable, script, *out, "--no-browser", "--wait", str(RESTART_WAIT_S)]
