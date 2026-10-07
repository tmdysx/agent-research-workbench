"""显式项目交付策略：真实计划、交付文件、任务状态和释放锁，不动实际项目。"""
from contextlib import contextmanager
import json
import os

import pytest

import agents
import blueprint
import claims
import construction_plans as plans
import deliveries
import dispatch
import store
import vcs
import workorders


CHECKS = [{"name": "实际检查", "ok": True, "detail": "文件内容正确"}]
POLICY = {"version": 1, "mode": "checks-pass"}


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _policy(proj, content=POLICY):
    _write(proj.root / deliveries.POLICY, json.dumps(content))


@pytest.fixture
def setup(proj, monkeypatch):
    _write(proj.root / "治理/目标/S1-1 样板.md",
           "# S1-1 样板\n\n**实际检查后交付。**\n\n"
           "| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
           "| S2-1 | 〔程序〕修改文件 | 文件内容正确 | 没做 |\n")
    _write(proj.root / "backend/result.txt", "真实测试结果")
    conn = store.connect(proj.db_path)
    agents.create(conn, proj, "writer", "写代码的", auto=True, plan_required=True)
    agents.create(conn, proj, "reviewer", roles=["审核", "验收"])
    record = plans.submit(conn, proj, "S1-1", "S2-1", "agent:writer",
                          "修正文件，读取实际内容并检查后交付。", ["backend/result.txt"])
    plans.review(conn, proj, record["code"], "agent:reviewer", True,
                 "范围准确，检查结果可核对。", record["revision"])
    _claim(conn)
    commits = []
    monkeypatch.setattr(vcs, "commit", lambda *a, **kw: commits.append(kw) or "test-commit")
    yield conn, commits
    conn.close()


def _claim(conn):
    claims.claim(conn, "S1-1", "S2-1", "agent:writer", ["S1-1"])
    claims.take_core(conn, "agent:writer", "临时项目核心检查")


def _deliver(proj, conn, **kw):
    return deliveries.deliver(conn, proj, goal="S1-1", sub="S2-1", did="完成并记录实际检查",
                              checks=kw.pop("checks", CHECKS), files=kw.pop("files", ["backend/result.txt"]),
                              by="agent:writer", **kw)


def _task(proj):
    return blueprint.find(blueprint.pyramid(proj), "S1-1")["subs"][0]


@pytest.mark.parametrize("with_acceptor", [False, True])
def test_managed_worker_passes_and_books_without_waiting_for_acceptor(proj, setup, with_acceptor):
    conn, commits = setup
    if not with_acceptor:
        agents.update(conn, proj, "reviewer", {"roles": ["审核"]}, by="人")
    _policy(proj)
    j = _deliver(proj, conn)
    assert j["state"] == "验收通过" and j["self_checks_passed"] is True
    assert "自动验收（交付策略 checks-pass）；检查全过" in j["body"]
    assert _task(proj)["status"] == "ok"
    assert not deliveries.independent_pending(proj, j)
    assert dispatch.review_job(conn, proj, "agent:reviewer") is None
    assert claims.of(conn, "agent:writer") == []
    assert len(commits) == 1 and "test-commit" in j["body"]


@pytest.mark.parametrize("bad", [False, None, "false", "true", 1, 0, "missing"])
def test_non_true_checks_are_rejected_and_repaired_submission_can_pass(proj, setup, bad):
    conn, commits = setup
    _policy(proj)
    failed = {"name": "尚未通过的检查", "detail": "失败或未测，不能报通过"}
    if bad != "missing":
        failed["ok"] = bad
    j = _deliver(proj, conn, checks=[*CHECKS, failed])
    assert j["state"] == "打回" and j["self_checks_passed"] is False
    assert j["self_checks"][0]["ok"] is True and j["self_checks"][1]["ok"] is False
    assert "没过 · 尚未通过的检查" in j["body"]
    assert "修复后实际复验再交付" in j["body"]
    assert _task(proj)["status"] == "todo"
    assert not deliveries.independent_pending(proj, j)
    assert claims.of(conn, "agent:writer") == []
    old = (proj.root / deliveries.DIR / j["file"]).read_bytes()
    _claim(conn)
    repaired = _deliver(proj, conn)
    assert repaired["state"] == "验收通过" and repaired["code"] != j["code"]
    assert (proj.root / deliveries.DIR / j["file"]).read_bytes() == old
    assert len(commits) == 2


def test_human_can_send_automatically_accepted_delivery_back(proj, setup):
    conn, _ = setup
    _policy(proj)
    j = _deliver(proj, conn)
    result = deliveries.reject(conn, proj, j["code"], "实际使用时结果不符合要求", by="人")
    assert result["state"] == "打回" and _task(proj)["status"] == "todo"
    assert "人 打回：实际使用时结果不符合要求" in deliveries.last_note(result)
    assert "自动验收" in result["body"]


@pytest.mark.parametrize("checks", [CHECKS, [{"name": "实际失败", "ok": False}]])
def test_missing_policy_keeps_existing_managed_review_gate(proj, setup, checks):
    conn, _ = setup
    j = _deliver(proj, conn, checks=checks)
    assert j["state"] == "等验收" and deliveries.independent_pending(proj, j)
    assert _task(proj)["status"] != "ok"


@pytest.mark.parametrize("checks", [[], None])
def test_empty_checks_do_not_create_delivery_or_release_claim(proj, setup, checks):
    conn, commits = setup
    _policy(proj)
    with pytest.raises(store.Refused, match="没验过"):
        _deliver(proj, conn, checks=checks)
    assert deliveries.list_all(proj) == [] and commits == []
    assert len(claims.of(conn, "agent:writer")) == 2


