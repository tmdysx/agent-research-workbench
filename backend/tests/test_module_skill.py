"""模块专属技能放在模块里：资料/<模块>/技能/SKILL.md。
作者 2026-09-28：「这个模块要有自己的skill」「模块专属技能就放模块里吧」。"""
import anyio
import shutil
import pytest
from fastapi.testclient import TestClient

import workorders
from main import create_app
from project import CODE_DIR
from test_mcp import _call

SKILL = "---\nname: 文献\ndescription: 文献模块怎么做事\n---\n# 文献模块的技能\n\n- 按页分段\n"


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "假的用户目录"
    monkeypatch.setenv("RC_HOME", str(h))              # 「本机」= 这里，不碰真的 ~/.claude
    return h


def test_module_skill_lives_in_the_module(proj, home):
    shutil.copytree(CODE_DIR / "技能库/交付自查", proj.root / "技能库/交付自查")
    d = proj.materials / "文献" / "技能"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(SKILL, encoding="utf-8")
    (proj.materials / "论文").mkdir()
    with TestClient(create_app(proj)) as client:
        lst = {s["id"]: s for s in client.get("/api/skills").json()}
        s = lst["模块:文献"]
        assert (s["module"], s["name"], s["where"], s["project"]) == ("文献", "文献", "资料/文献/技能/", None)
        assert "模块:论文" not in lst and lst["交付自查"]["module"] == ""                  # 没写技能的模块不列
        r = client.post("/api/skills/模块:文献/install", json={"where": "project"}).json()
        assert (proj.root / ".claude" / "skills" / "文献" / "SKILL.md").read_text(encoding="utf-8") == SKILL   # 装过去叫模块名
        assert {x["id"]: x for x in r["skills"]}["模块:文献"]["project"] == "same"
        assert client.post("/api/skills/模块:没有/install", json={"where": "project"}).status_code == 404
        assert client.post("/api/skills/模块:文献/fork").status_code == 404               # 模块的就在模块里改
        t = client.get("/api/modules/文献/tree").json()
        tree = next(x for x in t["sections"] if x["title"] == "目录")["items"]   # 10-06 起文献是工作台模块：技能在「目录」里
        assert "技能" in [n["path"] for n in tree]
    assert "资料/文献/技能/SKILL.md" in workorders.derive(proj, ["文献"])["materials"]     # 开工单装修文献：技能自动带上
    over = anyio.run(_call, proj, [("get_overview", {})])[0]
    assert "技能/SKILL.md" in over                                                       # 给 agent 的规矩里写着先读它
