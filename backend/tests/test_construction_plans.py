"""施工计划关的真实文件、独立审核、范围与版本冲突。只使用临时项目。"""
from pathlib import Path

import pytest

import agents
import claims
import construction_plans as plans
import store
import workorders


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def setup(proj):
    _write(proj.root / "治理/目标/S1-8 转得起来.md",
           "# S1-8 转得起来\n\n**实际跑通。**\n\n动到的模块：文献\n\n"
           "| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"
           "| S2-45 | 工种派活 | 项目::需-4 | 错工种领不到、正确工种领到 | 没做 |\n"
           "| S2-46 | 计划审核 | 项目::需-4 | 未审不能交付 | 没做 |\n")
    _write(proj.root / "治理/需求/项目.md",
           "# 项目需求\n\n| | 要什么功能 | 要什么效果 | 来自 | 关联目标 | 承接模块 |\n"
           "|---|---|---|---|---|---|\n| 需-4 | 自动推进 | 审核后施工 | 作者原话 | S1-8 | 文献 |\n")
    (proj.root / "backend").mkdir()
    conn = store.connect(proj.db_path)
    agents.create(conn, proj, "writer", "写代码的", program="Codex（gpt-6-sol）", roles=["干活", "审核"])
    agents.create(conn, proj, "reviewer", "审核的", program="Codex")
    agents.create(conn, proj, "other-reviewer", "审核的")
    yield conn
    conn.close()


def _submit(conn, proj, **kw):
    return plans.submit(conn, proj, "S1-8", "S2-45", "agent:writer",
                        kw.pop("text", "按要求修正派活，回归验证错误工种被拒绝。"),
                        kw.pop("files", ["backend/dispatch.py"]), rules=["通-13", "项-10"], **kw)


def _approve(conn, proj, record):
    return plans.review(conn, proj, record["code"], "agent:reviewer", True, "范围符合任务，验证能覆盖派活", record["revision"])


def _required(monkeypatch, proj, names=("writer",)):
    original = agents.find

    def find(p, key):
        prof = original(p, key)
        return dict(prof, plan_required=True) if prof and prof["name"] in names else prof

    monkeypatch.setattr(agents, "find", find)


def test_record_identity_provenance_and_no_index_dependency(proj, setup):
    d = _submit(setup, proj)
    assert d["by"] == "agent:writer" and d["employee"] == "G1" and d["model"] == "gpt-6-sol"
    assert d["state"] == plans.WAIT and d["how"] == "错工种领不到、正确工种领到"
    assert d["requirements"][0]["func"] == "自动推进"
    assert d["requirement_refs"] == ["%E9%A1%B9%E7%9B%AE::需-4"]
    assert d["rules"] == ["通-13", "项-10"] and d["revision"]
    assert plans.get(proj, d["code"]) == plans.listing(proj)[0]
    assert (proj.root / d["file"]).suffix == ".md"
    assert "agent:writer" in (proj.root / d["file"]).read_text(encoding="utf-8")


def test_submit_without_rules_uses_existing_layered_rule_paths(proj, setup):
    paths = ["治理/戒律/1 通用戒律.md", "治理/戒律/2 项目戒律.md", "治理/戒律/模块/文献.md"]
    for path in paths:
        _write(proj.root / path, "# 适用戒律\n\n已有规则原文。")
    d = plans.submit(setup, proj, "S1-8", "S2-45", "writer", "按照现存戒律施工。", ["backend/dispatch.py"])
    assert d["rules"] == paths and d["missing_rules"] == []
    assert d["rules_source"] == "项目现存适用戒律记录"
    d = _approve(setup, proj, d)
    first_line = (proj.root / d["formal_path"]).read_text(encoding="utf-8").splitlines()[0]
    assert all(path in first_line for path in paths) and "未填写" not in first_line


def test_missing_rule_records_are_reported_without_invention(proj, setup):
    _write(proj.root / "治理/戒律/1 通用戒律.md", "# 通用戒律\n\n只有已保存的一层。")
    d = plans.submit(setup, proj, "S1-8", "S2-45", "writer", "补齐派活测试。", ["backend/dispatch.py"])
    assert d["rules"] == ["治理/戒律/1 通用戒律.md"]
    assert d["missing_rules"] == ["项目戒律记录", "模块 文献戒律记录"]
    assert plans.get(proj, d["code"])["missing_rules"] == d["missing_rules"]
    d = _approve(setup, proj, d)
    first_line = (proj.root / d["formal_path"]).read_text(encoding="utf-8").splitlines()[0]
    assert "缺少：项目戒律记录、模块 文献戒律记录" in first_line


