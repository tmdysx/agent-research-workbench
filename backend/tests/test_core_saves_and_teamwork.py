"""09-30 两件：
- 存档只存核心、只留 10 档（作者：「没必要每次都全量存档……只保留10个左右的存档就行了」「只存核心就行了……外部文件和其他的乱七八糟的文件不存」）
- 几个 agent 一起干：认领、同一条道一个人、核心锁、过期放手、自己开工领活、交付放手（作者：「到时候你就可以开多个智能体……也能让codex也加入一起开发」）"""
import json
import time

import pytest

import agents
import claims
import dispatch
import readiness
import snapshot
import store
import tools
import vcs
import workorders


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(proj):
    _w(proj.root / "backend" / "main.py", "print(1)")
    _w(proj.root / "backend" / "governance_paths.py", "# 集中治理以后的程序")
    _w(proj.root / "模板.html", "<html>")
    _w(proj.root / "AGENTS.md", "规矩")
    _w(proj.root / "治理" / "目标" / "S0 终极目标.md", "# S0")
    _w(proj.materials / "测试" / "大视频.mp4", "x" * 1000)
    _w(proj.root / "笔记" / "总览.md", "# 总览 · 笔记\n")
    _w(proj.root / "666.docx", "零碎")
    _w(proj.root / ".claude" / "settings.json", "{}")
    _w(proj.root / ".claude" / "worktrees" / "别的会话" / "模板.html", "整个项目又一份")


def test_core_saves_only_program_and_rules(proj):
    _project(proj)
    c = store.connect(proj.db_path)
    m = snapshot.save(c, proj, name="改核心前", by="agent:x")                     # 不写存法：核心
    files = json.loads((proj.root / m["folder"] / "指纹.json").read_text(encoding="utf-8"))["files"]
    copied = sorted(r for r, v in files.items() if v[3])
    assert m["mode"] == "核心" and copied == [".claude/settings.json", "AGENTS.md", "backend/governance_paths.py", "backend/main.py",
                                             "模板.html", "治理/目标/S0 终极目标.md"]
    assert "资料/测试/大视频.mp4" in files and not files["资料/测试/大视频.mp4"][3]     # 指纹照记，不复制
    assert not any(r.startswith(".claude/worktrees") for r in files)                   # 别的会话的工作副本：不扫不存
    assert snapshot.offered("核心") == "全量" and snapshot.offered("只记指纹") == "全量"   # 10-03 起人和 agent 都存全量（内容只存改了的，作者「不分支的记录改动的地方就行」）
    c.close()


def test_only_ten_kept_plus_latest_settled(proj):
    _project(proj)
    c = store.connect(proj.db_path)
    first = snapshot.save(c, proj, name="最早", by="人")
    snapshot.settle(c, proj, first["code"], by="人")
    for i in range(2, 13):
        snapshot.save(c, proj, name=f"第{i}档", mode="只记指纹", by="人")
    codes = [m["code"] for m in snapshot.list_saves(proj)]
    assert len(codes) == 11 and "C1" in codes and "C2" not in codes and codes[0] == "C12"   # 最近 10 档 + 定性过的 C1
    assert [x["code"] for x in snapshot.dropped(proj)] == ["C2"]
    text = (proj.root / "存档" / "清单.md").read_text(encoding="utf-8")
    assert "## 已丢（只留最近 10 档）" in text and "C2 · 第2档" in text
    assert not (proj.root / "存档" / "C2 第2档").exists()
    assert "丢存档" in (proj.root / "笔记" / "日志" / f"{time.strftime('%Y-%m')}.md").read_text(encoding="utf-8")
    assert snapshot.save(c, proj, name="号不回收", mode="只记指纹", by="人")["code"] == "C13"
    c.close()


def test_old_full_saves_slim_down_to_core(proj):
    _project(proj)
    c = store.connect(proj.db_path)
    m = snapshot.save(c, proj, name="老的全量", mode="全量", by="人")
    folder = proj.root / m["folder"]
    assert snapshot.old_file(proj, m["code"], "资料/测试/大视频.mp4")[0].is_file()            # 内容在对象库（10-03 起）
    r = snapshot.slim(c, proj, m["code"])
    assert r["freed"] > 1000 and not (folder / "文件" / "资料").exists() and not (folder / "文件" / "666.docx").exists()
    d = snapshot.detail(proj, m["code"])
    assert d["mode"] == "核心" and d["slimmed"]["from"] == "全量" and "backend/main.py" in d["copied"]
    _w(proj.materials / "测试" / "新的.txt", "那之后放进来的测试文件")            # 瘦过的档回去时不动资料
    _w(proj.root / "backend" / "main.py", "print(2)")
    out = snapshot.restore(c, proj, m["code"], by="人", confirm=True)
    assert out["replaced"] == 1 and (proj.materials / "测试" / "新的.txt").is_file()
    assert (proj.root / "backend" / "main.py").read_text(encoding="utf-8") == "print(1)"
    c.close()


