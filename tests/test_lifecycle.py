"""Stop and Restart from the dashboard.

The server is never stopped from inside a request: the request only asks,
and run.py's own shutdown does the work after the reply has gone out. A
restart re-launches the same checkout with --no-browser and a --wait so the
new process can take over the lock and port the old one is releasing.
"""
import socket
import sys

import pytest
from fastapi.testclient import TestClient

import run
from backend.src.api.server import create_app
from backend.src.utils import lifecycle

H = {"X-Crypto-Trader": "1"}


@pytest.fixture(autouse=True)
def _clean():
    lifecycle.reset()
    yield
    lifecycle.reset()


def _c():
    return TestClient(create_app(), base_url="http://127.0.0.1:8890")


def test_nothing_happens_without_run_py_installing_a_handler():
    with pytest.raises(lifecycle.NotAvailable):
        lifecycle.request("stop")
    assert lifecycle.requested() is None


def test_request_records_the_action_and_calls_the_handler():
    calls = []
    lifecycle.install(lambda: calls.append(1), delay_s=0)
    lifecycle.request("restart")
    assert lifecycle.requested() == "restart"
    assert calls == [1]


def test_unknown_action_is_refused():
    lifecycle.install(lambda: None, delay_s=0)
    with pytest.raises(ValueError):
        lifecycle.request("reboot")
    assert lifecycle.requested() is None


def test_restart_argv_keeps_user_flags_and_adds_no_browser_and_wait():
    argv = lifecycle.restart_argv("/x/run.py", ["--wait", "3", "--no-browser"])
    assert argv[0] == sys.executable and argv[1] == "/x/run.py"
    assert argv.count("--no-browser") == 1
    assert argv[argv.index("--wait") + 1] == str(lifecycle.RESTART_WAIT_S)
    assert argv.count("--wait") == 1


def test_api_stop_and_restart_need_run_py(fake_exchange):
    assert _c().post("/api/system/restart", headers=H).status_code == 409


def test_api_restart_asks_run_py_to_exit(fake_exchange):
    calls = []
    lifecycle.install(lambda: calls.append(1), delay_s=0)
    r = _c().post("/api/system/restart", headers=H)
    assert r.status_code == 200 and r.json()["action"] == "restart"
    assert calls == [1] and lifecycle.requested() == "restart"


def test_api_stop_refuses_a_request_without_the_csrf_header(fake_exchange):
    calls = []
    lifecycle.install(lambda: calls.append(1), delay_s=0)
    assert _c().post("/api/system/stop").status_code == 403
    assert calls == [] and lifecycle.requested() is None


def test_relaunch_execs_on_posix_and_spawns_on_windows():
    lifecycle.install(lambda: None, delay_s=0)
    lifecycle.request("restart")
    execs, spawns = [], []
    run.relaunch_if_requested([], platform="darwin", execv=lambda p, a: execs.append(a),
                              popen=spawns.append)
    assert len(execs) == 1 and spawns == [] and "--no-browser" in execs[0]
    run.relaunch_if_requested([], platform="win32", execv=lambda p, a: execs.append(a),
                              popen=spawns.append)
    assert len(spawns) == 1 and len(execs) == 1


def test_stop_does_not_relaunch():
    lifecycle.install(lambda: None, delay_s=0)
    lifecycle.request("stop")
    seen = []
    run.relaunch_if_requested([], platform="darwin", execv=lambda p, a: seen.append(a),
                              popen=seen.append)
    assert seen == []


def test_wait_for_port_gives_up_when_the_port_stays_taken():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        port = s.getsockname()[1]
        assert run.wait_for_port("127.0.0.1", port, timeout=0.2) is False
    assert run.wait_for_port("127.0.0.1", port, timeout=2) is True
