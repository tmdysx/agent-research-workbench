"""先跟人一起规划，定稿了才全自动（作者 10-01：「需求蓝图等等东西这个是最重要的，要先和人一起规划，这个完毕之后才是全自动」）。"""
import pytest

import agents
import dispatch
import readiness
import store
import tools


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


S0 = "# S0 终极目标\n\n**做一个试验。**\n\n| S1 | 目标 |\n|---|---|\n| S1-1 试验 | 试一下 |\n"
S1 = ("# S1-1 试验\n\n**再试。**\n\n{final}| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
      "| S2-1 | 写说明 | 说明里有这一段 | 没做 |\n| S2-2 | 再写一段 |  | 没做 |\n")


@pytest.fixture
def c(proj, monkeypatch, tmp_path):
    _w(proj.materials / "蓝图" / "S0 终极目标.md", S0)
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1.format(final=""))
    _w(proj.root / "AGENTS.md", "# 戒律\n- 只在两类事上停：彻底删除、公开发布\n")
    _w(proj.root / ".mcp.json", "{\"mcpServers\": {\"research-console\": {}}}")
    lib = tmp_path / "工具库"
    lib.mkdir()
    monkeypatch.setattr(tools, "LIB", lib)
    monkeypatch.setattr(readiness, "_claude_cli", lambda: None)
    tools.forget()
    conn = store.connect(proj.db_path)
    agents.register(conn, proj, "a")
    yield conn
    conn.close()


def test_agents_only_pick_what_has_been_planned_to_the_end(proj, c):
    assert dispatch.ready_items(proj) == []                                         # 没定稿：agent 不自己挑
    with pytest.raises(store.Refused, match="没有你能自己做的件"):
        dispatch.next_task(c, proj, "agent:a")
    got = dispatch.start_work(c, proj, "agent:a", target=["S1-1 S2-1"])               # 人点名的照样能做
    assert got["wo"]["target"] == ["S1-1 S2-1"] and dispatch.next_task(c, proj, "agent:a")["task"]["sub"] == "S2-1"
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1.format(final="规划：定稿 · 2026-10-01 · 作者：「这块定稿」\n\n"))
    assert [(g["code"], x["code"]) for g, x in dispatch.ready_items(proj)] == [("S1-1", "S2-1")]   # 定稿了：写了怎么验的才挑


def test_what_is_still_missing_before_full_automation(proj, c):
    (proj.materials / "论文").mkdir(parents=True)
    rows = {r["code"]: r for r in dispatch.plan_status(proj)}
    s1 = rows["S1-1"]
    assert (s1["kind"], s1["left"], s1["no_how"], s1["final"]) == ("目标", 2, 1, "")
    assert rows["论文"]["kind"] == "模块" and rows["论文"]["needs"] == 0 and rows["论文"]["rules"] is False


def test_big_problems_and_format_check(proj, c):
    import blueprint
    import requirements
    s0 = S0 + "\n## 两个大问题\n\n| 大问题 | 小问题 | 归到 |\n|---|---|---|\n| 一、会跑偏 | 没说清 | S1-1 试验 |\n| | 没人盯 | S1-1、文献 |\n"
    _w(proj.materials / "蓝图" / "S0 终极目标.md", s0)
    assert [(b["big"], b["to"]) for b in blueprint.big_problems(proj)] == [("一、会跑偏", ["S1-1"]), ("一、会跑偏", ["S1-1", "文献"])]
    assert blueprint.lint(proj) == []
    bad = S1.format(final="").replace("| S2-2 | 再写一段 |  | 没做 |", "| S2-2 | 再写一段 | 没做 |") + "| S2-3 | 第三件 | 看看 | 最后做 |\n"
    _w(proj.materials / "蓝图" / "S1-1 试验.md", bad)
    texts = [x["text"] for x in blueprint.lint(proj)]
    assert any("S2-2 有 3 格，表头是 4 格" in t for t in texts) and any("「最后做」认不出" in t for t in texts)
    assert next(r for r in dispatch.plan_status(proj) if r["code"] == "S1-1")["group"] == "一、会跑偏"
    _w(proj.root / "治理" / "需求" / "项目.md", "# 项目需求\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n| 需-1 | 一件事 | 看得见 | 测试 | S1-1 | 源代码 |\n")
    _w(proj.materials / "蓝图" / "S1-1 试验.md", "# S1-1 试验\n\n**再试。**\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n| S2-1 | 写说明 | 项目 需-1 | 说明里有 | 没做 |\n")
    q = next(q for q in requirements.catalog(proj) if q["scope"] == "项目")
    assert [t["code"] for t in q["tasks"]] == ["S2-1"]                                # 人照格式说明写的「项目 需-1」也对得上