def test_claims_one_per_task_one_per_lane_and_core_lock(proj):
    c = store.connect(proj.db_path)
    claims.claim(c, "文献", "S2-1", "agent:a", ["文献"])
    with pytest.raises(store.Refused, match="agent:a 在做"):
        claims.claim(c, "文献", "S2-1", "agent:b", ["文献"])                     # 同一件
    with pytest.raises(store.Refused, match="这条道上 agent:a"):
        claims.claim(c, "文献", "S2-2", "agent:b", ["文献"])                     # 同一个模块
    claims.claim(c, "论文", "S2-1", "agent:b", ["论文"])                          # 别的模块：行
    claims.take_core(c, "agent:a")
    with pytest.raises(store.Refused):
        claims.take_core(c, "agent:b")                                           # 核心锁一次一个人
    assert claims.holds_core(c, "agent:a") and not claims.holds_core(c, "agent:b")
    c.execute("UPDATE claim SET beat = ? WHERE agent = 'agent:a'", (time.time() - claims.TTL - 5,))   # a 两个多小时没动静
    claims.claim(c, "文献", "S2-2", "agent:b", ["文献"])                          # 算放手了，b 能接
    assert {(r["agent"], r["goal"], r["sub"]) for r in claims.active(c)} == {("agent:b", "论文", "S2-1"), ("agent:b", "文献", "S2-2")}
    assert claims.release(c, "文献", "S2-2", "agent:a") is False and claims.release(c, "文献", "S2-2", "agent:b") is True
    c.close()


S0 = "# S0 终极目标\n\n**做一个试验。**\n\n| S1 | 目标 |\n|---|---|\n| S1-1 试验 | 试一下 |\n| S1-2 另一个 | 再试 |\n"
S1 = ("# S1-1 试验\n\n**把文献模块装修一下。**\n\n规划：定稿 · 2026-10-01 · 测试\n\n动到的模块：文献\n\n| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
      "| S2-1 | 文献列表 | 拖一篇进来左栏多一行 | 没做 |\n| S2-2 | 阅读页 | 翻到第 3 页 | 没做 |\n| S2-3 | 图解 |  | 没做 |\n")
S12 = "# S1-2 另一个\n\n**再试。**\n\n规划：定稿 · 2026-10-01 · 测试\n\n| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n| S2-1 | 写说明 |  | 没做 |\n"


def _blueprint(proj, monkeypatch, tmp_path):
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
    c = store.connect(proj.db_path)                                                 # 领活先报到（作者 09-30：「得给agent注册」）
    for n in ("a", "b"):
        agents.register(c, proj, n, "测试")
    c.close()


def test_agents_start_by_themselves_and_share_out_the_work(proj, monkeypatch, tmp_path):
    _blueprint(proj, monkeypatch, tmp_path)
    c = store.connect(proj.db_path)
    with store.tx(c):
        store.log(c, "agent:a", "看全貌")                                          # agent 连上过
    assert dispatch.auto_target(proj) == ["S1-1 S2-1", "S1-1 S2-2"]                # 没写怎么验的（S2-3、S1-2）不自己挑
    a = dispatch.next_task(c, proj, "agent:a")                                     # 没在跑的单：自己开一张、自己开工
    assert a["joined"] is False and a["wo"]["stored"] == "在跑" and a["wo"]["level"] == 2
    assert a["task"]["goal"] == "S1-1" and a["task"]["sub"] == "S2-1" and a["task"]["lanes"] == ["文献"]
    b = dispatch.next_task(c, proj, "agent:b")                                     # 同一条道（文献）有人：b 没活
    assert b["task"] is None and "agent:a" in b["reason"] and b["joined"] is True
    again = dispatch.next_task(c, proj, "agent:a")                                 # a 再问：接着做领着的
    assert again["task"]["sub"] == "S2-1" and "接着做" in again["reason"]
    import deliveries
    deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:a")
    assert claims.active(c) == []                                                  # 交了就放手
    b = dispatch.next_task(c, proj, "agent:b")
    assert b["task"]["sub"] == "S2-2"
    c.close()


