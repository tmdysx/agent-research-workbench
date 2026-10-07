"""模块页的左栏：蓝图（S0 · 总蓝图 · 模块）、戒律（AGENTS.md · 总戒律 · 模块）、源代码（代码地图）；别的模块顶上是本模块需求。"""
from fastapi.testclient import TestClient

from main import create_app


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _titles(t):
    return {s["title"]: [n.get("label") or n["name"] for n in s["items"]] for s in t["sections"]}


def test_blueprint_puts_s0_on_top_and_goals_in_number_order(proj):
    bp = proj.materials / "蓝图"
    _w(bp / "S0 终极目标.md", "# S0\n")
    _w(bp / "S1-2 乙.md", "| | 做什么 | 状态 |\n|---|---|---|\n| S2-1 | 甲 | 做完 |\n| S2-2 | 乙 | 没做 |\n")
    _w(bp / "S1-10 丙.md", "# S1-10\n")
    _w(bp / "S1-9 甲.md", "# S1-9\n")
    _w(bp / "待你定.md", "# 待你定\n")
    _w(bp / "戒律.md", "| 蓝-1 | 规矩 | 来历 |\n")
    with TestClient(create_app(proj)) as client:
        t = client.get("/api/modules/蓝图/tree").json()
    got = _titles(t)
    assert got["总的"] == ["项目全景", "S0 终极目标.md", "本模块戒律"]
    assert got["总蓝图"] == ["S1-2 乙.md", "S1-9 甲.md", "S1-10 丙.md"]        # S1-10 在 S1-9 后面
    assert got["其它"] == ["待你定.md"]                     # 10-07 起不再自动补 内置/
    assert t["default"] == "#项目全景"                                       # 统一全景；原 S0 文件仍能打开
    assert t["sections"][1]["items"][0]["note"] == "做完 1/2"


def test_rules_put_agents_on_top_and_module_rules_under_the_index(proj):
    _w(proj.root / "AGENTS.md", "- 通-1 不动文件\n")
    r = proj.materials / "戒律"
    _w(r / "1 通用戒律.md", "| | 规矩 | 从哪来 |\n|---|---|---|\n| 通-1 | 甲 | x |\n| 通-2 | 乙 | x |\n")
    _w(r / "2 项目戒律.md", "| 项-1 | 甲 | x |\n")
    _w(r / "3 模块戒律.md", "# 索引\n")
    _w(r / "戒律.md", "| 戒-1 | 甲 | x |\n")
    _w(proj.materials / "源代码" / "戒律.md", "| 源-1 | 甲 | x |\n| 源-2 | 乙 | x |\n")
    _w(r / ".链接.txt", "AGENTS.md\n资料/源代码/戒律.md\n")
    _w(proj.materials / "文献" / "戒律.md", "| 文-1 | 甲 | x |\n")
    _w(proj.materials / "文献" / "别的.md", "x\n")
    with TestClient(create_app(proj)) as client:
        t = client.get("/api/modules/戒律/tree").json()
    got = _titles(t)
    assert got["总的"] == ["AGENTS.md"] and t["default"] == "@/AGENTS.md"
    assert got["总戒律"] == ["1 通用戒律.md", "2 项目戒律.md"] and got["其它"] == ["3 模块戒律.md"]
    toc = {n["name"]: n for n in t["sections"][1]["items"]}
    assert toc["1 通用戒律.md"]["note"] == "2 条"
    # 「模块」那段现算：挂了链接的（源代码）、没挂的（文献）都在
    assert [(k["label"], k["note"]) for k in t["sections"][2]["items"]] == [("戒律模块", "1 条"), ("文献模块", "1 条"), ("源代码模块", "2 条")]
    with TestClient(create_app(proj)) as client:                       # 没挂链接的也能点开看，别的文件不行
        assert client.get("/api/modules/戒律/preview", params={"path": "@/资料/文献/戒律.md"}).status_code == 200
        assert client.get("/api/modules/戒律/preview", params={"path": "@/资料/文献/别的.md"}).status_code != 200


def test_code_module_opens_a_code_map_read_from_each_files_first_line(proj):
    b = proj.root / "backend"
    _w(b / "a.py", '"""管笔记的那块。\n\n细节……\n"""\nx = 1\n')
    _w(b / "b.py", "# 没有文档字符串，用第一句注释\nx = 2\n")
    _w(b / "c.py", "x = 3\n")
    _w(proj.root / "页.html", "<!DOCTYPE html>\n<!-- 整个网页 -->\n<html></html>\n")
    (proj.root / "开.bat").write_bytes('@echo off\r\nrem 双击打开\r\n'.encode("utf-8"))
    _w(proj.root / ".mcp.json", "{}")
    _w(proj.materials / "源代码" / ".链接.txt", "backend\n页.html\n开.bat\n.mcp.json\n")
    (proj.materials / "文献").mkdir()                    # 资料/ 先建了，起步模块不会自动建
    with TestClient(create_app(proj)) as client:
        t = client.get("/api/modules/源代码/tree").json()
        assert t["default"] == "#代码地图" and _titles(t)["总的"] == ["代码地图"]
        cm = client.get("/api/modules/源代码/codemap").json()
        ft = client.get("/api/modules/文献/tree").json()                              # 别的模块：顶上是本模块需求
        assert _titles(ft) == {"工作台": ["下载列表", "文献库"], "目录": []}
        assert ft["default"] == "#文献库:文献"
    says = {f["name"]: f["says"] for g in cm["groups"] for f in g["files"]}
    assert says == {"a.py": "管笔记的那块。", "b.py": "没有文档字符串，用第一句注释", "c.py": None,
                    "页.html": "整个网页", "开.bat": "双击打开", ".mcp.json": "给 agent 接上这个工具的配置（MCP）"}
    assert [g["dir"] for g in cm["groups"]] == ["", "backend"]            # 先这一层的文件，再进文件夹
