"""用真实临时项目审核计划并验证只读工作包，不派活、不运行程序、不改正本。"""
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

import agents
import claims
import construction_plans as plans
import deliveries
import dispatch
import skills
import store
import work_packages as packages
import workorders
from record_refs import Snapshot


def write(root, source, text):
    f = root / source
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


def goal(root, code="S1-1", needs="项目::需-1、业务甲::需-1", modules="业务甲", sub="S2-1"):
    return write(root, f"治理/目标/{code} 软件.md",
                 f"# {code} 软件\n\n**作者的目标原话。**\n\n怎么算做到：亲眼看见真实结果。\n动到的模块：{modules}\n"
                 "| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"
                 f"| {sub} | 修改工具界面 | {needs} | 真读材料不派活、不写正本 | 没做 |\n")


@pytest.fixture
def setup(proj, monkeypatch, tmp_path):
    monkeypatch.setenv("RC_HOME", str(tmp_path / "假用户"))
    write(proj.root, "AGENTS.md", "# 接手\n作者限定的接手原话。")
    write(proj.root, "治理/目标/S0 终极目标.md", "# S0 终极目标\n\n**先让作者看懂。**\n")
    goal(proj.root)
    goal(proj.root, "S1-2", needs="业务乙::需-1", modules="业务乙")
    for module in ("业务甲", "业务乙"):
        (proj.root / "资料" / module).mkdir(parents=True)
        write(proj.root, f"治理/戒律/模块/{module}.md", "# 模块戒律\n该模块的原始规则。")
    for layer in ("1 通用", "2 项目"):
        write(proj.root, f"治理/戒律/{layer}戒律.md", "# " + layer + "\n必须守原话。")
    for scope, func, module in (("项目", "项目作者原话", "业务甲"), ("业务甲", "甲需求原话", "业务甲"), ("业务乙", "乙需求原话", "业务乙")):
        write(proj.root, f"治理/需求/{scope}.md", "# 需求\n\n"
              "| | 要什么功能 | 要什么效果 | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n"
              f"| 需-1 | {func} | 本范围内可验 | 作者原话，不替代来源文件 | S1-1 | {module} |\n")
    write(proj.root, "backend/example.py", '"""合成测试源码。"""\nprint("不会执行")\n')
    conn = store.connect(proj.db_path)
    agents.create(conn, proj, "writer", "写代码的", program="Codex", roles=["干活"])
    agents.create(conn, proj, "reviewer", "审核的", program="Codex", roles=["审核"])
    yield conn
    conn.close()


def approve(conn, p, *, author="writer", files=None, sub="S2-1"):
    record = plans.submit(conn, p, "S1-1", sub, author, "依据作者目标整理只读材料。", files or ["backend/example.py", "backend/new.py"], rules=["治理/戒律/1 通用戒律.md"])
    return plans.review(conn, p, record["code"], "reviewer", True, "独立核验真实任务和文件范围", record["revision"])


def fingerprints(root):
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in root.rglob("*") if f.is_file()}


def assert_business_bytes_unchanged(before, after):
    assert before.keys() == after.keys(), "读包不得创建或移除任何文件"
    changed = {name for name in before if before[name] != after[name]}
    assert changed <= {"索引/state.db-shm"}, "只能由 SQLite 更新现存共享缓存的临时读标记"
    return changed


def test_source_scoped_requirements_tasks_and_full_rule_originals(proj, setup):
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert package["schema"] == 1 and package["read_only"]
    needs = package["requirements"]
    assert {q["func"] for q in needs} == {"项目作者原话", "甲需求原话"}
    assert len({q["ref"]["identity"] for q in needs}) == 2
    assert {q["ref"]["code"] for q in needs} == {"需-1"}
    other = packages.build(setup, proj, "S1-2", "S2-1")
    assert other["task"]["ref"]["identity"] != package["task"]["ref"]["identity"]
    assert {q["func"] for q in other["requirements"]} == {"乙需求原话"}
    assert {r["layer"] for r in package["rules"]} == {"接手", "通用", "项目", "模块"}
    assert all(r["document"]["complete"] for r in package["rules"])
    assert "作者的目标原话" in package["prompt"] and "该模块的原始规则" in package["prompt"]
    assert package["selected_plan"] is None and package["allowed_files"] == []


