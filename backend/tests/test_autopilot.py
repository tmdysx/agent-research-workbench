"""自动化 = 一张张开工单（K）：单上用到的每样一盏灯，有红的交不出去；交给 agent 了它才能转；做完一件交一张交付单，人验收或打回。
缺工具 agent 写一张「待你装」的卡。作者 2026-09-27：「左边目录应该是每个自定义清单的一个文件……准备好了之后，按照要求把这些交给agent」。"""
import anyio
from fastapi.testclient import TestClient

import blueprint
import deliveries
import readiness
import snapshot
import store
import tools
from main import create_app
from test_mcp import _call

S0 = "# S0 终极目标\n\n**做一个试验。**\n\n| S1 | 目标 |\n|---|---|\n| S1-1 试验 | 试一下 |\n"
S1 = ("# S1-1 试验\n\n**把文献模块装修一下。**\n\n怎么算做到：三件都验过。\n\n动到的模块：文献\n\n"
      "| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
      "| S2-1 | 文献列表 | 拖一篇进来左栏多一行 | 没做 |\n"
      "| S2-2 | 阅读页 |  | 没做 |\n"
      "| S2-3 | 图解 | 看得见 | 以后 |\n")


def _setup(proj, monkeypatch, tmp_path):
    bp = proj.materials / "蓝图"
    bp.mkdir(parents=True)
    (bp / "S0 终极目标.md").write_text(S0, encoding="utf-8")
    (bp / "S1-1 试验.md").write_text(S1, encoding="utf-8")
    (proj.materials / "文献").mkdir()
    (proj.root / ".mcp.json").write_text('{"mcpServers": {"research-console": {}}}', encoding="utf-8")
    lib = tmp_path / "工具库"
    lib.mkdir()
    (lib / "T1 网页.md").write_text("---\n编号: T1\n名字: 网页\n类别: 技术栈\n一句话: 一个 HTML\n检查:\n---\n# T1\n", encoding="utf-8")
    monkeypatch.setattr(tools, "LIB", lib)
    monkeypatch.setattr(readiness, "_claude_cli", lambda: None)
    tools.forget()
    return lib


def _lamps(d):
    return {x["key"]: x["lamp"] for x in d["panel"]["devices"]}


