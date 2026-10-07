"""外层轮转的停等、预算、失败跳过和真进程停止；不调用真实模型。"""
import json
import sys
from types import SimpleNamespace

import anyio
import pytest

import agents
import employee_runner as er
import store


class Session:
    def __init__(self, actions):
        self.actions = list(actions)
        self.calls, self.state = [], {}

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "next_action":
            value = self.actions.pop(0) if self.actions else {"action": "idle", "reason": "没有可执行动作", "limits": {"rounds": 10}}
        elif name == "report_employee_runtime":
            self.state = json.loads(json.dumps(arguments["state"]))
            value = self.state | {"code": "G1", "name": "worker", "updated": "服务器时间", "history": []}
        else:
            value = "已经记录"
        text = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], isError=False)


def job(kind="execute", goal="S1-8", sub="S2-45", **extra):
    return {"action": kind, "task": {"goal": goal, "sub": sub},
            "holding": [{"goal": goal, "sub": sub}], "limits": {"rounds": 10, "failures": 2}, **extra}


def run_drive(session, proj, execute, state=None, stop=None, idle=0.025):
    async def run():
        return await er.drive(session, proj, "worker", poll_seconds=0.001, idle_seconds=idle,
                              execute=execute, state_loader=lambda *args: state or {},
                              stop_check=stop or (lambda *args: ""))
    return anyio.run(run)


def test_idle_exit_keeps_saved_unfinished_work_and_releases_core(proj):
    s = Session([job('idle', holding=[{'goal': 'S1-8', 'sub': 'S2-45'}, {'goal': '核心', 'sub': ''}])])
    async def forbidden(*args):
        pytest.fail('空闲时不能启动模型')
    state = run_drive(s, proj, forbidden)
    releases = [a['goal'] for n, a in s.calls if n == 'release_task']
    assert state['status'] == 'idle' and 'S1-8' not in releases and '核心' in releases
    assert any('认领已保留' in a['text'] for n, a in s.calls if n == 'write_handover')


def test_waiting_does_not_start_model_and_two_tasks_continue(proj):
    s = Session([{"action": "waiting", "reason": "计划待审"}, job(sub="S2-45"), job(sub="S2-46"), {"action": "idle"}])
    actual = []

    async def execute(p, name, action):
        actual.append(er.action_key(action))
        return er.Outcome(0, "真实检查由这张交付单记录")

    result = run_drive(s, proj, execute)
    assert actual == ["execute:S1-8:S2-45", "execute:S1-8:S2-46"]
    assert result["rounds"] == 2 and result["status"] == "idle"
    states = [v["state"] for n, v in s.calls if n == "report_employee_runtime"]
    assert any(st["status"] == "waiting" and st["rounds"] == 0 for st in states)
    assert not any(set(st) - er.STATE_FIELDS for st in states)
    assert [n for n, _ in s.calls].count("write_handover") == 1
    assert not (proj.root / "自动化").exists()  # runner所有写入均经过模拟的MCP。


def test_two_failed_attempts_are_skipped_and_other_work_runs(proj):
    a, b = job(sub="S2-45"), job(sub="S2-46")
    s = Session([a, a, a, b, {"action": "idle"}])
    attempts = []

    async def execute(p, name, action):
        attempts.append(er.action_key(action))
        # A即使CLI退出0、MCP状态未进展，也算失败，不能假报完成。
        return er.Outcome(0, "这次没有实际提交")

    result = run_drive(s, proj, execute)
    assert attempts == ["execute:S1-8:S2-45", "execute:S1-8:S2-45", "execute:S1-8:S2-46"]
    assert result["blocked"] == ["execute:S1-8:S2-45"] and result["failure_counts"][result["blocked"][0]] == 2
    asks = [args for name, args in s.calls if name == "ask_human"]
    assert len(asks) == 1 and "连续 2 次" in asks[0]["question"] and "agent" not in asks[0]
    assert any(n == "release_task" and v["goal"] == "S1-8" and v["sub"] == "S2-45" for n, v in s.calls)