def test_a_goal_without_modules_lets_several_agents_work_side_by_side(proj, monkeypatch, tmp_path):
    _blueprint(proj, monkeypatch, tmp_path)
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1.replace("动到的模块：文献\n\n", ""))   # 没写动到的模块：一件一条道
    c = store.connect(proj.db_path)
    a = dispatch.next_task(c, proj, "agent:a")
    b = dispatch.next_task(c, proj, "agent:b")
    assert (a["task"]["sub"], b["task"]["sub"]) == ("S2-1", "S2-2")
    assert a["task"]["lanes"] == ["S1-1 S2-1"] and b["task"]["lanes"] == ["S1-1 S2-2"]
    claims.take_core(c, "agent:a")                                                 # 改核心照样一次一个人
    with pytest.raises(store.Refused):
        claims.take_core(c, "agent:b")
    c.close()


def test_when_the_order_is_full_the_next_agent_helps_elsewhere(proj, monkeypatch, tmp_path):
    _blueprint(proj, monkeypatch, tmp_path)
    _w(proj.materials / "蓝图" / "S1-2 另一个.md", S12.replace("| 写说明 |  |", "| 写说明 | 说明里有这一段 |"))
    c = store.connect(proj.db_path)
    a = dispatch.next_task(c, proj, "agent:a")                                     # 单是 S1-1（文献一条道）
    b = dispatch.next_task(c, proj, "agent:b")                                     # 文献有人：b 先做 S1-2 的
    assert a["task"]["goal"] == "S1-1" and b["task"]["goal"] == "S1-2" and b["task"].get("outside")
    assert b["wo"]["code"] == a["wo"]["code"] and "不算在" in b["reason"]
    again = dispatch.next_task(c, proj, "agent:b")                                 # 再问：接着做领着的那件
    assert again["task"]["goal"] == "S1-2" and "接着做" in again["reason"]
    import deliveries
    j = deliveries.deliver(c, proj, goal="S1-2", sub="S2-1", did="写了", checks=[{"name": "验", "ok": True}], by="agent:b")
    assert not j.get("workorder")                                                  # 单外帮忙的不记在那张单名下
    c.close()


def test_items_waiting_on_the_human_are_not_picked(proj, monkeypatch, tmp_path):
    _blueprint(proj, monkeypatch, tmp_path)
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1.replace("| 翻到第 3 页 | 没做 |", "| 翻到第 3 页 | 等你：缺一篇样品 |"))
    assert dispatch.auto_target(proj) == ["S1-1 S2-1"]


def test_human_stop_holds_and_a_finished_goal_moves_on_to_the_next(proj, monkeypatch, tmp_path):
    _blueprint(proj, monkeypatch, tmp_path)
    _w(proj.materials / "蓝图" / "S1-2 另一个.md", S12.replace("| 写说明 |  |", "| 写说明 | 说明里有这一段 |"))
    import deliveries
    c = store.connect(proj.db_path)
    a = dispatch.next_task(c, proj, "agent:a")
    k1 = a["wo"]["code"]
    workorders.stop(c, proj, k1)                                                   # 人在网页上叫停
    with pytest.raises(store.Refused, match="人叫停了"):
        dispatch.next_task(c, proj, "agent:a")                                     # 不自己开新单
    got = dispatch.start_work(c, proj, "agent:a", resume=True)                     # 人在对话里让开工
    assert got["joined"] is False and workorders.paused(c) == ""
    for sub in ("S2-1", "S2-2"):
        deliveries.deliver(c, proj, goal="S1-1", sub=sub, did="做了", checks=[{"name": "验", "ok": True}], by="agent:a")
    nxt = dispatch.next_task(c, proj, "agent:a")                                   # S1-1 做完了：放下那张，开 S1-2 的
    assert nxt["done"] == [got["wo"]["code"]] and nxt["task"]["goal"] == "S1-2" and nxt["task"]["sub"] == "S2-1"
    assert workorders.get(proj, got["wo"]["code"])["stored"] == "备料" and workorders.running(proj)["code"] == nxt["wo"]["code"]
    deliveries.deliver(c, proj, goal="S1-2", sub="S2-1", did="写了", checks=[{"name": "验", "ok": True}], by="agent:a")
    end = dispatch.next_task(c, proj, "agent:a")
    assert end["task"] is None and "没有别的你能自己做的件" in end["reason"] and workorders.running(proj) is None
    c.close()