@pytest.mark.parametrize("content", ["{", "null", "[]", "{}",
    '{"version": true, "mode": "checks-pass"}',
    '{"version": 2, "mode": "checks-pass"}',
    '{"version": 1, "mode": "always-pass"}',
    '{"version": 1, "mode": "checks-pass", "unknown": true}'])
def test_invalid_policy_refuses_before_writing_delivery(proj, setup, content):
    conn, commits = setup
    _write(proj.root / deliveries.POLICY, content)
    with pytest.raises(store.Refused, match="交付策略"):
        _deliver(proj, conn)
    assert deliveries.list_all(proj) == [] and commits == []
    assert not store._meta(conn, "delivery_seq")
    assert len(claims.of(conn, "agent:writer")) == 2


@pytest.mark.parametrize("part", ["file", "parent"])
def test_linked_policy_refuses_before_writing_delivery(proj, setup, tmp_path, part):
    conn, _ = setup
    outside = tmp_path / "outside"
    _write(outside / "交付策略.json", json.dumps(POLICY))
    target = proj.root / deliveries.POLICY
    target.parent.parent.mkdir(parents=True, exist_ok=True)
    try:
        if part == "file":
            target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(outside / "交付策略.json", target)
        else:
            os.symlink(outside, target.parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"当前测试环境不能创建链接：{exc}")
    with pytest.raises(store.Refused, match="交付策略.*链接"):
        _deliver(proj, conn)
    assert deliveries.list_all(proj) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows 目录联接检查")
def test_junction_policy_parent_is_not_followed(proj, setup, tmp_path):
    from test_builtin import _make_junction
    conn, _ = setup
    outside = tmp_path / "outside"
    _write(outside / "交付策略.json", json.dumps(POLICY))
    target = proj.root / deliveries.POLICY
    target.parent.parent.mkdir(parents=True, exist_ok=True)
    _make_junction(target.parent, outside)
    with pytest.raises(store.Refused, match="交付策略.*联接"):
        _deliver(proj, conn)
    assert deliveries.list_all(proj) == []


@pytest.mark.parametrize("checks", [[True], {"ok": True}, "passed"])
def test_malformed_checks_do_not_create_delivery(proj, setup, checks):
    conn, _ = setup
    _policy(proj)
    with pytest.raises(store.Refused, match="每条检查"):
        _deliver(proj, conn, checks=checks)
    assert deliveries.list_all(proj) == [] and not store._meta(conn, "delivery_seq")


def test_policy_changed_before_write_transaction_cannot_leave_half_delivery(proj, setup, monkeypatch):
    conn, _ = setup
    _policy(proj)
    original = store.tx
    first = True

    @contextmanager
    def tx(c):
        nonlocal first
        if first:
            first = False
            _write(proj.root / deliveries.POLICY, "broken")
        with original(c):
            yield c

    monkeypatch.setattr(store, "tx", tx)
    with pytest.raises(store.Refused, match="交付策略"):
        _deliver(proj, conn)
    assert deliveries.list_all(proj) == [] and not store._meta(conn, "delivery_seq")
    assert len(claims.of(conn, "agent:writer")) == 2


@pytest.mark.parametrize("change,reason", [("plan", "尚未通过"), ("scope", "范围"),
    ("claim", "认领"), ("project", "暂停"), ("employee", "暂停"), ("role", "岗位")])
def test_automatic_acceptance_keeps_existing_execution_guards(proj, setup, change, reason):
    conn, _ = setup
    _policy(proj)
    if change == "plan":
        record = plans.listing(proj)[0]
        plans.submit(conn, proj, "S1-1", "S2-1", "agent:writer", "修订未审计划",
                     ["backend/result.txt"], revision=record["revision"])
    elif change == "scope":
        agents.update(conn, proj, "writer", {"scope": ["S1-2"]}, by="人")
    elif change == "claim":
        claims.release(conn, "S1-1", "S2-1", "agent:writer")
    elif change == "project":
        store._set_meta(conn, workorders.PAUSE, "人叫停")
    elif change == "employee":
        agents.update(conn, proj, "writer", {"paused": True}, by="人")
    else:
        agents.update(conn, proj, "writer", {"roles": ["审核"]}, by="人")
    with pytest.raises(store.Refused, match=reason):
        _deliver(proj, conn)
    assert deliveries.list_all(proj) == []
    assert claims.holds_core(conn, "agent:writer")


@pytest.mark.parametrize("passed", [True, False])
def test_real_mcp_receipt_reports_automatic_result_without_human_wait(proj, setup, passed):
    import anyio
    from test_automation_mcp import call
    conn, _ = setup
    _policy(proj)
    results = anyio.run(call, proj, "writer", [("deliver", {
        "goal": "S1-1", "sub": "S2-1", "did": "实际核验后如实交付",
        "checks": [{"name": "实际检查", "ok": passed, "detail": "真实通过" if passed else "真实失败"}],
        "files": ["backend/result.txt"],
    })])
    error, receipt = results[0]
    assert not error and "没交" not in receipt
    j = deliveries.get(proj, "J1")
    assert j["state"] == ("验收通过" if passed else "打回")
    assert j["self_checks_passed"] is passed
    assert "待你验收" not in receipt and "等验收" not in receipt
    assert claims.of(conn, "agent:writer") == []
    if passed:
        assert "检查全过" in receipt and "做完" in receipt
    else:
        assert "自动打回返工" in receipt and "重新交付" in receipt
        assert "检查全过" not in receipt and "默认通过" not in receipt
