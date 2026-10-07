"""agent 报到和档案（作者 09-30：「得给agent注册，就是一个agent刚刚接手的时候，要有一个注册档案和编号，职责啥的都可以随着项目变迁」
「agent可以让人自定义……我还是想让玩家可以自己动手diy」）。"""
import time

import pytest

import agents
import claims
import deliveries
import dispatch
import readiness
import store
import tools
import trash


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


S0 = "# S0 终极目标\n\n**做一个试验。**\n\n| S1 | 目标 |\n|---|---|\n| S1-1 试验 | 试一下 |\n| S1-2 另一个 | 再试 |\n"
S1 = ("# S1-1 试验\n\n**把文献模块装修一下。**\n\n规划：定稿 · 2026-10-01 · 测试\n\n动到的模块：文献\n\n| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
      "| S2-1 | 文献列表 | 拖一篇进来左栏多一行 | 没做 |\n| S2-2 | 阅读页 | 翻到第 3 页 | 没做 |\n")
S12 = "# S1-2 另一个\n\n**再试。**\n\n规划：定稿 · 2026-10-01 · 测试\n\n| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n| S2-1 | 写说明 | 说明里有这一段 | 没做 |\n"


@pytest.fixture
def bp(proj, monkeypatch, tmp_path):
    _w(proj.materials / "蓝图" / "S0 终极目标.md", S0)
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1)
    _w(proj.materials / "蓝图" / "S1-2 另一个.md", S12)
    (proj.materials / "文献").mkdir(parents=True)
    _w(proj.root / "AGENTS.md", "# 戒律\n- 必停：彻底删除、公开发布\n")
    _w(proj.root / ".mcp.json", '{"mcpServers": {"research-console": {}}}')
    lib = tmp_path / "工具库"
    lib.mkdir()
    monkeypatch.setattr(tools, "LIB", lib)
    monkeypatch.setattr(readiness, "_claude_cli", lambda: None)
    tools.forget()
    c = store.connect(proj.db_path)
    yield c
    c.close()


def test_register_gives_a_number_that_is_never_reused(proj, bp):
    c = bp
    a = agents.register(c, proj, "claude-code", "Claude Code", "写程序")
    assert a["new"] and a["agent"]["code"] == "G1" and a["agent"]["core"] == "能"
    assert (proj.root / "自动化" / "agent" / "G1 claude-code.md").is_file()
    again = agents.register(c, proj, "agent:claude-code")                          # 同名再来：接上原来那份
    assert not again["new"] and again["agent"]["code"] == "G1"
    b = agents.register(c, proj, "codex#2", "Codex")["agent"]
    assert b["code"] == "G2" and "报到 · 用 Codex" in b["history"][0]
    agents.delete(c, proj, "G2", by="人", reason="试一下删")
    assert agents.register(c, proj, "cursor")["agent"]["code"] == "G3"            # 号不回收


def test_no_work_before_registering(proj, bp):
    with pytest.raises(store.Refused, match="还没报到"):
        dispatch.next_task(bp, proj, "agent:new-comer")
    with pytest.raises(store.Refused, match="还没报到"):
        agents.take_core(bp, proj, "agent:new-comer")


def test_the_profile_decides_what_it_gets(proj, bp):
    c = bp
    agents.register(c, proj, "doc")
    agents.update(c, proj, "doc", {"scope": "S1-2"}, by="人", why="只管写说明")
    got = dispatch.next_task(c, proj, "agent:doc")                                  # 蓝图里 S1-1 在前，但它只管 S1-2
    assert got["task"]["goal"] == "S1-2"
    agents.register(c, proj, "coder")
    agents.update(c, proj, "coder", {"avoid": "文献"}, by="人")
    assert dispatch.next_task(c, proj, "agent:coder")["task"] is None               # 剩下的都在文献这条道上：不给它
    agents.register(c, proj, "free")
    assert dispatch.next_task(c, proj, "agent:free")["task"]["goal"] == "S1-1"      # 档案上都没写：都能领


