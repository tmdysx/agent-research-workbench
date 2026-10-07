"""store / blueprint：库能自己建回来、蓝图（资料/蓝图/ 的金字塔）读得对、两个写入口写进同一张表。"""
import pytest

import blueprint
import store

def test_fresh_db_builds_itself_and_records_version(proj):
    c = store.connect(proj.db_path)
    rows = c.execute("SELECT version FROM schema_version").fetchall()
    assert [r[0] for r in rows] == [1, 2, 3, 4]
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"module", "note", "event", "meta", "schema_version", "intake"} <= tables
    assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    c.close()


def test_delete_db_then_rerun_rebuilds(proj):
    c = store.connect(proj.db_path)
    store.get_state(c, proj)
    c.close()
    for suffix in ("", "-wal", "-shm"):
        p = proj.db_path.with_name(proj.db_path.name + suffix)
        if p.exists():
            p.unlink()
    c = store.connect(proj.db_path)
    s = store.get_state(c, proj)
    assert s["blueprint"] == [] and s["s0"] is None
    assert c.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 4
    c.close()


def test_migrate_twice_is_harmless(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    store.migrate(c)
    assert c.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 4
    c.close()


def _goal(proj, name, rows):
    d = proj.materials / "蓝图"
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"# {name}", "", f"**{name}的一句话。**", "", "怎么算做到：看得见。", "",
             "| | 做什么 | 状态 |", "|---|---|---|"] + [f"| {c} | {w} | {s} |" for c, w, s in rows]
    (d / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_blueprint_is_the_pyramid_and_s1_status_comes_from_its_s2(proj):
    d = proj.materials / "蓝图"
    d.mkdir(parents=True)
    s0 = ["# S0", "", "**做一个好工具。** 后面的话", "", "| | 一句话 | 状态 |", "|---|---|---|",
          "| S1-1 甲 | x | 手写的不算 |", "| S1-2 乙 | x | x |", "| S1-10 丙 | x | x |", "| S1-3 丁 | x | x |"]
    (d / "S0 终极目标.md").write_text("\n".join(s0) + "\n", encoding="utf-8")
    _goal(proj, "S1-1 甲", [("S2-1", "a", "做完"), ("S2-2", "b", "做完（备注）")])
    _goal(proj, "S1-2 乙", [("S2-1", "a", "做完"), ("S2-2", "b", "没做，以后")])
    _goal(proj, "S1-10 丙", [("S2-1", "a", "以后"), ("S2-2", "b", "在做")])
    _goal(proj, "S1-4 戊", [])
    c = store.connect(proj.db_path)
    s = store.get_state(c, proj)
    assert s["s0"]["one_line"] == "做一个好工具" and s["project"]["one_line"] == "做一个好工具"
    g = {x["code"]: x for x in s["blueprint"]}
    assert list(g) == ["S1-1", "S1-2", "S1-4", "S1-10"]                    # 按编号排，S1-10 在最后
    assert [g[k]["status"] for k in g] == ["ok", "warn", "bad", "todo"]    # 从 S2 现算，S0 里手写的不算
    assert (g["S1-2"]["done"], g["S1-2"]["total"]) == (1, 2) and g["S1-1"]["one_line"] == "S1-1 甲的一句话"
    assert s["counts"] == {"ok": 3, "warn": 0, "todo": 1, "bad": 2}          # 数的是 S2
    assert "S0 里列了 S1-3，资料/蓝图/ 里找不到它那一份" in s["problems"]
    assert "S1-4 有文件，S0 的表里没列它" in s["problems"]
    assert s["modules"] and all(m["name"] != "S1-1" for m in s["modules"])  # 目标不是模块，不上第二栏
    c.close()


def test_blueprint_file_locked_is_reported_not_fatal(proj, monkeypatch):
    """Windows 上编辑器存盘那一瞬间文件可能被锁：读不了那一份记进 problems，别的照常。"""
    from pathlib import Path
    _goal(proj, "S1-1 甲", [("S2-1", "a", "做完")])
    _goal(proj, "S1-2 乙", [("S2-1", "a", "做完")])
    real = Path.read_text

    def locked(self, *a, **k):
        if self.name == "S1-2 乙.md":
            raise PermissionError("被别的程序占着")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", locked)
    c = store.connect(proj.db_path)
    s = store.get_state(c, proj)
    assert [x["code"] for x in s["blueprint"]] == ["S1-1"]
    assert any("暂时读不了" in x for x in s["problems"])
    c.close()


def test_blueprint_search_finds_goals_and_s2(proj):
    _goal(proj, "S1-1 甲", [("S2-1", "关键路径", "没做")])
    assert [blueprint.status_of(x) for x in ("做完（备注）", "待你验收", "在做", "以后", "没做")] == ["ok", "warn", "todo", "bad", "bad"]
    hits = blueprint.search(proj, "关键")
    assert hits == [{"kind": "蓝图", "code": "S1-1 S2-1", "text": "关键路径（没做）"}]


def test_add_module_creates_its_folder(proj):
    import project as P
    P.ensure_skeleton(proj)
    c = store.connect(proj.db_path)
    m = store.add_module(c, proj, "  检索页 ", by="人", source="human", en="Search")
    assert (m["name"], m["created_by"], m["en"]) == ("检索页", "人", "Search")
    assert (proj.materials / "检索页").is_dir()
    with pytest.raises(store.Duplicate):
        store.add_module(c, proj, "检索页", by="agent:x", source="agent")
    for bad in ("a/b", "CON", "_系统", "", "x" * 41, 'a"b'):
        with pytest.raises(store.Refused):
            store.add_module(c, proj, bad, by="人", source="human")
    names = [m["name"] for m in store.get_state(c, proj)["modules"]]
    assert names == ["想法", "蓝图", "戒律", "源代码", "测试", "文献", "论文", "实验", "汇报", "素材", "检索页"]   # 固定的七个最前，再是起步模块
    c.close()


def test_fixed_modules_always_come_back_starters_do_not(proj):
    """七个固定模块：文件夹没了下次启动补回来、不给删；起步模块只在新项目第一次建。"""
    import shutil
    import project as P
    assert P.ensure_skeleton(proj) == ["想法", "蓝图", "戒律", "源代码", "测试", "文献", "论文", "实验", "汇报", "素材"]   # 新项目：全建
    shutil.rmtree(proj.materials / "戒律")
    shutil.rmtree(proj.materials / "实验")
    assert P.ensure_skeleton(proj) == ["戒律"]                                        # 只补固定的
    c = store.connect(proj.db_path)
    ms = {m["name"]: m for m in store.get_state(c, proj)["modules"]}
    assert "实验" not in ms and all(ms[n]["fixed"] for n in ("戒律", "源代码", "测试", "文献", "论文"))
    c.close()


def test_folders_are_the_modules(proj):
    """你在资源管理器里建/删文件夹，网页跟着变；删掉的只标记，事件里留底。"""
    import shutil
    c = store.connect(proj.db_path)
    (proj.materials / "手建的").mkdir(parents=True)
    m = next(m for m in store.get_state(c, proj)["modules"] if m["name"] == "手建的")
    assert m["created_by"] == "文件夹里发现的"
    shutil.rmtree(proj.materials / "手建的")
    assert "手建的" not in [m["name"] for m in store.get_state(c, proj)["modules"]]
    assert store.recent_events(c, 1)[0]["action"] == "文件夹不见了"
    (proj.materials / "手建的").mkdir()
    assert "手建的" in [m["name"] for m in store.get_state(c, proj)["modules"]]
    assert store.recent_events(c, 1)[0]["action"] == "文件夹回来了"
    c.close()


def test_two_entries_write_the_same_table(proj):
    """网页进程和 MCP 进程各一个连接：一边写，另一边看得见，版本号涨了。"""
    web = store.connect(proj.db_path)
    agent = store.connect(proj.db_path)
    store.get_state(web, proj)
    v0 = store.version(web)
    store.add_module(agent, proj, "技能地图", by="agent:claude-code", source="agent")
    assert store.version(web) > v0
    m = next(m for m in store.get_state(web, proj)["modules"] if m["name"] == "技能地图")
    assert m["created_by"] == "agent:claude-code" and m["source"] == "agent"
    web.close()
    agent.close()


def test_ask_then_answer_becomes_decision(proj):
    c = store.connect(proj.db_path)
    q = store.ask_human(c, "数据库用 SQLite 还是 Postgres？", by="agent:codex", context="本地工具")
    assert q["code"] == "D-01"
    assert store.ask_human(c, "数据库用 SQLite 还是 Postgres？", by="agent:codex")["code"] == "D-01"   # 同一问题不重复
    d = store.answer(c, "D-01", "SQLite，先本地")
    assert (d["code"], d["ref"], d["detail"]) == ("A-01", "D-01", "数据库用 SQLite 还是 Postgres？")
    assert store.list_pending(c) == []
    with pytest.raises(store.Refused):
        store.answer(c, "D-01", "再拍一次")
    c.close()


def test_draft_and_export(proj):
    c = store.connect(proj.db_path)
    v0 = store.version(c)
    store.save_draft(c, "第一版")
    store.save_draft(c, "第二版")
    assert store.get_draft(c)["text"] == "第二版"
    assert store.version(c) == v0                        # 存草稿不记事件
    store.export_instruction(c, "# 给 agent 的指令\n做这个")
    assert store.list_instructions(c)[0]["text"].startswith("# 给 agent 的指令")
    assert store.version(c) == v0 + 1
    c.close()


def test_module_stats_count_own_files_and_links(proj):
    (proj.materials / "文献" / "子目录").mkdir(parents=True)
    (proj.materials / "文献" / "a.pdf").write_bytes(b"x" * 10)
    (proj.materials / "文献" / "子目录" / "b.pdf").write_bytes(b"y" * 5)
    (proj.materials / "源代码").mkdir()
    (proj.root / "根.json").write_text("{}", encoding="utf-8")
    (proj.materials / "源代码" / ".链接.txt").write_text(
        "# 必须待在原位的\n根.json\n../外面\n不存在.py\n", encoding="utf-8")
    c = store.connect(proj.db_path)
    s = store.get_state(c, proj)
    by = {m["name"]: m for m in s["modules"]}
    assert (by["文献"]["files"], by["文献"]["bytes"]) == (2, 15)
    assert by["源代码"]["files"] == 1 and by["源代码"]["links"] == ["根.json"]
    assert any("外面去了" in x for x in s["problems"]) and any("找不到" in x for x in s["problems"])
    assert s["materials"]["total"] == 3
    c.close()


def test_draft_is_kept_before_a_big_loss(proj):
    """随堂笔记的草稿只有一份、每次覆盖：清空、整段删掉之前旧的先留底，能找回来；一个字一个字删的不留；刚记下的不留。
    作者 09-29：「但是系统稳定之后不能有这种bug」。"""
    from fastapi.testclient import TestClient
    from main import create_app
    with TestClient(create_app(proj)) as client:
        put = lambda text, recorded=False: client.put("/api/note", json={"text": text, "recorded": recorded})
        put("我在想第三章的结构，先写实验再写方法")
        put("我在想第三章的结构，先写实验再写方")                                   # 删一个字：不留
        assert client.get("/api/note/backups").json()["items"] == []
        put("")                                                                     # 一下子清空：留底
        items = client.get("/api/note/backups").json()["items"]
        assert [x["text"] for x in items] == ["我在想第三章的结构，先写实验再写方"] and items[0]["at"]
        assert client.get("/api/state").json()["note"]["text"] == ""
        put("新写的一段，已经很长了很长了很长了")
        put("", recorded=True)                                                      # 「记下」清空的：已经在笔记本里了，不留
        assert len(client.get("/api/note/backups").json()["items"]) == 1
        put("另一段比较长的草稿，写了好几句话，还没记下")
        put("另一段")                                                               # 整段删掉一大截：留底
        assert client.get("/api/note/backups").json()["items"][0]["text"] == "另一段比较长的草稿，写了好几句话，还没记下"
