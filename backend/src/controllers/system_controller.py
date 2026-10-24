"""System page and header: status, version, pause, stop, restart."""
from __future__ import annotations

from backend.src import runtime
from backend.src.utils import lifecycle, version_history


def status() -> dict:
    return runtime.get().status()


def version() -> dict:
    return {"version": version_history.__version__, "app": version_history.APP_NAME}


def releases() -> list[dict]:
    return version_history.RELEASES


def set_paused(paused: bool) -> dict:
    runtime.get().paused = bool(paused)
    return runtime.get().status()


def lifecycle_action(action: str) -> dict:
    """Ask run.py to stop or restart the app. Raises lifecycle.NotAvailable."""
    return lifecycle.request(action)
