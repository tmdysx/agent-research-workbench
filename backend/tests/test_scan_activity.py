"""扫描火苗来自真正文件读取；不靠改动通知收尾。"""
import asyncio
import threading

import pytest
from fastapi.testclient import TestClient
import main
import scanmap
import store


class RecordingHub(main.Hub):
    def __init__(self):
        super().__init__()
        self.events = []

    async def broadcast(self, message):
        self.events.append(message)


def test_short_unchanged_read_reports_begin_and_end(proj):
    hub = RecordingHub()
    def walk(areas):
        assert scanmap.state(proj)["busy"] == ["笔记"]
        return {a: {} for a in areas}
    assert asyncio.run(main._scan_walk(proj, hub, walk, {"笔记"})) == {"笔记": {}}
    assert [m["active"] for m in hub.events] == [True, False]
    assert [m["areas"] for m in hub.events] == [["笔记"], []]
    assert all(m["type"] == "scanning" and m["project"] == str(proj.root) for m in hub.events)
    assert scanmap.state(proj)["busy"] == []


def test_read_failure_stops_animation_and_preserves_error(proj):
    hub = RecordingHub()
    def walk(_):
        raise OSError("actual read failure")
    with pytest.raises(OSError, match="actual read failure"):
        asyncio.run(main._scan_walk(proj, hub, walk, {"核心"}))
    assert [m["active"] for m in hub.events] == [True, False]
    assert scanmap.state(proj)["busy"] == []


def test_cancellation_waits_for_real_thread_before_stopping(proj):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    hub = RecordingHub()
    def walk(areas):
        entered.set()
        assert release.wait(3)
        finished.set()
        return {a: {} for a in areas}
    async def run():
        task = asyncio.create_task(main._scan_walk(proj, hub, walk, {"笔记"}))
        assert await asyncio.to_thread(entered.wait, 2)
        task.cancel()
        await asyncio.sleep(0)
        assert scanmap.state(proj)["busy"] == ["笔记"]
        assert [m["active"] for m in hub.events] == [True]
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert finished.is_set()
        assert [m["active"] for m in hub.events] == [True, False]
    try:
        asyncio.run(run())
    finally:
        release.set()
    assert scanmap.state(proj)["busy"] == []


def test_scan_query_reports_only_its_project_and_does_not_start_work(proj):
    before = dict(scanmap.state(proj))
    # 不进入启动生命周期：单个只读请求不得启动项目 watcher。
    client = TestClient(main.create_app(proj, tasks=False, global_keys=False))
    value = client.get("/api/scan").json()
    assert value["project"] == str(proj.root)
    assert value["busy"] == []
    assert value["on"] is False
    assert scanmap.state(proj) == before


def test_initial_watch_also_reports_balanced_real_reads(proj):
    hub = RecordingHub()
    conn = store.connect(proj.db_path)
    store.migrate(conn)
    conn.close()
    async def run():
        task = asyncio.create_task(main.watch(proj, hub, interval=0.02, realtime=False))
        try:
            for _ in range(300):
                if any(m["type"] == "scanning" and not m["active"] for m in hub.events):
                    break
                await asyncio.sleep(0.01)
            else:
                raise AssertionError("Initial file read did not complete")
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    asyncio.run(run())
    events = [m for m in hub.events if m["type"] == "scanning"]
    assert events and [m["active"] for m in events] == [True, False]
    assert scanmap.state(proj)["busy"] == []