def test_real_independent_approval_exact_files_new_file_metadata_and_no_execution(proj, setup, monkeypatch):
    record = approve(setup, proj)
    (proj.root / ".git").mkdir()
    def forbidden(*args, **kw):
        raise AssertionError("只读包不能派活、认领、开工、启动或运行程序")
    for module, names in [(dispatch, ["next_task"]), (claims, ["claim"]), (workorders, ["start"]), (agents, ["launcher"]), (subprocess, ["run", "Popen"])]:
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)
    before = fingerprints(proj.root)
    changes = setup.total_changes
    statements = []
    setup.set_trace_callback(statements.append)
    first = packages.build(setup, proj, "S1-1", "S2-1", plan_code=record["code"])
    second = packages.build(setup, proj, "S1-1", "S2-1", plan_code=record["code"])
    setup.set_trace_callback(None)
    assert first["selected_plan"]["revision"] == record["revision"]
    assert first["selected_plan"]["by"] == "agent:writer"
    assert first["allowed_files"] == record["files"]
    assert first["readiness"] == dict(state="ready_to_read", plan_valid=True, context_complete=True, gaps=[],
                                       warnings=["时间记录仅含项目已保存记录；本包未读取本机 Git", "戒律和技能显示当前正文版本；施工计划签名未覆盖全部上下文正文"], execution_authorized=False)
    assert first["context_files"][0]["document"]["text"] == ""
    assert not first["context_files"][0]["content_loaded"] and first["context_files"][1]["planned_new"]
    assert first["snapshot"]["digest"] == second["snapshot"]["digest"]
    assert first["snapshot"]["consistent"] and first["snapshot"]["retries"] == 0
    assert "复制不等于开工" in first["prompt"] and "本人员工身份" in first["prompt"]
    assert first["task"]["timeline_source"] == "saved_project_records"
    assert setup.total_changes == changes and fingerprints(proj.root) == before
    assert statements and all(s.lstrip().upper().startswith("SELECT ") for s in statements)


@pytest.mark.parametrize("change", ["formal", "goal", "need", "scope", "paused", "roles", "crafts"])
def test_changed_approval_or_employee_permissions_never_keep_allowed_files(proj, setup, change):
    record = approve(setup, proj)
    if change == "formal":
        f = proj.root / record["formal_path"]
        f.write_text(f.read_text(encoding="utf-8") + "\n人工改动", encoding="utf-8")
    elif change == "goal":
        goal(proj.root, needs="项目::需-1", modules="业务乙")
    elif change == "need":
        f = proj.root / "治理/需求/项目.md"
        f.write_text(f.read_text(encoding="utf-8").replace("项目作者原话", "修改后的方向"), encoding="utf-8")
    elif change == "scope":
        current = plans.get(proj, record["code"])
        current["files"].append("backend/another.py")
        plans._write(proj.root / current["file"], current)
    else:
        f = proj.root / "自动化/agent" / agents.find(proj, "writer")["file"]
        text = f.read_text(encoding="utf-8")
        if change == "paused":
            text = text.replace("暂停: 关", "暂停: 开")
        elif change == "roles":
            text = text.replace("岗位: 干活", "岗位: 审核")
        elif change == "crafts":
            text = text.replace("工种:", "工种: 翻译")
            fgoal = proj.root / "治理/目标/S1-1 软件.md"
            fgoal.write_text(fgoal.read_text(encoding="utf-8").replace("修改工具界面", "〔程序〕修改工具界面"), encoding="utf-8")
        f.write_text(text, encoding="utf-8")
    package = packages.build(setup, proj, "S1-1", "S2-1", plan_code=record["code"])
    assert not package["readiness"]["plan_valid"] and package["selected_plan"] is None
    assert package["allowed_files"] == []
    assert not package["execution_plans"][0]["valid"]
    assert "不准据此直接施工" in package["prompt"]


