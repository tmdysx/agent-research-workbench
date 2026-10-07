"""监管：网页自己盯着项目（作者 10-01：「我要做的是能自动化监管的活的网页端，不能全让agent来读取文件」）；
发现了不停，拿不准的放问答（「继续推进不懂的放agent问答中」）。只用临时项目。"""
import time

import pytest

import claims
import files
import store
import supervise
import trash
import workorders


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def watched(proj):
    """一个有核心、笔记、方向文件、模块的小项目，已经扫过一遍（监管记住了现在的样子）。"""
    _w(proj.root / "backend" / "x.py", "print(1)")
    _w(proj.root / "笔记" / "总览.md", "# 总览 · 笔记\n\n## 总-001\n第一条\n")
    _w(proj.root / "治理" / "戒律" / "2 项目戒律.md", "| 项-1 | 只做电脑 |\n")
    _w(proj.root / "治理" / "目标" / "S1-1 试验.md", "# S1-1 试验\n\n**做一个试验。**\n\n| | 做什么 | 状态 |\n|---|---|---|\n| S2-1 | 列表 | 没做 |\n")
    _w(proj.root / "资料" / "文献" / "a.md", "一篇")
    _w(proj.root / "资料" / "论文" / "b.md", "一稿")
    c = store.connect(proj.db_path)
    snap = {}
    files.proj_signature(proj, snap)
    supervise._TEXTS.clear()
    supervise.on_scan(c, proj, None, snap)
    state = {"c": c, "snap": snap}

    def scan():                                       # 再扫一遍：返回这一遍新记下的规矩号
        new = {}
        files.proj_signature(proj, new)
        got = supervise.on_scan(c, proj, state["snap"], new)
        state["snap"] = new
        return [x["rule"] for x in got]
    state["scan"] = scan
    yield state
    c.close()


def _later(path, text):                               # 写完把时间往后拨一点，免得同一纳秒里扫不出变化
    _w(path, text)
    t = time.time() + 2
    import os
    os.utime(path, (t, t))


def test_core_changed_without_the_lock(proj, watched):
    c = watched["c"]
    _later(proj.root / "backend" / "x.py", "print(2)")
    assert watched["scan"]() == [1]
    _later(proj.root / "backend" / "y.py", "print(3)")
    assert watched["scan"]() == []                                        # 同一件事只记一条，涉及的文件加上去
    f = supervise.listing(c)["open"][0]
    assert f["lamp"] == "红" and f["paths"] == "backend/x.py、backend/y.py"
    assert "改核心先拿锁" in supervise.reminder_text(c, "agent:someone")     # 看不出是谁：领活的 agent 都提醒一声
    supervise.ack(c, f["id"])
    claims.take_core(c, "agent:a")
    _later(proj.root / "backend" / "x.py", "print(4)")
    assert watched["scan"]() == []                                        # 拿着锁改：不算


def test_deleting_without_the_recycle_bin_goes_to_the_questions(proj, watched):
    c = watched["c"]
    (proj.root / "资料" / "文献" / "a.md").unlink()
    assert watched["scan"]() == [2]
    q = store.list_pending(c)
    assert len(q) == 1 and "资料/文献/a.md" in q[0]["text"] and q[0]["created_by"] == "监管"
    f = supervise.listing(c)["open"][0]
    assert f["qa"] == q[0]["code"]
    store.answer(c, q[0]["code"], "是我让删的")                         # 人在问答里拍板：这条就关了
    supervise.check_state(c, proj)
    assert supervise.listing(c)["open"] == [] and supervise.listing(c)["recent"][0]["state"] == "问答里定了"
    trash.move(c, proj, "资料/论文/b.md", by="agent:a", reason="不要了")
    assert watched["scan"]() == []                                        # 挪进回收站的：不算


def test_notes_only_grow(proj, watched):
    c = watched["c"]
    _later(proj.root / "笔记" / "总览.md", "# 总览 · 笔记\n\n## 总-001\n第一条\n\n## 总-002\n第二条\n")
    assert watched["scan"]() == []                                        # 末尾加一条：可以
    _later(proj.root / "笔记" / "总览.md", "# 总览 · 笔记\n\n## 总-001\n改掉了\n")
    assert watched["scan"]() == [3] and len(store.list_pending(c)) == 1


