"""内置照清单继承（10-07 统一内置：勾了的文件夹整个带、工作台随模块带，项目里没有 内置/），额外内容只在新建时逐级选择；测试只碰临时项目。"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import builtin
from main import create_app
from project import Project


def _write(root, rel, text="示例"):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "非科研项目"
    _write(root, "backend/main.py", "# 应用核心\n")
    _write(root, "backend/tests/test_sample.py", "# 通用回归测试\n")
    _write(root, "backend/builtin_resources.json", json.dumps({"version": 1, "paths": []}))
    _write(root, "模板.html", "<html>示例应用</html>")
    _write(root, "资料/天气/方法/样例.md", "每日天气模板")
    _write(root, "资料/天气/工作台/说明.md", "工作台随模块带")
    _write(root, "资料/天气/私有记录.md", "这个项目独有的记录")
    _write(root, "资料/天气/公共说明.md", "明确选择才继承")
    _write(root, "笔记/总览.md", "人的原笔记")
    (root / "资料/空模块/方法").mkdir(parents=True)
    _write(root, "内置标记.json", json.dumps({"version": 1, "paths": ["资料/天气/方法", "资料/空模块/方法"]}, ensure_ascii=False))
    return root


def test_every_builtin_and_core_is_required_in_preview(source):
    first = builtin.preview(source)
    rows = {r["path"]: r for r in first["folders"]}
    assert rows["资料/空模块/方法"]["files"] == 0
    assert "backend/tests/test_sample.py" in first["copied_paths"]
    assert "资料/天气/方法/样例.md" in first["copied_paths"]                  # 勾了的文件夹整个带
    assert "资料/天气/工作台/说明.md" in first["copied_paths"]                # 工作台随模块带
    assert "笔记/总览.md" not in first["copied_paths"]
    assert "资料/天气/私有记录.md" not in first["copied_paths"]
    proposal = {"extra": ["资料/天气/公共说明.md"]}
    preview = builtin.preview(source, proposal)
    assert "资料/天气/方法/样例.md" in preview["copied_paths"]
    assert "资料/天气/公共说明.md" in preview["copied_paths"]
    assert preview["files"] == len(preview["copied_paths"])
    assert preview["bytes"] == sum((source / p).stat().st_size for p in preview["copied_paths"])
    assert not (source / "内置配置.json").exists()  # 新建时的选择不保存成默认配置
    assert builtin.preview(source)["copied_paths"] == first["copied_paths"]


def test_selecting_parent_and_child_does_not_copy_files_twice(source):
    parent = builtin.preview(source, {"extra": ["资料/天气"]})
    overlap = builtin.preview(source, {"extra": ["资料/天气", "资料/天气/公共说明.md", "资料/天气"]})
    assert parent["copied_paths"] == overlap["copied_paths"]
    assert parent["files"] == overlap["files"] and parent["bytes"] == overlap["bytes"]


@pytest.mark.parametrize("rel", [".", "../其他项目", "C:/其他项目", "/其他项目", ".git", "资料/天气/.秘密", "索引", "存档", "回收站", "资料", "资料/_外部资料入口", "工具库/开源项目/原件", "自动化/交付/J1.md"])
def test_unsafe_or_project_history_cannot_be_selected(source, rel):
    if rel in {"索引", "存档", "回收站", ".git", "工具库/开源项目/原件", "资料/_外部资料入口", "资料/天气/.秘密"}:
        (source / rel).mkdir(parents=True, exist_ok=True)
    elif rel == "自动化/交付/J1.md":
        _write(source, rel, "真实交付记录")
    with pytest.raises(builtin.Invalid):
        builtin.preview(source, {"extra": [rel]})


@pytest.mark.parametrize("extra", ["资料/天气", [23], ["资料/不存在"]])
def test_invalid_extra_selection_is_reported(source, extra):
    with pytest.raises(builtin.Invalid):
        builtin.preview(source, {"extra": extra})


def test_hidden_subtree_is_not_silently_copied_but_gitkeep_is_allowed(source):
    _write(source, "资料/空模块/方法/.gitkeep", "")
    assert "资料/空模块/方法/.gitkeep" in builtin.preview(source)["copied_paths"]
    _write(source, "资料/天气/方法/.secret/token.txt", "不要复制的隐藏数据")
    with pytest.raises(builtin.Invalid):
        builtin.preview(source)


def test_selected_symlink_and_linked_subtree_are_refused(source, tmp_path):
    external = _write(tmp_path, "外部/secret.txt", "项目外数据")
    link = source / "资料/天气/方法/外部链接.txt"
    try:
        link.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"此测试环境不能创建软链接：{exc}")
    with pytest.raises(builtin.Invalid):
        builtin.preview(source)
    with pytest.raises(builtin.Invalid):
        builtin.preview(source, {"extra": [link.relative_to(source).as_posix()]})


def _make_junction(link, target):
    shell = shutil.which("powershell.exe")
    if not shell:
        pytest.skip("测试环境没有PowerShell，无法创建Windows目录联接")
    quote = lambda p: "'" + str(p).replace("'", "''") + "'"
    made = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command",
                           f"New-Item -ItemType Junction -Path {quote(link)} -Value {quote(target)} -ErrorAction Stop | Out-Null"],
                          capture_output=True, timeout=30,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert made.returncode == 0, made.stderr.decode("utf-8", "replace")
    assert link.is_junction()


@pytest.mark.skipif(os.name != "nt", reason="Windows目录联接检查")
def test_windows_directory_junction_cannot_escape_the_project(source, tmp_path):
    external = tmp_path / "项目外的目录"
    external.mkdir()
    link = source / "资料/天气/方法/外部目录"
    _make_junction(link, external)
    with pytest.raises(builtin.Invalid):
        builtin.preview(source)


def test_settings_browse_drills_into_folders_and_marks_required_items(source):
    with TestClient(create_app(Project(source))) as client:
        root = client.get("/api/settings/builtin/browse")
        assert root.status_code == 200 and root.json()["path"] == ""
        top = {r["name"]: r for r in root.json()["items"]}
        assert top["资料"]["kind"] == "folder"
        nested = client.get("/api/settings/builtin/browse", params={"path": "资料/天气"})
        assert nested.status_code == 200 and nested.json()["parent"] == "资料"
        rows = {r["name"]: r for r in nested.json()["items"]}
        assert rows["方法"]["required"] is True and rows["方法"]["kind"] == "folder"        # 勾了的文件夹
        assert rows["工作台"]["required"] is True                                            # 随模块带
        assert rows["公共说明.md"]["required"] is False and rows["公共说明.md"]["kind"] == "file"
        inside = client.get("/api/settings/builtin/browse", params={"path": "资料/天气/方法"}).json()
        assert inside["items"][0]["required"] is True
        for bad in ("../其他项目", "索引", "资料/_外部资料入口"):
            assert client.get("/api/settings/builtin/browse", params={"path": bad}).status_code == 400


def test_api_preview_is_readonly_and_builtin_cannot_be_cancelled(source):
    with TestClient(create_app(Project(source))) as client:
        initial = client.get("/api/settings/builtin")
        assert initial.status_code == 200
        body = {"extra": ["资料/天气/公共说明.md"]}
        preview = client.post("/api/settings/builtin/preview", json=body)
        assert preview.status_code == 200
        paths = preview.json()["copied_paths"]
        assert "资料/天气/公共说明.md" in paths and "资料/天气/方法/样例.md" in paths
        assert paths == builtin.preview(source, body)["copied_paths"]
        assert not (source / "内置配置.json").exists()
        cancelled = client.post("/api/settings/builtin/preview", json={"disabled": ["资料/天气/方法"], "extra": []})
        if cancelled.status_code == 200:
            assert "资料/天气/方法/样例.md" in cancelled.json()["copied_paths"]
        else:
            assert cancelled.status_code in (400, 422)
        assert client.post("/api/settings/builtin/preview", json={"extra": ["索引"]}).status_code == 400


def test_new_project_button_applies_only_the_current_extra_selection(source, tmp_path):
    parent = tmp_path / "新项目们"
    parent.mkdir()
    with TestClient(create_app(Project(source))) as client:
        body = {"name": "第二个项目", "where": str(parent), "extra": ["资料/天气/公共说明.md"]}
        created = client.post("/api/settings/new-project", json=body)
        assert created.status_code == 200
        result = created.json()
        target = parent / body["name"]
        assert target.resolve() == Path(result["target"]).resolve()
        assert (target / "资料/天气/公共说明.md").read_text(encoding="utf-8") == "明确选择才继承"
        assert (target / "资料/天气/方法/样例.md").is_file() and not [d for d in target.rglob("内置") if d.is_dir()]
        assert not (target / "资料/天气/私有记录.md").exists()
        assert (target / "backend/tests/test_sample.py").is_file()
        assert (target / result["manifest"]).is_file()
        assert result["file_count"] > 0 and result["bytes"] > 0
        before = (target / "资料/天气/公共说明.md").read_bytes()
        assert client.post("/api/settings/new-project", json=body).status_code == 409
        assert (target / "资料/天气/公共说明.md").read_bytes() == before
        assert client.post("/api/settings/new-project", json=body | {"name": "../越界"}).status_code == 400
        assert client.post("/api/settings/new-project", json=body | {"name": "第三个项目", "where": "相对位置"}).status_code == 400
        assert client.post("/api/settings/new-project", json=body | {"name": "第三个项目", "extra": ["../越界"]}).status_code == 400
        assert not (parent / "第三个项目").exists()
        assert client.post("/api/settings/new-project", json={"name": "第三个项目", "where": str(parent)}).status_code == 200
        assert not (parent / "第三个项目/资料/天气/公共说明.md").exists()


def test_new_module_from_web_has_no_builtin_folder(proj):
    """10-07 起新模块是干净的：不再补 内置/；要带什么去 设置 → 内置 勾。"""
    with TestClient(create_app(proj)) as client:
        assert client.post("/api/modules", json={"name": "天气", "en": "Weather"}).status_code == 200
        assert (proj.materials / "天气").is_dir() and not (proj.materials / "天气/内置").exists()
        rows = client.get("/api/settings/builtin").json()["folders"]
        assert not any(r["path"].startswith("资料/天气") for r in rows)


def test_human_note_is_only_included_when_explicitly_selected(source):
    before = (source / "笔记/总览.md").read_bytes()
    assert "笔记/总览.md" not in builtin.preview(source)["copied_paths"]
    chosen = builtin.preview(source, {"extra": ["笔记/总览.md"]})
    assert "笔记/总览.md" in chosen["copied_paths"]
    assert (source / "笔记/总览.md").read_bytes() == before


def test_templates_are_not_current_plans_or_governance_records(proj):
    import governance_paths
    import tidy

    plan = _write(proj.root, "治理/计划/项目/P1 正式计划.md", "当前正式计划")
    _write(proj.root, "治理/计划/项目/内置/P2 模板计划.md", "将来项目的计划模板")
    requirement = _write(proj.root, "治理/需求/项目.md", "当前项目需求")
    _write(proj.root, "治理/需求/内置/需求示例.md", "未来需求占位")
    _write(proj.root, "治理/戒律/内置/规则示例.md", "未来规则占位")
    _write(proj.root, "治理/目标/内置/S0 示例目标.md", "未来目标占位")
    assert set(governance_paths.plan_files(proj).values()) == {plan}
    assert set(tidy.canon_files(proj)) == {requirement}


def test_skill_and_plugin_templates_do_not_register_as_installed_capabilities(proj, tmp_path, monkeypatch):
    import plugins
    import skills

    monkeypatch.setenv("RC_HOME", str(tmp_path / "假用户目录"))
    lib = proj.root / "技能库"
    _write(proj.root, "技能库/正式技能/SKILL.md", "---\nname: 正式技能\ndescription: 当前能用的技能\n---\n")
    _write(proj.root, "技能库/内置/SKILL.md", "---\nname: 技能模板\ndescription: 以后填写\n---\n")
    _write(proj.root, "插件/正式插件/插件.md", "---\n名字: 正式插件\n---\n")
    _write(proj.root, "插件/内置/插件.md", "---\n名字: 插件模板\n---\n")
    assert [r["name"] for r in skills.catalog(proj, lib)] == ["正式技能"]
    assert [r["name"] for r in skills.list_skills(proj, lib)] == ["正式技能"]
    assert [r["name"] for r in plugins.list_plugins(proj.root / "插件")] == ["正式插件"]


def test_explicit_checkpoint_restore_restores_templates_but_preserves_actual_history(proj):
    import snapshot
    import store

    templates = ("笔记/内置/笔记模板.md", "治理/计划/内置/P1 示例计划.md", "自动化/日志/内置/日志模板.md")
    records = ("笔记/总览.md", "治理/计划/项目/P1 正式计划.md", "自动化/日志/2026-10.md")
    for rel in templates + records:
        _write(proj.root, rel, "原版")
    conn = store.connect(proj.db_path)
    try:
        saved = snapshot.save(conn, proj, name="模板修改前", mode="全量", by="agent:test")
        for rel in templates + records:
            _write(proj.root, rel, "新版")
        restored = snapshot.restore(conn, proj, saved["code"], paths=list(templates + records), confirm=True, by="agent:test")
        assert restored["replaced"] == len(templates)
        for rel in templates:
            assert (proj.root / rel).read_text(encoding="utf-8") == "原版", rel
        for rel in records:
            assert (proj.root / rel).read_text(encoding="utf-8") == "新版", rel
    finally:
        conn.close()


def test_branch_merge_puts_builtin_template_back_in_place_instead_of_archiving_it(proj):
    import store
    import worldtree

    rel = "自动化/交付/内置/交付模板.md"
    _write(proj.root, rel, "模板原版")
    conn = store.connect(proj.db_path)
    try:
        branch = worldtree.grow(conn, proj, name="模板试验", by="agent:test")
        root = Path(branch["path"])
        _write(root, rel, "模板新版")
        record = "自动化/交付/J2 新记录.md"
        _write(root, record, "枝上的实际交付")
        changes = worldtree.changes(proj, branch["code"])
        assert rel in changes["take"] and rel not in changes["records"]
        assert record in changes["records"]
        worldtree.merge(conn, proj, branch["code"], by="agent:test")
        assert (proj.root / rel).read_text(encoding="utf-8") == "模板新版"
        assert not (proj.root / record).exists()
        archived = proj.root / "自动化/世界树" / branch["code"] / "记录"
        assert (archived / record).read_text(encoding="utf-8") == "枝上的实际交付"
        assert not (archived / rel).exists()
    finally:
        conn.close()


def test_default_core_restore_includes_the_saved_templates_and_protects_human_notes(proj):
    import snapshot
    import store

    _write(proj.root, "backend/main.py", "# 程序原版")
    _write(proj.root, "backend/governance_paths.py", "# 集中治理路径")
    templates = ("资料/天气/方法/样例.md", "资料/天气/工作台/说明.md")      # 勾了的文件夹、工作台
    for rel in templates:
        _write(proj.root, rel, "模板原版")
    _write(proj.root, "内置标记.json", json.dumps({"version": 1, "paths": ["资料/天气/方法"]}, ensure_ascii=False))
    _write(proj.root, "笔记/总览.md", "人的原笔记")
    conn = store.connect(proj.db_path)
    try:
        saved = snapshot.save(conn, proj, name="只存核心也带模板", mode="核心", by="agent:test")
        for rel in templates:
            assert snapshot.old_file(proj, saved["code"], rel)[0].read_text(encoding="utf-8") == "模板原版"
            _write(proj.root, rel, "模板新版")
        _write(proj.root, "backend/main.py", "# 程序新版")
        _write(proj.root, "笔记/总览.md", "人的新笔记")
        snapshot.restore(conn, proj, saved["code"], confirm=True, whole=False, by="agent:test")
        for rel in templates:
            assert (proj.root / rel).read_text(encoding="utf-8") == "模板原版", rel
        assert (proj.root / "backend/main.py").read_text(encoding="utf-8") == "# 程序原版"
        assert (proj.root / "笔记/总览.md").read_text(encoding="utf-8") == "人的新笔记"
    finally:
        conn.close()


def test_legacy_checkpoint_does_not_remove_templates_created_after_it(proj):
    import snapshot
    import store

    _write(proj.root, "backend/main.py", "# 程序原版")
    _write(proj.root, "backend/governance_paths.py", "# 集中治理路径")
    conn = store.connect(proj.db_path)
    try:
        saved = snapshot.save(conn, proj, name="内置功能以前的存档", mode="全量", by="agent:test")
        meta_file = proj.root / saved["folder"] / "档.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta.pop("builtin_scope", None)  # 真实旧档没有此字段，保留其原有恢复范围
        meta_file.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        later = ("治理/需求/内置/需求模板.md", "治理/计划/内置/计划模板.md", "笔记/内置/笔记模板.md")
        for rel in later:
            _write(proj.root, rel, "后来创建的模板")
        _write(proj.root, "backend/main.py", "# 程序新版")
        snapshot.restore(conn, proj, saved["code"], confirm=True, whole=False, by="agent:test")
        assert (proj.root / "backend/main.py").read_text(encoding="utf-8") == "# 程序原版"
        for rel in later:
            assert (proj.root / rel).read_text(encoding="utf-8") == "后来创建的模板", rel
    finally:
        conn.close()


def test_slimmed_full_checkpoint_keeps_templates_restorable_and_preserves_new_notes(proj):
    import snapshot
    import store

    _write(proj.root, "backend/main.py", "# 程序原版")
    templates = {"资料/天气/方法/样例.md": "天气模板原版", "资料/天气/工作台/说明.md": "工作台原版"}
    for rel, text in templates.items():
        _write(proj.root, rel, text)
    _write(proj.root, "内置标记.json", json.dumps({"version": 1, "paths": ["资料/天气/方法"]}, ensure_ascii=False))
    _write(proj.root, "资料/天气/私有记录.md", "瘦身时不保留的真实业务材料")
    _write(proj.root, "笔记/总览.md", "人的原笔记")
    conn = store.connect(proj.db_path)
    try:
        saved = snapshot.save(conn, proj, name="全量档瘦身也保留模板", mode="全量", by="agent:test")
        slimmed = snapshot.slim(conn, proj, saved["code"], by="agent:test")
        assert slimmed["freed"] > 0
        assert snapshot.detail(proj, saved["code"])["mode"] == "核心"
        for rel, text in templates.items():
            assert snapshot.old_file(proj, saved["code"], rel)[0].read_text(encoding="utf-8") == text
            _write(proj.root, rel, "模板新版")
        _write(proj.root, "backend/main.py", "# 程序新版")
        _write(proj.root, "笔记/总览.md", "人的新笔记")
        snapshot.restore(conn, proj, saved["code"], confirm=True, whole=False, by="agent:test")
        assert (proj.root / "backend/main.py").read_text(encoding="utf-8") == "# 程序原版"
        for rel, text in templates.items():
            assert (proj.root / rel).read_text(encoding="utf-8") == text, rel
        assert (proj.root / "笔记/总览.md").read_text(encoding="utf-8") == "人的新笔记"
        assert (proj.root / "资料/天气/私有记录.md").read_text(encoding="utf-8") == "瘦身时不保留的真实业务材料"
    finally:
        conn.close()


@pytest.mark.parametrize("rel", ["自动化/世界树/枝-9", "自动化/交付/J1.md", "自动化/日志"])
def test_run_records_cannot_be_ticked_as_builtin(source, rel):
    """运行记录（世界树、交付、日志……）不能勾进内置清单：新项目不带别的项目的历史（10-07 起没有记录目录里的 内置/ 了）。"""
    _write(source, rel + ("" if rel.endswith(".md") else "/占位.md"), "历史记录")
    with pytest.raises(builtin.Invalid):
        builtin.parse_marks(json.dumps({"version": 1, "paths": [rel]}, ensure_ascii=False).encode("utf-8"))
    assert not any(p.startswith(rel) for p in builtin.preview(source)["copied_paths"])


@pytest.mark.skipif(os.name != "nt", reason="Windows目录联接检查")
@pytest.mark.parametrize("rel", [".claude/settings.json", "治理/戒律/1 通用戒律.md"])
def test_core_single_file_rejects_a_linked_parent_directory(source, tmp_path, rel):
    external = tmp_path / "外部核心文件"
    external.mkdir()
    _write(external, Path(rel).name, "外部占位资料")
    parent = (source / rel).parent
    parent.parent.mkdir(parents=True, exist_ok=True)
    _make_junction(parent, external)
    with pytest.raises(builtin.Invalid):
        builtin.files(source, source / rel, core=True)
    with pytest.raises(builtin.Invalid):
        builtin.preview(source)


def test_normal_hidden_core_settings_file_remains_required(source):
    rel = ".claude/settings.json"
    _write(source, rel, '{"plansDirectory": "./治理/计划"}')
    assert rel in builtin.preview(source)["copied_paths"]


@pytest.mark.parametrize("suffix", [".log", ".tmp", ".part", ".pyc", ".pyo"])
def test_template_suffixes_and_extra_folder_or_file_selection_copy_the_same_contents(source, tmp_path, suffix):
    import new_project

    template = f"资料/天气/方法/记录模板{suffix}"
    parent = "资料/天气/公开样例"
    example = f"{parent}/示例{suffix}"
    cache = f"backend/缓存{suffix}"
    _write(source, template, "内置模板，后缀不能导致丢失")
    _write(source, example, "用户明确选择的样例")
    _write(source, cache, "程序缓存默认不复制")
    initial = builtin.preview(source)
    assert template in initial["copied_paths"] and cache not in initial["copied_paths"]
    selections = ([parent], [example], [parent, example, parent])
    expected = None
    totals = []
    for i, selected in enumerate(selections):
        preview = builtin.preview(source, {"extra": selected})
        if expected is None:
            expected = preview["copied_paths"]
        assert preview["copied_paths"] == expected
        assert preview["extra_files"] == 1
        target = tmp_path / f"新项目{i}"
        new_project.make(target, source, extra=selected)
        assert (target / template).read_text(encoding="utf-8") == "内置模板，后缀不能导致丢失"
        assert (target / example).read_text(encoding="utf-8") == "用户明确选择的样例"
        assert not (target / cache).exists()
        manifest = json.loads((target / "新项目复制清单.json").read_text(encoding="utf-8"))
        paths = [f["path"] for f in manifest["files"]]
        assert paths.count(template) == 1 and paths.count(example) == 1
        totals.append((manifest["file_count"], manifest["bytes"]))
    assert len(set(totals)) == 1
