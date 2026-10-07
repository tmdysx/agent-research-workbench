"""自动接续用假终端与临时项目，验证真实派活动作和持久状态。"""
import json

import pytest

import agents
import autolaunch
import claims
import construction_plans as cp
import dispatch
import store
import workorders
from test_workflow_graph import ready as workflow_ready, enabled


@pytest.fixture
def conn(proj):
    c = store.connect(proj.db_path)
    yield c
    c.close()


class Terminal:
    def __init__(self):
        self.items, self.posts, self.calls = [], [], []
        self.fail = False

    def __call__(self, method, path, body=None):
        self.calls.append((method, path))
        if method == "POST":
            if self.fail:
                raise RuntimeError("网页终端启动失败")
            self.posts.append(body)
            self.items.append({"id": str(len(self.posts)), "title": body["title"], "alive": True})
            return {"id": str(len(self.posts))}
        return {"items": list(self.items)}


def _employee(conn, proj, name="codex", **fields):
    return agents.create(conn, proj, name, "写代码的", program=fields.pop("program", "Codex"), auto=fields.pop("auto", True), **fields)


def _job(action="execute", **fields):
    return {"action": action, "task": {"goal": "S1-8", "sub": "S2-45"}, "reason": "", **fields}


@pytest.fixture
def fake(monkeypatch):
    terminal = Terminal()
    monkeypatch.setattr(agents, "launcher", lambda p, key: {"title": key + " " + agents.get(p, key)["name"], "cmd": "fake-only"})
    return terminal


def test_cold_start_uses_dispatch_and_g1_is_not_special(proj, conn, fake, monkeypatch):
    a = _employee(conn, proj)
    calls = []
    monkeypatch.setattr(dispatch, "next_task", lambda c, p, who: calls.append(who) or _job("submit_plan"))
    assert autolaunch.settings(conn)["max"] == 3
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == []
    autolaunch.set_settings(conn, on=True)
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == ["G1 codex：S1-8 S2-45"]
    assert calls == ["agent:codex"] and fake.posts[0]["title"] == "G1 codex"
    state = autolaunch.runner_state(proj, a["code"])
    assert state["status"] == "running" and state["action"] == "submit_plan"


def test_pause_is_checked_before_terminal_and_dispatch(proj, conn, fake, monkeypatch):
    _employee(conn, proj)
    autolaunch.set_settings(conn, on=True)
    store._set_meta(conn, workorders.PAUSE, "人已叫停")
    monkeypatch.setattr(dispatch, "next_task", lambda *args: pytest.fail("叫停后不领活"))
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == []
    assert fake.calls == []


@pytest.mark.parametrize('gap', ['claim', 'launcher'])
def test_actual_flow_stop_before_start_never_posts_terminal_or_leaves_new_claim(proj, workflow_ready, fake, monkeypatch, gap):
    import workflow_graph as wf
    conn = workflow_ready
    for name in ('reviewer', 'acceptor', 'other'):
        agents.update(conn, proj, name, {'auto': False})
    record = enabled(conn, proj)
    original_claim, original_launcher = claims.claim, agents.launcher
    stopped = False
    def stop():
        nonlocal stopped
        if not stopped:
            stopped = True
            wf.control(conn, proj, record['code'], 'stop', record['revision'])
    def claim(c, goal, sub, *args, **kwargs):
        if goal == 'S1-9' and sub == 'S2-1' and gap == 'claim':
            stop()
        return original_claim(c, goal, sub, *args, **kwargs)
    def launcher(p, key):
        if gap == 'launcher':
            stop()
        return original_launcher(p, key)
    monkeypatch.setattr(claims, 'claim', claim)
    monkeypatch.setattr(agents, 'launcher', launcher)
    autolaunch.set_settings(conn, on=True)
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == []
    assert stopped and fake.posts == []
    assert autolaunch.runner_state(proj, 'worker')['status'] == 'waiting'
    assert claims.of(conn, 'agent:worker') == []


def test_only_explicit_automatic_unpaused_codex_employees_start(proj, conn, fake, monkeypatch):
    _employee(conn, proj, "claude", program="Claude Code", auto=True)
    _employee(conn, proj, "manual", auto=False)
    _employee(conn, proj, "paused", paused=True)
    _employee(conn, proj, "worker", auto=True)
    monkeypatch.setattr(dispatch, "next_task", lambda *args: _job())
    autolaunch.set_settings(conn, on=True)
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == ["G4 worker：S1-8 S2-45"]


def test_alive_code_prevents_duplicate_even_if_title_name_changes(proj, conn, fake, monkeypatch):
    _employee(conn, proj)
    fake.items = [{"title": "G1 old-name", "alive": True}]
    monkeypatch.setattr(dispatch, "next_task", lambda *args: pytest.fail("活窗口不重新派活"))
    autolaunch.set_settings(conn, on=True)
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == []


def test_capacity_and_cooldown_do_not_claim_extra_work(proj, conn, fake, monkeypatch):
    for name in ("one", "two", "three", "four"):
        _employee(conn, proj, name)
    seen = []
    monkeypatch.setattr(dispatch, "next_task", lambda c, p, who: seen.append(who) or _job())
    autolaunch.set_settings(conn, on=True)
    assert len(autolaunch.tick(conn, proj, now=1000, call=fake)) == 3
    assert seen == ["agent:one", "agent:two", "agent:three"]
    fake.items = []
    # 前三个人在冷却；只有第四个人能首次启动。
    assert autolaunch.tick(conn, proj, now=1100, call=fake) == ["G4 four：S1-8 S2-45"]
    fake.items = []
    assert autolaunch.tick(conn, proj, now=1200, call=fake) == []
    assert len(autolaunch.tick(conn, proj, now=1700, call=fake)) == 3


@pytest.mark.parametrize("action", ["waiting", "idle", "stopped"])
def test_waiting_and_no_work_do_not_open_empty_windows(proj, conn, fake, monkeypatch, action):
    a = _employee(conn, proj)
    monkeypatch.setattr(dispatch, "next_task", lambda *args: _job(action, reason="计划待审"))
    autolaunch.set_settings(conn, on=True)
    for now in (1000, 1600, 2200):
        assert autolaunch.tick(conn, proj, now=now, call=fake) == []
    assert fake.posts == [] and autolaunch.runner_state(proj, a["code"])["status"] == action


@pytest.mark.parametrize("blocked", ["stopped", "failed", "limit"])
def test_persistent_stop_and_limits_require_explicit_resume(proj, conn, fake, monkeypatch, blocked):
    a = _employee(conn, proj)
    autolaunch.write_runner_state(proj, a["code"], blocked, rounds=4, blocked=["execute:S1-8:S2-45"], failure_counts={"execute:S1-8:S2-45": 2}, last_result="真实失败记录", stop_requested=True)
    monkeypatch.setattr(dispatch, "next_task", lambda *args: _job())
    autolaunch.set_settings(conn, on=True)
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == []
    assert fake.posts == []
    autolaunch.resume_runner(proj, a["code"], "agent:manager", "人在对话让恢复")
    st = autolaunch.runner_state(proj, a["code"])
    assert st["rounds"] == st["cycles"] == 0 and st["blocked"] == [] and st["failure_counts"] == {}
    assert not st["stop_requested"]
    assert st["last_result"] == "真实失败记录" and st["history"][-1]["by"] == "agent:manager"
    assert autolaunch.tick(conn, proj, now=1000, call=fake)


def test_failed_start_is_recorded_and_does_not_retry_forever(proj, conn, fake, monkeypatch):
    a = _employee(conn, proj)
    monkeypatch.setattr(dispatch, "next_task", lambda *args: _job())
    autolaunch.set_settings(conn, on=True)
    fake.fail = True
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == []
    assert autolaunch.runner_state(proj, a["code"])["status"] == "failed"
    calls = len(fake.calls)
    autolaunch.tick(conn, proj, now=9999, call=fake)
    assert len(fake.calls) == calls + 1  # 只读取终端，不再POST


def test_merging_state_preserves_other_fields_and_survives_no_index(proj, conn):
    a = _employee(conn, proj)
    autolaunch.write_runner_state(proj, a["code"], "running", rounds=2, current="S1-8 S2-45", failure_counts={"x": 1}, last_result="第一轮完成")
    autolaunch.write_runner_state(proj, a["code"], "waiting", reason="等计划审核")
    result = autolaunch.runner_state(proj, a["code"])
    assert result["cycles"] == result["rounds"] == 2 and result["failure_counts"] == {"x": 1}
    assert result["last_result"] == "第一轮完成" and result["current"] == "S1-8 S2-45"
    path = proj.root / "自动化/运行状态/G1.json"
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "waiting"
    assert {"code", "name", "status", "action", "reason", "current", "last_result", "cycles", "updated"} <= result.keys()


def _goals(proj):
    path = proj.root / "治理/目标/S1-8 转得起来.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# S1-8 转得起来\n\n**验证接续。**\n\n规划：定稿 · 2026-10-02 · 作者\n\n"
                    "| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
                    "| S2-45 | 〔程序〕派活 | 拒绝错误工种 | 没做 |\n"
                    "| S2-46 | 〔程序〕审核关 | 未审不得交付 | 没做 |\n", encoding="utf-8")


