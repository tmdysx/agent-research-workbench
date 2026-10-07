"""通用内容工作台只继承窄模板和运行资源，用合成项目核验两代及配置边界。"""
import hashlib
import json
from pathlib import Path

import pytest

import new_project
import project


BACKEND = Path(__file__).resolve().parent.parent
GENERIC_ROOTS = ["资料/文献/工作台", "资料/论文/工作台"]          # 10-07 统一内置：内置/通用 → 工作台/
COMMON_MODULES = ["文献", "论文", "测试", "PPT"]
PRIVATE_PATHS = [
    "资料/文献/原文/L1 合成原文.pdf",
    "资料/文献/解读/L1/文本/笔记.md",
    "资料/文献/解读/L1/批注.json",
    "资料/文献/下载清单.md",
    "资料/论文/正文/引言/本次正文.md",
    "资料/论文/正文/方法/本次图.png",
    "资料/论文/项目文书/本次文书.md",
    "资料/论文/历史/内容工作台/旧正文.md",
    "资料/测试/数据集/本次.csv",
    "资料/测试/实验结果/本次结果.json",
    "资料/测试/测试代码/本次.py",
    "资料/测试/测试记录/本次记录.md",
    "资料/测试/建模/本次模型.blend",
    "笔记/总览.md",
    "笔记/历史/旧笔记.md",
    "笔记/日志/2026-10.md",
    "自动化/日志/运-0001.md",
    "自动化/交付/J1 本次.md",
    "治理/计划/S1-1/P1 本次.md",
    "工具库/下载/Blender/blender.exe",
    "索引/state.db",
    "存档/C1/副本.md",
    "回收站/X1/原件.md",
]