def test_multiple_authors_require_explicit_selection_and_wrong_code_has_no_range(proj, setup):
    first = approve(setup, proj)
    agents.create(setup, proj, "second-writer", "写代码的")
    second = approve(setup, proj, author="second-writer", files=["backend/example.py"])
    auto = packages.build(setup, proj, "S1-1", "S2-1")
    assert len(auto["execution_plans"]) == 2 and auto["selected_plan"] is None and auto["allowed_files"] == []
    assert any("多份" in g for g in auto["readiness"]["gaps"])
    explicit = packages.build(setup, proj, "S1-1", "S2-1", plan_code=second["code"])
    assert explicit["selected_plan"]["by"] == "agent:second-writer"
    wrong = packages.build(setup, proj, "S1-1", "S2-1", plan_code="施-999")
    assert wrong["selected_plan"] is None and wrong["allowed_files"] == []


def test_same_author_another_approved_record_cannot_endorse_selected_code(proj, setup):
    first = approve(setup, proj)
    # 合成历史同作者并存记录，真实 approved 会返回第一张；新包必须检查同 code/revision/by。
    clone = plans.get(proj, first["code"])
    clone.update(code="施-99", files=["backend/private.py"])
    clone["approval_signature"] = plans._approval_signature(clone)
    plans._write(proj.root / "自动化/施工计划/施-99.md", clone)
    package = packages.build(setup, proj, "S1-1", "S2-1", plan_code="施-99")
    assert package["selected_plan"] is None and package["allowed_files"] == []
    assert not next(p for p in package["execution_plans"] if p["code"] == "施-99")["valid"]


@pytest.mark.parametrize("relation", ["", "未关联", "待确认 项目::需-1", "我猜业务甲::需-1"])
def test_unlinked_or_unconfirmed_requirements_are_not_inferred(proj, setup, relation):
    goal(proj.root, needs=relation)
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert package["requirements"] == [] and package["task"]["needs_full"] == []
    assert any("需求" in g for g in package["readiness"]["gaps"])


def test_removed_module_retains_requirement_and_reports_unavailable(proj, setup):
    (proj.root / "资料/业务甲").rmdir()
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert {q["func"] for q in package["requirements"]} == {"项目作者原话", "甲需求原话"}
    assert all(q["missing_modules"] == ["业务甲"] for q in package["requirements"])


def test_no_git_missing_index_project_does_not_create_tables_or_files(proj, setup):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    before = fingerprints(proj.root)
    statements = []
    connection.set_trace_callback(statements.append)
    package = packages.build(connection, proj, "S1-1", "S2-1")
    assert package["task"] and not package["task"]["ownership_known"]
    assert any("索引" in g for g in package["readiness"]["gaps"])
    assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    assert not any(s.lstrip().upper().startswith("CREATE") for s in statements)
    assert fingerprints(proj.root) == before and not (proj.root / ".git").exists()
    connection.close()


def test_sql_wrapper_rejects_other_writes_and_only_skips_exact_claim_ddl():
    db = sqlite3.connect(":memory:")
    wrapper = packages.ReadOnlyConnection(db)
    wrapper.execute(claims._TABLE)
    for sql in ["CREATE TABLE fake(x)", "UPDATE claim SET agent='fake'", "DELETE FROM claim", "INSERT INTO claim VALUES(1)", "BEGIN", "PRAGMA journal_mode=WAL", "SELECT 1; DELETE FROM claim"]:
        with pytest.raises(ValueError):
            wrapper.execute(sql)
    assert db.execute("SELECT name FROM sqlite_master").fetchall() == []
    db.close()