def test_restart_keeps_budget_and_stop_releases_held_task_and_core(proj):
    s = Session([job(limits={"rounds": 2})])

    async def forbidden(*args):
        pytest.fail("到达轮次上限后不能启动模型")

    result = run_drive(s, proj, forbidden, state={"rounds": 2, "status": "running"})
    assert result["status"] == "limit" and result["rounds"] == 2
    assert any(n == "release_task" and a["goal"] == "核心" for n, a in s.calls)
    assert any(n == "release_task" and a["sub"] == "S2-45" for n, a in s.calls)
    s = Session([])
    result = run_drive(s, proj, forbidden, stop=lambda *args: "人叫停了")
    assert result["status"] == "stopped" and "人叫停" in result["reason"]
    assert any(n == "write_handover" and "人叫停了" in a["text"] and "本次已放手" in a["text"] for n, a in s.calls)
    s = Session([])
    result = run_drive(s, proj, forbidden, state={"rounds": 2, "status": "failed", "current": "S1-8 S2-45", "reason": "上次启动失败"})
    assert result["status"] == "failed" and any(n == "write_handover" for n, _ in s.calls)


def test_runtime_payload_cannot_grow_recursively_or_rewrite_server_metadata(proj):
    embedded = {"status": "waiting", "current": {"runtime": {"current": {"runtime": {"huge": "旧数据"}}}}}
    s = Session([job(runtime=embedded), {"action": "idle"}])

    async def execute(*args):
        return er.Outcome(0)

    result = run_drive(s, proj, execute, state={"updated": "旧时间", "code": "G99", "history": ["用户恢复"]})
    assert all("runtime" not in x["state"].get("current", {}) for n, x in s.calls if n == "report_employee_runtime")
    assert all(not (set(x["state"]) & {"updated", "code", "history"}) for n, x in s.calls if n == "report_employee_runtime")
    assert result["rounds"] == 1


def test_action_prompt_has_one_action_mcp_rules_and_no_self_review(proj):
    text = er.action_prompt(proj, "worker", {"action": "review_plan", "construction_plan": {"code": "施-2"}})
    assert "不能审自己的计划" in text and "不自行领下一件" in text and "MCP已经固定绑定" in text
    text = er.action_prompt(proj, "worker", job(construction_plan={"files": ["backend/a.py"]}))
    assert "claim_task('核心')" in text and "save_checkpoint" in text and "deliver" in text
    assert er.action_key({"action": "review_plan", "construction_plan": {"code": "施-2"}}) == "review_plan:施-2"


