"""项目本地业务技能与两代模板：合成资料、真文件/HTTP/MCP，不运行外部工具。"""
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import anyio
import pytest
from fastapi.testclient import TestClient

import new_project
import skills
from main import create_app
from project import Project, module_dirs
from test_mcp import _call
from test_release import COMMON_SKILLS, GENERAL_MODULES, SCIENCE_SKILLS, synthetic_source, write


GROUPS = [{"id": b, "title": {"zh-CN": title, "en": b}, "stages": [
    {"id": "start", "order": 1, "title": {"zh-CN": "开始", "en": "Start"}}]}
    for b, title in [("paper", "写论文"), ("video", "剪辑"), ("novel", "写小说")]]


def item(root, business="video", vendor="example", slug="outline", title="业务技能"):
    directory = f"技能库/业务/{business}/{vendor}/{slug}"
    install_name = f"mh-{business}-{vendor}-{slug}"
    write(root, directory + "/SKILL.md", f"---\nname: {install_name}\ndescription: 中文用法\n---\n# 中文正本\n")
    write(root, directory + "/SKILL.en.md", f"---\nname: {install_name}\ndescription: English use\n---\n# English source\n")
    write(root, directory + "/LICENSE.txt", "MIT License\nSynthetic test fixture\n")
    write(root, directory + "/SOURCE.md", "# 来源\n合成测试，不表示实际项目许可。\n")
    return {"id": f"biz:{business}:{vendor}:{slug}", "kind": "skill", "business": business,
            "stages": ["start"], "title": {"zh-CN": title, "en": "Business Skill"},
            "summary": {"zh-CN": "先看目标与验收", "en": "Read goals and checks"},
            "install_name": f"mh-{business}-{vendor}-{slug}", "path": directory + "/SKILL.md",
            "languages": {"zh-CN": directory + "/SKILL.md", "en": directory + "/SKILL.en.md"},
            "license": {"id": "MIT", "files": [directory + "/LICENSE.txt"]},
            "source": {"url": "https://github.com/example/skills", "commit": "a" * 40},
            "redistribution": {"status": "verified"}, "support_files": [directory + "/SOURCE.md"],
            "dependencies": [{"name": "FFmpeg", "required": False}]}


def manifest(root, items):
    return write(root, "技能库/业务/manifest.json", json.dumps({"schema": 1, "groups": GROUPS, "items": items}, ensure_ascii=False))


@pytest.fixture
def business(proj, monkeypatch, tmp_path):
    monkeypatch.setenv("RC_HOME", str(tmp_path / "假用户"))
    first = item(proj.root)
    manifest(proj.root, [first])
    return proj, first


def test_current_project_catalog_never_falls_back_to_application_skills(proj, tmp_path, monkeypatch):
    global_lib = tmp_path / "另外应用/技能库"
    write(global_lib.parent, "技能库/只能在另外项目/SKILL.md", "---\nname: 另一个项目\n---\n")
    monkeypatch.setattr(skills, "LIB", global_lib)
    assert skills.catalog(proj) == [] and skills.inventory(proj)["items"] == []
    with pytest.raises(KeyError):
        skills.read(proj, "只能在另外项目")
    with TestClient(create_app(proj, tasks=False, global_keys=False)) as client:
        assert client.get("/api/skills").json() == []


def test_same_slug_title_and_agent_name_require_full_business_id(business):
    p, first = business
    second = item(p.root, "novel", title=first["title"]["zh-CN"])
    manifest(p.root, [first, second])
    found = skills.inventory(p)
    assert {r["id"] for r in found["items"]} == {first["id"], second["id"]}
    assert len(found["groups"]) == 3 and found["issues"] == []
    for row in (first, second):
        assert skills.read(p, row["id"])["path"] == row["path"]
    for name in ("outline", "业务技能"):
        with pytest.raises(ValueError, match="完整编号"):
            skills.read(p, name)
    for row in (first, second):
        installed = skills.install(p, row["id"], "project")
        assert Path(installed["to"]).name == row["install_name"]
    assert len(list((p.root / ".claude/skills").iterdir())) == 2


