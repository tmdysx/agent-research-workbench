"""自动化看板（S1-8 S2-28～S2-31；作者 10-02「就这样做」）：四列分得对 · 一件的为什么那条链 · 四张图的数跟交付单、蓝图对得上。"""
from fastapi.testclient import TestClient

import board
import agents
import construction_plans as plans
import claims
import deliveries
import store
import supervise
import workorders
from main import create_app


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


S0 = ("# S0 终极目标\n\n**做一个试验。**\n\n## 两个大问题\n\n| 大问题 | 小问题 | 归到 |\n|---|---|---|\n"
      "| 一、会跑偏 | 没说清 | S1-1 说清 |\n| 二、接不上 | 换人 | S1-2 接上 |\n\n| S1 | 目标 |\n|---|---|\n| S1-1 说清 | 说 |\n| S1-2 接上 | 接 |\n")
HEAD = "| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"


def _setup(proj):
    _w(proj.materials / "蓝图" / "S0 终极目标.md", S0)
    _w(proj.materials / "蓝图" / "S1-1 说清.md", "# S1-1 说清\n\n**说清。**\n\n" + HEAD
       + "| S2-1 | 甲 | 项目 需-1 | 看 | 做完（J3 默认通过） |\n| S2-2 | 乙 | 项目 需-1 | 看 | 没做 |\n| S2-3 | 丙 | 项目 需-1 | 看 | 在做 |\n"
       "| S2-4 | 丁 | 项目 需-2 | 看 | 等你定：要不要丁 |\n")
    _w(proj.materials / "蓝图" / "S1-2 接上.md", "# S1-2 接上\n\n**接上。**\n\n" + HEAD + "| S2-1 | 戊 |  | 看 | 没做 |\n| S2-2 | 己 | 项目 需-2 | 看 | 以后 |\n")
    _w(proj.root / "治理" / "需求" / "项目.md", "# 项目需求\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n"
       "| 需-1 | 说清楚 | 看得见 | 测试 | S1-1 | 源代码 |\n| 需-2 | 接得上 | 看得见 | 测试 | S1-1、S1-2 | 源代码 |\n")
    _w(proj.root / "治理" / "戒律" / "1 通用戒律.md", "# 通用戒律\n\n| | 规矩 |\n|---|---|\n| 通-1 | 说人话 |\n")


def test_four_columns_and_who_holds_it(proj):
    _setup(proj)
    c = store.connect(proj.db_path)
    claims.claim(c, "S1-1", "S2-2", "agent:a", ["S1-1 S2-2"], "乙")
    col = {x["key"]: x for x in board.items(c, proj)}
    assert {k: x["col"] for k, x in col.items()} == {"S1-1 S2-1": "做完", "S1-1 S2-2": "在做", "S1-1 S2-3": "在做", "S1-1 S2-4": "等着",
                                                     "S1-2 S2-1": "能做", "S1-2 S2-2": "以后"}
    assert col["S1-1 S2-2"]["who"] == "a" and col["S1-1 S2-2"]["since"]          # 有人领着才算它的；状态写「在做」没人领的也在「在做」
    assert col["S1-1 S2-3"]["who"] == ""
    assert col["S1-1 S2-1"]["needs"] == ["项目 需-1"] and col["S1-2 S2-1"]["needs"] == []
    assert col["S1-1 S2-1"]["group"] == "一、会跑偏" and col["S1-2 S2-1"]["group"] == "二、接不上"
    snap = board.snapshot(c, proj)
    assert {k: snap["counts"][k] for k in board.COLS + ("以后",)} == {"能做": 1, "在做": 2, "等着": 1, "等验收": 0, "做完": 1, "以后": 1}


def test_one_item_carries_the_why_chain(proj):
    _setup(proj)
    c = store.connect(proj.db_path)
    workorders.create(c, proj, "说清那几件", ["S1-1"])
    d = board.detail(c, proj, "S1-1", "S2-4")
    assert "试验" in d["s0"] and d["group"] == "一、会跑偏" and d["goal_line"] == "说清"
    assert [(q["code"], q["func"]) for q in d["needs_full"]] == [("需-2", "接得上")]
    assert d["col"] == "等着" and d["text"].startswith("等你定")
    assert [r["layer"] for r in d["rules"]] == ["通用"]
    assert [o["name"] for o in d["orders"]] == ["说清那几件"]                      # 单上写了整个 S1-1：这件在单上
    assert board.detail(c, proj, "S1-1", "S2-9") is None
    assert board.detail(c, proj, "S1-2", "S2-1")["orders"] == []


