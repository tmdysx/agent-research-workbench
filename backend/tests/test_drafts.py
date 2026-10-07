"""草稿区：agent 起草的先放这，人点「行」才进正式文件（蓝图 S2-4；作者 10-01「需求蓝图……要先和人一起规划」）。"""
import pytest

import drafts
import store


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


S1 = "# S1-1 试验\n\n**再试。**\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n| S2-1 | 写说明 | 项目 需-1 | 说明里有 | 没做 |\n\n后面的话。\n"
NEEDS = "# 项目需求\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n| 需-1 | 一件事 | 看得见 | 测试 | S1-1 | 源代码 |\n"


@pytest.fixture
def setup(proj):
    _w(proj.materials / "蓝图" / "S0 终极目标.md", "# S0 终极目标\n\n**做一个试验。**\n\n| S1 | 目标 |\n|---|---|\n| S1-1 试验 | 试一下 |\n")
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1)
    _w(proj.root / "治理" / "需求" / "项目.md", NEEDS)
    (proj.materials / "文献").mkdir(parents=True, exist_ok=True)
    return proj


def test_a_draft_does_not_touch_the_real_files_until_a_person_says_yes(setup):
    from fastapi.testclient import TestClient
    from main import create_app
    p = setup
    d = drafts.propose(p, "任务", "S1-1", {"做什么": "再加一段", "为了": "项目 需-1", "怎么验": "说明里有第二段"}, "说明不够", by="agent:a")
    assert d["code"] == "草-1" and (p.materials / "蓝图" / "S1-1 试验.md").read_text(encoding="utf-8") == S1     # 正式文件没变
    assert [x["state"] for x in drafts.listing(p)] == ["等你看"]
    with TestClient(create_app(p)) as client:
        r = client.post("/api/drafts/草-1", json={"act": "行"})
        assert r.status_code == 200 and r.json()["new"] == "S2-2"
        text = (p.materials / "蓝图" / "S1-1 试验.md").read_text(encoding="utf-8")
        assert "| S2-2 | 再加一段 | 项目 需-1 | 说明里有第二段 | 没做 |\n\n后面的话。" in text                  # 接在表的最后一行后面，列照表头
        assert client.post("/api/drafts/草-1", json={"act": "行"}).status_code == 409                  # 收过的不能再收
        c = store.connect(p.db_path)
        try:
            assert c.execute("SELECT actor FROM event WHERE action = '草稿区行'").fetchone()[0] == "人"   # 记成人点的：监管不当越界
        finally:
            c.close()
        drafts.propose(p, "需求", "项目", {"要什么功能": "能导出", "要什么效果": "点了出文件", "来自": "10-01 作者原话", "关联目标": "S1-1", "承接模块": "源代码"}, "要导出", by="agent:b")
        r = client.post("/api/drafts/草-2", json={"act": "行", "fields": {"要什么功能": "能导出成 PDF"}})          # 改一下再收
        assert r.json()["new"] == "需-2"
        assert "| 需-2 | 能导出成 PDF | 点了出文件 | 10-01 作者原话 | S1-1 | 源代码 |" in (p.root / "治理" / "需求" / "项目.md").read_text(encoding="utf-8")
        drafts.propose(p, "任务", "文献", {"做什么": "加个按钮", "为了": "需-1", "怎么验": "页面上有"}, "顺手", by="agent:a")
        assert client.post("/api/drafts/草-3", json={"act": "不要"}).json()["state"] == "不要"
        assert [x["state"] for x in client.get("/api/drafts").json()["items"]] == ["不要", "收了", "收了"]


def test_a_draft_needs_its_parts(setup):
    p = setup
    with pytest.raises(store.Refused, match="怎么验"):
        drafts.propose(p, "任务", "S1-1", {"做什么": "x"}, "理由", by="a")
    with pytest.raises(store.Refused, match="没有「不存在」这个模块"):
        drafts.propose(p, "任务", "不存在", {"做什么": "x", "怎么验": "y"}, "理由", by="a")
    with pytest.raises(store.Refused, match="理由"):
        drafts.propose(p, "需求", "项目", {"要什么功能": "x"}, "", by="a")
    d = drafts.propose(p, "任务", "文献", {"做什么": "第一件", "为了": "需-1", "怎么验": "看得到"}, "理由", by="a")
    got = drafts.decide(p, d["code"], "行")
    assert got["new"] == "S2-1" and "| S2-1 | 第一件 | 需-1 | 看得到 | 没做 |" in (p.root / "治理" / "任务" / "文献.md").read_text(encoding="utf-8")   # 没有任务文件就建一份


def test_agents_get_the_tool():
    from pathlib import Path
    import mcp_server
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "def propose_draft(" in src and "propose_draft 放进草稿区" in src