def test_read_uses_selected_language_and_has_real_revision_and_fallback(business):
    p, row = business
    read = skills.read(p, row["id"], "en-US")
    assert "English source" in read["text"] and read["language"] == "en" and not read["fallback"]
    assert read["revision"] == hashlib.sha256((p.root / row["languages"]["en"]).read_bytes()).hexdigest()
    assert read["source"] == row["source"] and read["license"] == row["license"]
    assert read["dependencies"] == row["dependencies"] and read["support_files"] == row["support_files"]
    row["languages"].pop("en")
    manifest(p.root, [row])
    read = skills.read(p, row["id"], "en")
    assert read["fallback"] and read["language"] == "zh-CN" and "中文正本" in read["text"]
    with pytest.raises(ValueError):
        skills.read(p, row["id"], "python")


@pytest.mark.parametrize("missing", ["path", "language", "license", "support"])
def test_missing_content_is_reported_without_claiming_available(business, missing):
    p, row = business
    rel = {"path": row["path"], "language": row["languages"]["en"],
           "license": row["license"]["files"][0], "support": row["support_files"][0]}[missing]
    (p.root / rel).unlink()
    found = skills.inventory(p)
    entry = found["items"][0]
    assert not entry["available"] and not entry["installable"] and found["issues"]
    assert skills.read(p, row["id"])["issues"]
    with pytest.raises(ValueError, match="不能安装"):
        skills.install(p, row["id"], "project")


def test_link_is_readable_reference_and_never_installable_or_forked(business):
    p, row = business
    link = {"id": "biz:video:example:remote", "kind": "link", "business": "video", "stages": ["start"],
            "title": "外部参考", "path": None, "languages": {}, "source": {"url": "https://example.com/"}}
    manifest(p.root, [row, link])
    entry = skills.read(p, link["id"])
    assert entry["kind"] == "link" and not entry["available"] and not entry["installable"]
    assert entry["text"] == "" and entry["revision"] is None and entry["source"] == link["source"]
    with pytest.raises(ValueError, match="网址"):
        skills.install(p, link["id"], "project")
    with pytest.raises(ValueError, match="网址"):
        skills.fork(p, link["id"])
    assert not (p.root / ".claude").exists()


def test_legacy_research_manifest_enriches_the_same_original(business):
    p, row = business
    legacy = item(p.root, "paper", slug="route", title="科研路线")
    legacy["id"] = "research-route"
    legacy["install_name"] = "research-route"
    old = p.root / "技能库/research-route"
    shutil.copytree((p.root / legacy["path"]).parent, old)
    legacy["path"] = "技能库/research-route/SKILL.md"
    legacy["languages"] = {"zh-CN": legacy["path"], "en": "技能库/research-route/SKILL.en.md"}
    legacy["license"]["files"] = ["技能库/research-route/LICENSE.txt"]
    legacy["support_files"] = ["技能库/research-route/SOURCE.md"]
    manifest(p.root, [row, legacy])
    found = skills.list_skills(p)
    assert sum(r["id"] == "research-route" for r in found) == 1
    assert skills.find(p, "科研路线")["id"] == "research-route"
    assert skills.read(p, "research-route")["business"] == "paper"


@pytest.mark.parametrize("problem", ["schema", "duplicate_id", "duplicate_path", "duplicate_install", "case_install", "device", "duplicate_alias", "traversal", "absolute", "url", "bad_language", "fake_english", "stage"])
def test_invalid_manifest_is_a_friendly_validation_error(business, problem):
    p, first = business
    second = item(p.root, "novel")
    rows = [first, second]
    if problem == "duplicate_id": second["id"] = first["id"]
    elif problem == "duplicate_path": second["path"] = first["path"]
    elif problem == "duplicate_install": second["install_name"] = first["install_name"]
    elif problem == "case_install": second["install_name"] = first["install_name"].upper()
    elif problem == "device": first["install_name"] = "CON"
    elif problem == "duplicate_alias": first["aliases"] = second["aliases"] = ["同一个别名"]
    elif problem == "traversal": first["support_files"] = ["技能库/../外面.md"]
    elif problem == "absolute": first["languages"]["en"] = "C:/Windows/win.ini"
    elif problem == "url": first["source"]["url"] = "javascript:alert(1)"
    elif problem == "bad_language": first["languages"]["en"] = second["languages"]["en"]
    elif problem == "fake_english": first["languages"]["en"] = first["path"]
    elif problem == "stage": first["stages"] = ["未定义阶段"]
    f = manifest(p.root, rows)
    if problem == "schema":
        data = json.loads(f.read_text(encoding="utf-8")); data["schema"] = 999
        f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError): skills.inventory(p)


