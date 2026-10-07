"""新项目照内置清单继承（10-07 统一内置：勾了的文件夹、工作台随模块，项目里没有 内置/）和通用测试，不默认搬走外部安装、业务记录和历史。"""
import json

import pytest

import builtin
import new_project
from project import Project, ensure_skeleton


def _write(root, rel, text="示例"):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "通用源项目"
    _write(root, "backend/main.py", "# 应用核心\n")
    _write(root, "backend/tests/test_sample.py", "# 通用测试\n")
    _write(root, "backend/builtin_resources.json", json.dumps({"version": 1, "paths": ["工具库/下载/renderer"]}))
    _write(root, "工具库/下载/renderer/entry.js", "// 网页必需运行资源\n")
    _write(root, "工具库/下载/Blender/blender.exe", "本机安装，不默认继承")
    _write(root, "工具库/下载/未见过的软件/install.zip", "未知安装，不默认继承")
    _write(root, "模板.html", "<html>应用</html>")
    _write(root, "AGENTS.md", "# 接手说明\n\n## 核心\n通用规则\n")
    _write(root, "资料/天气/方法/样例.md", "天气模板")
    _write(root, "资料/天气/练习/示例/示例.txt", "嵌套模板")
    _write(root, "资料/天气/私有.md", "真实业务材料")
    _write(root, "治理/计划/S1-1/P1 原计划.md", "旧项目真实计划")
    _write(root, "自动化/交付/J1 历史.md", "真实交付历史")
    _write(root, "笔记/总览.md", "人的真实笔记")
    _write(root, "索引/state.db", "旧数据库")
    _write(root, "资料/测试/建模/model.blend", "真实建模试验")
    (root / "资料/空模块/方法").mkdir(parents=True)
    _write(root, "内置标记.json", json.dumps({"version": 1, "paths": ["资料/天气/方法", "资料/天气/练习/示例", "资料/空模块/方法"]}, ensure_ascii=False))
    return root


def test_mandatory_runtime_and_core_tests_survive_without_external_installs(source, tmp_path):
    target = tmp_path / "第二个项目"
    done = new_project.make(target, source)
    assert "backend/" in done
    for rel in ("backend/main.py", "backend/tests/test_sample.py", "工具库/下载/renderer/entry.js", "模板.html"):
        assert (target / rel).read_bytes() == (source / rel).read_bytes()
    for rel in ("工具库/下载/Blender", "工具库/下载/未见过的软件", "资料/天气/私有.md", "资料/测试/建模", "笔记/总览.md", "索引", "治理/计划/S1-1/P1 原计划.md", "自动化/交付/J1 历史.md"):
        assert not (target / rel).exists(), rel
    for module in ("想法", "蓝图", "戒律", "源代码", "测试", "论文", "文献", "实验", "汇报", "素材"):
        assert (target / "资料" / module).is_dir() and not (target / "资料" / module / "内置").exists(), module
    for rel in ("资料/天气/方法/样例.md", "资料/天气/练习/示例/示例.txt"):
        assert (target / rel).read_bytes() == (source / rel).read_bytes()
    assert (target / "资料/空模块/方法").is_dir()
    assert not [d for d in target.rglob("内置") if d.is_dir()]
    assert (target / "新项目复制清单.json").is_file()
    with pytest.raises(FileExistsError):
        new_project.make(target, source)
    assert (source / "工具库/下载/Blender/blender.exe").read_text(encoding="utf-8") == "本机安装，不默认继承"


def test_explicit_install_selection_is_for_this_copy_only(source, tmp_path):
    first = tmp_path / "第一代"
    second = tmp_path / "第二代"
    new_project.make(first, source, extra=["工具库/下载/Blender", "笔记/总览.md"])
    assert (first / "资料/天气/方法/样例.md").is_file()
    assert (first / "工具库/下载/Blender/blender.exe").is_file()
    assert (first / "笔记/总览.md").read_text(encoding="utf-8") == "人的真实笔记"
    assert not (first / "内置配置.json").exists()
    new_project.make(second, first)
    assert (second / "资料/天气/方法/样例.md").is_file()                     # 勾选跟着走到下一代
    assert (second / "资料/天气/练习/示例/示例.txt").read_text(encoding="utf-8") == "嵌套模板"
    assert not (second / "工具库/下载/Blender/blender.exe").exists()
    assert not (second / "笔记/总览.md").exists()
    assert not (second / "内置配置.json").exists()


def test_invalid_extra_selection_does_not_leave_half_a_new_project(source, tmp_path):
    target = tmp_path / "不能留下半个项目"
    with pytest.raises(builtin.Invalid):
        new_project.make(target, source, extra=["资料/不存在"])
    assert not target.exists()


def test_missing_required_resource_is_reported_before_creating_the_target(source, tmp_path):
    manifest = source / "backend/builtin_resources.json"
    manifest.write_text(json.dumps({"version": 1, "paths": ["工具库/下载/缺失运行库"]}), encoding="utf-8")
    target = tmp_path / "缺少运行库"
    with pytest.raises(builtin.Invalid):
        new_project.make(target, source)
    assert not target.exists()


def test_startup_does_not_recreate_a_deleted_starter_module(source, tmp_path):
    target = tmp_path / "新项目"
    new_project.make(target, source)
    testing = target / "资料/实验"
    assert testing.is_dir()
    # 模拟已通过回收站移走；临时测试只把目录改名，不碰真实文件。
    testing.rename(target / "移走的实验")
    ensure_skeleton(Project(target))
    assert not testing.exists()


def test_source_without_any_notes_still_creates_an_empty_notes_folder(tmp_path):
    src = tmp_path / "尚未写过笔记的源项目"
    _write(src, "backend/main.py", "# 程序")
    _write(src, "backend/builtin_resources.json", json.dumps({"version": 1, "paths": []}))
    _write(src, "模板.html", "<html>应用</html>")
    target = tmp_path / "新项目"
    new_project.make(target, src)
    assert not (src / "笔记").exists()
    assert (target / "笔记").is_dir() and not (target / "笔记/内置").exists()
    assert not (target / "笔记/总览.md").exists()


def test_real_new_project_keeps_public_tool_links_and_agent_catalog_usable(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import links
    import toolbox
    from main import create_app
    from project import CODE_DIR

    target = tmp_path / "通用工具仍可查看的新项目"
    new_project.make(target, CODE_DIR)
    for rel in ("工具库/网页链接.md", "工具库/智能体.md"):
        assert (target / rel).is_file(), rel
        assert (target / rel).read_bytes() == (CODE_DIR / rel).read_bytes()
    # 应用代码仍从当前测试进程导入，把两项默认资料定位到真实复制结果。
    # 工具页走正常接口读取和解析，不给它注入示例返回值。
    monkeypatch.setattr(links, "FILE", target / "工具库/网页链接.md")
    monkeypatch.setattr(toolbox, "CATALOG", target / "工具库/智能体.md")
    with TestClient(create_app(Project(target))) as client:
        linked = client.get("/api/tools/links")
        agents = client.get("/api/tools/catalog")
        assert linked.status_code == 200 and agents.status_code == 200
        assert any(g["items"] for g in linked.json()["groups"])
        assert any(g["items"] for g in agents.json()["groups"])
        assert linked.json()["file"] == "工具库/网页链接.md"
        assert agents.json()["file"] == "工具库/智能体.md"