def test_charts_add_up_with_deliveries_and_supervision(proj):
    _setup(proj)
    c = store.connect(proj.db_path)
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-2", did="乙做好了", checks=[{"name": "看", "ok": True}], by="agent:a")
    assert j["state"] == "验收通过"
    supervise.record(c, proj, 2, "a.md", "a.md 没了")
    supervise.record(c, proj, 2, "b.md", "b.md 没了")
    with store.tx(c):
        c.execute("UPDATE finding SET state = ? WHERE key = 'b.md'", (supervise.FIXED,))
    snap = board.snapshot(c, proj)
    d = snap["daily"]
    assert len(d["days"]) == 14 and d["passed"][-1] == 1 and sum(d["passed"]) == 1 and sum(d["rejected"]) == 0
    assert d["by_group"] == {"一、会跑偏": [0] * 13 + [1]}
    assert d["cumulative"][-1] == 2 and d["cumulative"][-2] == 1 and d["total"] == 5   # 做完两件（今天交的那件 + 以前的）；「以后」不算在一共里
    assert d["found"][-1] == 2 and d["closed"][-1] == 1
    assert snap["counts"]["做完这周"] == 1
    item = next(x for x in snap["items"] if x["key"] == "S1-1 S2-2")
    assert (item["col"], item["j"], item["j_by"]) == ("做完", j["code"], "a")


def test_board_api(proj):
    _setup(proj)
    with TestClient(create_app(proj)) as client:
        r = client.get("/api/board")
        assert r.status_code == 200 and r.json()["counts"]["能做"] == 2
        r = client.get("/api/board/item", params={"goal": "S1-1", "sub": "S2-4"})
        assert r.status_code == 200 and r.json()["needs_full"][0]["code"] == "需-2"
        assert client.get("/api/board/item", params={"goal": "S1-1", "sub": "S2-9"}).status_code == 404


def test_plan_states_match_board_and_detail_api(proj):
    _setup(proj)
    c = store.connect(proj.db_path)
    agents.create(c, proj, "writer", "写代码的")
    agents.create(c, proj, "reviewer", "审核的", program="Codex（review-model）")
    claims.claim(c, "S1-1", "S2-2", "agent:writer", ["S1-1 S2-2"])
    with TestClient(create_app(proj)) as client:
        def check(state, valid=False):
            card = next(x for x in client.get("/api/board").json()["items"] if x["key"] == "S1-1 S2-2")
            detail = client.get("/api/board/item", params={"goal": "S1-1", "sub": "S2-2"}).json()
            assert card["execution_plan"] == detail["execution_plan"]
            p = card["execution_plan"]
            if state is None:
                assert p is None
            else:
                assert p["display_state"] == state and p["valid"] is valid
                assert bool(p["approved_files"]) is valid
            return p
        check(None)
        d = plans.submit(c, proj, "S1-1", "S2-2", "writer", "实现乙", ["result.txt"])
        check("待审")
        d = plans.review(c, proj, d["code"], "reviewer", False, "补检查", d["revision"])
        assert check("打回")["reviewer_model"] == "review-model"
        d = plans.submit(c, proj, "S1-1", "S2-2", "writer", "实现并检查乙", ["result.txt"], revision=d["revision"])
        check("待审")
        d = plans.review(c, proj, d["code"], "reviewer", True, "完整", d["revision"])
        p = check("通过", True)
        assert p["reviewer"] == "agent:reviewer" and (proj.root / p["formal_path"]).is_file()
        formal = proj.root / p["formal_path"]
        formal.write_text(formal.read_text(encoding="utf-8") + "\nchanged", encoding="utf-8")
        check("失效")
        d = plans.submit(c, proj, "S1-1", "S2-2", "writer", "修订乙", ["result.txt"], revision=d["revision"])
        p = check("待审")
        assert not p["formal_path"] and not p["reviewer"]
    c.close()


def test_plan_selection_follows_holder_then_latest_author(proj):
    _setup(proj)
    c = store.connect(proj.db_path)
    for name in ("first", "second", "third"):
        agents.create(c, proj, name, "写代码的")
    agents.create(c, proj, "reviewer", "审核的")
    first = plans.submit(c, proj, "S1-1", "S2-2", "first", "第一人的计划", ["first.txt"])
    plans.review(c, proj, first["code"], "reviewer", True, "范围正确", first["revision"])
    second = plans.submit(c, proj, "S1-1", "S2-2", "second", "第二人的计划", ["second.txt"])
    def selected():
        return board.detail(c, proj, "S1-1", "S2-2")["execution_plan"]
    assert selected()["by"] == "agent:second"  # 无持有人时取最近记录，作者仍明确
    for name, expected in (("first", "通过"), ("second", "待审"), ("third", None)):
        claims.claim(c, "S1-1", "S2-2", "agent:" + name, ["S1-1 S2-2"])
        p = selected()
        assert (p["display_state"] if p else None) == expected
        if p:
            assert p["by"] == "agent:" + name
        claims.release(c, "S1-1", "S2-2", "agent:" + name)
    # 老作者后续修订的时间更晚，即使编号更小也不能取编号最大的。
    d = plans.get(proj, first["code"])
    d["updated"] = "2099-01-01T00:00:00"
    plans._write(proj.root / d["file"], d)
    assert selected()["code"] == first["code"] != second["code"]
    c.close()