def test_git_books_each_delivery_under_the_agents_name(proj, tmp_path):
    if vcs._git() is None:
        pytest.skip("这台电脑没找到 git")
    import subprocess
    subprocess.run([vcs._git(), "init", "-q", str(proj.root)], check=True)
    _w(proj.root / "backend" / "main.py", "print(1)")
    _w(proj.root / "资料" / "测试" / "别人的.txt", "别人还没交的")
    h = vcs.commit(proj, ["backend"], agent="agent:codex", message="J1 · S1-1 S2-1 · 试")
    assert h
    log = vcs.log(proj)
    assert log[0]["who"] == "agent:codex" and log[0]["msg"].startswith("J1")
    code, out = vcs._run(proj, "status", "--porcelain")
    assert "资料/" in out or "资料" in out                                          # 别人的改动没被带进去
    assert vcs.commit(proj, ["backend"], agent="agent:codex", message="没变") == ""
    (proj.materials / "素材").mkdir(parents=True, exist_ok=True)              # 领活时连带的模块是空文件夹：git 不认识，不能挡住整次提交
    (proj.root / "backend" / "y.py").write_text("y = 1\n", encoding="utf-8")
    assert vcs.commit(proj, ["backend", "资料/素材"], agent="agent:codex", message="J2 · 带空文件夹")


def test_replace_waits_when_windows_says_access_denied(tmp_path, monkeypatch):
    import atomic
    import os
    src, dst = tmp_path / "a.md.tmp", tmp_path / "a.md"
    src.write_text("新的", encoding="utf-8")
    dst.write_text("旧的", encoding="utf-8")
    real, tries = os.replace, []

    def busy(a, b):                                                                # 前两次：别的程序正读着
        tries.append(1)
        if len(tries) < 3:
            raise PermissionError(5, "拒绝访问")
        real(a, b)
    monkeypatch.setattr(os, "replace", busy)
    monkeypatch.setattr(atomic.time, "sleep", lambda s: None)
    atomic.replace(src, dst)
    assert len(tries) == 3 and dst.read_text(encoding="utf-8") == "新的"


def test_two_agents_arriving_together_open_only_one_order(proj, monkeypatch, tmp_path):
    _blueprint(proj, monkeypatch, tmp_path)
    import threading
    got, errs = {}, []

    def come(name):
        c = store.connect(proj.db_path)
        try:
            got[name] = dispatch.next_task(c, proj, name)
        except Exception as e:                                                     # noqa: BLE001
            errs.append(repr(e))
        finally:
            c.close()
    ts = [threading.Thread(target=come, args=(n,)) for n in ("agent:a", "agent:b")]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert errs == [] and len(workorders.list_all(proj)) == 1                     # 同时进来：只开了一张
    assert {got["agent:a"]["wo"]["code"], got["agent:b"]["wo"]["code"]} == {workorders.list_all(proj)[0]["code"]}
    c = store.connect(proj.db_path)
    store._set_meta(c, dispatch.OPENING, "agent:x|0")                              # 开到一半断了的锁：60 秒后算放了
    assert dispatch._lock(c, "agent:b")
    c.close()


def test_an_item_waiting_on_another_is_handed_out_after_that_one_is_done(proj, monkeypatch, tmp_path):
    """等谁（S1-8 S2-35）：状态写「等 S2-1」的卡在那件后面——不派；那件做完了自动能领，不用人改状态。"""
    import board
    import deliveries
    _blueprint(proj, monkeypatch, tmp_path)
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1.replace("动到的模块：文献\n\n", "").replace("| 翻到第 3 页 | 没做 |", "| 翻到第 3 页 | 等 S2-1 |"))
    c = store.connect(proj.db_path)
    assert dispatch.auto_target(proj) == ["S1-1 S2-1"]                             # 等着的不自己挑
    a = dispatch.next_task(c, proj, "agent:a")
    b = dispatch.next_task(c, proj, "agent:b")
    assert a["task"]["sub"] == "S2-1" and b["task"] is None                       # 道不撞，但 S2-2 卡在 S2-1 后面
    col = {x["key"]: x for x in board.items(c, proj)}
    assert col["S1-1 S2-2"]["col"] == "等着" and col["S1-1 S2-2"]["wait_on"] == "S1-1 S2-1"
    assert col["S1-1 S2-1"]["blocking"] == ["S1-1 S2-2"]
    deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:a")
    assert {x["key"]: x for x in board.items(c, proj)}["S1-1 S2-2"]["col"] == "能做"   # 等的那件做完了：回到能做
    b = dispatch.next_task(c, proj, "agent:b")
    assert b["task"]["sub"] == "S2-2"
    d = board.detail(c, proj, "S1-1", "S2-2")
    assert d["wait_on"] == "S1-1 S2-1" and d["wait_done"] is True
    c.close()


