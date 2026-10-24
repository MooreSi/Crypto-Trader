"""One app per data directory.

Ported from FOREX Trader, where it stops two checkouts that share one data
directory from trading one account twice. Here the data directory is this
app's own (`CryptoTrader`), so the lock never meets FOREX Trader's -- the two
apps run side by side and each refuses only a second copy of itself.

What it must not allow is two Crypto Traders on one data directory: two
processes managing the same Hyperliquid positions would each try to move the
same stop.

**This is an OS advisory lock, not a pid file.** The kernel releases it when
the holding process dies, however it dies, so there is no staleness rule to
get wrong and no way for a crash or a `kill -9` to leave an install that will
not start. The pid and checkout path written into the file are for the error
message and the Stop scripts only.

The file's byte 0 holds that metadata and is never locked, so a rival can
read who is holding it. The lock itself is taken on a byte far past the end
of the file (`_LOCK_OFFSET`), because Windows file locking is mandatory --
locking byte 0 there would make the metadata unreadable by the one process
that needs it.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

# Well past any metadata this file will ever hold. The byte does not need to
# exist: both APIs lock a range, not content.
_LOCK_OFFSET = 1 << 30

_LOCK_NAME = "crypto_trader.lock"

_fd: Optional[int] = None


class AlreadyRunning(RuntimeError):
    """Raised when another process already holds the lock."""

    def __init__(self, pid, root, since) -> None:
        self.pid = pid
        self.root = root
        self.since = since
        where = f" from {root}" if root else ""
        started = ""
        if since:
            started = f", started {time.strftime('%H:%M:%S', time.localtime(since))}"
        super().__init__(
            f"Crypto Trader is already running (pid {pid if pid is not None else 'unknown'}"
            f"{where}{started}). Only one instance may use this data directory: "
            f"they would share the same database, settings and positions."
        )


def lock_path() -> Path:
    """Where the lock lives: the shared data directory, never the checkout.

    Resolved per call, and through the config module's attribute rather than a
    captured value, so `CRYPTO_TRADER_DATA_DIR` still separates two installs
    that are meant to run side by side.
    """
    import backend.src.config as cfg
    return Path(cfg.USER_DATA_DIR) / _LOCK_NAME


def _open(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    return os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)


def _try_lock(fd: int) -> bool:
    """Take the lock without blocking. False if someone else holds it."""
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _read_metadata(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # A first run, a truncated write, or a file from a version that wrote
        # something else. The lock is what matters; the metadata is a courtesy.
        return {}


def _write_metadata(fd: int) -> None:
    from backend.src.utils.os_utils import repo_root
    try:
        from backend.src.utils.version_history import __version__ as version
    except Exception:
        version = ""
    blob = json.dumps({
        "pid": os.getpid(),
        "root": str(repo_root()),
        "version": version,
        "since": time.time(),
    }).encode("utf-8")
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, blob)
    os.ftruncate(fd, len(blob))


def acquire(timeout: float = 0.0) -> None:
    """Claim the lock, or raise `AlreadyRunning`.

    Calling twice in one process is a no-op rather than a deadlock, so
    `main()` is safe to re-enter.

    `timeout` exists for a restart, which is two instances overlapping on
    purpose: the replacement starts and waits for its parent to exit.
    """
    global _fd
    if _fd is not None:
        return

    path = lock_path()
    fd = _open(path)
    deadline = time.time() + max(timeout, 0.0)
    while True:
        if _try_lock(fd):
            _fd = fd
            _write_metadata(fd)
            return
        if time.time() >= deadline:
            break
        time.sleep(0.25)

    os.close(fd)
    meta = _read_metadata(path)
    raise AlreadyRunning(meta.get("pid"), meta.get("root"), meta.get("since"))


def release() -> None:
    """Drop the lock. The file stays so `holder()` can still be read."""
    global _fd
    if _fd is None:
        return
    fd, _fd = _fd, None
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        os.close(fd)


def holder() -> Optional[dict]:
    """Who holds the lock right now, or None if nobody does.

    Probes by trying to take it, so the answer comes from the kernel rather
    than from the file's contents -- a leftover file from a clean exit is not
    a held lock.
    """
    path = lock_path()
    if not path.exists():
        return None
    fd = _open(path)
    try:
        if _try_lock(fd):
            return None
    finally:
        os.close(fd)
    return _read_metadata(path) or {}