def test_core_permission_is_only_changed_by_the_human(proj, bp):
    c = bp
    agents.register(c, proj, "writer")
    with pytest.raises(store.Refused, match="只有人能改"):
        agents.update(c, proj, "writer", {"core": "能"}, by="agent:writer")
    agents.update(c, proj, "writer", {"line": "写说明", "brief": "- 只写文档"}, by="agent:writer", why="项目到了写文档的阶段")
    agents.update(c, proj, "writer", {"core": "不能"}, by="人")
    with pytest.raises(store.Refused, match="改核心：不能"):
        agents.take_core(c, proj, "agent:writer")
    with pytest.raises(store.Refused, match="只能改自己的"):
        agents.update(c, proj, "writer", {"line": "乱改"}, by="agent:someone")
    h = agents.get(proj, "writer")["history"]                                      # 变迁：每次改一行，写着谁改的、为什么
    assert len(h) == 3 and "agent:writer" in h[1] and "项目到了写文档的阶段" in h[1] and "人 · 改核心：能 → 不能" in h[2]


def test_people_make_their_own_agents(proj, bp):
    c = bp
    a = agents.create(c, proj, "codex", "写文档的", by="人", program="Codex")
    assert a["code"] == "G1" and a["core"] == "不能" and "只写" not in a["line"] and a["brief"]
    assert agents.register(c, proj, "codex")["agent"]["code"] == "G1"               # 提前建好：它来了报同样的名字就接上
    b = agents.copy(c, proj, "G1", "codex#2")
    assert b["code"] == "G2" and b["brief"] == a["brief"] and "照 G1 codex 复制" in b["history"][0]
    with pytest.raises(store.Refused, match="已经有档案"):
        agents.create(c, proj, "codex")
    x = agents.delete(c, proj, "G2", by="人", reason="不要了")
    assert agents.find(proj, "codex#2") is None
    trash.restore(c, proj, x["code"], by="人")
    assert agents.find(proj, "codex#2")["code"] == "G2"


def test_roster_lamps_and_the_story_of_one_item(proj, bp):
    c = bp
    agents.register(c, proj, "a")
    agents.register(c, proj, "b")
    with store.tx(c):
        store.log(c, "agent:visitor", "看全貌")                                     # 来过、没报到的
    dispatch.next_task(c, proj, "agent:a")
    lamps = {r["name"]: (r["lamp"], r["registered"]) for r in agents.roster(c, proj)}
    assert lamps == {"a": ("在干活", True), "b": ("空着", True), "visitor": ("空着", False)}
    c.execute("UPDATE claim SET beat = ? WHERE agent = 'agent:a'", (time.time() - 40 * 60,))
    assert next(r for r in agents.roster(c, proj) if r["name"] == "a")["lamp"] == "停了"
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:a")
    deliveries.reject(c, proj, j["code"], "左栏没多一行", by="人")
    story = [e["what"] for e in agents.timeline(c, proj, "S1-1", "S2-1") if e["what"] != "本机 git"]
    assert story == ["领了", "交付", "验收通过", "放手", "打回"]
    assert next(r for r in agents.roster(c, proj) if r["name"] == "a")["delivered"] == [j["code"]]
    assert claims.active(c) == []


def test_the_web_page_can_make_and_change_agents(proj, bp):
    from fastapi.testclient import TestClient
    from main import create_app
    with TestClient(create_app(proj)) as client:
        a = client.post("/api/agents", json={"name": "codex", "template": "写代码的", "program": "Codex"}).json()
        assert a["code"] == "G1" and a["core"] == "能"
        b = client.put("/api/agents/G1", json={"scope": ["S1-2"], "core": "不能", "why": "先只写说明"}).json()
        assert b["scope"] == ["S1-2"] and b["core"] == "不能" and "先只写说明" in b["history"][-1]
        one = client.get("/api/agents/codex").json()
        assert one["path"] == "自动化/agent/G1 codex.md" and one["roster"]["lamp"] == "空着"
        allp = client.get("/api/agents").json()
        assert "写文档的" in allp["templates"] and [r["code"] for r in allp["items"]] == ["G1"]
        assert client.post("/api/agents/G1/copy", json={"name": "codex#2"}).json()["code"] == "G2"
        assert client.post("/api/agents/G2/delete", json={"reason": "多余"}).status_code == 200
        auto = client.get("/api/auto").json()
        assert [r["name"] for r in auto["agents"]] == ["codex"] and auto["handovers"] == []
        assert client.get("/api/auto/timeline", params={"goal": "S1-1", "sub": "S2-1"}).json()["items"] == []