def test_delivery_failure_and_wait_states_preserve_actual_checks(proj, setup):
    for n, state, check in [(1, "打回", "没过"), (2, "等验收", "过了"), (3, "待你验收", "过了"), (4, "验收通过", "过了")]:
        write(proj.root, f"自动化/交付/J{n} 原文.md", f"---\n编号: J{n}\n目标: S1-1\n小目标: S2-1\n状态: {state}\n谁: agent:writer\n时间: 2026-10-01 12:0{n}\n---\n# 交付\n\n## 怎么验的\n\n- {check} · 实测：真实结果{n}\n")
    write(proj.root, "自动化/交付/J9 其他任务.md", "---\n编号: J9\n目标: S1-2\n小目标: S2-1\n状态: 验收通过\n---\n别的目标不能串入。")
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert {j["state"] for j in package["deliveries"]} == {"打回", "等验收", "待你验收", "验收通过"}
    assert next(j for j in package["deliveries"] if j["code"] == "J1")["self_checks_passed"] is False
    assert all(j["code"] != "J9" for j in package["deliveries"])
    assert "真实结果1" in package["prompt"] and "别的目标不能串入" not in package["prompt"]


def test_selected_local_skills_language_no_default_and_changes(proj, setup):
    write(proj.root, "技能库/甲/SKILL.md", "---\nname: 同名\ndescription: 中文原话\n---\n# 中文材料")
    english = write(proj.root, "技能库/甲/SKILL.en.md", "---\nname: Shared\ndescription: English\n---\n# English material")
    write(proj.root, "技能库/乙/SKILL.md", "---\nname: 同名\ndescription: 另一正文\n---\n# 乙正文")
    assert packages.build(setup, proj, "S1-1", "S2-1")["skills"] == []
    selected = packages.build(setup, proj, "S1-1", "S2-1", skill_ids=["甲"], lang="en-US")
    assert selected["skills"][0]["language"] == "en" and "English material" in selected["prompt"]
    assert selected["skills"][0]["execution_state"] == "未运行" and not selected["skills"][0]["executed"]
    ambiguous = packages.build(setup, proj, "S1-1", "S2-1", skill_ids=["同名"])
    assert ambiguous["skills"][0]["reference_state"] == "missing"
    english.write_text("# Changed English material", encoding="utf-8")
    changed = packages.build(setup, proj, "S1-1", "S2-1", skill_ids=["甲"], lang="en-US")
    assert changed["skills"][0]["ref"]["revision"] != selected["skills"][0]["ref"]["revision"]
    assert changed["snapshot"]["digest"] != selected["snapshot"]["digest"]


def test_work_package_skill_never_probes_actual_machine_or_project_installed_copies(proj, setup, monkeypatch, tmp_path):
    import shutil
    source = "技能库/甲/SKILL.md"
    original = write(proj.root, source, "---\nname: 甲\ndescription: 正本\n---\n# 正本材料")
    machine = tmp_path / "假用户/.claude/skills/甲"
    project = proj.root / ".claude/skills/甲"
    for destination in (machine, project):
        shutil.copytree(original.parent, destination)
    installed = skills.read(proj, "甲")
    assert installed["machine"] == installed["project"] == "same"
    first = packages.build(setup, proj, "S1-1", "S2-1", skill_ids=["甲"])
    for destination in (machine, project):
        (destination / "SKILL.md").write_text("# 安装副本被改动", encoding="utf-8")
    installed = skills.read(proj, "甲")
    assert installed["machine"] == installed["project"] == "different"
    def forbidden(*args, **kwargs):
        raise AssertionError("工作包不应探测本机或已安装技能副本")
    for name in ("_public", "status_of", "target_base", "machine_home"):
        monkeypatch.setattr(skills, name, forbidden)
    second = packages.build(setup, proj, "S1-1", "S2-1", skill_ids=["甲"])
    assert first["snapshot"]["consistent"] and second["snapshot"]["consistent"]
    assert first["snapshot"]["digest"] == second["snapshot"]["digest"]
    assert first["skills"] == second["skills"]
    selected = second["skills"][0]
    assert selected["reference_state"] == "ok" and "正本材料" in selected["text"]
    assert not selected["installation_status_checked"] and selected["installation_status"] == "not_checked"
    assert "machine" not in selected and "project" not in selected
    assert all(".claude" not in row["source"] for row in second["snapshot"]["sources"])


