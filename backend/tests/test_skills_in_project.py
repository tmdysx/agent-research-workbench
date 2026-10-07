"""技能留在项目里：哪家 agent 进门都看得到、调得到。
作者 2026-09-30：「能不能把技能留在我的这个项目里，这样每一个agent接手这个项目都可以看到并且调用，
这样我这个平台才能服务更多的人，因为不是每一个人都用得起codex和你的」"""
import anyio
import shutil

import new_project
import skills
from project import CODE_DIR
from test_mcp import _call

START, END = skills.INDEX_START, skills.INDEX_END


def _lib(tmp_path):
    lib = tmp_path / "技能库"
    (lib / "甲").mkdir(parents=True)
    (lib / "甲" / "SKILL.md").write_text("---\nname: 甲\ndescription: 做甲的时候用 | 带竖线\n---\n# 甲\n照这个做", encoding="utf-8")
    (lib / "甲" / "参考.md").write_text("参考", encoding="utf-8")
    (lib / "没有说明书").mkdir()
    return lib


def test_index_in_agents_md(proj, tmp_path):
    lib = _lib(tmp_path)
    (proj.materials / "文献" / "技能").mkdir(parents=True)
    (proj.materials / "文献" / "技能" / "SKILL.md").write_text("---\nname: 文献\ndescription: 读论文时用\n---\n", encoding="utf-8")
    cat = skills.catalog(proj, lib)
    assert [(s["name"], s["path"], s["module"]) for s in cat] == [("甲", "技能库/甲/SKILL.md", ""), ("文献", "资料/文献/技能/SKILL.md", "文献")]
    assert skills.find(proj, "文献", lib)["path"] == "资料/文献/技能/SKILL.md" and skills.find(proj, "没这个", lib) is None
    agents = proj.root / "AGENTS.md"
    assert skills.write_index(proj, lib) is False                                  # 没有 AGENTS.md：不建
    agents.write_bytes(f"# 规矩\r\n\r\n作者写的一段\r\n\r\n{START}\r\n{END}\r\n\r\n后面也是作者的\r\n".encode("utf-8"))
    assert skills.write_index(proj, lib) is True
    text = agents.read_bytes().decode("utf-8")
    assert "| 甲 | 做甲的时候用 / 带竖线 | `技能库/甲/SKILL.md` |" in text                # 竖线不把表格拆坏
    assert "| 文献（文献 模块专属） | 读论文时用 | `资料/文献/技能/SKILL.md` |" in text
    assert text.startswith("# 规矩\r\n\r\n作者写的一段") and text.endswith("后面也是作者的\r\n")   # 标记外一个字不动，换行照旧
    assert skills.write_index(proj, lib) is False                                  # 没变不再写
    agents.write_text("# 没有标记\n", encoding="utf-8")
    assert skills.write_index(proj, lib) is False and agents.read_text(encoding="utf-8") == "# 没有标记\n"


def test_any_agent_reads_skills_through_mcp(proj):
    shutil.copytree(CODE_DIR / "技能库/自动化科研交互界面", proj.root / "技能库/自动化科研交互界面")
    (proj.root / "自动化" / "交接").mkdir(parents=True)
    (proj.root / "自动化" / "交接" / "H1 · 2026-09-30 · codex.md").write_text("# H1\n- 下一步：…", encoding="utf-8")
    listed, read, missing, overview = anyio.run(_call, proj, [
        ("list_skills", {}), ("read_skill", {"name": "自动化科研交互界面"}), ("read_skill", {"name": "没这个"}), ("get_overview", {}),
    ])
    assert "自动化科研交互界面" in listed and "技能库/自动化科研交互界面/SKILL.md" in listed
    assert read.startswith("# 技能库/自动化科研交互界面/SKILL.md") and "走之前" in read   # 全文，含交接单那一节
    assert "没有「没这个」" in missing
    assert "## 进门先读" in overview and "自动化/交接/H1 · 2026-09-30 · codex.md" in overview and "自动化科研交互界面" in overview


def test_new_project_brings_the_entry_files(tmp_path):
    target = tmp_path / "别人的项目"
    new_project.make(target, CODE_DIR)
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert START in agents and END in agents and "## 做事的流程" in agents and "通-1" in agents
    assert "项-1" not in agents and "被推翻过的设计" not in agents                   # 这个项目自己的不带过去
    assert "@AGENTS.md" in (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert (target / "治理" / "戒律" / "1 通用戒律.md").is_file() and (target / "治理" / "戒律" / "2 项目戒律.md").is_file()
    assert (target / "技能库" / "自动化科研交互界面" / "SKILL.md").is_file()