def test_source_snapshot_fingerprint_is_checked_without_running_it(business):
    p, row = business
    local = row["path"].rsplit("/", 1)[0] + "/raw/原始技能.md"
    f = write(p.root, local, "# 固定来源原件\n")
    row["source"]["files"] = [{"path": "upstream/SKILL.md", "local_path": local,
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "url": "https://example.com/blob/commit/SKILL.md"}]
    manifest(p.root, [row])
    assert skills.inventory(p)["items"][0]["available"]
    f.write_text("原件被替换", encoding="utf-8")
    assert not skills.inventory(p)["items"][0]["available"]
    assert any("指纹不符" in issue["message"] for issue in skills.inventory(p)["issues"])
    with pytest.raises(ValueError): skills.install(p, row["id"], "project")


def test_business_native_skill_name_must_match_unique_install_name(business):
    p, row = business
    doc = p.root / row['path']
    doc.write_text(doc.read_text(encoding='utf-8').replace(row['install_name'], 'outline'), encoding='utf-8')
    entry = skills.inventory(p)['items'][0]
    assert not entry['available'] and not entry['installable']
    assert any('唯一安装名' in issue for issue in entry['issues'])
    with pytest.raises(ValueError): skills.install(p, row['id'], 'project')


@pytest.mark.skipif(os.name != "nt", reason="Windows 联接检查")
def test_business_package_junction_is_never_read_or_installed(business, tmp_path):
    from test_builtin import _make_junction
    p, row = business
    old = (p.root / row["path"]).parent
    retained = old.with_name("原包")
    old.rename(retained)
    _make_junction(old, retained)
    with pytest.raises(ValueError, match="联接"):
        skills.read(p, row["id"])
    with pytest.raises(ValueError):
        skills.install(p, row["id"], "project")


def test_business_install_backup_and_fork_keep_attribution_in_current_project(business):
    p, row = business
    original = (p.root / row["path"]).read_bytes()
    skills.install(p, row["id"], "project")
    installed = p.root / ".claude/skills" / row["install_name"]
    (installed / "SKILL.md").write_text("作者修改", encoding="utf-8")
    with pytest.raises(skills.Conflict): skills.install(p, row["id"], "project")
    result = skills.install(p, row["id"], "project", overwrite=True)
    assert (Path(result["backup"]) / "SKILL.md").read_text(encoding="utf-8") == "作者修改"
    copied = skills.fork(p, row["id"])
    copy = p.root / "技能库" / copied
    assert all((copy / file).is_file() for file in ("SKILL.md", "SKILL.en.md", "LICENSE.txt", "SOURCE.md"))
    assert (p.root / row["path"]).read_bytes() == original
    assert skills.read(p, copied)["id"] == copied
    assert skills.read(p, row["id"])["id"] == row["id"]


def business_source(tmp_path):
    src = synthetic_source(tmp_path)
    first = item(src)
    manifest(src, [first])
    write(src, "技能库/业务/README.md", "# 三类业务\n")
    cfgfile = src / "backend/template_profiles.json"
    cfg = json.loads(cfgfile.read_text(encoding="utf-8"))
    g = cfg["profiles"]["general"]
    roots = []
    for name in ("写论文", "剪辑", "写小说"):
        rel = f"资料/{name}/内置"
        roots.append(rel)
        write(src, rel + "/README.md", "# 分阶段路线\n")
    cfg["profiles"]["business"] = {"label": "三类业务", "modules": ["写论文", "剪辑", "写小说"],
        "skills": COMMON_SKILLS + SCIENCE_SKILLS + ["业务"], "template_roots": g["template_roots"] + roots,
        "module_skills": [], "module_labels": {"写论文": "Paper Writing", "剪辑": "Video Editing", "写小说": "Novel Writing"}}
    cfgfile.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return src, first