def test_oversize_legacy_requirement_prevents_complete_work_package(proj, setup):
    import record_refs
    legacy = write(proj.root, "资料/业务甲/需求.md", "")
    with legacy.open("wb") as stream:
        stream.truncate(record_refs.MAX_HASH_BYTES + 1)
    package = packages.build(setup, proj, "S1-1", "S2-1")
    requirement = next(row for row in package["requirements"] if row["scope"] == "业务甲")
    assert requirement["reference_state"] == "conflict_unverifiable"
    assert requirement["document"]["body_complete"] and not requirement["document"]["complete"]
    assert requirement["unverified_sources"][0]["source"] == "资料/业务甲/需求.md"
    assert not package["readiness"]["context_complete"] and package["snapshot"]["consistent"]
    assert any("需求" in gap for gap in package["readiness"]["gaps"])


def test_missing_skill_and_invalid_inputs_explicit(proj, setup):
    package = packages.build(setup, proj, "S1-1", "S2-1", skill_ids=["missing"])
    assert package["skills"][0]["reference_state"] == "missing"
    assert any("所选技能" in g for g in package["readiness"]["gaps"])
    for options in [dict(plan_code="P1"), dict(skill_ids="甲"), dict(lang="python")]:
        with pytest.raises(ValueError):
            packages.build(setup, proj, "S1-1", "S2-1", **options)
    missing = packages.build(setup, proj, "S1-1", "S2-404")
    assert missing["task"] is None and missing["readiness"]["gaps"]


def test_whole_package_retries_once_then_discards_mixed_content(proj, setup, monkeypatch):
    original = Snapshot.validate
    count = 0
    def changing(snapshot):
        nonlocal count
        count += 1
        goal(proj.root, needs="项目::需-1" if count == 1 else "业务甲::需-1")
        return original(snapshot)
    monkeypatch.setattr(Snapshot, "validate", changing)
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert count == 2 and package["snapshot"]["retries"] == 1
    assert package["readiness"]["state"] == "inconsistent"
    assert package["task"] is None and package["requirements"] == [] and package["allowed_files"] == []
    assert not package["snapshot"]["consistent"]


def test_single_change_is_rebuilt_with_new_body_and_versions(proj, setup, monkeypatch):
    original = Snapshot.validate
    count = 0
    def change_once(snapshot):
        nonlocal count
        count += 1
        if count == 1:
            goal(proj.root, needs="业务乙::需-1", modules="业务乙")
        return original(snapshot)
    monkeypatch.setattr(Snapshot, "validate", change_once)
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert count == 2 and package["snapshot"]["retries"] == 1 and package["snapshot"]["consistent"]
    assert {q["func"] for q in package["requirements"]} == {"乙需求原话"}
    assert package["task"]["ref"]["revision"] == hashlib.sha256((proj.root / "治理/目标/S1-1 软件.md").read_bytes()).hexdigest()


def test_rule_version_changes_are_context_versions_not_forged_plan_approval(proj, setup):
    record = approve(setup, proj)
    old = packages.build(setup, proj, "S1-1", "S2-1", plan_code=record["code"])
    f = proj.root / "治理/戒律/2 项目戒律.md"
    f.write_text("# 项目新戒律\n作者刚保存的正文。", encoding="utf-8")
    new = packages.build(setup, proj, "S1-1", "S2-1", plan_code=record["code"])
    before = next(r for r in old["rules"] if r["layer"] == "项目")
    after = next(r for r in new["rules"] if r["layer"] == "项目")
    assert before["ref"]["revision"] != after["ref"]["revision"]
    assert new["snapshot"]["digest"] != old["snapshot"]["digest"]
    assert new["selected_plan"]["revision"] == old["selected_plan"]["revision"]
    assert new["selected_plan"]["context_signature_scope"] == "existing_plan_signature_only"
    assert "未覆盖全部上下文正文" in new["prompt"] and "作者刚保存的正文" in new["prompt"]