def test_what_the_first_real_run_caught(proj, bp):
    """10-01 真跑一次：两个子 agent 都卡在开工单的红灯上——
    戒律灯认死「必停」两个字；「所有模块（说明）」被当成模块名；开不了工的单每调一次多一张、报错不说缺什么。"""
    c = bp
    _w(proj.root / "AGENTS.md", "# 戒律\n- 通-15 自动推进只在两类事上停：彻底删除 / 公开发布；改方向\n")   # 09-30 放宽后的写法
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1.replace("动到的模块：文献", "动到的模块：所有模块（插件在文件上加按钮）、文献"))
    import blueprint
    assert blueprint.find(blueprint.pyramid(proj), "S1-1")["modules"] == ["所有模块", "文献"]
    agents.register(c, proj, "a")
    got = dispatch.next_task(c, proj, "agent:a")
    assert got["task"]["goal"] == "S1-1"                                           # 照样开得了工
    import workorders
    workorders.stop(c, proj, got["wo"]["code"], by="agent:a")
    claims.release(c, "S1-1", "S2-1", "agent:a")
    _w(proj.root / "AGENTS.md", "# 戒律\n- 什么都没写\n")                     # 真缺：开不了工
    for _ in range(2):
        with pytest.raises(store.Refused, match="有活，但 K1 开不了工——戒律：AGENTS.md 里没写在哪几件事上停"):
            dispatch.next_task(c, proj, "agent:a")
    assert [w["code"] for w in workorders.list_all(proj)] == ["K1"]                # 上回那张接着用，再调也不多开一张


def test_roles_levels_and_bosses_only_people_set(proj):
    """分工（S1-8 S2-38，样图 R3）：岗位、等级、上级三格只有人改；上级不能是自己、不能绕圈；组织页按岗位分、流程每关几件。"""
    c = store.connect(proj.db_path)
    for n in ("a", "b", "c"):
        agents.register(c, proj, n, "测试")
    a = agents.get(proj, "a")
    assert (a["roles"], a["level"], a["boss"]) == ([], "正式", "人") and agents.jobs(a) == ["干活"]   # 以前的档案：算干活、正式、向人汇报
    with pytest.raises(store.Refused):
        agents.update(c, proj, "a", {"roles": ["审核"]}, by="agent:a")                 # agent 自己改不了岗位
    agents.update(c, proj, "a", {"roles": ["干活", "带队"], "level": "资深"}, by="人", why="带队")
    agents.update(c, proj, "b", {"roles": ["审核"], "boss": "G1", "level": "资深"}, by="人")      # 资深才能当别人的上级
    agents.update(c, proj, "c", {"roles": ["验收"], "boss": "b"}, by="人")
    with pytest.raises(store.Refused):
        agents.update(c, proj, "a", {"boss": "G3"}, by="人")                           # G3 往上是 G2、G1：绕回自己
    with pytest.raises(store.Refused):
        agents.update(c, proj, "b", {"boss": "G2"}, by="人")                           # 不能是自己
    with pytest.raises(store.Refused):
        agents.update(c, proj, "b", {"roles": ["老板"]}, by="人")
    b = agents.get(proj, "b")
    assert b["roles"] == ["审核"] and b["boss"] == "G1" and "岗位：（空） → 审核" in b["history"][-1]
    assert "岗位：审核" in agents.brief_text(b) and "上级：G1" in agents.brief_text(b)
    o = agents.org(c, proj)
    people = {r["code"]: r for r in o["people"]}
    assert people["G1"]["reports"] == ["G2"] and people["G2"]["reports"] == ["G3"] and people["G1"]["level"] == "资深"
    flow = {f["key"]: f for f in o["flow"]}
    assert flow["审核"]["who"] == ["G2"] and flow["验收"]["who"] == ["G3"] and flow["规划"]["who"] == []
    assert agents.create(c, proj, "d", "复查的")["roles"] == ["验收"]                  # 以前的样子名「复查的」= 验收的
    c.close()