@pytest.mark.parametrize("profile", ["general", "business"])
def test_real_catalog_http_and_mcp_stay_isolated_in_two_generations(tmp_path, profile):
    src, row = business_source(tmp_path)
    first, second = tmp_path / "第一代", tmp_path / "第二代"
    new_project.make(first, src, profile=profile)
    # 即使通用项目随后出现了未列为负载的业务正本，下一代仍按声明过滤。
    if profile == "general":
        shutil.copytree(src / "技能库/业务", first / "技能库/业务")
    new_project.make(second, first)
    expected_modules = set(GENERAL_MODULES + (["写论文", "剪辑", "写小说"] if profile == "business" else []))
    p = Project(second)
    assert set(module_dirs(p)) == expected_modules
    found = {r["id"] for r in skills.list_skills(p)}
    assert found == set(COMMON_SKILLS + (SCIENCE_SKILLS + [row["id"]] if profile == "business" else []))
    assert (second / "技能库/业务/manifest.json").exists() == (profile == "business")
    with TestClient(create_app(p, tasks=False, global_keys=False)) as client:
        assert {r["id"] for r in client.get("/api/skills").json()} == found
        assert {r["name"] for r in client.get("/api/state").json()["modules"]} == expected_modules
        http_catalog = client.get('/api/skills/catalog').json()
        http_read = client.get('/api/skills/' + row['id'], params={'language': 'en'}).json()
    listed, read = anyio.run(_call, p, [("list_skills", {}), ("read_skill", {"name": row["id"]})])
    assert (row["id"] in listed) == (profile == "business")
    assert ("中文正本" in read) == (profile == "business")
    shared_catalog, shared_read = anyio.run(_call, p, [("list_skill_catalog", {}),
        ("read_skill_entry", {"id": row["id"], "language": "en"})])
    assert json.loads(shared_catalog) == http_catalog
    if profile == 'business':
        assert json.loads(shared_read) == http_read and 'English source' in http_read['text']
    else:
        assert 'Error' in shared_read or 'error' in shared_read or row['id'] in shared_read
    assert json.loads((second / "模板配置.json").read_text(encoding="utf-8"))["profile"] == profile


def test_business_to_general_and_missing_business_source_fail_without_fallback(tmp_path):
    src, row = business_source(tmp_path)
    business_root, general, missing = tmp_path / "带业务", tmp_path / "切回通用", tmp_path / "不可偷借业务"
    new_project.make(business_root, src, profile="business")
    new_project.make(general, business_root, profile="general")
    assert set(module_dirs(Project(general))) == set(GENERAL_MODULES)
    assert not (general / "技能库/业务").exists()
    with pytest.raises(ValueError): new_project.make(missing, general, profile="business")
    assert not missing.exists()


def test_inherited_profile_keeps_explicit_current_extras_and_human_module_labels(tmp_path):
    src, row = business_source(tmp_path)
    first, second, third = tmp_path / "通用", tmp_path / "通用本次附件", tmp_path / "通用下一代"
    new_project.make(first, src, profile="general")
    write(first, "资料/天气/本次.md", "本次明确选择")
    cfgfile = first / "模板配置.json"
    cfg = json.loads(cfgfile.read_text(encoding="utf-8")); cfg["module_labels"] = {"测试": "Local Test"}
    cfgfile.write_text(json.dumps(cfg), encoding="utf-8")
    new_project.make(second, first, extra=["资料/天气/本次.md"])
    assert (second / "资料/天气/本次.md").is_file()
    new_project.make(third, second)
    assert not (third / "资料/天气").exists()
    assert json.loads((third / "模板配置.json").read_text(encoding="utf-8"))["module_labels"]["测试"] == "Local Test"


