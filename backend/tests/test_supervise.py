"""监管：网页自己盯着项目（作者 10-01：「我要做的是能自动化监管的活的网页端，不能全让agent来读取文件」）；
发现了不停，拿不准的放问答（「继续推进不懂的放agent问答中」）。只用临时项目。"""
import time

import pytest

import claims
import file_actions
import files
import intake
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


def _agent_moves(proj, c, rel):
    return file_actions.move_to_inbox(c, proj, rel, by="agent:a", source=file_actions.MCP, reason="放错模块了")


@pytest.mark.parametrize("claimed", [False, True])
def test_moving_through_the_intake_is_not_a_deletion(proj, watched, claimed):
    """10-08 移到入口：入口里有同名的就改名（a（sha6）.md），库里记着原路径和是谁挪的——不算删东西、不算越界。"""
    c = watched["c"]
    _w(proj.materials / "_外部资料入口" / "a.md", "入口里先有一份同名的")
    intake.sync(c, proj)
    if claimed:
        claims.claim(c, "论文", "S2-1", "agent:a", ["论文"])          # 自动化在跑，可没人领着「文献」
    assert watched["scan"]() == []
    r = _agent_moves(proj, c, "资料/文献/a.md")
    assert r["to"] != "资料/_外部资料入口/a.md"
    assert watched["scan"]() == []
    intake.place(c, proj, r["item"]["id"], "文献", by="agent:a", reason="放回原处")
    assert watched["scan"]() == [] and (proj.materials / "文献" / "a.md").read_text(encoding="utf-8") == "一篇"


def test_agent_sorting_into_a_module_with_the_same_name_is_not_a_deletion(proj, watched):
    c = watched["c"]
    _w(proj.materials / "_外部资料入口" / "b.md", "入口里的另一份 b")
    store.get_state(c, proj)                                              # 模块、入口都对一次账
    claims.claim(c, "文献", "S2-1", "agent:a", ["文献"])               # 在跑，可没人领着「论文」
    assert watched["scan"]() == []
    it = intake.waiting(c)[0]
    r = intake.place(c, proj, it["id"], "论文", by="agent:a", reason="是稿子")
    assert r["item"]["sorted_to"] != "论文/b.md"
    assert watched["scan"]() == []


def test_moves_outside_the_intake_records_are_still_reported(proj, watched):
    import os
    c = watched["c"]
    (proj.materials / "_外部资料入口").mkdir(parents=True, exist_ok=True)
    os.replace(proj.materials / "文献" / "a.md", proj.materials / "_外部资料入口" / "a（123456）.md")
    assert watched["scan"]() == [2]                                       # 没经过移到入口：照样报
    r = _agent_moves(proj, c, "资料/论文/b.md")
    assert watched["scan"]() == []
    intake.place(c, proj, r["item"]["id"], "论文", by="agent:a", reason="放回原处")
    assert watched["scan"]() == []
    (proj.materials / "论文" / "b.md").unlink()                           # 放回原处以后再直接删：照样报
    assert watched["scan"]() == [2]


@pytest.mark.parametrize("sorted_away", [False, True])
@pytest.mark.parametrize("body", ["后来新写的一篇", "一篇"])
def test_a_new_file_at_a_moved_path_deleted_directly_is_reported(proj, watched, sorted_away, body):
    """开脱只管这一遍真挪的那一件：挪走以后同一个路径上新写的文件，直接删了照样报（等着分拣、分拣到别处都一样）。"""
    c = watched["c"]
    r = _agent_moves(proj, c, "资料/文献/a.md")
    assert watched["scan"]() == []
    if sorted_away:
        intake.place(c, proj, r["item"]["id"], "论文", by="agent:a", reason="其实是稿子")
        assert watched["scan"]() == []
    _later(proj.materials / "文献" / "a.md", body)                       # 内容一样、大小一样也不行：不是挪走的那一份
    assert watched["scan"]() == []
    (proj.materials / "文献" / "a.md").unlink()
    assert watched["scan"]() == [2]