def test_local_stop_is_read_only_and_corrupt_state_is_not_fresh_budget(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    a = agents.create(c, proj, "worker", program="Codex", auto=True)
    assert not er.local_stop_reason(proj, "worker")
    with store.tx(c):
        store._set_meta(c, "auto_paused", "人按了暂停")
    assert er.local_stop_reason(proj, "worker") == "人按了暂停"
    c.close()
    state = proj.root / "自动化" / "运行状态" / f"{a['code']}.json"
    state.parent.mkdir(parents=True)
    state.write_text("损坏", encoding="utf-8")
    assert er.load_state(proj, "worker")["status"] == "failed"


def test_duplicate_runner_is_rejected(proj):
    with er.singleton(proj, "worker"):
        with pytest.raises(RuntimeError, match="已经在运行"):
            with er.singleton(proj, "worker"):
                pass


def test_running_process_is_really_stopped_and_output_streamed(proj):
    checks = []

    def stop(*args):
        checks.append(1)
        return "员工已暂停" if len(checks) >= 3 else ""

    async def run():
        return await er.run_codex(proj, "worker", job(), poll_seconds=0.05, stop_check=stop,
                                 command=[sys.executable, "-u", "-c", "import time; print('started', flush=True); time.sleep(30)"])

    result = anyio.run(run)
    assert result.stopped == "员工已暂停" and result.returncode != 0 and "started" in result.output


def test_real_mcp_binds_employee_and_records_idle_without_starting_a_model(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    a = agents.create(c, proj, "worker", program="Codex", auto=True, plan_required=True)
    c.close()

    async def forbidden(*args):
        pytest.fail("没有任务的真实MCP不能启动模型")

    async def run():
        params = er.StdioServerParameters(command=sys.executable, args=[str(er.CODE_DIR / "backend" / "mcp_server.py"),
                                         "--project", str(proj.root), "--agent", "worker", '--runner-control'])
        async with er.stdio_client(params) as (read, write):
            async with er.ClientSession(read, write, client_info=er.Implementation(name="worker", version="test")) as s:
                await s.initialize()
                return await er.drive(s, proj, "worker", idle_seconds=0, execute=forbidden)

    result = anyio.run(run)
    assert result["status"] == "idle" and result["rounds"] == 0
    data = json.loads((proj.root / "自动化" / "运行状态" / f"{a['code']}.json").read_text(encoding="utf-8"))
    assert data["name"] == "worker" and data["code"] == a["code"] and data["rounds"] == 0
    h = list((proj.root / "自动化" / "交接").glob("H*.md"))
    assert len(h) == 1 and "worker" in h[0].name and "没有启动模型" in h[0].read_text(encoding="utf-8")


def test_long_model_round_does_not_consume_the_following_wait(proj, monkeypatch):
    clock = SimpleNamespace(now=0)
    monkeypatch.setattr(er, "time", SimpleNamespace(monotonic=lambda: clock.now, time_ns=lambda: 123))
    waiting = job("waiting", reason="计划待审")

    class WaitingSession(Session):
        def __init__(self):
            super().__init__([job("submit_plan")] + [waiting] * 20)
            self.reads = 0

        async def call_tool(self, name, arguments):
            if name == "next_action" and self.reads:
                clock.now += 5
            if name == "next_action":
                self.reads += 1
            return await super().call_tool(name, arguments)

    s = WaitingSession()

    async def execute(*args):
        clock.now += 100  # 模拟长模型轮次，不等真的100秒。
        return er.Outcome(0, "提交了施工计划")

    result = run_drive(s, proj, execute, idle=20)
    assert result["status"] == "waiting" and result["rounds"] == 1
    assert clock.now == 120 and s.reads == 5  # 完整等待20秒，模型100秒不占等待预算。


def test_waiting_exit_keeps_construction_claim_but_releases_coordination_locks(proj):
    held = [{"goal": "S1-8", "sub": "S2-45"}, {"goal": "核心", "sub": ""},
            {"goal": "施工审核", "sub": "施-7"}, {"goal": "审核", "sub": "D2"},
            {"goal": "验收", "sub": "J3"}]
    s = Session([job("waiting", holding=held, reason="计划待审")])

    async def forbidden(*args):
        pytest.fail("等待审批不能启动模型")

    result = run_drive(s, proj, forbidden, idle=0,
                       state={"rounds": 3, "last_result": "原始输出不要进入交接" * 400})
    releases = {(args["goal"], args["sub"]) for name, args in s.calls if name == "release_task"}
    assert result["status"] == "waiting" and result["rounds"] == 3
    assert releases == {("核心", ""), ("施工审核", "施-7"), ("审核", "D2"), ("验收", "J3")}
    handover = next(args["text"] for name, args in s.calls if name == "write_handover")
    assert "认领已保留" in handover and "等待相应员工" in handover
    assert "原始输出不要进入交接" not in handover and "是否恢复由人决定" not in handover
    assert len(handover) < 1000


def test_pause_before_next_action_releases_the_saved_construction_claim(proj):
    s = Session([])
    saved = {"rounds": 4, "status": "waiting", "current": job("waiting")}

    async def forbidden(*args):
        pytest.fail("暂停时不能启动模型")

    result = run_drive(s, proj, forbidden, state=saved, stop=lambda *args: "人叫停了")
    releases = {(args["goal"], args["sub"]) for name, args in s.calls if name == "release_task"}
    assert result["status"] == "stopped" and result["rounds"] == 4
    assert releases == {("核心", ""), ("S1-8", "S2-45")}
    assert not any(name == "next_action" for name, _ in s.calls)


def test_restart_keeps_an_existing_failure_block_and_does_not_retry_it(proj):
    action = job()
    key = er.action_key(action)
    s = Session([action, {"action": "idle"}])

    async def forbidden(*args):
        pytest.fail("连续失败后的同一件不能因重启而自动重试")

    result = run_drive(s, proj, forbidden, state={"status": "idle", "rounds": 2,
                       "blocked": [key], "failure_counts": {key: 2}})
    assert result["rounds"] == 2 and result["blocked"] == [key]
    assert result["failure_counts"] == {key: 2}
    handover = next(args["text"] for name, args in s.calls if name == "write_handover")
    assert "连续失败事项已留在待判断区" in handover


def test_explicit_empty_holding_does_not_release_a_stale_task(proj):
    s = Session([job("waiting", reason="计划待审"), {"action": "idle", "holding": []}])

    async def forbidden(*args):
        pytest.fail("无活不能启动模型")

    run_drive(s, proj, forbidden, idle=0.006)
    releases = [(args["goal"], args["sub"]) for name, args in s.calls if name == "release_task"]
    assert releases == [("核心", "")]