def test_stuck_work_goes_to_the_boss_then_to_people(proj):
    """卡住了有人管（S1-8 S2-36）：半小时没动静报给上级（它领活时先看到），一小时起也报给人；上级能让它放手。"""
    import time
    c = store.connect(proj.db_path)
    for n in ("a", "b", "x"):
        agents.register(c, proj, n, "测试")
    agents.update(c, proj, "b", {"roles": ["干活", "带队"], "level": "资深"}, by="人")
    agents.update(c, proj, "a", {"boss": "G2"}, by="人")
    claims.claim(c, "S1-1", "S2-1", "agent:a", ["S1-1 S2-1"], "甲")
    assert agents.stuck(c, proj) == [] and agents.wake_text(c, proj, "b") == ""
    c.execute("UPDATE claim SET beat = ? WHERE agent = 'agent:a'", (time.time() - 40 * 60,))
    s = agents.stuck(c, proj)
    assert [(r["code"], r["boss"], r["to"]) for r in s] == [("G1", "G2", "G2")]
    w = agents.wake_text(c, proj, "b")
    assert "叫你是因为" in w and "G1 a 领着 S1-1 S2-1" in w and 'for_agent="G1"' in w
    assert agents.wake_text(c, proj, "x") == ""                                          # 不是它的上级：不叫它
    c.execute("UPDATE claim SET beat = ? WHERE agent = 'agent:a'", (time.time() - 70 * 60,))
    assert agents.stuck(c, proj)[0]["to"] == "人"                                        # 一小时了：人那边也看得到
    with pytest.raises(store.Refused):
        agents.release_for(c, proj, "x", "G1", "S1-1", "S2-1")                           # 不是上级不能让它放手
    assert agents.release_for(c, proj, "b", "G1", "S1-1", "S2-1", "换人") == "S1-1 S2-1"
    assert claims.active(c) == []
    c.close()


def test_levels_limit_what_an_agent_may_do(proj):
    """等级管权限（S1-8 S2-41）：见习拿不到核心锁、交的要验收（没有验收的 agent 就等人）；带队、当上级要资深；降等级前先换下面人的上级；按记录建议升级。"""
    c = store.connect(proj.db_path)
    for n in ("a", "b"):
        agents.register(c, proj, n, "测试")
    with pytest.raises(store.Refused):
        agents.update(c, proj, "a", {"roles": ["带队"]}, by="人")                       # 正式的不能带队
    with pytest.raises(store.Refused):
        agents.update(c, proj, "b", {"boss": "G1"}, by="人")                           # G1 不是资深：当不了上级
    agents.update(c, proj, "a", {"level": "资深"}, by="人")
    agents.update(c, proj, "b", {"boss": "G1", "level": "见习"}, by="人")
    with pytest.raises(store.Refused):
        agents.update(c, proj, "a", {"level": "正式"}, by="人")                        # 下面还有 G2：先换上级
    with pytest.raises(store.Refused):
        agents.take_core(c, proj, "b")                                                  # 见习不能改核心
    assert "见习" in agents.brief_text(agents.get(proj, "b"))
    assert agents.suggest(agents.get(proj, "b"), 10, 0) == "通过 10 件、打回 0 件，可以升正式"
    assert agents.suggest(agents.get(proj, "b"), 10, 1) == ""
    assert agents.suggest(agents.get(proj, "a"), 40, 1) == ""                         # 资深：不用再升
    c.close()