def test_self_review_role_and_revision_rejected(proj, setup):
    d = _submit(setup, proj)
    with pytest.raises(store.Refused, match="自己"):
        plans.review(setup, proj, d["code"], "writer", True, "想自审", d["revision"])
    agents.create(setup, proj, "worker", "写代码的")
    with pytest.raises(store.Refused, match="岗位"):
        plans.review(setup, proj, d["code"], "worker", True, "并非审核岗", d["revision"])
    with pytest.raises(store.Refused, match="版本"):
        plans.review(setup, proj, d["code"], "reviewer", True, "版本过时", "stale")
    assert plans.get(proj, d["code"])["state"] == plans.WAIT


def test_formal_number_uses_legacy_and_central_history(proj, setup):
    _write(proj.root / "计划/S1-8 转得起来/P8 · 2026-09-30 · 历史.md", "历史正本原文")
    _write(proj.root / "治理/计划/S1-8 转得起来/P7 · 2026-10-01 · 最近.md", "最近正本")
    d = _approve(setup, proj, _submit(setup, proj))
    assert "/P9 · " in d["formal_path"] and d["state"] == plans.OK
    assert d["approved_files"] == ["backend/dispatch.py"]
    text = (proj.root / d["formal_path"]).read_text(encoding="utf-8")
    assert "状态：审核通过" in text and "审核：agent:reviewer" in text
    assert "怎么验：错工种领不到、正确工种领到" in text
    assert (proj.root / "计划/S1-8 转得起来/P8 · 2026-09-30 · 历史.md").read_text(encoding="utf-8") == "历史正本原文"
    assert plans.approved(proj, "S1-8", "S2-45", "writer")["code"] == d["code"]


def test_rejection_revision_and_scope_changes_need_new_approval(proj, setup, monkeypatch):
    _required(monkeypatch, proj)
    d = _submit(setup, proj)
    with pytest.raises(store.Refused, match="尚未通过"):
        plans.require_approved(proj, "S1-8", "S2-45", "writer", ["backend/dispatch.py"])
    d = plans.review(setup, proj, d["code"], "reviewer", False, "补上模块范围回归", d["revision"])
    assert d["state"] == plans.NO
    d = _submit(setup, proj, revision=d["revision"], text="补上负责模块范围回归。")
    d = _approve(setup, proj, d)
    first_formal = d["formal_path"]
    plans.require_approved(proj, "S1-8", "S2-45", "writer", ["backend/dispatch.py"])
    with pytest.raises(store.Refused, match="不在审核通过"):
        plans.require_approved(proj, "S1-8", "S2-45", "writer", ["backend/agents.py"])
    with pytest.raises(store.Refused, match="版本"):
        _submit(setup, proj, files=["backend/"], revision="old-revision")
    d = _submit(setup, proj, files=["backend/"], revision=d["revision"])
    assert d["state"] == plans.WAIT and plans.approved(proj, "S1-8", "S2-45", "writer") is None
    with pytest.raises(store.Refused, match="尚未通过"):
        plans.require_approved(proj, "S1-8", "S2-45", "writer")
    d = _approve(setup, proj, d)
    assert first_formal != d["formal_path"] and (proj.root / first_formal).is_file()
    plans.require_approved(proj, "S1-8", "S2-45", "writer", ["backend/agents.py"])
    assert [h["act"] for h in d["history"]] == ["提交", "打回", "修订", "通过", "修订", "通过"]


@pytest.mark.parametrize("path", ["../other.py", "C:/outside.py", "/outside.py", "backend/../other.py", "backend//x.py",
                                 "索引/state.db", "回收站/a.md", "存档/a.md", "笔记/总览.md", "笔记/历史/old.md", ".git/config", "backend/*.py"])
def test_invalid_or_protected_paths_are_not_saved(proj, setup, path):
    with pytest.raises(store.Refused):
        _submit(setup, proj, files=[path])
    assert plans.listing(proj) == []


@pytest.mark.parametrize("path", ["笔记 /a.md", "笔记./a.md", "backend/x.py:other-stream", "backend/NUL.txt"])
def test_windows_path_aliases_cannot_bypass_protected_directories(proj, setup, path):
    with pytest.raises(store.Refused):
        _submit(setup, proj, files=[path])