def test_work_order_goes_green_before_it_is_handed_to_the_agent(proj, monkeypatch, tmp_path):
    lib = _setup(proj, monkeypatch, tmp_path)
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/workorders").json() == {"items": [], "running": None}
        assert client.post("/api/workorders", json={"name": "文献", "target": ["随便"]}).status_code == 400
        d = client.post("/api/workorders", json={"name": "文献模块装修", "target": ["S1-1"]}).json()
        wo = d["wo"]
        assert wo["code"] == "K1" and wo["state"] == "备料" and wo["step"] == 1
        assert wo["product"] == "把文献模块装修一下。" or wo["product"]               # 没写就用 S1 的一句话
        assert wo["modules"] == ["文献"] and wo["rules"] == [] and wo["saves"] == []  # 照目标配齐：S1 写了动到文献
        assert (proj.root / "自动化" / "开工单" / "K1 文献模块装修.md").is_file()
        assert [x["code"] for x in d["panel"]["items"]] == ["S2-1", "S2-2"]            # 「以后」的不算
        lamps = _lamps(d)
        assert lamps["blueprint"] == "bad" and "S2-2 没写怎么验" in d["panel"]["devices"][2]["summary"]
        assert lamps["rules"] == "bad"                                                # 没有 AGENTS.md
        assert lamps["saves"] == "warn" and lamps["agent"] == "bad" and lamps["plans"] == "warn"   # 09-30 放宽：没定性的存档是黄的
        assert lamps["modules"] == "ok" and lamps["tools"] == "ok" and lamps["materials"] == "ok"
        r = client.post("/api/workorders/K1/start")
        assert r.status_code == 400 and "蓝图" in r.json()["detail"] and "存档" not in r.json()["detail"]

        # 单上加一样材料（不在）→ 材料红；改成在的 → 绿；交代三格存进文件、文件里改了网页也读得到
        d = client.put("/api/workorders/K1", json={"materials": ["资料/文献/格式说明.md"], "notes": {"不许": "改原文 PDF"}}).json()
        assert _lamps(d)["materials"] == "bad" and "找不到 资料/文献/格式说明.md" in d["panel"]["devices"][6]["summary"]
        (proj.materials / "文献" / "格式说明.md").write_text("一篇一个文件夹", encoding="utf-8")
        f = proj.root / "自动化" / "开工单" / "K1 文献模块装修.md"
        text = f.read_text(encoding="utf-8")
        assert "材料: 资料/文献/格式说明.md" in text and "### 不许\n\n改原文 PDF" in text
        f.write_text(text.replace("### 建议\n", "### 建议\n\n先做列表\n"), encoding="utf-8")
        (proj.materials / "文献" / "戒律.md").write_text("不改原文", encoding="utf-8")
        opt = client.get("/api/workorders/K1/options").json()
        assert "资料/文献/格式说明.md" in opt["materials"] and "资料/文献/戒律.md" not in opt["materials"]
        assert "资料/文献/戒律.md" not in opt["rules"] and "文献" in opt["modules"]         # 单上的模块自己的戒律自动带上，不用加
        stack = client.get("/api/workorders/K1").json()["panel"]["rules"]
        assert [(r["layer"], r.get("module")) for r in stack] == [("通用", None), ("项目", None), ("模块", "文献"), ("这张单", None)]
        (proj.materials / "文献" / "戒律.md").unlink()
        d = client.get("/api/workorders/K1").json()
        assert _lamps(d)["materials"] == "ok" and d["wo"]["notes"] == {"要做到": "", "建议": "先做列表", "不许": "改原文 PDF"}
        assert d["hrefs"]["资料/文献/格式说明.md"] == "#/m/文献?f=格式说明.md" and d["hrefs"]["S1-1"] == "#/m/蓝图?f=S1-1 试验.md"
        assert client.put("/api/workorders/K1", json={"materials": ["C:/外面/x.md"]}).status_code == 400
        assert client.put("/api/workorders/K1", json={"level": 0}).status_code == 400
        d = client.put("/api/workorders/K1", json={"tools": ["T9"]}).json()
        assert _lamps(d)["tools"] == "bad" and "没有 T9" in d["panel"]["devices"][5]["summary"]
        client.put("/api/workorders/K1", json={"tools": []})

        # 手动一样样补：怎么验、AGENTS.md、存档定性、agent 连上过；一张「待你装」的卡让工具变红
        f2 = proj.materials / "蓝图" / "S1-1 试验.md"
        f2.write_text(f2.read_text(encoding="utf-8").replace("| S2-2 | 阅读页 |  |", "| S2-2 | 阅读页 | 用 pdf.js 翻到第 3 页，右边是第 3 页 |"), encoding="utf-8")
        (proj.root / "AGENTS.md").write_text("# 戒律\n- 通-15 自动转圈必停：删 / 搬文件\n", encoding="utf-8")
        c = store.connect(proj.db_path)
        m = snapshot.save(c, proj, name="开工前", why="试", mode="只记指纹", picks=[], by="人", checks=None)
        with store.tx(c):
            store.log(c, "agent:test", "看全貌")
        c.close()
        d = client.post("/api/workorders/K1/fill").json()                             # 照目标配齐：戒律不用列（自动算）；存档还没定性，不加
        assert d["wo"]["rules"] == [] and d["wo"]["saves"] == []
        d = client.put("/api/workorders/K1", json={"rules": ["AGENTS.md", "资料/文献/格式说明.md"]}).json()   # 自动的写了也不重复
        assert d["wo"]["rules"] == ["资料/文献/格式说明.md"] and [r["layer"] for r in d["panel"]["rules"]][-2:] == ["另加", "这张单"]
        d = client.put("/api/workorders/K1", json={"rules": []}).json()
        d = client.put("/api/workorders/K1", json={"saves": [m["code"]]}).json()
        assert _lamps(d)["saves"] == "warn" and "没定性" in d["panel"]["devices"][8]["summary"]
        c = store.connect(proj.db_path)
        snapshot.settle(c, proj, m["code"], by="人")
        c.close()
        t = tools.propose("pdf.js", one_line="看 PDF", why="阅读页要", install="从 GitHub 下载放进 vendor/pdfjs/",
                          kind="技术栈", by="agent:test", lib=lib)
        assert t["code"] == "T2" and tools.list_tools(lib)[1]["state"] == "待你装"
        tools.propose("Three.js", one_line="3D", why="图解要", install="下载放进 vendor/three/", kind="技术栈", lib=lib)
        d = client.get("/api/workorders/K1").json()
        lamps = _lamps(d)
        assert lamps["tools"] == "warn" and "T2 pdf.js 待你装" in d["panel"]["devices"][5]["summary"]
        assert [x["lamp"] for x in d["panel"]["devices"][5]["checks"]] == ["warn", "warn"]  # 09-30 放宽：待你装的 agent 能自己装，都是黄的
        assert lamps["rules"] == "warn" and lamps["saves"] == "ok"                          # 文献没有模块戒律：黄的，能转
        c = store.connect(proj.db_path)
        q = store.ask_human(c, "请你装 T2 pdf.js：看 PDF", by="agent:test")
        c.close()
        assert client.post("/api/tools/T2/installed").status_code == 200             # 人装好了：去掉「待你装」，请装的那条问答了结
        assert tools.list_tools(lib)[1]["state"] == "" and q["code"] not in [x["code"] for x in client.get("/api/state").json()["pending"]]
        d = client.get("/api/workorders/K1").json()
        assert d["panel"]["ready"] and d["panel"]["red"] == [], d["panel"]["red"]
        k2 = client.post("/api/workorders/K1/copy").json()["wo"]
        assert k2["code"] == "K2" and k2["name"] == "文献模块装修（复制）" and k2["notes"]["不许"] == "改原文 PDF"

        # 交给 agent 之前转不了；交了以后能报「在跑」、日志记下照哪张单；一次只跑一张；叫停了又不能
        import runs
        c = store.connect(proj.db_path)
        try:
            runs.report(c, proj, "W1", by="agent:test", goal="S1-1 S2-1", did="偷跑")
            raise AssertionError
        except store.Refused as e:
            assert "开工单" in str(e)
        d = client.post("/api/workorders/K1/start").json()
        assert d["wo"]["state"] == "在跑" and d["wo"]["step"] == 2 and d["wo"]["started"]
        assert client.get("/api/state").json()["running"] == {"code": "K1", "name": "文献模块装修"}
        r = client.post("/api/workorders/K2/start")
        assert r.status_code == 400 and "一次只跑一张" in r.json()["detail"]
        assert runs.report(c, proj, "W1", by="agent:test", goal="S1-1 S2-1", did="做了")["code"] == "W1-1.1"
        assert client.get("/api/workorders/K1").json()["panel"]["run"]["code"] == "W1-1"
        assert client.get("/api/workorders/K2").json()["panel"]["run"] is None
        assert client.post("/api/workorders/K1/stop").json()["wo"]["state"] == "备料"
        try:
            runs.report(c, proj, "W1", by="agent:test", run="W1-1", goal="S1-1 S2-1", did="接着跑")
            raise AssertionError
        except store.Refused:
            pass
        runs.report(c, proj, "W1", by="agent:test", run="W1-1", goal="S1-1 S2-1", did="停下", status="停了等你")
        c.close()
        kinds = [e["kind"] for e in client.get("/api/log").json()["entries"]]
        assert "交给 agent" in kinds and "叫停" in kinds and "新开工单" in kinds
        s = client.get("/api/workorders").json()
        assert [(x["code"], x["state"]) for x in s["items"]] == [("K1", "备料"), ("K2", "备料")] and s["running"] is None
        assert client.post("/api/workorders/K2/shelve", json={"confirm": True}).json()["wo"]["state"] == "搁置"


