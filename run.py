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
import socket
import sys
import threading
import webbrowser

from backend.src import config
from backend.src.utils import single_instance
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {__version__}")
    parser.add_argument("--no-browser", action="store_true", help="do not open the dashboard")
    parser.add_argument("--wait", type=float, default=0.0,
                        help="seconds to wait for a previous instance to exit")
    args = parser.parse_args(argv)

    config.load()
    try:
        single_instance.acquire(timeout=args.wait)
    except single_instance.AlreadyRunning as exc:
        print(f"\n  {exc}\n")
        return 2

    setup_logging()
    host = "127.0.0.1"
    port = int(config.get("dashboard_port", config.DEFAULT_DASHBOARD_PORT))
    if not port_free(host, port):
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
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    finally:
        single_instance.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