def test_folder_boundary_and_human_notes_cannot_be_bypassed(proj, setup, monkeypatch):
    _required(monkeypatch, proj)
    _approve(setup, proj, _submit(setup, proj, files=["backend/"]))
    with pytest.raises(store.Refused, match="不在审核通过"):
        plans.require_approved(proj, "S1-8", "S2-45", "writer", ["backend-extra/a.py"])
    assert plans.normalize_files(proj, ["笔记/日志/2026-10.md"]) == ["笔记/日志/2026-10.md"]


def test_formal_or_blueprint_changes_invalidate_approval(proj, setup, monkeypatch):
    _required(monkeypatch, proj)
    d = _approve(setup, proj, _submit(setup, proj))
    with (proj.root / d["formal_path"]).open("a", encoding="utf-8") as f:
        f.write("\n新增修改范围，未经审核。")
    assert plans.approved(proj, "S1-8", "S2-45", "writer") is None
    d = _submit(setup, proj, revision=d["revision"])
    d = _approve(setup, proj, d)
    bp = proj.root / "治理/目标/S1-8 转得起来.md"
    _write(bp, bp.read_text(encoding="utf-8").replace("错工种领不到、正确工种领到", "新增权限验收要求"))
    assert plans.approved(proj, "S1-8", "S2-45", "writer") is None
    with pytest.raises(store.Refused, match="尚未通过"):
        plans.require_approved(proj, "S1-8", "S2-45", "writer")


def test_linked_requirement_content_change_invalidates_approval(proj, setup, monkeypatch):
    _required(monkeypatch, proj)
    _approve(setup, proj, _submit(setup, proj))
    needs = proj.root / "治理/需求/项目.md"
    _write(needs, needs.read_text(encoding="utf-8").replace("审核后施工", "审核且需独立验收后继续"))
    assert plans.approved(proj, "S1-8", "S2-45", "writer") is None
    with pytest.raises(store.Refused, match="尚未通过"):
        plans.require_approved(proj, "S1-8", "S2-45", "writer")


@pytest.mark.parametrize("fields,reason", [({"paused": True}, "暂停"), ({"roles": ["审核"]}, "干活岗位"), ({"scope": ["S1-9"]}, "负责范围")])
def test_changed_employee_permission_invalidates_previous_approval(proj, setup, monkeypatch, fields, reason):
    _required(monkeypatch, proj)
    _approve(setup, proj, _submit(setup, proj))
    agents.update(setup, proj, "writer", fields, by="人")
    assert plans.approved(proj, "S1-8", "S2-45", "writer") is None
    with pytest.raises(store.Refused, match=reason):
        plans.require_approved(proj, "S1-8", "S2-45", "writer")


def test_new_requirements_cannot_be_approved_using_stale_submission(proj, setup):
    d = _submit(setup, proj)
    bp = proj.root / "治理/目标/S1-8 转得起来.md"
    _write(bp, bp.read_text(encoding="utf-8").replace("错工种领不到、正确工种领到", "还要检查范围"))
    with pytest.raises(store.Refused, match="已变化"):
        _approve(setup, proj, d)
    assert plans.get(proj, d["code"])["state"] == plans.WAIT


def test_pause_and_exclusive_review_claims(proj, setup):
    d = _submit(setup, proj)
    assert plans.next_review(setup, proj, "writer") is None  # 不审自己的
    store._set_meta(setup, workorders.PAUSE, "人在网页叫停")
    assert plans.next_review(setup, proj, "reviewer") is None
    assert claims.active(setup) == []
    with pytest.raises(store.Refused, match="叫停"):
        _approve(setup, proj, d)
    workorders.resume(setup)
    assert plans.next_review(setup, proj, "reviewer")["code"] == d["code"]
    assert plans.next_review(setup, proj, "other-reviewer") is None
    with pytest.raises(store.Refused, match="其他员工"):
        plans.review(setup, proj, d["code"], "other-reviewer", True, "不抢别人的", d["revision"])
    _approve(setup, proj, d)
    assert claims.active(setup) == []
    assert plans.next_review(setup, proj, "reviewer") is None


def test_unmanaged_old_profile_preserves_old_delivery_behavior(proj, setup):
    assert plans.require_approved(proj, "S1-8", "S2-45", "writer", ["backend/dispatch.py"]) is None
    assert plans.require_approved(proj, "legacy", "S2-1", "not-registered") is None


def test_manual_draft_scope_or_text_change_also_needs_reapproval(proj, setup, monkeypatch):
    _required(monkeypatch, proj)
    d = _approve(setup, proj, _submit(setup, proj))
    f = proj.root / d["file"]
    _write(f, f.read_text(encoding="utf-8").replace('"backend/dispatch.py"', '"backend/agents.py"'))
    assert plans.approved(proj, "S1-8", "S2-45", "writer") is None
    with pytest.raises(store.Refused, match="尚未通过"):
        plans.require_approved(proj, "S1-8", "S2-45", "writer", ["backend/agents.py"])


