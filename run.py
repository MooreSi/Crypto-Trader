#!/usr/bin/env python3
"""Start Crypto Trader: claim the lock, check the port, serve the dashboard.

    .venv/bin/python run.py                # http://127.0.0.1:8890
    .venv/bin/python run.py --no-browser

Runs locally only. There is no VPS mode in this build: the dashboard binds
127.0.0.1 and nothing listens on a public interface.

**Never kills another process.** FOREX Trader's launcher frees its port by
killing whatever holds it. This one refuses to start instead and says who has
the port -- on a machine that also runs FOREX Trader, a kill here could hit
a live trading app.
"""
from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from backend.src import config
from backend.src.utils import lifecycle, single_instance
from backend.src.utils.version_history import APP_NAME, __version__

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def setup_logging() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(str(config.get("log_level", "INFO")).upper())
    fmt = logging.Formatter(LOG_FORMAT)
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    root.handlers = [file_handler, stream]
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def wait_for_port(host: str, port: int, timeout: float) -> bool:
    """True once the port is free. A restart waits here for the old process's port."""
    deadline = time.monotonic() + timeout
    while not port_free(host, port):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.25)
    return True


def relaunch_if_requested(argv: list[str], platform: str = sys.platform,
                          execv=os.execv, popen=subprocess.Popen) -> None:
    """After a dashboard Restart: start this checkout again. POSIX replaces this
    process (same terminal window); Windows has no real exec, so it spawns the
    new process into the same console and this one exits."""
    if lifecycle.requested() != "restart":
        return
    cmd = lifecycle.restart_argv(str(Path(__file__).resolve()), argv)
    logging.getLogger(__name__).info("[Run] restarting: %s", " ".join(cmd[1:]))
    logging.shutdown()
    if platform == "win32":
        popen(cmd)
    else:
        execv(cmd[0], cmd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {__version__}")
    parser.add_argument("--no-browser", action="store_true", help="do not open the dashboard")
    parser.add_argument("--wait", type=float, default=0.0,
                        help="seconds to wait for a previous instance to exit")
    raw_argv = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(raw_argv)

    config.load()
    try:
        single_instance.acquire(timeout=args.wait)
    except single_instance.AlreadyRunning as exc:
        print(f"\n  {exc}\n")
        return 2

    setup_logging()
    host = "127.0.0.1"
    port = int(config.get("dashboard_port", config.DEFAULT_DASHBOARD_PORT))
    if not wait_for_port(host, port, args.wait):
        print(f"\n  Port {port} is in use by another program. {APP_NAME} will not stop it.\n"
              f"  Set dashboard_port in {config.CONFIG_FILE} to a free port and start again.\n")
        single_instance.release()
        return 3

    import uvicorn
    from backend.src.app import app

    url = f"http://{host}:{port}"
    logging.getLogger(__name__).info("%s %s starting on %s (network: %s)", APP_NAME,
                                     __version__, url, config.get("network"))
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning",
                                           timeout_graceful_shutdown=5))
    lifecycle.install(lambda: setattr(server, "should_exit", True))
    try:
        server.run()
    finally:
        single_instance.release()
    relaunch_if_requested(raw_argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