def write(root, rel, text="原创合成模板"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture
def synthetic_source(tmp_path):
    """只读源代码配置；所有材料、模板正文和业务示例均在 TEMP 造出。"""
    root = tmp_path / "合成内容源"
    profiles = read_json(BACKEND / "template_profiles.json")
    # 本组核无科研方法包的合法历史模板。真实 92 方法闭包由独立两代检查覆盖。
    for cfg in profiles['profiles'].values():
        cfg['builtin_skill_ids'] = []
    write(root, "backend/template_profiles.json", json.dumps(profiles, ensure_ascii=False))
    write(root, "backend/main.py", "# 合成应用核心\n")
    write(root, "backend/tests/test_sample.py", "# 合成通用测试\n")
    write(root, "backend/builtin_resources.json", json.dumps({"version": 1, "paths": ["内容工作台.js"]}))
    write(root, "内容工作台.js", "// 合成工作台运行资源\n")
    write(root, "模板.html", "<html>合成网页</html>")
    write(root, "AGENTS.md", "# 合成接手说明\n\n## 核心\n通用规则\n")
    roots, skills = set(), set()
    for cfg in profiles["profiles"].values():
        roots.update(cfg["template_roots"])
        skills.update(cfg["skills"])
        for rel in cfg["module_skills"]:
            write(root, rel + "/SKILL.md", "# 合成模块技能\n")
    for rel in sorted(roots):
        write(root, rel + "/示例.md")
    # 10-07 统一内置：方法/ 这些靠清单勾上才带（工作台随模块带，不用勾），跟真项目搬家后一样
    write(root, "内置标记.json", json.dumps({"version": 1, "paths": sorted(r for r in roots if not r.endswith("/工作台"))}, ensure_ascii=False))
    for name in sorted(skills):
        write(root, f"技能库/{name}/SKILL.md", f"# 合成技能 {name}\n")
    write(root, "技能库/业务/manifest.json", json.dumps({"schema": 1, "groups": [], "items": []}))
    for module in COMMON_MODULES:
        if module == '文献':
            sections = [{'id': k, 'title': t, 'en': en, 'kind': k, 'folder': folder, 'templates': []}
                        for k, t, en, folder in [('downloads', '下载列表', 'Downloads', '下载清单.md'),
                                                ('reading', '精读', 'Reading', '解读'),
                                                ('originals', '原文', 'Originals', '原文'),
                                                ('notes', '专属笔记', 'Notes', '解读')]]
        else:
            folders = (['正文/' + name for name in ['引言', '相关工作', '方法', '实验', '超参数', '应用', '结果', '未来展望', '参考文献']]
                       if module == '论文' else ['材料', '大纲', '幻灯片', '导出', '检查'] if module == 'PPT'
                       else ['数据集', '实验结果', '测试代码', '测试记录'])
            sections = [{'id': f's{i}', 'title': folder.split('/')[-1], 'en': f'Section {i}',
                         'kind': 'documents', 'folder': folder, 'templates': []} for i, folder in enumerate(folders)]
        write(root, f"资料/{module}/工作台/工作台.json", json.dumps({"version": 1, "sections": sections}, ensure_ascii=False))
        write(root, f"资料/{module}/工作台/README.md", f"# 合成{module}通用说明\n")
        write(root, f"资料/{module}/工作台/README.en.md", "# Synthetic generic guide\n")
    write(root, "资料/论文/工作台/模板/引言.md", "# 引言\n原创占位，不是工作正文。\n")
    write(root, "资料/测试/工作台/模板/检查脚本.py", "# 合成检查模板；不执行\n")
    write(root, "资料/文献/方法/科研/来源包/旧来源.md", "旧科研合成来源包")
    for module in ("写论文", "宣传片", "写小说"):
        write(root, f"资料/{module}/方法/业务样板.md", "合成业务样板")
    for rel in PRIVATE_PATHS:
        write(root, rel, "不得默认带走的合成私有标记")
    return root


def test_profiles_declare_narrow_generic_content_and_runtime():
    profiles = read_json(BACKEND / "template_profiles.json")["profiles"]
    assert profiles["general"]["modules"] == COMMON_MODULES
    assert "实验" in profiles["research"]["modules"]
    assert "数据与分析" in profiles["research"]["modules"]
    assert profiles["business"]["modules"] == ["写论文", "宣传片", "写小说", "PPT"]
    for cfg in profiles.values():
        assert all(rel in cfg["template_roots"] for rel in GENERIC_ROOTS)
        assert "资料/测试/工作台" in cfg["template_roots"]
        assert not any("内置" in r.split("/") for r in cfg["template_roots"])            # 10-07 起没有 内置/ 了
    for name in ("general", "business"):
        roots = profiles[name]["template_roots"]
        assert "资料/文献" not in roots and "资料/文献/方法" not in roots
        assert "资料/论文" not in roots and "资料/论文/方法" not in roots
    assert "内容工作台.js" in read_json(BACKEND / "builtin_resources.json")["paths"]


@pytest.mark.parametrize("profile", ["general", "research", "business"])
def test_production_copier_inherits_generic_content_and_runtime_for_two_generations(synthetic_source, tmp_path, profile):
    source = synthetic_source
    first, second = tmp_path / (profile + "一代"), tmp_path / (profile + "二代")
    new_project.make(first, source, profile=profile)
    # 第一代工作产生的新材料仍不得成为第二代的内置。
    write(first, "资料/论文/正文/引言/一代新增.md", "第一代真实工作占位")
    write(first, "资料/论文/正文/方法/一代新增图.png", "第一代图占位")
    write(first, "资料/测试/测试记录/一代新增.md", "第一代运行记录占位")
    write(first, "笔记/总览.md", "第一代人的笔记占位")
    new_project.make(second, first)
    expected = ["内容工作台.js", "资料/论文/工作台/模板/引言.md",
                "资料/测试/工作台/模板/检查脚本.py"]
    expected += [f"资料/{module}/工作台/{name}" for module in COMMON_MODULES
                 for name in ("工作台.json", "README.md", "README.en.md")]
    for descendant in (first, second):
        for rel in expected:
            assert (descendant / rel).read_bytes() == (source / rel).read_bytes(), rel
        for module in COMMON_MODULES:
            assert (descendant / "资料" / module).is_dir()
        for module in ('论文', '测试', 'PPT'):
            configuration = read_json(descendant / f'资料/{module}/工作台/工作台.json')
            for section in configuration['sections']:
                folder = descendant / '资料' / module / section['folder']
                assert folder.is_dir()
                assert not (folder / '.gitkeep').exists()
        cfg = read_json(descendant / "模板配置.json")
        assert cfg["profile"] == profile
        if profile == "general":
            assert cfg["modules"] == COMMON_MODULES
        else:
            assert cfg["modules"] == read_json(source / "backend/template_profiles.json")["profiles"][profile]["modules"]
        for rel in PRIVATE_PATHS:
            if descendant == first and rel == "笔记/总览.md":
                continue  # 上面明确造出的第一代工作记录。
            assert not (descendant / rel).exists(), rel
        manifest = read_json(descendant / "新项目复制清单.json")
        copied = {row["path"] for row in manifest["files"]}
        assert set(expected) <= copied
        assert not any(rel in copied for rel in PRIVATE_PATHS)
        old_source = descendant / "资料/文献/方法/科研/来源包/旧来源.md"
        assert old_source.exists() == (profile == "research")
        for module in ("写论文", "宣传片", "写小说"):
            assert (descendant / f"资料/{module}/方法/业务样板.md").exists() == (profile == "business")
    assert not (second / "资料/论文/正文/引言/一代新增.md").exists()
    assert not (second / "资料/论文/正文/方法/一代新增图.png").exists()
    assert not (second / "资料/测试/测试记录/一代新增.md").exists()


@pytest.mark.parametrize("old_modules", [[], ["学习"]])
def test_generated_general_configuration_gains_starters_only_in_new_descendants(synthetic_source, tmp_path, old_modules):
    source = synthetic_source
    # 这条只看通用项目自己的起步模块：只勾通用模块（勾了东西的业务模块会默认带上，见 test_builtin_layout）
    marks = read_json(source / "内置标记.json")
    marks["paths"] = [p for p in marks["paths"] if p.split("/")[1] in COMMON_MODULES + project.FIXED_NAMES]
    write(source, "内置标记.json", json.dumps(marks, ensure_ascii=False))
    original = write(source, "模板配置.json", json.dumps({"version": 1, "profile": "general", "modules": old_modules,
                     "module_skills": [], "module_labels": {"学习": "Learning"}, "label": "已有通用项目"}, ensure_ascii=False))
    revision = hashlib.sha256(original.read_bytes()).hexdigest()
    assert project.template_start_names(source) == old_modules
    first, second = tmp_path / "旧配置的新后代", tmp_path / "继续新建的后代"
    new_project.make(first, source)
    new_project.make(second, first)
    for descendant in (first, second):
        cfg = read_json(descendant / "模板配置.json")
        assert cfg["modules"] == old_modules + COMMON_MODULES
        assert cfg["module_labels"] == {"学习": "Learning"}
        assert cfg["label"] == "已有通用项目"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == revision
    assert project.template_start_names(source) == old_modules


@pytest.mark.parametrize("path", ["资料/文献", "资料/文献/方法", "资料/文献/技能/子目录",
                                  "资料\\文献\\技能", "资料/ 文献/技能", "资料/文献/技能/"])
def test_profile_module_skills_refuses_wide_or_noncanonical_paths_before_creation(synthetic_source, tmp_path, path):
    source = synthetic_source
    manifest = source / "backend/template_profiles.json"
    cfg = read_json(manifest)
    cfg["profiles"]["general"]["module_skills"] = [path]
    manifest.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    target = tmp_path / "不留下半个项目"
    with pytest.raises(ValueError, match="模块技能路径"):
        new_project.make(target, source, profile="general")
    assert not target.exists()


def test_profile_module_skill_must_be_a_directory(synthetic_source, tmp_path):
    source = synthetic_source
    write(source, "资料/假的/技能", "普通文件，不能冒充技能目录")
    manifest = source / "backend/template_profiles.json"
    cfg = read_json(manifest)
    cfg["profiles"]["general"]["module_skills"] = ["资料/假的/技能"]
    manifest.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    target = tmp_path / "技能不是目录"
    with pytest.raises(ValueError, match="技能目录"):
        new_project.make(target, source, profile="general")
    assert not target.exists()


def test_generated_module_skills_uses_the_same_narrow_validation(synthetic_source, tmp_path):
    source = synthetic_source
    write(source, "模板配置.json", json.dumps({"version": 1, "profile": "general", "modules": [],
                     "module_skills": ["资料/文献"], "module_labels": {}}))
    target = tmp_path / "旧宽根不能传给后代"
    with pytest.raises(ValueError, match="模块技能路径"):
        new_project.make(target, source)
    assert not target.exists()


@pytest.mark.parametrize('folder', ['../../笔记', '内置/通用', '正文/VENV', '正文/../项目文书', '正文/CON'])
def test_invalid_workspace_folder_refused_before_project_creation(synthetic_source, tmp_path, folder):
    path = synthetic_source / '资料/论文/工作台/工作台.json'
    cfg = read_json(path)
    cfg['sections'][0]['folder'] = folder
    path.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
    target = tmp_path / '坏目录不能留下半个项目'
    with pytest.raises(ValueError):
        new_project.make(target, synthetic_source, profile='general')
    assert not target.exists()