def test_the_handed_out_item_carries_its_why(proj, monkeypatch, tmp_path):
    """活带着为什么（S1-8 S2-34）：交给 agent 的那件写着 S0 那句、目标一句话和定稿、怎么验、守的戒律。"""
    import board
    _blueprint(proj, monkeypatch, tmp_path)
    text = board.why_text(proj, "S1-1", "S2-1")
    assert "## 为什么做这件" in text and "总的（S0）：做一个试验" in text
    assert "目标 S1-1 试验：把文献模块装修一下（规划定稿了）" in text and "怎么验：拖一篇进来左栏多一行" in text
    assert "没写为了哪条需求" in text                                               # 这份测试蓝图没写「为了」：照实说，叫它先问人
    assert board.why_text(proj, "S1-1", "S2-9") == ""


def test_acceptance_gate_with_an_accepting_agent(proj, monkeypatch, tmp_path):
    """验收关（S1-8 S2-39 / S2-21 互查）：有验收的 agent 时交付停在等验收；它领到验收活、过了做完、打回回到原来干的手里；三次交给人。"""
    import board
    import blueprint
    import deliveries
    _blueprint(proj, monkeypatch, tmp_path)
    _w(proj.materials / "蓝图" / "S1-1 试验.md", S1.replace("动到的模块：文献\n\n", ""))
    c = store.connect(proj.db_path)
    agents.update(c, proj, "b", {"roles": ["验收"]}, by="人")
    assert dispatch.next_task(c, proj, "agent:b")["task"] is None                  # 只管验收：没有等验收的，也不领干活的件
    a = dispatch.next_task(c, proj, "agent:a")
    ok = [{"name": "拖一篇", "ok": True}]
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=ok, by="agent:a")
    assert j["state"] == "等验收" and blueprint.pyramid(proj)["goals"][0]["subs"][0]["text"].startswith("待验收（J1）")
    assert {x["key"]: x["col"] for x in board.items(c, proj)}["S1-1 S2-1"] == "等验收"
    r = dispatch.next_task(c, proj, "agent:b")
    assert r["review"]["code"] == "J1"
    with pytest.raises(store.Refused):
        deliveries.review(c, proj, "J1", True, "看到了", by="agent:a")              # a 没有验收岗位
    j = deliveries.review(c, proj, "J1", True, "左栏多了一行", by="agent:b", checks=ok)
    assert j["state"] == "验收通过" and "G2 b 验收过了" in deliveries.last_note(j)
    assert blueprint.pyramid(proj)["goals"][0]["subs"][0]["text"] == "做完（J1 验收 · G2）"
    # 打回：回到原来干活的 a 手里；别人两小时内领不到它
    agents.register(c, proj, "x", "测试")
    a = dispatch.next_task(c, proj, "agent:a")
    assert a["task"]["sub"] == "S2-2"
    for n in range(deliveries.MAX_ROUNDS):
        j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-2", did="阅读页", checks=ok, by="agent:a")
        assert j["state"] == "等验收"
        assert dispatch.next_task(c, proj, "agent:b")["review"]["code"] == j["code"]
        deliveries.review(c, proj, j["code"], False, "翻到第 3 页是空白", by="agent:b")
        x = dispatch.next_task(c, proj, "agent:x")
        assert x["task"] is None or x["task"]["sub"] != "S2-2"                     # 留给 a 改
        back = dispatch.next_task(c, proj, "agent:a")
        assert back["task"]["sub"] == "S2-2" and "验收没过" in back["reason"]
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-2", did="阅读页", checks=ok, by="agent:a")
    assert j["state"] == "待你验收"                                                   # 打回三次：交给人
    c.close()


def test_without_an_accepting_agent_it_still_passes_by_default(proj, monkeypatch, tmp_path):
    import deliveries
    _blueprint(proj, monkeypatch, tmp_path)
    c = store.connect(proj.db_path)
    agents.update(c, proj, "a", {"roles": ["干活", "验收"]}, by="人")                  # 只有自己会验收：不验自己的，照旧默认通过
    dispatch.next_task(c, proj, "agent:a")
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:a")
    assert j["state"] == "验收通过"
    c.close()