def test_old_global_order_becomes_k1(proj):
    bp = proj.materials / "蓝图"
    bp.mkdir(parents=True)
    (bp / "S1-1 试验.md").write_text(S1, encoding="utf-8")
    c = store.connect(proj.db_path)
    store.migrate(c)
    with store.tx(c):
        store._set_meta(c, "auto_scope", '["S1-1"]')
        store._set_meta(c, "auto_fails", "3")
        store._set_meta(c, "auto_state", "已发动")
    c.close()
    with TestClient(create_app(proj)) as client:
        [k] = client.get("/api/workorders").json()["items"]
        assert (k["code"], k["name"], k["state"]) == ("K1", "试验", "在跑")
        wo = client.get("/api/workorders/K1").json()["wo"]
        assert wo["target"] == ["S1-1"] and wo["fails"] == 3 and wo["modules"] == ["文献"]
    (proj.root / "自动化" / "开工单" / "K1 试验.md").unlink()
    with TestClient(create_app(proj)) as client:                                    # 只迁一次：删了不会再冒出来
        assert client.get("/api/workorders").json()["items"] == []


def test_done_and_waiting_are_worked_out(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    monkeypatch.setattr(deliveries, "DEFAULT_PASS", False)          # 这条测人手验收 / 打回：关掉默认通过
    f = proj.materials / "蓝图" / "S1-1 试验.md"
    f.write_text(f.read_text(encoding="utf-8").replace("| S2-2 | 阅读页 |  |", "| S2-2 | 阅读页 | 翻页 |"), encoding="utf-8")
    (proj.materials / "文献" / "列表.md").write_text("x", encoding="utf-8")
    c = store.connect(proj.db_path)
    import workorders
    wo = workorders.create(c, proj, "只做列表", ["S1-1 S2-1"])
    assert wo["target"] == ["S1-1 S2-1"]
    wo["stored"] = "在跑"
    workorders._write(proj, wo)
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:test")
    assert j["workorder"] == "K1"
    workorders.stop(c, proj, "K1")
    d = workorders.detail(c, proj, "K1")
    assert d["wo"]["state"] == "等你验收" and d["wo"]["step"] == 3 and [x["code"] for x in d["panel"]["deliveries"]] == ["J1"]
    deliveries.accept(c, proj, "J1")
    assert workorders.detail(c, proj, "K1")["wo"]["state"] == "做完"
    c.close()


def test_deliver_then_accept_or_send_back(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    monkeypatch.setattr(deliveries, "DEFAULT_PASS", False)          # 这条测人手验收 / 打回：关掉默认通过
    out = proj.materials / "文献" / "列表.md"
    out.write_text("L1 …\n", encoding="utf-8")
    c = store.connect(proj.db_path)
    for bad, why in ((dict(checks=[]), "怎么验"), (dict(files=["资料/没有.md"]), "找不到"), (dict(sub="S2-9"), "没有")):
        kw = dict(goal="S1-1", sub="S2-1", did="做好了列表", checks=[{"name": "拖一篇", "ok": True}], files=["资料/文献/列表.md"])
        kw.update(bad)
        try:
            deliveries.deliver(c, proj, **kw)
            raise AssertionError(bad)
        except store.Refused as e:
            assert why in str(e)
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="做好了列表", checkpoint="C1", run="W1-1.2",
                           checks=[{"name": "拖一篇进来", "ok": True, "detail": "左栏多了 L1"}], files=["资料/文献/列表.md"],
                           by="agent:test")
    assert j["code"] == "J1" and j["state"] == "待你验收" and "左栏多了 L1" in j["body"]
    sub = lambda code: next(x for x in blueprint.pyramid(proj)["goals"][0]["subs"] if x["code"] == code)
    assert sub("S2-1")["text"] == "待你验收（J1）"
    j2 = deliveries.deliver(c, proj, goal="S1-1", sub="S2-2", did="阅读页", checks=[{"name": "翻到第 3 页", "ok": False}], by="agent:test")
    c.close()
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/state").json()["deliveries"] == 2
        assert [x["code"] for x in client.get("/api/deliveries").json()["items"]] == ["J2", "J1"]
        assert client.post("/api/deliveries/J1/accept").json()["state"] == "验收通过"
        assert sub("S2-1")["text"] == "做完（J1 验收）" and sub("S2-1")["status"] == "ok"
        assert client.post("/api/deliveries/J1/accept").status_code == 400                  # 验过的不能再验
        assert client.post("/api/deliveries/J2/reject", json={"reason": " "}).status_code == 400
        r = client.post("/api/deliveries/J2/reject", json={"reason": "右边没跟着翻页"}).json()
        assert r["state"] == "打回" and "右边没跟着翻页" in r["body"]
        assert sub("S2-2")["text"].startswith("在做（J2 打回：右边没跟着翻页") and sub("S2-2")["status"] == "todo"
        log = client.get("/api/log").json()["entries"]
        assert [e["kind"] for e in log][-2:] == ["验收", "打回"] and "右边没跟着翻页" in log[-1]["body"]
        assert client.get("/api/state").json()["deliveries"] == 0
    assert j2["code"] == "J2"


def test_agent_marks_and_delivers_through_mcp(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    (proj.materials / "文献" / "列表.md").write_text("x", encoding="utf-8")
    done, wait, give, overview = anyio.run(_call, proj, [
        ("mark_goal", {"goal": "S1-1", "sub": "S2-1", "status": "做完"}),
        ("mark_goal", {"goal": "S1-1", "sub": "S2-2", "status": "等工具", "note": "等 pdf.js"}),
        ("deliver", {"goal": "S1-1", "sub": "S2-1", "did": "列表", "checks": [{"name": "拖一篇", "ok": True}],
                     "files": ["资料/文献/列表.md"]}),
        ("get_overview", {}),
    ])
    assert "只有人" in done                                                       # 不交付就自己标做完：不行
    assert "等工具（等 pdf.js）" in wait and "J1" in give and "默认通过" in give    # 交付了、检查全过：默认通过
    assert "没有在跑的开工单" in overview and "不要转圈" in overview
    subs = {x["code"]: x["text"] for x in blueprint.pyramid(proj)["goals"][0]["subs"]}
    assert subs == {"S2-1": "做完（J1 默认通过）", "S2-2": "等工具（等 pdf.js）", "S2-3": "以后"}


def test_delivery_passes_by_default_and_can_still_be_sent_back(proj, monkeypatch, tmp_path):
    """作者 09-30：「验收一律默认通过」——检查全过就算做完；有没过的检查还等人看；通过了的人照样能打回。"""
    _setup(proj, monkeypatch, tmp_path)
    c = store.connect(proj.db_path)
    j1 = deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:test")
    j2 = deliveries.deliver(c, proj, goal="S1-1", sub="S2-2", did="阅读页", checks=[{"name": "翻页", "ok": False}], by="agent:test")
    assert j1["state"] == "验收通过" and "默认通过" in j1["body"] and j2["state"] == "待你验收"
    subs = {x["code"]: x["text"] for x in blueprint.pyramid(proj)["goals"][0]["subs"]}
    assert subs["S2-1"] == "做完（J1 默认通过）" and subs["S2-2"] == "待你验收（J2）"
    assert deliveries.pending(proj) == 1
    back = deliveries.reject(c, proj, "J1", "左栏没排序")
    assert back["state"] == "打回"
    assert next(x for x in blueprint.pyramid(proj)["goals"][0]["subs"] if x["code"] == "S2-1")["text"].startswith("在做（J1 打回")
    c.close()


def test_old_three_column_tables_still_read(proj):
    bp = proj.materials / "蓝图"
    bp.mkdir(parents=True)
    (bp / "S1-2 旧.md").write_text("# S1-2 旧\n\n| | 做什么 | 状态 |\n|---|---|---|\n| S2-1 | 旧的 | 做完 |\n", encoding="utf-8")
    [g] = blueprint.pyramid(proj)["goals"]
    assert g["subs"] == [{"code": "S2-1", "what": "旧的", "how": "", "for": [], "text": "做完", "status": "ok"}] and g["modules"] == []
