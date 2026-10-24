"""A second Crypto Trader on the same data folder is refused, by the kernel's lock."""
import subprocess
import sys
from pathlib import Path

from backend.src.utils import single_instance

ROOT = Path(__file__).resolve().parents[1]


def test_second_process_is_refused_while_the_first_holds_the_lock(tmp_path, monkeypatch):
    from backend.src import config
    monkeypatch.setattr(config, "USER_DATA_DIR", tmp_path)
    single_instance.acquire()
    try:
        code = (
            "import sys; sys.path.insert(0, %r)\n"
            "from backend.src import config; from pathlib import Path\n"
            "config.USER_DATA_DIR = Path(%r)\n"
            "from backend.src.utils import single_instance as s\n"
            "try:\n    s.acquire()\n    print('ACQUIRED')\n"
            "except s.AlreadyRunning as e:\n    print('REFUSED', e)\n"
        ) % (str(ROOT), str(tmp_path))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             env={"CRYPTO_TRADER_DATA_DIR": str(tmp_path), "PATH": ""}).stdout
        assert out.startswith("REFUSED") and "Crypto Trader is already running" in out
        assert single_instance.holder()["pid"]
    finally:
        single_instance.release()
    assert single_instance.holder() is None
