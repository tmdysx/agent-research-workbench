"""清理 → 摘要 · 重写（S1-8 S2-62、S2-63；需-29）：该写哪几份摘要、给材料、收稿；「现在的样子」放进 get_overview 最前面；
重写单出单、对照、点行才换、换前存档、旧版进归档标被取代、方向文件只有人能换、出单后正本被改过就拒。"""
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import agents
import archive
import claims
import digest
import dispatch
import journal
import knobs
import rewrite
import snapshot
import store
from main import create_app


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


NOW_TEXT = ("## 要做成什么\n一个让人定方向、agent 干活的工具（S0）。\n\n## 现在在做什么\nG1 在做清理（S1-8 S2-62，志-0003）。\n\n"
            "## 做到哪了\n存档、世界树做完了（J1）。\n\n## 定下来的做法\n改核心先拿锁（通-1）。\n")


def _project(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    _w(proj.root / "笔记" / "日志" / "2026-09.md", "# 日志 · 2026-09\n\n## 志-0001 · 2026-09-20 10:00 · 人 · 操作 · 总览\n九月的一条\n\n"
                                                 "## 志-0002 · 2026-09-21 10:00 · agent:甲 · 交付 · 总览\n交了 J1\n")
    journal.add(c, proj, "十月的一条", kind="操作", by="人")
    _w(proj.root / "AGENTS.md", "# 规矩\n\n- 通-1 改核心先拿锁\n- 通-1 改核心先拿锁（又抄了一遍）\n")
    _w(proj.root / "治理" / "戒律" / "1 通用戒律.md", "# 通用戒律\n\n- 通-1 改核心先拿锁\n")
    return c


def test_digests_come_due_get_material_and_are_written(proj):
    c = _project(proj)
    ds = {(d["kind"], d["key"]) for d in digest.due(c, proj)}
    assert ("月摘要", "2026-09") in ds and ("现在的样子", "现在的样子") in ds
    assert not any(d["key"] == datetime.now().strftime("%Y-%m") for d in digest.due(c, proj))   # 这个月的不写
    pk = digest.packet(c, proj, "月摘要", "2026-09")
    assert len(pk["logs"]) == 2 and pk["logs"][0].startswith("志-0001") and "出处" in pk["ask"]
    with pytest.raises(store.Refused):
        digest.write(c, proj, "现在的样子", "现在的样子", "太短", by="agent:甲")
    with pytest.raises(store.Refused, match="定下来的做法"):
        digest.write(c, proj, "现在的样子", "现在的样子", NOW_TEXT.replace("## 定下来的做法", "## 别的") + "x" * 80, by="agent:甲")
    r = digest.write(c, proj, "月摘要", "2026-09", "九月：立项、交了第一件（J1，志-0002）。" * 5, by="agent:甲")
    f = proj.root / r["out"]
    assert f.read_text(encoding="utf-8").startswith("# 2026-09 摘要\n\n> 谁写的：agent:甲") and "日志 2 条" in r["basis"]
    assert not any(d["key"] == "2026-09" for d in digest.due(c, proj))                    # 写过了
    assert any(d["kind"] == "总摘要" for d in digest.due(c, proj))                          # 有了月摘要，该写总的
    digest.write(c, proj, "现在的样子", "现在的样子", NOW_TEXT, by="agent:甲")
    assert [x["title"] for x in digest.listing(proj)][:1] == ["现在的样子"]
    t, h = digest.now_text(proj)
    assert "## 做到哪了" in t and h["谁写的"] == "agent:甲"
    c.close()


def test_planner_gets_the_digest_job_and_overview_shows_now(proj):
    c = _project(proj)
    agents.create(c, proj, "claude-code", "规划的", by="人", program="Claude Code")             # G1
    a = agents.create(c, proj, "乙", "规划的", by="人", program="Codex（gpt-6-astra）")
    agents.update(c, proj, a["code"], {"roles": ["规划"]}, by="人")
    got = dispatch.next_task(c, proj, "agent:乙")
    assert got["action"] == "write_digest" and got["digest"]["kind"] in ("月摘要", "现在的样子") and got["digest"]["packet"]["ask"]
    assert any(r["goal"] == digest.JOB for r in claims.active(c))                         # 同一份只给一个人
    knobs.set_many(c, {"digest_by": "G1"})
    assert digest.job(c, proj, "agent:乙") is None
    digest.write(c, proj, "现在的样子", "现在的样子", NOW_TEXT, by="agent:乙")
    c.close()
    import mcp_server
    import anyio
    from test_mcp import _call
    out = anyio.run(_call, proj, [("get_overview", {})])
    text = out[0] if isinstance(out, list) else str(out)
    assert "项目现在的样子" in text and "## 做到哪了" in text


def test_rewrite_sheet_compare_accept_and_rules(proj):
    c = _project(proj)
    new = "# 规矩\n\n- 通-1 改核心先拿锁（详细见 治理/戒律/1 通用戒律.md）\n"
    with pytest.raises(store.Refused):
        rewrite.propose(c, proj, "笔记/总览.md", new, [{"what": "x", "why": "y"}], by="agent:乙")      # 不是正本
    with pytest.raises(store.Refused):
        rewrite.propose(c, proj, "AGENTS.md", new, [{"what": "合并重复"}], by="agent:乙")            # 没写为什么
    x = rewrite.propose(c, proj, "AGENTS.md", new, [{"what": "合并重复的通-1", "from": "AGENTS.md 第 3、4 行", "why": "同一条抄了两遍"}], by="agent:乙")
    assert x["code"] == "改-1" and x["state"] == "待定" and not x["direction"]
    d = rewrite.diff(proj, "改-1")
    assert any(l.startswith("-- 通-1 改核心先拿锁（又抄了一遍）") or "又抄了一遍" in l for l in d["lines"]) and not d["stale"]
    with pytest.raises(store.Refused):
        rewrite.accept(c, proj, "改-1", by="agent:乙")                                       # 别的 agent 不能点
    n = len(snapshot.list_saves(proj))
    r = rewrite.accept(c, proj, "改-1", by="agent:claude-code")                               # G1 能点非方向文件
    assert (proj.root / "AGENTS.md").read_text(encoding="utf-8") == new and len(snapshot.list_saves(proj)) == n + 1
    old = proj.root / r["old_version"]
    assert old.read_text(encoding="utf-8").count("通-1") == 2
    assert any(row["state"] == "旧版" and row["replaced_by"] == "改-1" for row in archive.index(proj))
    # 方向文件：只有人能换；出单后又被改过就拒
    y = rewrite.propose(c, proj, "治理/戒律/1 通用戒律.md", "# 通用戒律\n\n- 通-1 改核心先拿锁，交付时自动放\n",
                        [{"what": "补一句", "from": "协议第五节", "why": "跟现在的做法对上"}], by="agent:乙")
    assert y["direction"]
    with pytest.raises(store.Refused, match="方向文件"):
        rewrite.accept(c, proj, y["code"], by="agent:claude-code")
    _w(proj.root / "治理" / "戒律" / "1 通用戒律.md", "# 通用戒律\n\n- 通-1 改核心先拿锁（人刚改过）\n")
    with pytest.raises(store.Refused, match="又被改过"):
        rewrite.accept(c, proj, y["code"], by="人")
    assert rewrite.drop(c, proj, y["code"], by="人", why="正本改过了")["state"] == "不要了"
    c.close()


def test_ask_for_a_rewrite_and_the_pages(proj):
    c = _project(proj)
    a = agents.create(c, proj, "乙", "规划的", by="人", program="Codex（gpt-6-astra）")
    agents.update(c, proj, a["code"], {"roles": ["规划"]}, by="人")
    digest.write(c, proj, "月摘要", "2026-09", "九月：立项（志-0001）。" * 10, by="agent:乙")
    digest.write(c, proj, "总摘要", "总的", "到现在：立项（2026-09）。" * 10, by="agent:乙")
    digest.write(c, proj, "现在的样子", "现在的样子", NOW_TEXT, by="agent:乙")
    c.close()
    with TestClient(create_app(proj)) as client:
        assert client.post("/api/rewrite/ask", json={"path": "AGENTS.md", "note": "抄的戒律换成指向原处"}).json()["rel"] == "AGENTS.md"
        c = store.connect(proj.db_path)
        assert dispatch.next_task(c, proj, "agent:乙")["action"] == "draft"                  # 规划的活排在前面
        got = {"rewrite": rewrite.job(c, proj, "agent:乙")}                                   # 规划活做完了才轮到重写单
        assert got["rewrite"]["rel"] == "AGENTS.md"
        x = rewrite.propose(c, proj, "AGENTS.md", "# 规矩\n\n- 通-1 见戒律\n", [{"what": "换成指向", "from": "通-1", "why": "抄的会过时"}], by="agent:乙")
        c.close()
        d = client.get("/api/rewrite").json()
        assert d["items"][0]["code"] == x["code"] and d["wanted"] == [] and "AGENTS.md" in d["canon"]
        assert client.get(f"/api/rewrite/{x['code']}/diff").json()["target"] == "AGENTS.md"
        assert client.post(f"/api/rewrite/{x['code']}/accept", json={"confirm": False}).status_code == 409
        assert client.post(f"/api/rewrite/{x['code']}/accept", json={"confirm": True}).json()["state"] == "换上了"
        g = client.get("/api/digest").json()
        assert [i["title"] for i in g["items"]] == ["现在的样子", "总的", "2026-09"]
        assert any(r["kind"] == "旧版" for r in client.get("/api/archive").json()["items"])


def test_agents_do_the_rewrite_end_to_end(proj):
    """作者 10-03「我的想法是重铸由agent来做」：查乱报的自动派给规划的员工出单，另一个审核的员工审过就换上；方向文件还是只有人能换。"""
    c = _project(proj)
    agents.create(c, proj, "claude-code", "规划的", by="人", program="Claude Code")             # G1
    for name, role in (("乙", "规划"), ("丙", "审核")):
        a = agents.create(c, proj, name, "写代码的", by="人", program="Codex（gpt-6-astra）")
        agents.update(c, proj, a["code"], {"roles": [role]}, by="人")
    for kind, key, text in (("月摘要", "2026-09", "九月（志-0001）。" * 12), ("总摘要", "总的", "到现在（2026-09）。" * 12), ("现在的样子", "现在的样子", NOW_TEXT)):
        digest.write(c, proj, kind, key, text, by="agent:乙")
    long_rule = "- 通-2 网页能直接做的（删模块、复活、删存档）先挪进回收站：空的直接做，有文件先警告、人确认；agent 照删除请求挪，不直接删"
    _w(proj.root / "AGENTS.md", "# 规矩\n\n- 通-1 改核心先拿锁\n" + long_rule + "\n")
    _w(proj.root / "治理" / "戒律" / "1 通用戒律.md", "# 通用戒律\n\n- 通-1 改核心先拿锁\n" + long_rule.replace("不直接删", "不要直接删") + "\n")
    assert knobs.get(c, "rewrite_auto")                                                       # 默认开着
    rels = [w["rel"] for w in rewrite.wanted(c, proj)]
    assert "AGENTS.md" in rels and "治理/戒律/1 通用戒律.md" in rels                          # 查乱报的重复：不用人点
    got = dispatch.next_task(c, proj, "agent:乙")
    assert got["action"] == "write_rewrite" and got["rewrite"]["rel"] == "AGENTS.md" and got["rewrite"]["dups"]
    x = rewrite.propose(c, proj, "AGENTS.md", "# 规矩\n\n- 通-1 改核心先拿锁（全文见 治理/戒律/1 通用戒律.md）\n",
                        [{"what": "合并重复的通-1", "from": "AGENTS.md 第 3、4 行", "why": "同一条抄了两遍"}], by="agent:乙")
    assert dispatch.next_task(c, proj, "agent:乙")["action"] != "review_rewrite"            # 不审自己出的
    rv = dispatch.next_task(c, proj, "agent:丙")
    assert rv["action"] == "review_rewrite" and rv["rewrite_review"]["code"] == x["code"] and rv["rewrite_review"]["diff"]
    with pytest.raises(store.Refused):
        rewrite.review(c, proj, x["code"], True, "行", by="agent:乙")                       # 出单的人不能审
    r = rewrite.review(c, proj, x["code"], True, "出处对得上，没删掉有效的规矩", by="agent:丙")
    assert r["state"] == "换上了" and "全文见" in (proj.root / "AGENTS.md").read_text(encoding="utf-8")
    assert not any(cl["goal"] == rewrite.REVIEW for cl in claims.active(c))
    y = rewrite.propose(c, proj, "治理/戒律/1 通用戒律.md", "# 通用戒律\n\n- 通-1 改核心先拿锁，交付时自动放\n",
                        [{"what": "补一句", "from": "协议第五节", "why": "跟现在的做法对上"}], by="agent:乙")
    assert rewrite.review_job(c, proj, "agent:丙") is None                                    # 方向文件不派给员工审
    knobs.set_many(c, {"digest_by": "G1"})                                                   # 「现阶段由你全权处理」：员工不领、不审
    assert rewrite.job(c, proj, "agent:乙") is None and digest.job(c, proj, "agent:乙") is None
    with pytest.raises(store.Refused, match="方向文件"):
        rewrite.review(c, proj, y["code"], True, "行", by="agent:丙")
    c.close()
