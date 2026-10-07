"""一条线：想法 → 需求 → 蓝图 → 戒律，分「总的」和「模块」两层；自动化一次装修一个模块。
作者 2026-09-27：「我们现在这个自动化是模块装修的自动化」「除了蓝图和戒律还有需求……这决定了施工的方向」
「把想法变成需求模块也要优化」。"""
import anyio
from fastapi.testclient import TestClient

import blueprint
import deliveries
import ideas
import requirements
import store
import tools
from main import create_app
from test_mcp import _call

NEED = ("# 文献 · 需求\n\n**文献模块装修成轻量的阅读管理。**\n\n为了：S1-1、S1-4\n\n"
        "| | 要什么功能 | 要什么效果（打开能看见什么） | 来自 |\n|---|---|---|---|\n"
        "| 需-1 | 文献库 | 拖进来就多一篇 | |\n| 需-2 | 左右对照读 | 左原文右译文，照 资料/文献/格式说明.md 写 | |\n| 需-3 | 导出引用 |  | |\n")
PLAN = ("# 文献 · 蓝图\n\n怎么算装好：需求里每一条都达到。\n\n"
        "| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"
        "| S2-1 | 文献列表 | 需-1 | 拖一篇进来多一行 | 做完 |\n"
        "| S2-2 | 阅读页（用 pdf.js） | 需-2 | 翻到第 3 页右边是第 3 页 | 没做 |\n"
        "| S2-3 | 顺手加个图标 |  | 看得见 | 没做 |\n")


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _setup(proj, monkeypatch, tmp_path):
    _w(proj.materials / "文献" / "需求.md", NEED)
    _w(proj.materials / "文献" / "蓝图.md", PLAN)
    _w(proj.materials / "文献" / "格式说明.md", "一篇一个文件夹")
    _w(proj.materials / "文献" / "戒律.md", "| | 规矩 | 从哪来 |\n|---|---|---|\n| 文-1 | 原文不改 | 09-27 |\n")
    _w(proj.materials / "蓝图" / "S0 终极目标.md", "# S0\n\n**做个工具。**\n\n| S1 | 目标 |\n|---|---|\n| S1-1 看得懂 | x |\n")
    _w(proj.materials / "蓝图" / "S1-1 看得懂.md", "# S1-1 看得懂\n\n**看得懂。**\n\n| | 做什么 | 状态 |\n|---|---|---|\n| S2-1 | 总览 | 做完 |\n")
    lib = tmp_path / "工具库"
    _w(lib / "T10 pdf.js.md", "---\n编号: T10\n名字: pdf.js\n类别: 外部工具\n一句话: 看 PDF\n检查:\n---\n# T10\n")
    monkeypatch.setattr(tools, "LIB", lib)
    tools.forget()


