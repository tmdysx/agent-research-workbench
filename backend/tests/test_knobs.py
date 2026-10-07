"""设置里的自动化档位和存档（S1-8 S2-57、S2-58、S2-59；作者 10-03「就是自动化的程度吧，有档位，一个是单agent，单存档，自动按照蓝图需求任务
一个个跑，高档位就是，同时开多个agent，多个节点多个分支一起做项目，然后优中选优……存档可以设计成最多存多少档，默认如何存档等等，可以自定义多一点」）。"""
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import agents
import autolaunch
import branching
import claims
import deliveries
import dispatch
import knobs
import snapshot
import store
import worldtree
from main import create_app
from project import Project


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _conn(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    return c


def test_levels_fill_the_numbers_and_bad_numbers_are_refused(proj):
    c = _conn(proj)
    d = knobs.all_auto(c)
    assert d["level"] == 2 and d["max_agents"] == 3 and d["per_item"] == 1 and not d["custom"]   # 默认就是现在的样子
    r = knobs.set_many(c, {"level": 4})
    assert r["auto"]["max_agents"] == 4 and r["auto"]["per_item"] == 2 and not r["auto"]["custom"]
    assert knobs.set_many(c, {"max_agents": 6})["auto"]["custom"]                           # 改了一个数：自定义
    assert knobs.set_many(c, {"level": 1})["auto"]["max_agents"] == 1
    with pytest.raises(store.Refused):
        knobs.set_many(c, {"max_agents": 3})                                                # 一条线只开一个
    with pytest.raises(store.Refused):
        knobs.set_many(c, {"keep": 9999})
    with pytest.raises(store.Refused):
        knobs.set_many(c, {"picker": "随便"})
    with pytest.raises(store.Refused):
        knobs.set_many(c, {"stuck_boss_min": 90, "stuck_human_min": 60})                    # 报上级要早于告诉你
    autolaunch.set_settings(c, max_=3)                                                      # 窗口页上改「同时最多」：一条线变成档位 2
    assert knobs.get(c, "level") == 2 and autolaunch.settings(c)["max"] == 3
    c.close()


def test_times_follow_the_settings(proj):
    c = _conn(proj)
    knobs.set_many(c, {"release_min": 10, "stuck_boss_min": 5, "stuck_human_min": 8, "cooldown_min": 3, "rounds": 7})
    assert claims.ttl(c) == 600 and autolaunch.cooldown(c) == 180 and agents.busy(c) == 300
    import runs
    assert runs.settings(c)["rounds"] == 7
    claims.claim(c, "S1-1", "S2-1", "agent:甲", ["S1-1 S2-1"])
    with store.tx(c):
        c.execute("UPDATE claim SET beat = ?", (time.time() - 11 * 60,))
    assert claims.active(c) == []                                                           # 10 分钟没动静就算放手
    c.close()


def test_saves_keep_what_the_settings_say_and_auto_ones_are_counted_apart(proj):
    c = _conn(proj)
    _w(proj.root / "a.txt", "1")
    knobs.set_many(c, {"keep": 3, "keep_auto": 1})
    first = snapshot.save(c, proj, name="手1", mode="全量", by="人")
    snapshot.settle(c, proj, first["code"], by="人")
    for i in range(2, 6):
        _w(proj.root / "a.txt", str(i))
        snapshot.save(c, proj, name=f"手{i}", mode="全量", by="人")
    a1 = snapshot.auto_save(c, proj, "on_core", name="改核心前 甲", by="agent:甲")
    a2 = snapshot.auto_save(c, proj, "on_deliver", name="交了 J1", by="agent:甲", checks=[{"name": "测试", "ok": True}])
    assert a2["name"].startswith("自动 · ") and a2["auto"] and a2["grade"] == "绿档"
    names = [m["name"] for m in snapshot.list_saves(proj)]
    assert names == [a2["name"], "手5", "手4", "手3", "手1"]          # 手动的留 3 档 + 定性的；自动的另留 1 个，不挤掉手动的
    assert a1["code"] not in [m["code"] for m in snapshot.list_saves(proj)]
    knobs.set_many(c, {"on_core": False})
    assert snapshot.auto_save(c, proj, "on_core", name="改核心前 乙", by="agent:乙") is None   # 关了就不存
    st = snapshot.status(proj)
    assert st["saves"] == 5 and st["auto"] == 1 and st["settled"] == 1
    c.close()


def test_timed_save_only_when_due_and_changed(proj):
    c = _conn(proj)
    _w(proj.root / "a.txt", "1")
    m = snapshot.save(c, proj, name="开头", mode="全量", by="人")
    assert snapshot.timed_save(c, proj) is None                                            # 设置里没开
    knobs.set_many(c, {"every_h": 2})
    later = datetime.strptime(m["at"], "%Y-%m-%d %H:%M") + timedelta(hours=3)
    assert snapshot.timed_save(c, proj, now=later) is None                                 # 到点了，可没改动
    _w(proj.root / "a.txt", "2")
    assert snapshot.timed_save(c, proj, now=datetime.strptime(m["at"], "%Y-%m-%d %H:%M") + timedelta(minutes=30)) is None   # 没到点
    got = snapshot.timed_save(c, proj, now=later)
    assert got and got["auto"] and got["name"] == "自动 · 定时"
    c.close()


def test_ignore_table_and_space_cap(proj, monkeypatch):
    c = _conn(proj)
    _w(proj.root / "大数据" / "原始.csv", "很大")
    _w(proj.root / "a.txt", "1")
    rows = snapshot.set_ignore(c, proj, [{"path": "大数据/", "why": "能重新下载"}, {"path": " "}])
    assert rows == [{"path": "大数据", "why": "能重新下载"}]
    with pytest.raises(store.Refused):
        snapshot.set_ignore(c, proj, [{"path": "../外面"}])
    m = snapshot.save(c, proj, name="一", mode="全量", by="人")
    assert not any(k.startswith("大数据/") for k in snapshot._files(snapshot._folder(proj, m["code"])))
    for i in range(3):
        _w(proj.root / "a.txt", f"x{i}")
        snapshot.auto_save(c, proj, "on_core", name=f"自{i}", by="agent:甲")
    monkeypatch.setattr(snapshot, "total_size", lambda p: 999 << 30)                       # 超了空间上限：每存一次丢一个最老的自动档
    snapshot.prune(c, proj)
    left = [x["name"] for x in snapshot.list_saves(proj) if x.get("auto")]
    assert len(left) == 2 and "自动 · 自0" not in left and any(x["name"] == "一" for x in snapshot.list_saves(proj))
    with pytest.raises(store.Refused, match="空间上限"):
        worldtree.grow(c, proj, name="枝", by="人")
    c.close()


def test_the_settings_pages_read_and_write(proj):
    c = _conn(proj)
    c.close()
    with TestClient(create_app(proj)) as client:
        d = client.get("/api/settings/auto").json()
        assert [x["name"] for x in d["spec"]["levels"]] == ["一条线", "主干上几个人", "分枝并行", "优中选优"] and d["knobs"]["level"] == 2
        r = client.put("/api/settings/auto", json={"patch": {"level": 4, "picker": "你"}}).json()
        assert r["auto"]["per_item"] == 2 and r["auto"]["picker"] == "你"
        assert client.put("/api/settings/auto", json={"patch": {"level": 9}}).status_code >= 400
        s = client.get("/api/settings/saves").json()
        assert s["knobs"]["keep"] == 10 and s["knobs"]["on_core"] and "total" in s["space"]
        assert client.put("/api/settings/saves", json={"patch": {"keep": 20, "every_h": 4}}).json()["saves"]["keep"] == 20
        assert client.put("/api/settings/save-ignore", json={"rows": [{"path": "数据", "why": "大"}]}).json()["ignore"][0]["path"] == "数据"
        assert client.get("/api/settings/saves").json()["ignore"] == [{"path": "数据", "why": "大"}]
        assert client.post("/api/checkpoints/gc").json()["removed"] == 0


# ---------------------------------------------------------------- 档位 3、4 自己转

GOAL = ("# S1-1 看得懂\n\n**一句话**\n\n规划：定稿 · 2026-10-03 · 作者：「定稿」\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"
        "| S2-1 | 〔程序〕第一件 | 项目 需-1 | 测试 | 没做 |\n| S2-2 | 〔文档〕第二件 | 项目 需-1 | 看 | 没做 |\n")


def _team(proj):
    c = _conn(proj)
    _w(proj.root / "治理" / "目标" / "S1-1 看得懂.md", GOAL)
    _w(proj.root / "模板.html", "<p>一</p>\n<p>二</p>\n")
    _w(proj.root / "AGENTS.md", "规矩\n")
    for name, prog, roles in (("甲", "Codex（gpt-6-astra）", ["干活"]), ("乙", "Codex（gpt-5.5）", ["干活"]), ("丙", "Codex（gpt-6-astra）", ["验收"])):
        a = agents.create(c, proj, name, "写代码的", by="人", program=prog)
        agents.update(c, proj, a["code"], {"auto": True, "roles": roles}, by="人")
    return c


def _calls():
    sent = []

    def call(method, path, body=None):
        sent.append(body)
        return {"items": []}
    return sent, call


def _deliver_on(b, ok, text):
    bp = Project(Path(b["path"]))
    _w(bp.root / "模板.html", text)
    bc = store.connect(bp.db_path)
    try:
        return deliveries.deliver(bc, bp, goal="S1-1", sub="S2-1", did="改了首页", by="agent:" + b["name"].split()[-1],
                                  checks=[{"name": "测试", "ok": ok, "detail": "跑了"}])
    finally:
        bc.close()


def test_level_four_grows_two_branches_and_the_reviewer_picks_one(proj):
    c = _team(proj)
    knobs.set_many(c, {"level": 4})
    sent, call = _calls()
    got = branching.tick(c, proj, running=0, alive=set(), call=call)
    gs = branching.groups(proj)
    assert len(gs) == 1 and gs[0]["item"] == "S1-1 S2-1" and len(gs[0]["branches"]) == 2 and len(got) == 2
    assert {b["title"].split(" · ")[0] for b in sent} == set(gs[0]["branches"])                 # 窗口标题带枝号
    assert {a for a in gs[0]["agents"]} == {agents.find(proj, "甲")["code"], agents.find(proj, "乙")["code"]}   # 两个不同模型的
    g1 = dispatch.blueprint.find(dispatch.blueprint.pyramid(proj), "S1-1")
    x1 = g1["subs"][0]
    assert "枝上做" in dispatch._work_reason(proj, agents.find(proj, "甲"), g1, x1)            # 主干上这件不领
    assert any(r["agent"] == "世界树:" + gs[0]["code"] for r in claims.active(c))
    bs = [worldtree.get(proj, code) for code in gs[0]["branches"]]
    _deliver_on(bs[0], True, "<p>一 甲改的</p>\n<p>二</p>\n")
    _deliver_on(bs[1], False, "<p>一</p>\n<p>二 乙改的</p>\n")                                 # 检查没过：不结果
    branching.tick(c, proj, running=2, alive=set(gs[0]["agents"]), call=call)
    assert worldtree.get(proj, bs[0]["code"])["state"] == "结果了" and worldtree.get(proj, bs[1]["code"])["state"] == "长着"
    assert branching.group(proj, gs[0]["code"])["state"] == "长着"                             # 还有在长的、没等够
    branching.tick(c, proj, running=2, alive=set(gs[0]["agents"]), call=call, now=time.time() + 5 * 3600)
    g = branching.group(proj, gs[0]["code"])
    assert g["state"] == "等挑" and [x["branch"] for x in g["candidates"]] == [bs[0]["code"]]
    rv = "agent:丙"
    job = branching.pick_job(c, proj, rv)
    assert job and job["code"] == g["code"] and branching.pick_job(c, proj, "agent:甲") is None   # 自己做的不挑
    nt = dispatch.next_task(c, proj, rv)
    assert nt["action"] == "pick_fruit" and nt["fruit"]["code"] == g["code"]
    g = branching.pick(c, proj, g["code"], bs[0]["code"], "甲那版检查全过", by=rv)
    assert g["state"] == "合了" and "甲改的" in (proj.root / "模板.html").read_text(encoding="utf-8")
    assert worldtree.get(proj, bs[1]["code"])["state"] == "砍了"
    assert not any(r["agent"].startswith("世界树:") for r in claims.active(c))
    c.close()


def test_level_three_without_reviewers_picks_by_checks_and_merges(proj):
    c = _team(proj)
    agents.update(c, proj, agents.find(proj, "丙")["code"], {"auto": False}, by="人")       # 没有能挑的验收员工
    knobs.set_many(c, {"level": 3, "branch_scope": "动到核心的"})
    sent, call = _calls()
    branching.tick(c, proj, running=0, alive=set(), call=call)
    gs = branching.groups(proj)
    assert [g["item"] for g in gs] == ["S1-1 S2-1"] and len(gs[0]["branches"]) == 1          # 〔文档〕那件不开枝，在主干做
    b = worldtree.get(proj, gs[0]["branches"][0])
    _deliver_on(b, True, "<p>一 枝上改的</p>\n<p>二</p>\n")
    branching.tick(c, proj, running=1, alive=set(gs[0]["agents"]), call=call)
    g = branching.group(proj, gs[0]["code"])
    assert g["state"] == "合了" and "按检查自动挑" in g["why"] and "枝上改的" in (proj.root / "模板.html").read_text(encoding="utf-8")
    c.close()


def test_limits_hold_and_after_pick_can_wait_for_you(proj):
    c = _team(proj)
    knobs.set_many(c, {"level": 4, "max_agents": 1})
    sent, call = _calls()
    assert branching.tick(c, proj, running=0, alive=set(), call=call) == [] and branching.groups(proj) == []   # 人不够一组：不开
    knobs.set_many(c, {"max_agents": 4, "wt_max": 1})
    branching.tick(c, proj, running=0, alive=set(), call=call)
    g = branching.groups(proj)[0]
    assert len(g["branches"]) == 1 and g["k"] == 1                                         # 最多 1 根枝：长了 1 根就停
    knobs.set_many(c, {"after_pick": "等你点", "picker": "验收的员工", "compare_wait_h": 1})
    _deliver_on(worldtree.get(proj, g["branches"][0]), True, "<p>改</p>\n")
    branching.tick(c, proj, running=1, alive=set(g["agents"]), call=call, now=time.time() + 2 * 3600)
    g = branching.pick(c, proj, g["code"], g["branches"][0], "就这根", by="agent:丙")
    assert g["state"] == "等你点合" and "<p>改</p>" not in (proj.root / "模板.html").read_text(encoding="utf-8")
    g = branching.pick(c, proj, g["code"], g["pick"], "行", by="人")
    assert g["state"] == "合了"
    c.close()