def test_finalize_is_checked_first_and_only_people_press_it(proj, c):
    """蓝图 S2-3：定稿前先查，缺东西就拒、写清缺什么；齐了的定稿后 agent 挑得到、取消后挑不到；agent 没有这个口子。"""
    from fastapi.testclient import TestClient
    from main import create_app
    import mcp_server
    with pytest.raises(store.Refused, match="还缺：.*还没有需求.*1 件没写怎么验"):
        dispatch.set_final(proj, "S1-1", True, "定稿")
    assert dispatch.ready_items(proj) == []
    _w(proj.root / "治理" / "需求" / "项目.md", "# 项目需求\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n| 需-1 | 一件事 | 看得见 | 测试 | S1-1 | 源代码 |\n")
    _w(proj.materials / "蓝图" / "S1-1 试验.md", "# S1-1 试验\n\n**再试。**\n\n怎么算做到：看得见。\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n| S2-1 | 写说明 | 项目 需-1 | 说明里有 | 没做 |\n")
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/blueprint/final/S1-1").json()["missing"] == []
        r = client.post("/api/blueprint/final/S1-1", json={"on": True, "words": "这块定稿"})
        assert r.status_code == 200 and r.json()["final"].startswith("定稿 · ") and r.json()["final"].endswith("作者：「这块定稿」")
        text = (proj.materials / "蓝图" / "S1-1 试验.md").read_text(encoding="utf-8")
        assert text.index("规划：定稿") < text.index("怎么算做到：")                    # 写在「怎么算做到」前面
        assert [(g["code"], x["code"]) for g, x in dispatch.ready_items(proj)] == [("S1-1", "S2-1")]
        assert client.post("/api/blueprint/final/S1-1", json={"on": False}).status_code == 200
        assert "规划：" not in (proj.materials / "蓝图" / "S1-1 试验.md").read_text(encoding="utf-8")
        assert dispatch.ready_items(proj) == []
        assert client.post("/api/blueprint/final/S9-9", json={"on": True}).status_code == 409
    from pathlib import Path
    assert "set_final" not in Path(mcp_server.__file__).read_text(encoding="utf-8")    # MCP 里没有定稿的口子：只有人在网页上按


def test_the_blueprint_module_has_its_own_tasks(proj, c):
    """「蓝图」这个模块自己的任务在 治理/任务/蓝图.md：认得出、能改状态（以前被当成总蓝图跳过了）。"""
    import blueprint
    _w(proj.root / "治理" / "任务" / "蓝图.md", "# 蓝图 · 任务\n\n规划：定稿 · 2026-10-01 · 作者：「蓝图定稿」\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n"
                                              "|---|---|---|---|---|\n| S2-1 | 大问题卡 | 需-1 | 卡上的数对得上 | 没做 |\n")
    g = blueprint.find(blueprint.pyramid(proj), "蓝图")
    assert g and g["final"].startswith("定稿") and [x["code"] for x in g["subs"]] == ["S2-1"]
    assert blueprint.set_status(proj, "蓝图", "S2-1", "做完（J1）") == "没做"
    assert "做完（J1）" in (proj.root / "治理" / "任务" / "蓝图.md").read_text(encoding="utf-8")


def test_a_delivery_that_cannot_mark_the_blueprint_leaves_no_empty_slip(proj, c, monkeypatch):
    """蓝图那一格改不上：交付单收回、说清为什么，不留一张挂在「待你验收」的空单（10-01 J31）。"""
    import blueprint
    import deliveries

    def boom(*a, **k):
        raise ValueError("蓝图里没有 S1-1")
    monkeypatch.setattr(blueprint, "set_status", boom)
    with pytest.raises(store.Refused, match="蓝图里没有"):
        deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="写了", checks=[{"name": "看", "ok": True}], by="agent:a")
    assert not list((proj.root / "自动化" / "交付").glob("J*.md"))