def test_module_needs_drive_the_module_blueprint(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    import deliveries
    monkeypatch.setattr(deliveries, "DEFAULT_PASS", False)          # 这条测人手验收 / 打回：关掉默认通过
    bp = blueprint.pyramid(proj)
    g = blueprint.find(bp, "文献")
    assert [g["code"], g["kind"], g["one_line"], g["modules"]] == ["文献", "module", "文献模块装修成轻量的阅读管理", ["文献"]]
    assert [(s["code"], s["for"], s["how"]) for s in g["subs"]][:2] == [("S2-1", ["需-1"], "拖一篇进来多一行"), ("S2-2", ["需-2"], "翻到第 3 页右边是第 3 页")]
    assert [x["code"] for x in bp["goals"]] == ["S1-1"] and not bp["problems"]           # 模块的不混进总蓝图
    v = requirements.view(proj, "文献", bp)
    assert [(q["code"], q["state"]) for q in v["reqs"]] == [("需-1", "达到"), ("需-2", "还没做"), ("需-3", "还没有要做的件")]
    assert v["loose"] == ["S2-3"] and (v["met"], v["total"], v["done"], v["items"]) == (1, 3, 1, 3)
    assert requirements.read(proj, "文献")["for"] == ["S1-1", "S1-4"]

    # 加一条、补一条；号不回收
    assert requirements.add(proj, "文献", "搜得到", "搜标题里的词能搜到", source="想-1") == "需-4"
    requirements.supplement(proj, "文献", "需-3", "导出的 .bib 能编译", source="想-2")
    r = {q["code"]: q for q in requirements.read(proj, "文献")["reqs"]}
    assert r["需-4"]["source"] == "想-1" and r["需-3"]["effect"] == "补：导出的 .bib 能编译" and r["需-3"]["source"] == "想-2"

    # 模块蓝图里的一件能交付、验收；交付单写上为了哪条需求
    c = store.connect(proj.db_path)
    store.migrate(c)
    j = deliveries.deliver(c, proj, goal="文献", sub="S2-2", did="阅读页", checks=[{"name": "翻页", "ok": True}], by="agent:t")
    assert j["for"] == ["需-2"] and "为了 文献 需-2" in j["body"]
    deliveries.accept(c, proj, j["code"])
    c.close()
    assert requirements.view(proj, "文献")["reqs"][1]["state"] == "达到"
    assert "做完（J1 验收）" in (proj.materials / "文献" / "蓝图.md").read_text(encoding="utf-8")

    # 还没写的模块：建空的样子
    (proj.materials / "论文").mkdir()
    assert requirements.skeleton(proj, "论文") == ["资料/论文/需求.md", "资料/论文/蓝图.md"]
    assert requirements.skeleton(proj, "论文") == []
    assert requirements.modules(proj) == ["文献", "论文"] or requirements.modules(proj) == sorted(["文献", "论文"])


def test_ideas_come_in_one_door_and_each_gets_a_destination(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    with TestClient(create_app(proj)) as client:
        e = client.post("/api/notes/文献", json={"text": "文献要能按年份排", "idea": True}).json()
        x = ideas.get(proj, e["idea"])
        assert (x["code"], x["source"], x["about"], x["state"]) == ("想-1", f"笔记 {e['id']}", "文献", "待整理")
        assert client.post("/api/notes/总览", json={"text": "想要个深色的封面", "idea": True}).json()["idea"] == "想-2"
        assert ideas.get(proj, "想-2")["about"] == "整个项目"
        client.post("/api/ideas", json={"text": "不许把 PDF 传上网", "about": "文献"})
        client.post("/api/ideas", json={"text": "导出要能编译", "about": "文献"})
        client.post("/api/ideas", json={"text": "做个手机版", "about": "整个项目"})
        assert client.post("/api/ideas", json={"text": "x", "about": "没有这个"}).status_code == 400

        c = store.connect(proj.db_path)
        for bad in ([{"to": "需求", "module": "文献", "func": "排序", "effect": "按年份"}],                 # 没理由
                    [{"to": "需求", "module": "没有", "func": "a", "effect": "b", "reason": "r"}],
                    [{"to": "需求", "module": "文献", "req": "需-9", "add": "x", "reason": "r"}],
                    [{"to": "总的", "what": "随便", "text": "x", "reason": "r"}]):
            try:
                ideas.suggest(c, proj, "想-1", bad, by="agent:t")
                raise AssertionError(bad)
            except store.Refused:
                pass
        ideas.suggest(c, proj, "想-1", [{"to": "需求", "module": "文献", "func": "按年份排", "effect": "点「年份」列表就按年份排", "reason": "文献列表要的"},
                                         {"to": "需求", "module": "文献", "req": "需-1", "add": "能按年份排", "reason": "也可以算文献库的一部分"}], by="agent:t")
        ideas.suggest(c, proj, "想-3", [{"to": "戒律", "module": "文献", "rule": "不把 PDF 传到外网", "reason": "是规矩不是功能"}], by="agent:t")
        ideas.suggest(c, proj, "想-4", [{"to": "需求", "module": "文献", "req": "需-3", "add": "导出的 .bib 能编译", "reason": "补进导出引用"}], by="agent:t")
        ideas.suggest(c, proj, "想-5", [{"to": "总的", "what": "S1", "text": "加一个 S1：手机上能看", "reason": "整个项目的方向"}], by="agent:t")
        c.close()
        items = {x["code"]: x for x in client.get("/api/ideas").json()["items"]}
        assert items["想-1"]["candidates"][0]["say"] == "「文献」新需求：按年份排——点「年份」列表就按年份排"

        # 人点：新需求、补一条、戒律、总的（进问答，不自动写）、放一放
        assert client.post("/api/ideas/想-1/adopt", json={"index": 0}).json()["dest"] == "变成需求：文献 需-4"
        assert client.post("/api/ideas/想-4/adopt", json={"index": 0}).json()["dest"] == "补进需求：文献 需-3"
        assert client.post("/api/ideas/想-3/adopt", json={"index": 0}).json()["dest"] == "变成戒律：文献 文-2"
        d = client.post("/api/ideas/想-5/adopt", json={"index": 0}).json()["dest"]
        assert d.startswith("等你改总的：S1（问答 D-")
        assert any("想-5 想改总的 S1" in q["text"] for q in client.get("/api/state").json()["pending"])
        assert client.post("/api/ideas/想-2/dest", json={"dest": "放一放"}).json()["state"] == "放一放"
        assert client.post("/api/ideas/想-1/adopt", json={"index": 0}).status_code == 400          # 候选用过就清了

    need = requirements.read(proj, "文献")
    r = {q["code"]: q for q in need["reqs"]}
    assert r["需-4"]["func"] == "按年份排" and r["需-4"]["source"] == "想-1" and "想-4" in r["需-3"]["source"]
    rules = (proj.materials / "文献" / "戒律.md").read_text(encoding="utf-8")
    assert "| 文-2 | 不把 PDF 传到外网 | 来自 想-3" in rules
    assert "S1-5" not in "".join(f.name for f in (proj.materials / "蓝图").iterdir())         # 总的那层没自动写
    states = {x["code"]: x["state"] for x in ideas.list_all(proj)}
    assert states == {"想-1": "变成了需求", "想-2": "放一放", "想-3": "变成了戒律", "想-4": "变成了需求", "想-5": "等你改总的"}
    assert "| 想-1 |" in (proj.materials / "想法" / "想法.md").read_text(encoding="utf-8")


def test_work_order_renovates_one_module(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    with TestClient(create_app(proj)) as client:
        client.post("/api/ideas", json={"text": "要能搜", "about": "文献"})
        d = client.post("/api/workorders", json={"module": "文献"}).json()
        wo, pnl = d["wo"], d["panel"]
        assert (wo["name"], wo["target"], wo["modules"], wo["product"]) == ("文献模块装修", ["文献"], ["文献"], "文献模块装修成轻量的阅读管理")
        assert wo["tools"] == ["T10"] and wo["materials"] == ["资料/文献/格式说明.md"]     # 需求、蓝图里提到的工具和文件
        assert wo["rules"] == [] and [r["layer"] for r in pnl["rules"]][:3] == ["通用", "项目", "模块"]
        assert [x["code"] for x in pnl["items"]] == ["S2-2", "S2-3"] and pnl["items"][0]["for"] == ["需-2"]
        lamps = {x["key"]: x for x in pnl["devices"]}
        assert lamps["ideas"]["lamp"] == "warn" and "1 个想法没定去向" in lamps["ideas"]["summary"]
        assert lamps["reqs"]["lamp"] == "bad"                                               # 需-3 没写效果
        assert "需-3 没写要什么效果" in lamps["reqs"]["summary"]
        assert any("S2-3 没写为了哪条需求" in c["text"] for c in lamps["reqs"]["checks"])
        assert d["hrefs"]["文献"] == "#/m/文献?f=%23%E9%9C%80%E6%B1%82%3A%E6%96%87%E7%8C%AE" and d["labels"]["文献"] == "整个模块"

        # 只做一条需求：「文献 需-2」只带为它做的几件
        d = client.post("/api/workorders", json={"module": "文献", "target": ["文献 需-2"], "name": "只做阅读"}).json()
        assert [x["code"] for x in d["panel"]["items"]] == ["S2-2"] and d["labels"]["文献 需-2"] == "左右对照读"
        assert client.post("/api/workorders", json={"module": "没有"}).status_code == 400
        assert client.post("/api/workorders", json={"name": "x", "target": ["没有这个"]}).status_code == 400

        # 左栏：蓝图页「模块」那段、文献页顶上三篇、想法页按去向分组
        t = client.get("/api/modules/蓝图/tree").json()
        row = next(s for s in t["sections"] if s["title"] == "模块")["items"][0]
        assert (row["path"], row["note"]) == ("#需求:文献", "需求 1/3 · 施工 1/3 · K1 备料")
        t = client.get("/api/modules/文献/tree").json()
        assert not any(n.get("label", "").startswith("本模块") for section in t["sections"] for n in section["items"])
        t = client.get("/api/modules/想法/tree").json()
        assert [s["title"] for s in t["sections"]][:2] == ["总的", "待整理"] and t["sections"][1]["items"][0]["path"] == "#想法:想-1"
        assert not any(i.get("name") == "内置" for s in t["sections"] for i in s["items"])   # 10-07 起不再自动补 内置/
        assert t["default"] == "想法.md"  # 加需求入口不能把默认页从想法仓库移走
        assert next(n for n in t["sections"][0]["items"] if n["path"] == "想法.md")["label"] == "想法仓库"
        assert any(n["path"] == "#需求:全部" and n["virtual"] for n in t["sections"][0]["items"])
        v = client.get("/api/requirements/文献").json()
        assert [w["code"] for w in v["workorders"]] == ["K1", "K2"] and v["ideas"][0]["code"] == "想-1"


def test_agent_records_ideas_and_suggests_destinations(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    got = anyio.run(_call, proj, [
        ("add_idea", {"text": "文献要能按年份排", "about": "文献", "source": "对话 09-27"}),
        ("suggest_requirement", {"idea": "想-1", "candidates": [
            {"to": "需求", "module": "文献", "func": "按年份排", "effect": "点年份就排好", "reason": "列表要的"}]}),
        ("suggest_requirement", {"idea": "想-1", "candidates": [{"to": "需求", "module": "文献"}]}),
        ("get_overview", {}),
    ])
    assert "想-1" in got[0] and "「文献」新需求：按年份排" in got[1] and got[2].startswith("没写上")
    assert "想-1（关于 文献）文献要能按年份排" in got[3]
    assert ideas.get(proj, "想-1")["source"] == "对话 09-27"