def test_unknown_inherited_profile_refuses_before_creating_destination(tmp_path):
    src, row = business_source(tmp_path)
    write(src, "模板配置.json", json.dumps({"version": 1, "profile": "unknown", "modules": []}))
    target = tmp_path / "不能无声换模板"
    with pytest.raises(ValueError, match="发行模板"): new_project.make(target, src)
    assert not target.exists()


def test_business_template_requires_its_own_manifest_before_copy(tmp_path):
    src, row = business_source(tmp_path)
    (src / '技能库/业务/manifest.json').unlink()
    target = tmp_path / '缺少业务清单'
    with pytest.raises(ValueError, match='manifest.json'):
        new_project.make(target, src, profile='business')
    assert not target.exists()


def test_read_snapshot_is_reused_only_within_one_request(business, monkeypatch):
    p, row = business
    document = p.root / row['path']
    original_read = Path.read_bytes
    calls = []

    def tracked_read(path):
        calls.append(path)
        return original_read(path)

    monkeypatch.setattr(Path, 'read_bytes', tracked_read)
    first = skills.read(p, row['id'])
    assert calls.count(document) == 1  # 正文、元数据、包指纹共用这次读到的字节。
    document.write_text(document.read_text(encoding='utf-8') + '\n作者刚保存的正文\n', encoding='utf-8')
    second = skills.read(p, row['id'])
    assert '作者刚保存的正文' in second['text'] and second['revision'] != first['revision']
    assert calls.count(document) == 2
    assert skills._READ.get() is None
    (p.root / row['license']['files'][0]).unlink()
    assert not skills.read(p, row['id'])['available']


def test_failed_read_never_leaves_a_snapshot_for_the_next_request(business):
    p, row = business
    file = p.root / '技能库/业务/manifest.json'
    valid = file.read_bytes()
    file.write_text('{invalid', encoding='utf-8')
    with pytest.raises(ValueError):
        skills.inventory(p)
    assert skills._READ.get() is None
    file.write_bytes(valid)
    assert skills.read(p, row['id'])['available']


def test_concurrent_project_reads_have_separate_request_snapshots(business, tmp_path, monkeypatch):
    p, first = business
    other = Project(tmp_path / '另一个并发项目')
    second = item(other.root, slug='other', title='另一个项目的技能')
    manifest(other.root, [second])
    barrier, contexts = Barrier(2), []
    real_verify = skills._verify_read

    def simultaneous_verify(snapshot):
        contexts.append(snapshot)
        barrier.wait(timeout=10)
        assert skills._READ.get() is snapshot
        real_verify(snapshot)

    monkeypatch.setattr(skills, '_verify_read', simultaneous_verify)
    with ThreadPoolExecutor(max_workers=2) as workers:
        jobs = [workers.submit(skills.read, project, row['id']) for project, row in [(p, first), (other, second)]]
        values = [job.result(timeout=15) for job in jobs]
    assert contexts[0] is not contexts[1]
    assert [value['id'] for value in values] == [first['id'], second['id']]
    assert values[0]['name'] != values[1]['name']
    assert skills._READ.get() is None


def test_document_changed_during_read_is_reported_instead_of_returning_stale_bytes(business, monkeypatch):
    p, row = business
    document = p.root / row['path']
    real_read = Path.read_bytes
    changed = False

    def replace_after_read(path):
        nonlocal changed
        content = real_read(path)
        if path == document and not changed:
            changed = True
            document.write_bytes(content + '\n读取途中作者保存的文字\n'.encode('utf-8'))
        return content

    monkeypatch.setattr(Path, 'read_bytes', replace_after_read)
    with pytest.raises(ValueError, match='读取期间发生变化'):
        skills.read(p, row['id'])
    assert skills._READ.get() is None
    assert '读取途中作者保存的文字' in skills.read(p, row['id'])['text']


def test_ordinary_cloud_reparse_tag_is_not_treated_as_a_junction(business, monkeypatch):
    p, row = business
    document = p.root / row['path']
    real_lstat = Path.lstat

    def cloud_lstat(path):
        if path == document:
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_reparse_tag=0x9000001A)
        return real_lstat(path)

    monkeypatch.setattr(Path, 'lstat', cloud_lstat)
    assert skills.read(p, row['id'])['available']