def test_real_plan_wait_review_then_worker_resume(proj, conn, fake, monkeypatch):
    _goals(proj)
    worker = _employee(conn, proj, "worker", plan_required=True)
    reviewer = _employee(conn, proj, "reviewer", roles=["审核"], core="不能")
    record = cp.submit(conn, proj, "S1-8", "S2-45", "worker", "实现工种派活并测试。", ["backend/dispatch.py"])
    monkeypatch.setattr(dispatch, "_next_task", lambda *args: _job() | {"done": [], "wo": None})
    autolaunch.set_settings(conn, on=True)
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == ["G2 reviewer：施工计划 施-1"]
    assert autolaunch.runner_state(proj, worker["code"])["status"] == "waiting"
    cp.review(conn, proj, record["code"], "reviewer", True, "范围与验收明确", record["revision"])
    fake.items = []
    # 审核角色无待审工作，由模拟底层派活返回idle；施工员收到真实execute。
    monkeypatch.setattr(dispatch, "_next_task", lambda c, p, who: (_job() if agents.short(who) == "worker" else _job("idle", task=None)) | {"done": [], "wo": None})
    assert autolaunch.tick(conn, proj, now=1600, call=fake) == ["G1 worker：S1-8 S2-45"]
    assert autolaunch.runner_state(proj, worker["code"])["action"] == "execute"


def test_missing_roles_uses_real_pending_plans_and_craft_scope(proj, conn):
    _goals(proj)
    _employee(conn, proj, "writer", crafts=["网页"])
    _employee(conn, proj, "programmer", crafts=["程序"], auto=False)
    # 手工操作的程序员有权提交，却没有自动审核人。
    cp.submit(conn, proj, "S1-8", "S2-45", "programmer", "修派活。", ["backend/dispatch.py"])
    missing = autolaunch.missing_roles(conn, proj)
    assert "施-1 缺少独立审核员工" in missing
    assert any("S2-46" in x and "程序工种" in x for x in missing)
    assert autolaunch.status(conn, proj)["missing_roles"] == missing


def test_pending_delivery_with_wrong_scope_reports_missing_acceptor(proj, conn, monkeypatch):
    import deliveries
    _goals(proj)
    _employee(conn, proj, "reviewer", roles=["验收"], scope=["S1-9"])
    monkeypatch.setattr(deliveries, "list_all", lambda p: [{"code": "J1", "goal": "S1-8", "sub": "S2-45", "state": "等验收", "by": "agent:worker"}])
    assert "J1 缺少独立验收员工" in autolaunch.missing_roles(conn, proj)


def test_blocked_plan_review_is_skipped_for_next_plan(proj, conn):
    _goals(proj)
    _employee(conn, proj, "writer")
    reviewer = _employee(conn, proj, "reviewer", roles=["审核"])
    first = cp.submit(conn, proj, "S1-8", "S2-45", "writer", "第一件施工计划。", ["backend/a.py"])
    second = cp.submit(conn, proj, "S1-8", "S2-46", "writer", "第二件施工计划。", ["backend/b.py"])
    autolaunch.write_runner_state(proj, reviewer["code"], "ready", blocked=["review_plan:" + first["code"]])
    assert cp.next_review(conn, proj, "reviewer")["code"] == second["code"]
    assert claims.active(conn)[0]["sub"] == second["code"]


def test_paused_reviewer_cannot_take_or_review_plan(proj, conn):
    _goals(proj)
    _employee(conn, proj, "writer")
    _employee(conn, proj, "reviewer", roles=["审核"], paused=True)
    plan = cp.submit(conn, proj, "S1-8", "S2-45", "writer", "实现任务。", ["backend/a.py"])
    assert cp.next_review(conn, proj, "reviewer") is None
    with pytest.raises(store.Refused, match="暂停"):
        cp.review(conn, proj, plan["code"], "reviewer", True, "不该继续", plan["revision"])


def test_existing_managed_failed_delivery_wakes_reviewer_and_returns_rework(proj, conn, fake):
    import blueprint
    import deliveries
    _goals(proj)
    _employee(conn, proj, 'writer', plan_required=True, scope=['S1-8 S2-45'])
    _employee(conn, proj, 'reviewer', roles=['验收'])
    f = proj.root / '自动化/交付/J83 S1-8 S2-45.md'
    f.parent.mkdir(parents=True)
    f.write_text('---\n编号: J83\n目标: S1-8\n小目标: S2-45\n状态: 待你验收\n谁: agent:writer\n---\n\n'
                 '# 旧交付格式\n\n## 怎么验的\n\n- 过了 · 其他检查\n- 没过 · 安装检查：未实际安装\n\n## 东西在哪\n\n- result.txt\n', encoding='utf-8')
    blueprint.set_status(proj, 'S1-8', 'S2-45', '待你验收（J83）')
    autolaunch.set_settings(conn, on=True)
    assert autolaunch.tick(conn, proj, now=1000, call=fake) == ['G2 reviewer：验收 J83']
    assert claims.of(conn, 'agent:reviewer')[0]['sub'] == 'J83'
    assert deliveries.get(proj, 'J83')['state'] == '待你验收'
    with pytest.raises(store.Refused, match='原交付自查有失败'):
        deliveries.review(conn, proj, 'J83', True, '不能假装全过', by='agent:reviewer', checks=[{'name':'安装检查','ok':True}])
    deliveries.review(conn, proj, 'J83', False, '实查安装仍未验证，修复后重新交付', by='agent:reviewer', checks=[{'name':'安装检查','ok':False}])
    assert dispatch.next_task(conn, proj, 'agent:writer')['action'] == 'submit_plan'
