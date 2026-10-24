"""Shutdown waits for a pass that is already running.

Cancelling a task that awaits `asyncio.to_thread` stops the await, not the
thread. Before this, Stop / Ctrl+C closed the databases while an engine or
positions pass was still working in its thread: the pass then failed with
"database is closed", and one caught between placing an order and recording
it would have left an unrecorded position.
"""
import asyncio
import threading

from backend.src.runtime import TradingRuntime


def test_stop_returns_only_after_the_running_pass_has_finished():
    rt = TradingRuntime()
    started, release = threading.Event(), threading.Event()
    finished: list[int] = []

    def slow_pass():
        started.set()
        release.wait(5)
        finished.append(1)

    async def main():
        rt._tasks = [asyncio.get_running_loop().create_task(rt._every(60, slow_pass))]
        await asyncio.to_thread(started.wait, 5)
        threading.Timer(0.3, release.set).start()
        await rt.stop()
        return list(finished)

    assert asyncio.run(main()) == [1]


def test_stop_with_nothing_running_returns_at_once():
    rt = TradingRuntime()

    async def main():
        rt._tasks = [asyncio.get_running_loop().create_task(asyncio.sleep(60))]
        await asyncio.wait_for(rt.stop(), timeout=1)

    asyncio.run(main())