def test_blocked_business_skill_preserves_document_and_dependencies_without_execution(proj, setup):
    directory = "技能库/业务/video/synthetic/blocked"
    write(proj.root, directory + "/SKILL.md", "---\nname: mh-video-synthetic-blocked\ndescription: 兼容性未通过\n---\n# 可读原话\n运行分支未启用。")
    write(proj.root, directory + "/LICENSE.txt", "Synthetic test license")
    row = {"id": "biz:video:synthetic:blocked", "kind": "skill", "business": "video", "stages": ["start"],
           "title": {"zh-CN": "仅可准备", "en": "Preparation only"}, "summary": {"zh-CN": "兼容性待处理"},
           "install_name": "mh-video-synthetic-blocked", "path": directory + "/SKILL.md",
           "languages": {"zh-CN": directory + "/SKILL.md"}, "license": {"id": "MIT", "files": [directory + "/LICENSE.txt"]},
           "source": {"url": "https://example.com/source", "commit": "a" * 40},
           "redistribution": {"status": "pending", "reason": "测试兼容性未通过"},
           "dependencies": [{"name": "Example Engine", "required": True, "status": "blocked", "reason": "版本不兼容"}]}
    write(proj.root, "技能库/业务/manifest.json", json.dumps({"schema": 1, "groups": [{"id": "video", "title": {"zh-CN": "剪辑"},
          "stages": [{"id": "start", "order": 1, "title": {"zh-CN": "开始"}}]}], "items": [row]}, ensure_ascii=False))
    package = packages.build(setup, proj, "S1-1", "S2-1", skill_ids=[row["id"]])
    selected = package["skills"][0]
    assert selected["id"] == row["id"] and "可读原话" in selected["text"]
    assert selected["dependencies"] == row["dependencies"]
    assert selected["issues"] and not selected["installable"] and not selected["executed"]
    assert any("技能配套" in gap for gap in package["readiness"]["gaps"])
    assert "运行分支未启用" in package["prompt"] and "版本不兼容" in package["prompt"]


def test_duplicate_goal_or_sub_codes_report_ambiguous_sources(proj, setup):
    goal(proj.root, code="S1-1")
    f = proj.root / "治理/目标/S1-1 软件.md"
    write(proj.root, "治理/目标/S1-1 另一来源.md", f.read_text(encoding="utf-8"))
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert package["task"] is None and any("不唯一" in g for g in package["readiness"]["gaps"])
    (proj.root / "治理/目标/S1-1 另一来源.md").unlink()
    text = f.read_text(encoding="utf-8")
    duplicate = next(line for line in text.splitlines() if line.startswith("| S2-1 |"))
    f.write_text(text + duplicate + "\n", encoding="utf-8")
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert package["task"] is None and any("不唯一" in g for g in package["readiness"]["gaps"])


def test_workorder_relation_uses_goal_sub_and_source_scoped_need(proj, setup):
    for n, target in [(1, "S1-1 S2-1"), (2, "S1-1"), (3, "S1-1 需-1"), (4, "S1-2 S2-1")]:
        write(proj.root, f"自动化/开工单/K{n} 开工.md", f"---\n编号: K{n}\n名字: 合成{n}\n状态: 备料\n目标: {target}\n开始: 2026-10-01 12:00\n---\n# 原文开工单{n}\n")
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert {w["code"] for w in package["workorders"]} == {"K1", "K2"}
    assert all("原文开工单" in w["document"]["text"] for w in package["workorders"])
    assert {t["detail"] for t in package["timeline"] if t["kind"] == "workorder"} == {"K1", "K2"}
    assert all(t["at"] == "2026-10-01 12:00" for t in package["timeline"] if t["kind"] == "workorder")