def test_direction_files_only_change_by_the_human(proj, watched):
    c = watched["c"]
    goal = proj.root / "治理" / "目标" / "S1-1 试验.md"
    _later(goal, goal.read_text(encoding="utf-8").replace("| 没做 |", "| 做完（J1 默认通过） |"))
    assert watched["scan"]() == []                                        # S2 那几行（交付改状态）：不算
    _later(proj.root / "治理" / "戒律" / "2 项目戒律.md", "| 项-1 | 只做手机 |\n")
    assert watched["scan"]() == [4]
    with store.tx(c):
        store.log(c, "人", "改了治理正文", "治理/目标/S1-1 试验.md")          # 网页上人刚改的：不算
    _later(goal, goal.read_text(encoding="utf-8").replace("做一个试验", "做两个试验"))
    assert watched["scan"]() == []


def test_changing_a_module_nobody_claimed_while_automation_runs(proj, watched):
    c = watched["c"]
    _later(proj.root / "资料" / "文献" / "a.md", "改了一点")
    assert watched["scan"]() == []                                        # 自动化没在跑：多半是你自己改的
    claims.claim(c, "论文", "S2-1", "agent:a", ["论文"])
    _later(proj.root / "资料" / "文献" / "a.md", "又改了")
    assert watched["scan"]() == [5]
    _later(proj.root / "资料" / "论文" / "b.md", "领着论文的人改论文")
    assert watched["scan"]() == []


def test_stalled_work_and_unregistered_agents_come_and_go(proj, watched):
    c = watched["c"]
    claims.claim(c, "论文", "S2-1", "agent:a", ["论文"])
    c.execute("UPDATE claim SET beat = ? WHERE agent = 'agent:a'", (time.time() - 40 * 60,))
    got = supervise.check_state(c, proj, [{"state": "在跑", "registered": False, "agent": "cursor"}])
    assert sorted(x["rule"] for x in got) == [6, 7]
    claims.beat(c, "agent:a")
    supervise.check_state(c, proj, [])
    assert supervise.listing(c)["open"] == []                            # 动了、走了：自动「已经好了」
    assert {x["state"] for x in supervise.listing(c)["recent"]} == {"已经好了"}
    assert workorders.running(proj) is None


def test_a_restart_does_not_hide_the_change_that_caused_it(proj, watched):
    """改了 backend/ 的程序，后台会整个重启：新的那个要跟上回存的样子比，不然那次改动就看不到了（10-01 试的时候踩到）。"""
    c = watched["c"]
    supervise._TEXTS.clear()                                              # 当作后台重启了：内存里什么都没有
    _later(proj.root / "backend" / "x.py", "print('重启前改的')")
    _later(proj.root / "笔记" / "总览.md", "# 总览 · 笔记\n\n## 总-001\n被改了\n")
    old = supervise.restore(proj)
    assert old is not None and "backend/x.py" in old
    new = {}
    files.proj_signature(proj, new)
    assert sorted(x["rule"] for x in supervise.on_scan(c, proj, old, new)) == [1, 3]


def test_temporary_files_are_not_deletions(proj, watched):
    """S1-8 S2-27：程序换文件时的临时文件（x.tmp、x.tmp.<号>、下载的 .part）没了不算删东西；以前报错的关掉、问人的收回。"""
    c = watched["c"]
    for n in ("a.md.tmp", "repos.py.tmp.22116.419cbcab2c9f", "paperclip-main.zip.part"):
        _later(proj.root / "资料" / "文献" / n, "临时")
    assert watched["scan"]() == []
    for n in ("a.md.tmp", "repos.py.tmp.22116.419cbcab2c9f", "paperclip-main.zip.part"):
        (proj.root / "资料" / "文献" / n).unlink()
    assert watched["scan"]() == [] and store.list_pending(c) == []
    supervise.record(c, proj, 2, "backend/old.py.tmp.1.2", "「backend/old.py.tmp.1.2」没了，回收站里也没有", ask="是你让删的吗？")   # 改之前记下的那种误报
    assert len(store.list_pending(c)) == 1
    supervise.check_state(c, proj)
    assert supervise.listing(c)["open"] == [] and store.list_pending(c) == []                                   # 关了、问题收回了
    (proj.root / "资料" / "文献" / "a.md").unlink()
    assert watched["scan"]() == [2]                                                                              # 真删的照样报
