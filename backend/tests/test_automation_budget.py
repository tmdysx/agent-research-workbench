"""配置更新与明确恢复分开：活员工的消耗预算不可被反复配置清零。"""
import json
import os
import subprocess
import sys

import anyio
import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

import agents
import autolaunch
import automation_mcp
import store
import workorders
from conftest import BACKEND


@pytest.fixture
def conn(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    yield c
    c.close()


def employee(conn, proj, name, status, **fields):
    a = agents.create(conn, proj, name, program="Codex", auto=fields.pop("auto", True), **fields)
    autolaunch.write_runner_state(proj, a["code"], status, rounds=4, cycles=4,
        failure_counts={"execute:S1-8:S2-45": 1}, blocked=["review_plan:施-1"], last_result="先前真实结果")
    return a


def raw_state(proj, a):
    return (proj.root / "自动化" / "运行状态" / f"{a['code']}.json").read_bytes()


def test_restoring_only_resets_terminal_employees_without_alive_windows(proj, conn, monkeypatch):
    running = employee(conn, proj, "running", "running")
    waiting = employee(conn, proj, "waiting", "waiting")
    old_window = employee(conn, proj, "old-name", "failed")
    limited = employee(conn, proj, "limited", "limit")
    stopped = employee(conn, proj, "stopped", "stopped")
    paused = employee(conn, proj, "paused", "stopped", paused=True)
    manual = employee(conn, proj, "manual", "failed", auto=False)
    unchanged = [running, waiting, old_window, paused, manual]
    before = {a["code"]: raw_state(proj, a) for a in unchanged}
    monkeypatch.setattr(autolaunch, "windows", lambda p, **kwargs: [{"title": f"{old_window['code']} renamed", "alive": True}])
    assert automation_mcp.resume_inactive_runners(proj, restoring=True, by="人", reason="明确恢复") == [limited["code"], stopped["code"]]
    assert all(raw_state(proj, a) == before[a["code"]] for a in unchanged)
    for a in (limited, stopped):
        state = autolaunch.runner_state(proj, a["code"])
        assert state["status"] == "ready" and state["rounds"] == state["cycles"] == 0
        assert state["blocked"] == [] and state["failure_counts"] == {} and state["last_result"] == "先前真实结果"


def test_window_query_failure_never_resets_a_live_runner_pid(proj, conn, monkeypatch):
    a = employee(conn, proj, "worker", "stopped")
    autolaunch.write_runner_state(proj, a["code"], pid=os.getpid())
    before = raw_state(proj, a)
    monkeypatch.setattr(autolaunch, "windows", lambda p, **kwargs: [])
    assert automation_mcp._runner_pid_alive(os.getpid())
    assert automation_mcp.resume_inactive_runners(proj, restoring=True, by="人", reason="明确恢复") == []
    assert raw_state(proj, a) == before


@pytest.mark.parametrize("restore", [False, True])
def test_web_on_and_max_changes_keep_active_budget(proj, conn, monkeypatch, restore):
    from main import create_app
    live = employee(conn, proj, "live", "running")
    waiting = employee(conn, proj, "waiting", "waiting")
    limited = employee(conn, proj, "limited", "limit")
    before = {a["code"]: raw_state(proj, a) for a in (live, waiting, limited)}
    autolaunch.set_settings(conn, on=not restore, max_=3)
    if restore:
        store._set_meta(conn, workorders.PAUSE, "人叫停了")
    monkeypatch.setattr(autolaunch, "tick", lambda *args, **kwargs: [])
    monkeypatch.setattr(autolaunch, "windows", lambda p, **kwargs: [{"title": f"{live['code']} live", "alive": True}, {"title": f"{waiting['code']} waiting", "alive": True}])
    with TestClient(create_app(proj, tasks=False)) as client:
        response = client.put("/api/auto/launch", json={"on": True, "max": 5})
        assert response.status_code == 200, response.text
        assert response.json()["max"] == 5
        assert raw_state(proj, live) == before[live["code"]] and raw_state(proj, waiting) == before[waiting["code"]]
        if restore:
            assert autolaunch.runner_state(proj, limited["code"])["rounds"] == 0
        else:
            assert raw_state(proj, limited) == before[limited["code"]]
        now = raw_state(proj, live)
        response = client.put("/api/auto/launch", json={"max": 2})
        assert response.status_code == 200 and raw_state(proj, live) == now


def test_web_explicit_resume_recovers_terminal_but_keeps_waiting(proj, conn, monkeypatch):
    from main import create_app
    waiting = employee(conn, proj, "waiting", "waiting")
    limited = employee(conn, proj, "limited", "limit")
    autolaunch.set_settings(conn, on=True)
    before = raw_state(proj, waiting)
    monkeypatch.setattr(autolaunch, "tick", lambda *args, **kwargs: [])
    monkeypatch.setattr(autolaunch, "windows", lambda p, **kwargs: [])
    with TestClient(create_app(proj, tasks=False)) as client:
        response = client.put("/api/auto/launch", json={"on": True, "resume": True})
        assert response.status_code == 200, response.text
    assert autolaunch.runner_state(proj, limited["code"])["rounds"] == 0
    assert raw_state(proj, waiting) == before


async def mcp_configure(proj, auth, params):
    cfg = StdioServerParameters(command=sys.executable, args=[str(BACKEND / "mcp_server.py"), "--project", str(proj.root),
                            "--agent", "boss", "--configuration-authorization", auth])
    async with stdio_client(cfg) as (read, write):
        async with ClientSession(read, write, client_info=Implementation(name="boss", version="test")) as session:
            await session.initialize()
            result = await session.call_tool("configure_automation", params | {"authorization_path": auth})
            text = "\n".join(x.text for x in result.content if x.type == "text")
            assert not result.isError, text
            return json.loads(text)


def test_real_mcp_settings_update_preserves_budget_and_explicit_resume_is_selective(proj, conn):
    agents.create(conn, proj, "boss", program="Codex", auto=False)
    live = employee(conn, proj, "live", "running")
    waiting = employee(conn, proj, "waiting", "waiting")
    limited = employee(conn, proj, "limited", "limit")
    blocked = employee(conn, proj, "blocked", "idle")
    f = proj.root / "治理" / "计划" / "S0 总体" / "P1 · 2026-10-03 · 配置授权.md"
    f.parent.mkdir(parents=True)
    f.write_text("> 授权：作者本次明确批准自动化配置\n> 授权操作者：boss\n> 授权对象：G2、G3、G4\n", encoding="utf-8")
    auth = f.relative_to(proj.root).as_posix()
    before = {a["code"]: raw_state(proj, a) for a in (live, waiting, limited, blocked)}
    autolaunch.set_settings(conn, on=True)
    out = anyio.run(mcp_configure, proj, auth, {"on": True, "max_windows": 3, "round_limit": 20})
    assert out["on"] and all(raw_state(proj, a) == before[a["code"]] for a in (live, waiting, limited, blocked))
    anyio.run(mcp_configure, proj, auth, {"on": True, "max_windows": 2, "round_limit": 20, "resume": True})
    assert raw_state(proj, live) == before[live["code"]] and raw_state(proj, waiting) == before[waiting["code"]]
    assert autolaunch.runner_state(proj, limited["code"])["rounds"] == 0
    assert autolaunch.runner_state(proj, blocked["code"])["blocked"] == []


@pytest.mark.parametrize("explicit_resume", [False, True])
def test_idle_blocked_requires_explicit_resume_and_preserves_evidence(proj, conn, monkeypatch, explicit_resume):
    blocked = employee(conn, proj, "blocked", "idle")
    idle = employee(conn, proj, "idle", "idle")
    autolaunch.write_runner_state(proj, idle["code"], blocked=[])
    before = {a["code"]: raw_state(proj, a) for a in (blocked, idle)}
    monkeypatch.setattr(autolaunch, "windows", lambda p, **kwargs: [])
    assert automation_mcp.resume_inactive_runners(proj, restoring=True, explicit_resume=explicit_resume,
        by="人", reason="明确恢复") == ([blocked["code"]] if explicit_resume else [])
    assert raw_state(proj, idle) == before[idle["code"]]
    if explicit_resume:
        state = autolaunch.runner_state(proj, blocked["code"])
        assert state["status"] == "ready" and state["rounds"] == state["cycles"] == 0
        assert state["blocked"] == [] and state["failure_counts"] == {}
        assert state["last_result"] == "先前真实结果"
        assert state["history"][-1]["from"] == "idle" and state["history"][-1]["by"] == "人"
    else:
        assert raw_state(proj, blocked) == before[blocked["code"]]


@pytest.mark.parametrize("guard", ["live_pid", "live_window", "unknown_windows"])
def test_idle_blocked_resume_keeps_budget_without_confirmed_exit(proj, conn, monkeypatch, guard):
    a = employee(conn, proj, "worker", "idle")
    if guard == "live_pid":
        autolaunch.write_runner_state(proj, a["code"], pid=os.getpid())
    before = raw_state(proj, a)
    def windows(p, **kwargs):
        assert kwargs["require_known"]
        if guard == "unknown_windows":
            raise OSError("终端服务断连")
        return [{"title": f"{a['code']} renamed", "alive": True}] if guard == "live_window" else []
    monkeypatch.setattr(autolaunch, "windows", windows)
    assert automation_mcp.resume_inactive_runners(proj, restoring=True, explicit_resume=True,
        by="人", reason="明确恢复") == []
    assert raw_state(proj, a) == before


def test_idle_blocked_with_exited_pid_and_dead_window_recovers(proj, conn, monkeypatch):
    a = employee(conn, proj, "worker", "idle")
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    assert process.wait(timeout=10) == 0
    assert not automation_mcp._runner_pid_alive(process.pid)
    autolaunch.write_runner_state(proj, a["code"], pid=process.pid)
    monkeypatch.setattr(autolaunch, "windows", lambda p, **kwargs: [{"title": f"{a['code']} worker", "alive": False}])
    assert automation_mcp.resume_inactive_runners(proj, restoring=True, explicit_resume=True,
        by="人", reason="明确恢复") == [a["code"]]
    state = autolaunch.runner_state(proj, a["code"])
    assert state["status"] == "ready" and state["rounds"] == 0 and state["blocked"] == []


def test_known_window_query_distinguishes_never_started_from_disconnected(proj, monkeypatch):
    def unavailable(*args):
        raise OSError("服务不可达")
    monkeypatch.setattr(autolaunch, "_call", unavailable)
    assert autolaunch.windows(proj, require_known=True) == []
    f = autolaunch.plugins._state_file(proj, autolaunch.TERM)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("{}", encoding="utf-8")
    assert autolaunch.windows(proj) == []  # 普通读取兼容原接口。
    with pytest.raises(OSError, match="服务不可达"):
        autolaunch.windows(proj, require_known=True)
    monkeypatch.setattr(autolaunch, "_call", lambda *args: {"items": [{"title": "G1 worker"}]})
    with pytest.raises(RuntimeError, match="状态不完整"):
        autolaunch.windows(proj, require_known=True)
    monkeypatch.setattr(autolaunch, "_call", lambda *args: {"items": [{"title": "G1 worker", "alive": False}]})
    assert autolaunch.windows(proj, require_known=True) == [{"title": "G1 worker", "alive": False}]


def test_web_idle_blocked_survives_toggle_but_explicit_resume_clears(proj, conn, monkeypatch):
    from main import create_app
    blocked = employee(conn, proj, "blocked", "idle")
    before = raw_state(proj, blocked)
    autolaunch.set_settings(conn, on=False)
    monkeypatch.setattr(autolaunch, "tick", lambda *args, **kwargs: [])
    monkeypatch.setattr(autolaunch, "windows", lambda p, **kwargs: [])
    with TestClient(create_app(proj, tasks=False)) as client:
        assert client.put("/api/auto/launch", json={"on": True}).status_code == 200
        assert raw_state(proj, blocked) == before
        assert client.put("/api/auto/launch", json={"max": 2}).status_code == 200
        assert raw_state(proj, blocked) == before
        response = client.put("/api/auto/launch", json={"on": True, "resume": True})
        assert response.status_code == 200, response.text
    state = autolaunch.runner_state(proj, blocked["code"])
    assert state["status"] == "ready" and state["blocked"] == [] and state["rounds"] == 0


def test_model_connection_cannot_clear_idle_blocked_budget(proj, conn):
    from test_automation_mcp import call
    a = employee(conn, proj, "worker", "idle")
    before = raw_state(proj, a)
    results = anyio.run(call, proj, "worker", [
        ("report_employee_runtime", {"state": {"status": "ready", "blocked": [], "rounds": 0}}),
        ("configure_automation", {"on": True, "max_windows": 3, "resume": True,
            "authorization_path": "治理/计划/S0 总体/P1 · 伪造授权.md"}),
    ])
    assert all(error for error, text in results)
    assert "只由外层运行器" in results[0][1] and "没有配置授权" in results[1][1]
    assert raw_state(proj, a) == before