def test_two_authors_of_same_task_have_independent_plans(proj, setup):
    agents.create(setup, proj, "another-worker", "写代码的")
    first = _submit(setup, proj)
    second = plans.submit(setup, proj, "S1-8", "S2-45", "another-worker", "接手后的另一份计划", ["backend/agents.py"])
    assert first["code"] != second["code"]
    _approve(setup, proj, first)
    assert plans.approved(proj, "S1-8", "S2-45", "another-worker") is None


def test_review_model_snapshot_survives_profile_and_plan_revisions(proj, setup):
    agents.update(setup, proj, "reviewer", {"program": "Codex（review-model-a）"}, by="人")
    assert agents.get(proj, "reviewer")["program"] == "Codex（review-model-a）"
    d = _submit(setup, proj)
    revision = d["revision"]
    d = plans.review(setup, proj, d["code"], "reviewer", False, "补检查", revision)
    assert d["reviewer_model"] == d["history"][-1]["reviewer_model"] == "review-model-a"
    assert d["reviewed_revision"] == d["history"][-1]["reviewed_revision"] == revision
    assert d["reviewer_employee"] == "G2" and d["reviewed"] == d["history"][-1]["at"]
    assert not d["formal_path"] and not list((proj.root / "治理/计划").rglob("P*.md"))
    d = _submit(setup, proj, revision=d["revision"])
    assert not d["reviewer_model"] and not d["reviewer"] and not d["reviewed_revision"]
    d = _approve(setup, proj, d)
    first_path = proj.root / d["formal_path"]
    first_bytes = first_path.read_bytes()
    assert "审核：agent:reviewer · 模型：review-model-a" in first_bytes.decode("utf-8")
    assert d["reviewed_revision"] in first_bytes.decode("utf-8")
    agents.update(setup, proj, "reviewer", {"program": "Codex（review-model-b）"}, by="人")
    assert plans.approved(proj, "S1-8", "S2-45", "writer")["reviewer_model"] == "review-model-a"
    d = _submit(setup, proj, revision=d["revision"])
    assert not d["formal_path"] and first_path.read_bytes() == first_bytes
    d = _approve(setup, proj, d)
    assert [h["reviewer_model"] for h in d["history"] if h["act"] in (plans.OK, plans.NO)] == ["review-model-a", "review-model-a", "review-model-b"]
    assert "模型：review-model-b" in (proj.root / d["formal_path"]).read_text(encoding="utf-8")
    assert first_path.read_bytes() == first_bytes


def test_default_model_and_legacy_approval_remain_truthful(proj, setup):
    d = _approve(setup, proj, _submit(setup, proj))
    assert d["reviewer_model"] == "沿用员工当前默认模型（档案未指定）"
    # 复原旧版落盘格式及旧签名，模拟从未记录过审核模型的历史。
    for k in ("reviewer_model", "reviewer_employee", "reviewed_revision"):
        d.pop(k)
    for h in d["history"]:
        h.pop("reviewer_model", None)
        h.pop("reviewer_employee", None)
    raw = b"# Legacy approved plan\n"
    formal = proj.root / d["formal_path"]
    formal.write_bytes(raw)
    d["formal_revision"] = plans._digest(raw)
    d["approval_signature"] = plans._approval_signature(d)
    plans._write(proj.root / d["file"], d)
    agents.update(setup, proj, "reviewer", {"program": "Codex（later-model）"}, by="人")
    d = plans.approved(proj, "S1-8", "S2-45", "writer")
    assert d and "reviewer_model" not in d and "reviewer_model" not in d["history"][-1]
    assert formal.read_bytes() == raw


@pytest.mark.parametrize("field", ["reviewer_model", "reviewer", "reviewed_revision", "why"])
def test_new_approval_rejects_edited_review_metadata(proj, setup, field):
    d = _approve(setup, proj, _submit(setup, proj))
    d[field] = "changed"
    plans._write(proj.root / d["file"], d)
    assert plans.approved(proj, "S1-8", "S2-45", "writer") is None


def test_removing_new_review_metadata_cannot_restore_approval(proj, setup):
    d = _approve(setup, proj, _submit(setup, proj))
    d.pop("reviewer_model")
    plans._write(proj.root / d["file"], d)
    assert plans.approved(proj, "S1-8", "S2-45", "writer") is None