def test_unsafe_governance_junction_fails_closed_without_external_text(proj, setup, tmp_path):
    import os
    if os.name != "nt":
        pytest.skip("Windows 联接专项")
    external = tmp_path.parent / (tmp_path.name + "-outside")
    external.mkdir()
    write(external, "S1-99 外面.md", "绝不返回的外部秘密正文")
    link = proj.root / "治理/外部"
    process = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(external)], capture_output=True)
    assert process.returncode == 0
    package = packages.build(setup, proj, "S1-1", "S2-1")
    assert package["task"] is None and package["readiness"]["gaps"]
    assert "绝不返回的外部秘密正文" not in json.dumps(package, ensure_ascii=False)


def test_read_connection_missing_index_does_not_create_any_files(proj):
    before = fingerprints(proj.root)
    with packages.open_read_connection(proj) as conn:
        assert conn is None
        package = packages.build(conn, proj, "S1-1", "S2-1")
        assert package["readiness"]["gaps"]
    assert fingerprints(proj.root) == before and not proj.index_dir.exists()


def test_read_connection_cannot_write_and_preserves_database_wal_and_business_bytes(proj, setup):
    claims.active(setup)  # 初始化已有索引的测试夹具；读包本身不得补建。
    before = fingerprints(proj.root)
    with packages.open_read_connection(proj) as conn:
        assert conn is not None
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("CREATE TABLE should_not_exist(x)")
        package = packages.build(conn, proj, "S1-1", "S2-1")
        assert package["task"] and package["task"]["ownership_known"]
    assert_business_bytes_unchanged(before, fingerprints(proj.root))


def test_fresh_live_wal_read_returns_saved_event_despite_actual_shm_read_mark_change(proj, setup):
    claims.active(setup)
    store.log(setup, "agent:fresh", "领了", "S1-1 S2-1", "fresh existing WAL record")
    before = fingerprints(proj.root)
    assert before["索引/state.db-wal"] and before["索引/state.db-shm"]
    with packages.open_read_connection(proj) as reader:
        assert reader is not None
        first = packages.build(reader, proj, "S1-1", "S2-1")
        second = packages.build(reader, proj, "S1-1", "S2-1")
    changed = assert_business_bytes_unchanged(before, fingerprints(proj.root))
    assert changed == {"索引/state.db-shm"}, "真实首次 WAL SELECT 应触发旧实现误判的共享读标记变化"
    assert first["task"] and first["snapshot"]["consistent"] and second["snapshot"]["consistent"]
    assert "fresh existing WAL record" in json.dumps(first["task"], ensure_ascii=False)
    assert first["snapshot"]["digest"] == second["snapshot"]["digest"]
    cache = next(row for row in first["snapshot"]["sources"] if row["source"] == "index:索引/state.db-shm")
    assert cache["role"] == "sqlite_shared_cache" and not cache["content_fingerprint"]
    assert cache["version_basis"] == "ordinary_path_identity_only" and cache["revision"] == ""


def test_live_wal_without_shared_cache_is_unavailable_and_never_creates_cache(proj, setup, tmp_path):
    import shutil
    from project import Project
    claims.active(setup)
    store.log(setup, "agent:fresh", "领了", "S1-1 S2-1", "真实 WAL 配对")
    destination = tmp_path / "没有共享缓存的副本"
    index = destination / "索引"
    index.mkdir(parents=True)
    for suffix in ("", "-wal"):
        shutil.copyfile(Path(str(proj.db_path) + suffix), index / ("state.db" + suffix))
    copy = Project(destination)
    before = fingerprints(destination)
    with packages.open_read_connection(copy) as reader:
        assert reader is None
    assert fingerprints(destination) == before and not Path(str(copy.db_path) + "-shm").exists()


def test_read_connection_after_last_writer_closes_preserves_files(proj, setup):
    claims.active(setup)
    setup.close()
    before = fingerprints(proj.root)
    with packages.open_read_connection(proj) as conn:
        package = packages.build(conn, proj, "S1-1", "S2-1")
        assert package["task"] and package["task"]["ownership_known"]
    assert fingerprints(proj.root) == before


