"""项目普通 W 图和实际派发/计划/交付关卡。仅临时项目，不启动模型或终端。"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

import agents
import autolaunch
import blueprint
import builtin
import claims
import construction_plans as cp
import deliveries
import dispatch
import runs
import store
import workflow_graph as wf
import workorders
from project import Project


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def ready(proj):
    write(proj.root / "治理/目标/S0 终极目标.md", "# S0 终极目标\n\n**完成一般项目的真实任务。**\n")
    for code in ("S1-9", "S1-10"):
        write(proj.root / f"治理/目标/{code} 演练.md", f"# {code} 演练\n\n**完成临时文件核对。**\n\n"
              "规划：定稿 · 2026-10-05 · 作者：「临时项目核对」\n\n怎么算做到：文件和真实检查一致\n\n"
              "| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"
              "| S2-1 | 核对文字 | | 文件内容一致 | 没做 |\n"
              "| S2-2 | 核对附件 | | 附件内容一致 | 没做 |\n")
    write(proj.root / "治理/戒律/1 通用戒律.md", "# 通用戒律\n\n通-15 只在公开发布、彻底删除时停。\n")
    write(proj.root / "治理/戒律/2 项目戒律.md", "# 项目戒律\n\n只用临时材料。\n")
    write(proj.root / "AGENTS.md", "# 项目规则\n\n通-15 必停：公开发布、彻底删除。\n")
    write(proj.root / ".mcp.json", '{"mcpServers":{"research-console":{}}}')
    write(proj.root / "资料/演练/产物.txt", "真实临时检查产物")
    conn = store.connect(proj.db_path)
    for name, roles in (("worker", ["干活", "审核", "验收"]), ("reviewer", ["审核"]),
                        ("acceptor", ["验收"]), ("other", ["干活", "审核", "验收"])):
        agents.create(conn, proj, name, "空白", roles=roles, program="Codex", auto=True,
                      plan_required=False, scope=["S1-9", "S1-10"], core="能")
    store.log(conn, "agent:worker", "临时报到", "", "只使用临时项目，不启动模型")
    yield conn
    conn.close()


def graph(task="S1-9 S2-1", prefix="", worker="G1", reviewer="G2", acceptor="G3"):
    stages = [("start", "start"), ("dispatch", "dispatch"), ("plan", "review_plan"),
              ("execute", "execute"), ("accept", "review_delivery"), ("end", "end")]
    nodes = []
    for key, kind in stages:
        node = {"id": prefix + key, "type": kind, "label": kind, "x": len(nodes) * 120, "y": 80}
        if kind in wf.STAGES:
            node |= {"task": task, "employee": reviewer if kind == "review_plan" else acceptor if kind == "review_delivery" else worker}
        nodes.append(node)
    edges = [{"id": prefix + "e" + str(i), "from": nodes[i]["id"], "to": nodes[i + 1]["id"], "when": "always"} for i in range(len(nodes) - 1)]
    return {"schema": 1, "nodes": nodes, "edges": edges}


def enabled(conn, proj, value=None):
    record = wf.save(conn, proj, "", "临时流程", value or graph(), by="人")
    wf.control(conn, proj, record["code"], "enable", record["revision"], by="人")
    return wf.read(proj, record["code"])


def submit(conn, proj, task="S1-9 S2-1", **kwargs):
    goal, sub = wf.split_task(task)
    return cp.submit(conn, proj, goal, sub, "worker", "核对真实临时文件并记录检查。",
                     ["资料/演练/产物.txt"], rules=["通-15"], **kwargs)


def approve(conn, proj, plan):
    return cp.review(conn, proj, plan["code"], "reviewer", True, "范围清楚，可复跑", plan["revision"])


def snapshot_files(root):
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in root.rglob("*") if f.is_file() and "索引" not in f.parts}


def test_save_preserves_text_history_and_immutable_active_snapshot(proj, ready):
    record = enabled(ready, proj)
    file = proj.root / record["file"]
    write(file, "作者手写说明，不得丢失。\n\n" + file.read_text(encoding="utf-8"))
    old = wf.read(proj, record["code"])
    revised = copy.deepcopy(old["graph"])
    revised["nodes"][1]["label"] = "新的派活标题"
    new = wf.save(ready, proj, old["code"], "临时流程", revised, old["revision"])
    assert "作者手写说明，不得丢失。" in new["text"]
    assert new["active"]["graph"]["nodes"][1]["label"] == "dispatch"
    assert new["active"]["snapshot_revision"] == record["revision"]
    assert len(list((proj.root / wf.DIR / "历史").glob("*.md"))) == 1
    with pytest.raises(store.Refused, match="版本"):
        wf.save(ready, proj, old["code"], "临时流程", revised, old["revision"])
    with pytest.raises(store.Refused, match="先明确停用"):
        wf.control(ready, proj, new["code"], "enable", new["revision"])
    assert not autolaunch.settings(ready)["on"]


@pytest.mark.parametrize("mutation,expected", [
    (lambda g: g["nodes"][2].update(employee="G1"), "自审"),
    (lambda g: g["nodes"][4].update(employee="G1"), "自验"),
    (lambda g: g["nodes"][1].update(employee="G99"), "真实员工"),
    (lambda g: g["nodes"][1].update(task="S2-1"), "完整目标"),
    (lambda g: g["edges"].append({"id": "loop", "from": "accept", "to": "dispatch"}), "无环"),
])
def test_invalid_draft_can_save_but_cannot_enable(proj, ready, mutation, expected):
    value = graph()
    mutation(value)
    result = wf.validate(proj, value)
    assert not result["ok"] and any(expected in e for e in result["errors"])
    record = wf.save(ready, proj, "", "未完工草稿", value)
    with pytest.raises(store.Refused, match="不能启用"):
        wf.control(ready, proj, record["code"], "enable", record["revision"])
    assert wf.list_all(proj)["active"] is None


def test_dry_run_is_read_only_even_after_real_records(proj, ready):
    value = graph()
    before = snapshot_files(proj.root)
    events = ready.execute("SELECT COUNT(*) FROM event").fetchone()[0]
    result = wf.dry_run(ready, proj, value)
    assert result["ok"] and result["read_only"]
    assert next(n for n in result["nodes"] if n["id"] == "dispatch")["status"] == "ready"
    assert claims.active(ready) == [] and workorders.list_all(proj) == []
    assert snapshot_files(proj.root) == before
    assert ready.execute("SELECT COUNT(*) FROM event").fetchone()[0] == events


def test_dry_run_reports_employee_and_project_pause_without_clearing_it(proj, ready):
    enabled(ready, proj)
    agents.update(ready, proj, 'worker', {'paused': True})
    result = wf.dry_run(ready, proj, graph())
    node = next(n for n in result['nodes'] if n['id'] == 'dispatch')
    assert node['status'] == 'waiting' and '员工已暂停' in node['reason']
    agents.update(ready, proj, 'worker', {'paused': False})
    store._set_meta(ready, workorders.PAUSE, '临时人工停止')
    result = wf.dry_run(ready, proj, graph())
    assert result['project_paused'] == '临时人工停止'
    assert not any(n['status'] == 'ready' for n in result['nodes'])
    with pytest.raises(store.Refused, match='叫停'):
        submit(ready, proj)
    assert workorders.paused(ready) == '临时人工停止'


def test_true_dispatch_plan_review_execution_delivery_independent_acceptance(proj, ready):
    record = enabled(ready, proj)
    # 真实 next_task 自己开 K、认领，再按图强制未开启必审的旧档案提交计划。
    first = dispatch.next_task(ready, proj, "agent:worker")
    assert first["action"] == "submit_plan" and first["task"]["sub"] == "S2-1"
    assert first["workflow"]["revision"] == record["revision"]
    assert any(c["agent"] == "agent:worker" for c in claims.active(ready))
    with pytest.raises(store.Refused, match="流程|尚未通过"):
        deliveries.deliver(ready, proj, goal="S1-9", sub="S2-1", did="试图未审交付", checks=[{"name": "内容", "ok": True}], files=["资料/演练/产物.txt"], by="worker")
    plan = submit(ready, proj)
    assert (dispatch.next_task(ready, proj, "agent:other").get("task") or {}).get("sub") != "S2-1"
    reviewer = dispatch.next_task(ready, proj, "agent:reviewer")
    assert reviewer["action"] == "review_plan" and reviewer["construction_plan"]["code"] == plan["code"]
    with pytest.raises(store.Refused, match="指定"):
        cp.review(ready, proj, plan["code"], "other", True, "非图指定审核员", plan["revision"])
    approve(ready, proj, plan)
    execution = dispatch.next_task(ready, proj, "agent:worker")
    assert execution["action"] == "execute"
    j = deliveries.deliver(ready, proj, goal="S1-9", sub="S2-1", did="真实文字检查已过",
                           checks=[{"name": "内容一致", "ok": True, "detail": "读取临时文件一致"}],
                           files=["资料/演练/产物.txt"], by="worker")
    assert j["state"] == "等验收"  # 旧档案 auto=True 之外，图始终要求独立验收。
    with pytest.raises(store.Refused, match="自己"):
        deliveries.review(ready, proj, j["code"], True, "自验", by="worker", checks=[{"name": "复跑", "ok": True}])
    acceptor = dispatch.next_task(ready, proj, "agent:acceptor")
    assert acceptor["action"] == "review_delivery" and acceptor["review"]["code"] == j["code"]
    with pytest.raises(store.Refused, match="指定"):
        deliveries.review(ready, proj, j["code"], True, "其他员工想验", by="other", checks=[{"name": "复跑", "ok": True}])
    deliveries.review(ready, proj, j["code"], True, "独立读取真实文件一致", by="acceptor", checks=[{"name": "复跑一致", "ok": True}])
    assert blueprint.is_done(blueprint.pyramid(proj), "S1-9 S2-1")
    next_task = dispatch.next_task(ready, proj, "agent:worker")["task"]
    assert (next_task["goal"], next_task["sub"]) != ("S1-9", "S2-1")


def test_linear_rejection_revises_plan_and_redoes_delivery(proj, ready):
    enabled(ready, proj)
    dispatch.next_task(ready, proj, "agent:worker")
    plan = submit(ready, proj)
    cp.review(ready, proj, plan["code"], "reviewer", False, "补充检查步骤", plan["revision"])
    assert dispatch.next_task(ready, proj, "agent:worker")["action"] == "submit_plan"
    revised = submit(ready, proj, revision=cp.get(proj, plan["code"])["revision"])
    approve(ready, proj, revised)
    assert dispatch.next_task(ready, proj, "agent:worker")["action"] == "execute"
    j = deliveries.deliver(ready, proj, goal="S1-9", sub="S2-1", did="提交初稿", checks=[{"name": "读取", "ok": True}], files=["资料/演练/产物.txt"], by="worker")
    dispatch.next_task(ready, proj, "agent:acceptor")
    deliveries.review(ready, proj, j["code"], False, "临时返工检查", by="acceptor", checks=[{"name": "未满足", "ok": False}])
    assert dispatch.next_task(ready, proj, "agent:worker")["action"] == "execute"


def conditional_graph():
    value = graph(task="S1-9 S2-1", prefix="a-")
    value["nodes"] += [n for n in graph(task="S1-9 S2-2", prefix="b-")["nodes"] if n["type"] != "start"]
    value["nodes"].append({"id": "condition", "type": "condition", "task": "S1-10 S2-1", "field": "task_done", "value": True})
    value["edges"] = [e for e in value["edges"] if e["from"] != "a-start"]
    value["edges"] += [e for e in graph(task="S1-9 S2-2", prefix="b-")["edges"] if e["from"] != "b-start"]
    value["edges"] += [{"id": "begin", "from": "a-start", "to": "condition", "when": "always"},
                       {"id": "yes", "from": "condition", "to": "a-dispatch", "when": "true"},
                       {"id": "no", "from": "condition", "to": "b-dispatch", "when": "false"}]
    return value


@pytest.mark.parametrize("done,expected", [(False, "S2-2"), (True, "S2-1")])
def test_condition_only_dependency_controls_actual_claim_not_bare_sub_number(proj, ready, done, expected):
    if done:
        blueprint.set_status(proj, "S1-10", "S2-1", "做完（临时既有记录）")
    value = conditional_graph()
    assert wf.validate(proj, value)["ok"]
    enabled(ready, proj, value)
    next_ = dispatch.next_task(ready, proj, "agent:worker")
    assert next_["action"] == "submit_plan" and next_["task"]["sub"] == expected
    held = [r for r in claims.of(ready, "agent:worker") if r["goal"] == "S1-9"]
    assert len(held) == 1 and held[0]["sub"] == expected
    assert not wf.requires_plan(proj, "S1-10", "S2-1")  # 条件来源不成为新的施工授权。


def test_stopped_guard_survives_process_restart_and_cannot_fall_back(proj, ready):
    record = enabled(ready, proj)
    dispatch.next_task(ready, proj, "agent:worker")
    plan = submit(ready, proj)
    approve(ready, proj, plan)
    wf.control(ready, proj, record["code"], "stop", record["active"]["snapshot_revision"])
    assert wf.read(Project(proj.root), record["code"])["active"] is None
    assert "停用" in wf.action_reason(proj, "execute", "S1-9", "S2-1", "worker")
    with pytest.raises(store.Refused, match="停用"):
        deliveries.deliver(ready, proj, goal="S1-9", sub="S2-1", did="停止后不能交", checks=[{"name": "读取", "ok": True}], files=["资料/演练/产物.txt"], by="worker")
    next_ = dispatch.next_task(ready, proj, "agent:worker")
    assert (next_.get("task") or {}).get("sub") != "S2-1"
    assert not any(r["goal"] == "S1-9" and r["sub"] == "S2-1" for r in claims.of(ready, "agent:worker"))
    assert not autolaunch.settings(ready)["on"]


def test_changed_approved_plan_cannot_execute_or_be_counted_approved(proj, ready):
    record = enabled(ready, proj)
    dispatch.next_task(ready, proj, "agent:worker")
    plan = approve(ready, proj, submit(ready, proj))
    file = proj.root / plan["formal_path"]
    write(file, file.read_text(encoding="utf-8") + "\n额外修改批准正文\n")
    result = wf.dry_run(ready, proj, record["graph"])
    assert next(n for n in result["nodes"] if n["id"] == "dispatch")["status"] == "ready"
    assert dispatch.next_task(ready, proj, "agent:worker")["action"] == "submit_plan"
    assert cp.approved(proj, "S1-9", "S2-1", "worker") is None


def test_unknown_dependency_waits_and_cannot_route_false(proj, ready):
    value = conditional_graph()
    enabled(ready, proj, value)
    source = proj.root / "治理/目标/S1-10 演练.md"
    write(source, source.read_text(encoding="utf-8").replace("附件内容一致", "改变前置验收").replace("文件内容一致", "改变前置方向"))
    assert "范围已变化" in wf.action_reason(proj, "submit_plan", "S1-9", "S2-1", "worker")
    next_ = dispatch.next_task(ready, proj, "agent:worker")
    assert (next_.get("task") or {}).get("goal") != "S1-9"
    assert not any(r["goal"] == "S1-9" for r in claims.of(ready, "agent:worker"))


def test_private_workflow_and_state_never_inherit_into_new_project(proj, ready):
    record = enabled(ready, proj)
    write(proj.root / "自动化/工作流/W1 通用流程.md", "---\n编号: W1\n名字: 通用流程\n---\n普通通用模板")
    write(proj.root / "自动化/流程状态/内置/不应该带.json", "{}");
    selected = builtin.files(proj.root, proj.root / "自动化/工作流", core=True)
    assert selected == ["自动化/工作流/W1 通用流程.md"]
    with pytest.raises(builtin.Invalid, match="私有工作流"):
        builtin.path(proj.root, record["file"])
    assert not any("流程状态" in f for f in builtin.folders(proj.root))
    write(proj.root / "自动化/工作流/项目模板/内置/模板.md", "公开通用模板")
    assert "自动化/工作流/项目模板/内置" in builtin.folders(proj.root)


def test_project_mcp_and_web_workflow_source_same_without_global_private_leak(proj, ready, tmp_path):
    record = enabled(ready, proj)
    cards = runs.list_workflows(project=proj)
    assert any(c["code"] == record["code"] and c["graph"] == record["graph"] for c in cards)
    other = Project(tmp_path / "另一个项目")
    other.root.mkdir()
    assert wf.list_all(other)["items"] == []
    assert not any(c.get("project") for c in runs.list_workflows(project=other))


def test_no_graph_old_behavior_and_corrupt_active_fail_closed(proj, ready):
    assert not wf.requires_plan(proj, "S1-9", "S2-1")
    assert wf.action_reason(proj, "execute", "S1-9", "S2-1", "worker") == ""
    enabled(ready, proj)
    control = proj.root / wf.STATE
    data = json.loads(control.read_text(encoding="utf-8"))
    data["active"]["graph"]["nodes"][1]["employee"] = "G4"
    write(control, json.dumps(data, ensure_ascii=False))
    assert "快照已变更" in wf.action_reason(proj, "execute", "S1-9", "S2-1", "worker")
    next_ = dispatch.next_task(ready, proj, "agent:worker")
    assert next_["action"] == "idle" and "快照已变更" in next_["reason"]
    assert claims.active(ready) == []


def test_malformed_stop_guard_is_reported_without_falling_back(proj, ready):
    write(proj.root / wf.STATE, json.dumps({'schema': 1, 'active': None, 'guards': {'S1-9 S2-1': []}, 'history': []}))
    assert '守卫格式不完整' in wf.action_reason(proj, 'execute', 'S1-9', 'S2-1', 'worker')
    assert claims.active(ready) == []


def test_old_manual_profiles_still_require_plan_and_independent_delivery(proj, ready):
    for name in ("worker", "reviewer", "acceptor", "other"):
        agents.update(ready, proj, name, {"auto": False, "plan_required": False})
    enabled(ready, proj)
    first = dispatch.next_task(ready, proj, "agent:worker")
    assert first["action"] == "submit_plan"
    plan = approve(ready, proj, submit(ready, proj))
    assert dispatch.next_task(ready, proj, "agent:worker")["action"] == "execute"
    j = deliveries.deliver(ready, proj, goal="S1-9", sub="S2-1", did="手动档案真实交付",
                           checks=[{"name": "文件核对", "ok": True}], files=["资料/演练/产物.txt"], by="worker")
    assert j["state"] == "等验收" and j["plan"] == plan["formal_path"]
    with pytest.raises(store.Refused, match="独立"):
        deliveries.accept_by_word(ready, proj, j["code"], "假借口头通过", agent="worker")


def test_flow_stop_signal_interrupts_existing_runner_without_enabling_automation(proj, ready):
    import employee_runner
    record = enabled(ready, proj)
    current = dispatch.next_task(ready, proj, "agent:worker")
    autolaunch.write_runner_state(proj, "worker", "running", current=current)
    assert employee_runner.local_stop_reason(proj, "worker") == ""
    wf.control(ready, proj, record["code"], "stop", record["revision"])
    assert "流程已停用" in employee_runner.local_stop_reason(proj, "worker")
    assert not autolaunch.settings(ready)["on"]


def test_changed_task_binding_waits_without_claiming_wrong_worker(proj, ready):
    enabled(ready, proj)
    agents.update(ready, proj, "worker", {"roles": ["审核"]})
    result = dispatch.next_task(ready, proj, "agent:other")
    assert (result.get("task") or {}).get("goal") != "S1-9" or (result.get("task") or {}).get("sub") != "S2-1"
    assert not any(r['goal'] == 'S1-9' and r['sub'] == 'S2-1' for r in claims.active(ready))


def test_web_routes_versions_and_readonly_check_use_same_project_files(proj, ready):
    from fastapi.testclient import TestClient
    from main import create_app
    with TestClient(create_app(proj)) as client:
        assert client.post('/api/auto/workflows/validate', json={'graph': None}).json()['ok'] is False
        draft = client.post('/api/auto/workflows', json={'name': '网页流程', 'graph': graph()})
        assert draft.status_code == 200
        record = draft.json()
        assert wf.read(proj, record['code'])['graph'] == record['graph']
        listed = client.get('/api/auto/workflows').json()
        assert listed['items'][0]['revision'] == record['revision'] and listed['active'] is None
        assert any(w.get('code') == record['code'] and w.get('project') for w in client.get('/api/auto').json()['workflows'])
        events = ready.execute('SELECT COUNT(*) FROM event').fetchone()[0]
        assert client.post('/api/auto/workflows/dry-run', json={'graph': record['graph']}).json()['read_only']
        assert ready.execute('SELECT COUNT(*) FROM event').fetchone()[0] == events
        assert claims.active(ready) == []
        stale = client.post('/api/auto/workflows/' + record['code'] + '/control', json={'action': 'enable', 'revision': 'stale'})
        assert stale.status_code == 400
        enabled_ = client.post('/api/auto/workflows/' + record['code'] + '/control', json={'action': 'enable', 'revision': record['revision']}).json()
        assert enabled_['active']['snapshot_revision'] == record['revision']
        assert not autolaunch.settings(ready)['on']
        assert client.post('/api/auto/workflows', json={'name': '非法/名称', 'graph': graph()}).status_code == 400


def test_real_mcp_draft_read_matches_http_and_activation_requires_specific_authorization(proj, ready):
    import anyio
    import sys
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Implementation
    async def call(calls, authorization=''):
        args = [str(Path(__file__).parents[1] / 'mcp_server.py'), '--project', str(proj.root), '--agent', 'worker']
        if authorization:
            args += ['--configuration-authorization', authorization]
        params = StdioServerParameters(command=sys.executable, args=args)
        output = []
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w, client_info=Implementation(name='wrong-client', version='1')) as session:
                await session.initialize()
                for name, arguments in calls:
                    result = await session.call_tool(name, arguments)
                    output.append((bool(result.isError), '\n'.join(c.text for c in result.content if c.type == 'text')))
        return output
    results = anyio.run(call, [('save_workflow_graph', {'name': 'MCP临时流程', 'graph': graph()})])
    assert not results[0][0]
    draft = json.loads(results[0][1])
    unauthorized = anyio.run(call, [('read_workflow_graph', {'code': draft['code']}),
                                  ('configure_workflow_graph', {'code': draft['code'], 'action': 'enable', 'revision': draft['revision'], 'authorization_path': '治理/计划/S0 总体/P1.md'})])
    assert json.loads(unauthorized[0][1])['graph'] == wf.read(proj, draft['code'])['graph']
    assert unauthorized[1][0] and '没有配置授权' in unauthorized[1][1]
    authorization = '治理/计划/S0 总体/P1 · 2026-10-05 · 临时工作流授权.md'
    write(proj.root / authorization, f'> 授权：作者本次明确启用工作流 {draft["code"]}\n> 授权操作者：worker\n')
    enabled_ = anyio.run(call, [('configure_workflow_graph', {'code': draft['code'], 'action': 'enable', 'revision': draft['revision'], 'authorization_path': authorization})], authorization)
    assert not enabled_[0][0] and json.loads(enabled_[0][1])['active']['code'] == draft['code']
    assert not autolaunch.settings(ready)['on'] and claims.active(ready) == []


@pytest.mark.parametrize("value", [None, {"nodes": [], "edges": []}, {"nodes": [{"id": [], "type": "condition"}], "edges": []}])
def test_invalid_json_reports_friendly_validation_not_typeerror(proj, ready, value):
    assert wf.validate(proj, value)["ok"] is False


@pytest.mark.parametrize("stopped", [False, True])
def test_real_mcp_legacy_employee_cannot_take_core_before_flow_task_or_plan(proj, ready, stopped):
    import anyio
    from test_automation_mcp import call
    record = enabled(ready, proj)
    assert not agents.get(proj, 'worker')['plan_required']
    if stopped:
        wf.control(ready, proj, record['code'], 'stop', record['revision'])
    results = anyio.run(call, proj, 'worker', [('claim_task', {'goal': '核心'})])
    assert '先领施工任务' in results[0][1]
    assert not claims.holds_core(ready, 'agent:worker') and cp.listing(proj) == []


def test_flow_employee_unrelated_claim_does_not_authorize_core(proj, ready):
    import anyio
    from test_automation_mcp import call
    enabled(ready, proj)
    claims.claim(ready, 'S1-10', 'S2-1', 'agent:worker', ['S1-10 S2-1'])
    results = anyio.run(call, proj, 'worker', [('claim_task', {'goal': '核心'})])
    assert '流程绑定的施工任务' in results[0][1]
    assert not claims.holds_core(ready, 'agent:worker')


def test_real_mcp_core_preserves_no_flow_legacy_and_approved_flow_behavior(proj, ready):
    import anyio
    from test_automation_mcp import call
    legacy = anyio.run(call, proj, 'worker', [('claim_task', {'goal': '核心'})])
    assert '领了 核心' in legacy[0][1] and claims.holds_core(ready, 'agent:worker')
    claims.release(ready, '核心', '', 'agent:worker')
    enabled(ready, proj)
    dispatch.next_task(ready, proj, 'agent:worker')
    denied = anyio.run(call, proj, 'worker', [('claim_task', {'goal': '核心'})])
    assert not claims.holds_core(ready, 'agent:worker') and '计划' in denied[0][1]
    approve(ready, proj, submit(ready, proj))
    approved = anyio.run(call, proj, 'worker', [('claim_task', {'goal': '核心'})])
    assert '领了 核心' in approved[0][1] and claims.holds_core(ready, 'agent:worker')


@pytest.mark.parametrize("stage,employee,claim_goal", [
    ('submit_plan', 'worker', 'S1-9'), ('review_plan', 'reviewer', cp.REVIEW),
    ('review_delivery', 'acceptor', '验收')])
def test_stop_between_gate_and_claim_retracts_new_work_or_review_claim(proj, ready, monkeypatch, stage, employee, claim_goal):
    record = enabled(ready, proj)
    if stage != 'submit_plan':
        dispatch.next_task(ready, proj, 'agent:worker')
        plan = submit(ready, proj)
        if stage == 'review_delivery':
            approve(ready, proj, plan)
            deliveries.deliver(ready, proj, goal='S1-9', sub='S2-1', did='TEMP真实产物',
                               checks=[{'name': 'TEMP', 'ok': True}], files=['资料/演练/产物.txt'], by='worker')
    original = claims.claim
    stopped = False
    def stop_before_claim(conn, goal, sub, *args, **kwargs):
        nonlocal stopped
        if goal == claim_goal and not stopped:
            stopped = True
            wf.control(ready, proj, record['code'], 'stop', record['revision'])
        return original(conn, goal, sub, *args, **kwargs)
    monkeypatch.setattr(claims, 'claim', stop_before_claim)
    got = dispatch.next_task(ready, proj, 'agent:' + employee)
    assert stopped and got['action'] not in wf.ACTION_TYPES
    assert claims.of(ready, 'agent:' + employee) == []


@pytest.mark.parametrize("operation", ['submit', 'deliver'])
def test_stop_before_write_transaction_refuses_new_plan_or_delivery(proj, ready, monkeypatch, operation):
    from contextlib import contextmanager
    record = enabled(ready, proj)
    dispatch.next_task(ready, proj, 'agent:worker')
    if operation == 'deliver':
        approve(ready, proj, submit(ready, proj))
    original = store.tx
    pending = True
    @contextmanager
    def stop_then_transaction(conn):
        nonlocal pending
        if pending:
            pending = False
            wf.control(ready, proj, record['code'], 'stop', record['revision'])
        with original(conn):
            yield conn
    monkeypatch.setattr(store, 'tx', stop_then_transaction)
    before = (len(cp.listing(proj)), len(deliveries.list_all(proj)))
    with pytest.raises(store.Refused, match='停用'):
        if operation == 'submit':
            submit(ready, proj)
        else:
            deliveries.deliver(ready, proj, goal='S1-9', sub='S2-1', did='不应落盘',
                               checks=[{'name': 'TEMP', 'ok': True}], files=['资料/演练/产物.txt'], by='worker')
    assert before == (len(cp.listing(proj)), len(deliveries.list_all(proj)))