def test_an_old_sorting_destination_rewritten_in_an_unclaimed_module_is_reported(proj, watched):
    """分拣进来那一遍不报；以后同一个路径上 agent 新写的，跟别的文件一样要领活。"""
    c = watched["c"]
    _w(proj.materials / "_外部资料入口" / "z.md", "入口里的 z")
    store.get_state(c, proj)
    claims.claim(c, "论文", "S2-1", "agent:a", ["论文"])
    claims.claim(c, "文献", "S2-2", "agent:b", ["文献"])                 # 放掉论文以后自动化还在跑
    assert watched["scan"]() == []
    it = next(x for x in intake.waiting(c) if x["name"] == "z.md")
    intake.place(c, proj, it["id"], "论文", by="agent:a", reason="是稿子")
    assert watched["scan"]() == []
    trash.move(c, proj, "资料/论文/z.md", by="agent:a", reason="不要了")
    assert watched["scan"]() == []
    claims.release(c, "论文", "S2-1", "agent:a")
    _later(proj.materials / "论文" / "z.md", "入口里的 y")                # 大小跟库里那一行一样，内容不一样
    assert watched["scan"]() == [5]


def test_files_sorted_from_a_cold_intake_are_not_reported(proj, watched):
    """入口那片没扫到过（放进来、分拣走都在这一遍里）：内容指纹对得上就不报。"""
    c = watched["c"]
    claims.claim(c, "文献", "S2-1", "agent:a", ["文献"])               # 在跑，可没人领着「论文」
    assert watched["scan"]() == []
    _w(proj.materials / "_外部资料入口" / "冷.md", "没扫到过的")
    store.sync_folders(c, proj)
    intake.sync(c, proj)
    it = next(x for x in intake.waiting(c) if x["name"] == "冷.md")
    intake.place(c, proj, it["id"], "论文", by="agent:a", reason="是稿子")
    assert watched["scan"]() == []


@pytest.mark.parametrize("dest,folder,name", [
    ("论文", "", "戒律.md"), ("论文", "", "需求.md"), ("论文", "技能", "SKILL.md"), ("论文", "解读", "x.md"),
])
def test_governance_shaped_destinations_are_never_exempt(proj, watched, dest, folder, name):
    """人点进治理形状的位置（agent 分拣不过去）：监管照常按规矩看，不因为经过入口就开脱。"""
    c = watched["c"]
    _w(proj.materials / "_外部资料入口" / name, "入口里的规矩")
    store.get_state(c, proj)
    claims.claim(c, "文献", "S2-1", "agent:a", ["文献"])
    assert watched["scan"]() == []
    it = next(x for x in intake.waiting(c) if x["name"] == name)
    intake.sort(c, proj, it["id"], dest, by="人", folder=folder)
    with store.tx(c):                                                     # 人点过去 20 秒了：不算人刚改
        c.execute("UPDATE event SET at = '2000-01-01T00:00:00' WHERE actor = '人'")
    assert watched["scan"]() == [5]


def test_scan_times_are_kept_per_area_and_survive_a_restart(proj, watched):
    """经入口挪的只认上回扫到那一片之后记的：每片记各自的时间，存进监管快照，重启后还在。"""
    import datetime as dt
    supervise.seen(proj, ["资料/文献"], 2_000_000_000)
    want = dt.datetime.fromtimestamp(2_000_000_000 - supervise._SLACK).isoformat(timespec="seconds")
    assert supervise._cutoff(proj, "资料/文献/a.md") == want
    assert supervise._cutoff(proj, "资料/论文/b.md") < want                    # 论文那片还是整个项目一起扫的时间
    supervise._save(proj, watched["snap"])
    supervise._SEEN.pop(str(proj.root))
    assert supervise.restore(proj) is not None and supervise._cutoff(proj, "资料/文献/a.md") == want