def test_new_wal_during_immutable_read_is_inconsistent_not_silently_ignored(proj, setup):
    claims.active(setup)
    setup.close()
    with packages.open_read_connection(proj) as reader:
        writer = store.connect(proj.db_path)
        store.log(writer, "agent:test", "领了", "S1-1 S2-1", "新 WAL 中的记录")
        package = packages.build(reader, proj, "S1-1", "S2-1")
        assert not package["snapshot"]["consistent"] and package["readiness"]["state"] == "inconsistent"
        assert package["task"] is None and package["allowed_files"] == []
        writer.close()


def test_oversize_wal_is_unavailable_instead_of_ignored_as_no_wal(proj, setup, monkeypatch):
    import record_refs
    claims.active(setup)
    monkeypatch.setattr(record_refs, "MAX_HASH_BYTES", 32)
    with packages.open_read_connection(proj) as conn:
        assert conn is None


def test_http_and_real_stdio_mcp_have_same_sources_and_preserve_business_files(proj, setup, monkeypatch, tmp_path):
    import sys
    import shutil
    import anyio
    from fastapi.testclient import TestClient
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Implementation
    from main import create_app
    from conftest import BACKEND
    record = approve(setup, proj)
    claims.active(setup)
    skill = write(proj.root, "技能库/接口验证/SKILL.md", "---\nname: 接口验证\ndescription: 接口正本\n---\n# 技能正文")
    write(proj.root, "技能库/接口验证/SKILL.en.md", "---\nname: Interface verification\ndescription: English source\n---\n# Selected English source")
    for target in (proj.root / ".claude/skills/接口验证", tmp_path / "假用户/.claude/skills/接口验证"):
        shutil.copytree(skill.parent, target)
    backend = proj.root / "backend"
    shutil.copytree(BACKEND, backend, dirs_exist_ok=True, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    # 先完成旧服务初始化；下面只统计读包调用区间。
    with TestClient(create_app(proj, tasks=False, global_keys=False, watch_interval=1000)) as client:
        async def compare():
            parameters = StdioServerParameters(command=sys.executable, args=["-B", str(backend / "mcp_server.py"), "--project", str(proj.root)],
                                               env={"RC_HOME": str(tmp_path / "假用户"), "RC_OFFLINE": "1"})
            async with stdio_client(parameters) as (receive, send):
                async with ClientSession(receive, send, client_info=Implementation(name="readonly-test", version="1")) as session:
                    await session.initialize()
                    assert "get_work_package" in {tool.name for tool in (await session.list_tools()).tools}
                    # 初始化第一次读后再取基线，排除 HTTP 既有 watch 的首圈初始化。
                    request = {"goal": "S1-1", "sub": "S2-1", "plan_code": record["code"], "skill_ids": ["接口验证"], "lang": "en"}
                    response = client.get("/api/work-package", params=request)
                    assert response.status_code == 200
                    store.log(setup, "agent:fresh", "领了", "S1-1 S2-1", "接口真实活跃 WAL 记录")
                    before = fingerprints(proj.root)
                    result = await session.call_tool("get_work_package", request)
                    native = json.loads(result.content[0].text)
                    http = client.get("/api/work-package", params=request).json()
                    assert native["read_only"] and http["read_only"]
                    assert native["task"]["document"] == http["task"]["document"]
                    assert native["ref"] == http["ref"] and native["requirements"] == http["requirements"]
                    assert native["selected_plan"] == http["selected_plan"]
                    assert native["allowed_files"] == http["allowed_files"] == record["files"]
                    assert native["skills"] == http["skills"]
                    assert native["skills"][0]["language"] == "en" and not native["skills"][0]["installation_status_checked"]
                    assert "接口真实活跃 WAL 记录" in json.dumps(native["task"], ensure_ascii=False)
                    assert native["readiness"] == http["readiness"]
                    assert native["snapshot"]["digest"] == http["snapshot"]["digest"]
                    assert native["snapshot"]["sources"] == http["snapshot"]["sources"]
                    assert_business_bytes_unchanged(before, fingerprints(proj.root))
        anyio.run(compare)