def test_review_gate_for_drafts_and_planning_jobs(proj, monkeypatch, tmp_path):
    """审核关（S1-8 S2-40）：规划的 agent 领到「哪块还缺什么」、起草；审核的 agent 先审草稿，准或打回；打回回到写的人改同一张；三轮交给人。"""
    import drafts
    _blueprint(proj, monkeypatch, tmp_path)
    _w(proj.materials / "蓝图" / "S1-2 另一个.md", S12.replace("规划：定稿 · 2026-10-01 · 测试\n\n", ""))   # S1-2 还没定稿、缺东西
    c = store.connect(proj.db_path)
    agents.register(c, proj, "c", "测试")
    assert drafts.stage(proj, drafts.propose(proj, "任务", "S1-2", {"做什么": "先试", "怎么验": "看"}, "试", by="agent:a")) == "没人审"
    agents.update(c, proj, "b", {"roles": ["审核"]}, by="人")
    agents.update(c, proj, "c", {"roles": ["规划"]}, by="人")
    pj = dispatch.next_task(c, proj, "agent:c")["plan"]
    assert pj["kind"] == "规划" and pj["row"]["code"] == "S1-2"
    d = drafts.propose(proj, "任务", "S1-2", {"做什么": "写说明", "为了": "", "怎么验": "看得到"}, "补一件", by="agent:c")
    assert drafts.stage(proj, d) == "等审"
    got = dispatch.next_task(c, proj, "agent:b")
    assert got["draft"]["code"] in ("草-1", "草-2")
    with pytest.raises(store.Refused):
        drafts.review(proj, d["code"], True, "好", by="agent:c")                       # 规划的不能审，也不审自己写的
    drafts.review(proj, d["code"], False, "怎么验写得太虚", by="agent:b")
    assert drafts.stage(proj, next(x for x in drafts.listing(proj) if x["code"] == d["code"])) == "打回"
    back = dispatch.next_task(c, proj, "agent:c")["plan"]
    assert back["kind"] == "改草稿" and back["draft"]["code"] == d["code"]
    drafts.revise(proj, d["code"], {"怎么验": "测试 test_note 过"}, "改了怎么验", by="agent:c")
    x = drafts.review(proj, d["code"], True, "这回机器查得了", by="agent:b")
    assert drafts.stage(proj, x) == "准" and x["fields"]["怎么验"] == "测试 test_note 过"
    took = drafts.decide(proj, d["code"], "行")
    assert took["state"] == drafts.TAKEN                                             # 人照样点「行」收进去
    import board
    got = board.detail(c, proj, "S1-2", took["new"])["drafted"]                      # 一件的详情：谁起草、审核怎么说
    assert got["by"] == "c" and got["review"].startswith("G2 b 准")
    e = drafts.propose(proj, "任务", "S1-2", {"做什么": "再试", "怎么验": "看"}, "试", by="agent:c")
    for n in range(drafts.MAX_ROUNDS):
        drafts.review(proj, e["code"], False, f"第 {n + 1} 轮不行", by="agent:b")
        if n < drafts.MAX_ROUNDS - 1:
            drafts.revise(proj, e["code"], {"怎么验": f"改 {n}"}, "改了", by="agent:c")
    assert drafts.stage(proj, next(y for y in drafts.listing(proj) if y["code"] == e["code"])) == "交给你"
    c.close()


def test_a_trainee_delivery_waits_for_people_when_nobody_accepts(proj, monkeypatch, tmp_path):
    import deliveries
    _blueprint(proj, monkeypatch, tmp_path)
    c = store.connect(proj.db_path)
    agents.update(c, proj, "a", {"level": "见习"}, by="人")
    dispatch.next_task(c, proj, "agent:a")
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:a")
    assert j["state"] == "待你验收" and "见习" in deliveries.last_note(j)               # 见习：检查全过也不默认通过
    agents.update(c, proj, "b", {"roles": ["验收"]}, by="人")
    dispatch.next_task(c, proj, "agent:a")
    j = deliveries.deliver(c, proj, goal="S1-1", sub="S2-2", did="阅读页", checks=[{"name": "翻页", "ok": True}], by="agent:a")
    assert j["state"] == "等验收"                                                    # 有验收的 agent：给它验
    c.close()