def _split_scan(proj, watched, first_area):
    """先只扫 first_area（入口页开着时入口那片是热区，先扫），再扫整个项目：跟 main.watch 分片扫一样。"""
    c, old = watched["c"], watched["snap"]
    whole = {}
    files.proj_signature(proj, whole)
    part = {k: v for k, v in old.items() if not k.startswith(first_area + "/")}
    part.update({k: v for k, v in whole.items() if k.startswith(first_area + "/")})
    got = supervise.on_scan(c, proj, old, part, areas=[first_area])
    got += supervise.on_scan(c, proj, part, whole)
    watched["snap"] = whole
    return [x["rule"] for x in got]


@pytest.mark.parametrize("rewrite", [False, True])
def test_sorting_seen_across_split_scans(proj, watched, rewrite):
    """入口那片先单独扫过、目标模块晚一遍才扫：合法分拣不报；分拣进来以后内容被改写（大小不变）的照样报 5。"""
    c = watched["c"]
    _w(proj.materials / "_外部资料入口" / "分.md", "入口里的分")
    store.get_state(c, proj)
    claims.claim(c, "文献", "S2-1", "agent:a", ["文献"])               # 在跑，可没人领着「论文」
    assert watched["scan"]() == []
    it = next(x for x in intake.waiting(c) if x["name"] == "分.md")
    intake.place(c, proj, it["id"], "论文", by="agent:a", reason="是稿子")
    if rewrite:
        _later(proj.materials / "论文" / "分.md", "入口里的改")       # 字节数一样，内容不一样
    got = _split_scan(proj, watched, "资料/_外部资料入口")
    assert (5 in got) if rewrite else got == []                        # 改写过的：目标对不上，入口那份挪走也认不了，可能连 2 一起报


def test_putting_back_across_split_scans_is_not_reported(proj, watched):
    """agent 挪回入口、再放回原处，入口那片先单独扫：不当成越界改写。"""
    c = watched["c"]
    claims.claim(c, "论文", "S2-1", "agent:a", ["论文"])               # 在跑，可没人领着「文献」
    assert watched["scan"]() == []
    r = _agent_moves(proj, c, "资料/文献/a.md")
    assert watched["scan"]() == []
    intake.place(c, proj, r["item"]["id"], "文献", by="agent:a", reason="放回原处")
    assert _split_scan(proj, watched, "资料/_外部资料入口") == []
    assert (proj.materials / "文献" / "a.md").read_text(encoding="utf-8") == "一篇"


def test_a_same_size_rewrite_before_the_next_scan_is_reported(proj, watched):
    """分拣进无人认领的模块后、下一遍扫描前就被改写（大小不变）：不是分拣进来的那一份，照样报 5。"""
    c = watched["c"]
    _w(proj.materials / "_外部资料入口" / "y.md", "入口里的 y")
    store.get_state(c, proj)
    claims.claim(c, "文献", "S2-1", "agent:a", ["文献"])
    assert watched["scan"]() == []
    it = next(x for x in intake.waiting(c) if x["name"] == "y.md")
    intake.place(c, proj, it["id"], "论文", by="agent:a", reason="是稿子")
    _later(proj.materials / "论文" / "y.md", "入口里的 z")
    assert watched["scan"]() == [5]


def test_a_new_intake_file_with_a_sorted_name_deleted_directly_is_reported(proj, watched):
    """分拣走（目标同名改了指纹名）以后，入口里又来了个同名的新文件、被直接删掉：照样报 2。"""
    c = watched["c"]
    _w(proj.materials / "_外部资料入口" / "b.md", "入口里的另一份 b")
    store.get_state(c, proj)
    assert watched["scan"]() == []
    it = next(x for x in intake.waiting(c) if x["name"] == "b.md")
    r = intake.place(c, proj, it["id"], "论文", by="agent:a", reason="是稿子")
    assert r["item"]["sorted_to"] != "论文/b.md"
    assert watched["scan"]() == []
    _w(proj.materials / "_外部资料入口" / "b.md", "又来一份新的 b")
    assert watched["scan"]() == []
    (proj.materials / "_外部资料入口" / "b.md").unlink()
    assert watched["scan"]() == [2]
