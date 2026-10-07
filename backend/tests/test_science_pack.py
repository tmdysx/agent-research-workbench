"""两版模块和科研能力隔离：合成中文模板，不运行科研或启动员工。"""
from pathlib import Path
import hashlib
import json
import re
import shutil
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

import new_project
import skills
from main import create_app
from project import CODE_DIR, Project, module_dirs
from test_release import COMMON_SKILLS, GENERAL_MODULES, RESEARCH_MODULES, SCIENCE_SKILLS, synthetic_source, write


@pytest.fixture
def source(tmp_path):
    return synthetic_source(tmp_path)


def require_science_profile():
    """只有明确声明为纯通用发行版时跳过；源码、科研版缺资源仍是错误。"""
    f = CODE_DIR / "模板配置.json"
    if f.is_file():
        assert not f.is_symlink() and not f.is_junction(), "模板配置须为普通文件"
        cfg = json.loads(f.read_text(encoding="utf-8-sig"))
        if cfg.get("version") == 1 and cfg.get("profile") == "general":
            pytest.skip("纯通用发行版按模板配置不带科研资源")


@pytest.mark.parametrize("profile,names", [("general", GENERAL_MODULES), ("research", RESEARCH_MODULES)])
def test_profile_modules_and_formal_skills_are_visible_in_the_started_project(source, tmp_path, profile, names):
    target = tmp_path / profile
    new_project.make(target, source, profile=profile)
    assert set(module_dirs(Project(target))) == set(names)
    lib = target / "技能库"
    found = {r["name"] for r in skills.catalog(Project(target), lib) if r["path"].startswith("技能库/")}
    expected = set(COMMON_SKILLS + (SCIENCE_SKILLS if profile == "research" else []))
    assert found == expected
    for name in expected:
        assert (lib / name / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname:")
    assert (target / "插件/安装说明.md").is_file()
    assert (target / "backend/tests/test_sample.py").is_file()
    config = json.loads((target / "模板配置.json").read_text(encoding="utf-8"))
    assert config["profile"] == profile and set(config["modules"]) == set(names)
    with TestClient(create_app(Project(target), tasks=False, global_keys=False)) as client:
        state = client.get("/api/state")
        assert state.status_code == 200
        assert {m["name"] for m in state.json()["modules"]} == set(names)
    assert not (target / "资料/天气").exists()


def test_general_second_generation_stays_general_after_startup(source, tmp_path):
    first = tmp_path / "通用一代"
    second = tmp_path / "通用二代"
    new_project.make(first, source, profile="general")
    new_project.make(second, first)
    assert set(module_dirs(Project(second))) == set(GENERAL_MODULES)
    with TestClient(create_app(Project(second), tasks=False, global_keys=False)) as client:
        assert {m["name"] for m in client.get("/api/state").json()["modules"]} == set(GENERAL_MODULES)
        assert {s['id'] for s in client.get('/api/skills').json()} == set(COMMON_SKILLS)
    assert not list((second / "技能库").glob("科研-*"))
    assert json.loads((second / "模板配置.json").read_text(encoding="utf-8"))["profile"] == "general"


def test_research_second_generation_keeps_the_module_skill_entry(source, tmp_path):
    first = tmp_path / "科研一代"
    second = tmp_path / "科研二代"
    new_project.make(first, source, profile="research")
    new_project.make(second, first)
    rel = "资料/文献/技能/SKILL.md"
    assert (second / rel).is_file()
    assert (second / rel).read_bytes() == (first / rel).read_bytes()
    assert (second / "技能库/科研-文献/SKILL.md").is_file()
    assert set(module_dirs(Project(second))) == set(RESEARCH_MODULES)
    entries = skills.catalog(Project(second), second / "技能库")
    assert any(row["path"] == rel for row in entries)


def test_ordinary_new_project_keeps_all_builtin_and_only_the_current_extra(source, tmp_path):
    first = tmp_path / "普通新项目"
    second = tmp_path / "普通二代"
    extra = "资料/天气/本次材料.md"
    new_project.make(first, source, extra=[extra])
    assert (first / "资料/天气/方法/天气模板.md").is_file()
    assert (first / extra).is_file()
    new_project.make(second, first)
    assert (second / "资料/天气/方法/天气模板.md").is_file()
    assert not (second / extra).exists()


def test_research_version_keeps_module_skill_references_and_mit_attribution(source, tmp_path):
    target = tmp_path / "科研包"
    new_project.make(target, source, profile="research")
    module = (target / "资料/文献/技能/SKILL.md").read_text(encoding="utf-8")
    assert "技能库/科研-文献/SKILL.md" in module
    assert (target / "技能库/科研-文献/SKILL.md").is_file()
    for name in SCIENCE_SKILLS:
        assert "MIT License" in (target / "技能库" / name / "LICENSE-MIT.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("quote", ["", '"'])
def test_chinese_skill_metadata_is_findable_and_forks_have_distinct_labels(tmp_path, monkeypatch, quote):
    monkeypatch.setenv("RC_HOME", str(tmp_path / "假的用户目录"))
    p = Project(tmp_path)
    lib = tmp_path / "技能库"
    original = write(tmp_path, "技能库/research-route/SKILL.md",
                     "---\nname: research-route\ndescription: 科研阶段与路线\nmetadata:\n"
                     f"  display_name: {quote}科研路线{quote}\n  version: 1.0.0\n---\n# 科研路线\n")
    raw = original.read_bytes()
    row = skills.find(p, "科研路线", lib)
    assert row and row["id"] == "research-route" and row["agent_name"] == "research-route"
    assert skills.find(p, "research-route", lib)["name"] == "科研路线"
    assert skills.list_skills(p, lib)[0]["name"] == "科研路线"
    copied_ids = [skills.fork(p, "research-route", lib) for _ in range(2)]
    rows = {row["id"]: row for row in skills.catalog(p, lib)}
    labels = [rows[sid]["name"] for sid in copied_ids]
    assert len(set(labels + ["科研路线"])) == 3
    for sid, label in zip(copied_ids, labels):
        assert "科研路线" in label
        assert skills.find(p, label, lib)["id"] == sid
        assert rows[sid]["agent_name"] == sid
    assert original.read_bytes() == raw


def test_research_module_labels_survive_ordinary_second_generation(source, tmp_path):
    first, second = tmp_path / "有英文科研一代", tmp_path / "有英文科研二代"
    expected = {"数据与分析": "Data & Analysis", "投稿与返修": "Submission & Revision"}
    new_project.make(first, source, profile="research")
    new_project.make(second, first)
    for target in (first, second):
        cfg = json.loads((target / "模板配置.json").read_text(encoding="utf-8"))
        assert cfg["module_labels"] == expected
        with TestClient(create_app(Project(target), tasks=False, global_keys=False)) as client:
            rows = {m["name"]: m for m in client.get("/api/state").json()["modules"]}
            assert {name: rows[name]["en"] for name in expected} == expected


def test_diy_label_comes_from_template_and_keeps_a_human_override(source, tmp_path):
    f = source / "backend/template_profiles.json"
    cfg = json.loads(f.read_text(encoding="utf-8"))
    cfg["profiles"]["general"]["modules"].append("天气")
    cfg["profiles"]["general"]["module_labels"] = {"天气": "Weather Dashboard"}
    cfg["profiles"]["general"]["template_roots"].append("资料/天气/方法")
    f.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    target = tmp_path / "非科研的声明模块"
    new_project.make(target, source, profile="general")
    with TestClient(create_app(Project(target), tasks=False, global_keys=False)) as client:
        rows = {m["name"]: m for m in client.get("/api/state").json()["modules"]}
        assert rows["天气"]["en"] == "Weather Dashboard"
        assert not (set(rows) & (set(RESEARCH_MODULES) - set(GENERAL_MODULES)))
        assert client.put("/api/modules/天气/info", json={"en": "Local Weather"}).status_code == 200
    with TestClient(create_app(Project(target), tasks=False, global_keys=False)) as client:
        rows = {m["name"]: m for m in client.get("/api/state").json()["modules"]}
        assert rows["天气"]["en"] == "Local Weather"


def test_installed_science_skills_have_resolvable_local_references_and_names(tmp_path):
    require_science_profile()
    cfg = new_project.profile_config(CODE_DIR, "research")
    science = [name for name in cfg["skills"] if name.startswith("research-")]
    assert len(science) == 9
    lib = tmp_path / "技能库"
    shutil.copytree(CODE_DIR / "技能库" / "业务", lib / "业务")      # 新项目整个技能库一起带：科研技能会指向业务技能（10-06）
    for name in science:
        source_dir = CODE_DIR / "技能库" / name
        shutil.copytree(source_dir, lib / name)
        assert "MIT License" in (lib / name / "LICENSE.txt").read_text(encoding="utf-8")
        for doc in (lib / name).rglob("*.md"):
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
                if link.startswith(("http:", "https:", "#", "mailto:")):
                    continue
                rel = unquote(link.split("#", 1)[0]).strip().removeprefix("<").removesuffix(">")   # [x](<带空格的路径>)
                target = (doc.parent / rel).resolve()
                assert target.is_relative_to(lib.resolve()) and target.is_file(), (doc, link)
    p = Project(tmp_path)
    for row in skills.catalog(p, lib):
        if row["id"] not in science:                       # 一起带上的业务技能另有测试
            continue
        assert re.search("[\u4e00-\u9fff]", row["name"]), row["name"]
        assert skills.find(p, row["name"], lib)["id"] == row["id"]


def test_retained_public_source_snapshots_match_the_pinned_fingerprints():
    require_science_profile()
    f = CODE_DIR / "资料/文献/方法/科研/来源/sources.lock.json"           # 10-07 统一内置：内置/科研 → 方法/科研
    cfg = json.loads(f.read_text(encoding="utf-8"))
    retained = []
    for repo in cfg["repositories"]:
        assert repo["license"] == "MIT" and re.fullmatch(r"[a-f0-9]{40}", repo["commit"])
        rows = [row for row in repo["files"] if row["retained_in_release"]]
        assert any(row["source_path"] == repo["license_path"] for row in rows)
        for row in rows:
            target = CODE_DIR / row["local_path"]
            assert target.resolve().is_relative_to(f.parent.resolve())
            raw = target.read_bytes()
            assert len(raw) == row["bytes"]
            assert hashlib.sha256(raw).hexdigest() == row["sha256"]
            assert f"/blob/{repo['commit']}/" in row["url"]
        retained.extend(rows)
    assert retained