@pytest.mark.skipif(os.name != 'nt', reason='Windows 联接检查')
def test_a_new_junction_after_a_successful_read_is_checked_again(business):
    from test_builtin import _make_junction
    p, row = business
    assert skills.read(p, row['id'])['available']
    original = (p.root / row['path']).parent
    retained = original.with_name('保留原件')
    original.rename(retained)
    _make_junction(original, retained)
    with pytest.raises(ValueError, match='联接'):
        skills.read(p, row['id'])
    assert skills._READ.get() is None


@pytest.mark.skipif(os.name != 'nt', reason='Windows 联接检查')
def test_junction_swapped_during_read_is_rejected_before_return(business, monkeypatch):
    from test_builtin import _make_junction
    p, row = business
    document = p.root / row['path']
    package = document.parent
    retained = package.with_name('读取途中保留原件')
    real_read = Path.read_bytes
    changed = False

    def replace_after_read(path):
        nonlocal changed
        content = real_read(path)
        if path == document and not changed:
            changed = True
            package.rename(retained)
            _make_junction(package, retained)
        return content

    monkeypatch.setattr(Path, 'read_bytes', replace_after_read)
    with pytest.raises(ValueError, match='联接|读取期间发生变化'):
        skills.read(p, row['id'])
    assert skills._READ.get() is None


def _target_with_length(base, length):
    return base / ('x' * (length - len(str(base)) - 1))


@pytest.mark.skipif(os.name != 'nt', reason='Windows 普通路径长度边界')
@pytest.mark.parametrize('kind,relative,limit', [
    ('folder', '材料/' + '目录' * 15, 248),
    ('file', '材料/' + '文件' * 40 + '.md', 260),
])
def test_windows_preflight_checks_copy_boundaries_before_creating_anything(tmp_path, kind, relative, limit):
    target_length = limit - len(relative) - 1
    folders = [{'path': relative}] if kind == 'folder' else []
    copied = [] if kind == 'folder' else [relative]
    accepted = _target_with_length(tmp_path, target_length - 1)
    skills_before = set(tmp_path.iterdir())
    new_project._windows_path_preflight(accepted, copied, folders, [], entry=False, configured=False)
    rejected = _target_with_length(tmp_path, target_length)
    with pytest.raises(ValueError, match='更短的目标目录'):
        new_project._windows_path_preflight(rejected, copied, folders, [], entry=False, configured=False)
    assert set(tmp_path.iterdir()) == skills_before and not rejected.exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows 普通路径长度边界')
def test_windows_preflight_counts_utf16_characters_for_generated_files(tmp_path):
    # 汉字和补充平面字符均按 Windows 路径单位计数，不把一个 emoji 当成一个单位。
    root = _target_with_length(tmp_path, 205)
    module = '🧪' * 18
    with pytest.raises(ValueError, match='文件夹完整路径'):
        new_project._windows_path_preflight(root, [], [], [module], entry=True, configured=True)
    assert not root.exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows 普通路径长度边界')
def test_make_refuses_long_copied_files_without_partial_project_or_source_changes(tmp_path):
    src = synthetic_source(tmp_path)
    relative = '资料/本次附件/' + '长文件名' * 20 + '.md'
    source = write(src, relative, '只读来源不变')
    before = source.read_bytes()
    target = _target_with_length(tmp_path, 260 - len(relative) - 1)
    with pytest.raises(ValueError, match='更短的目标目录'):
        new_project.make(target, src, extra=[relative])
    assert not target.exists() and source.read_bytes() == before


@pytest.mark.skipif(os.name != 'nt', reason='Windows 普通路径长度边界')
def test_make_refuses_long_generated_module_builtin_before_target_mkdir(tmp_path):
    src = synthetic_source(tmp_path)
    name = '自定义长模块' * 4
    write(src, '模板配置.json', json.dumps({'version': 1, 'modules': [name]}, ensure_ascii=False))
    generated = '资料/' + name + '/内置'
    target = _target_with_length(tmp_path, 248 - len(generated) - 1)
    with pytest.raises(ValueError, match='更短的目标目录'):
        new_project.make(target, src)
    assert not target.exists()
