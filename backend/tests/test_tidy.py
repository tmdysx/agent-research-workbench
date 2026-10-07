"""清理 → 查乱 · 归档（S1-8 S2-61；需-29；作者 10-03「清理模块不光得有垃圾桶的功能，还得有重铸的功能，因为ai编程很多信息是重复杂乱的……
相当于上下文压缩了」）：找出重复段落、能归档的旧记录、太长的正本、计划重号；归档整份搬、带索引、能拿回来；归档后各处照样查得到；人的笔记不碰。"""
import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

import agents
import archive
import files
import journal
import knobs
import snapshot
import store
import supervise
import tidy
import timeline
from main import create_app


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


RULE = "- 通-2 网页能直接做的（删模块、复活、删存档）先挪进回收站：空的直接做，有文件先警告、人确认；agent 照删除请求挪，不直接删"
GOAL = ("# S1-1 看得懂\n\n**一句话**\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"
        "| S2-1 | 第一件 | 项目 需-1 | 测试 | 做完（J1） |\n| S2-2 | 第二件 | 项目 需-1 | 测试 | 没做 |\n")


def _project(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    _w(proj.root / "AGENTS.md", "# 规矩\n\n" + RULE + "\n\n- 别的一条完全不一样的规矩，讲的是网页上的字要说人话，不写比方词和术语\n")
    _w(proj.root / "治理" / "戒律" / "1 通用戒律.md", "# 通用戒律\n\n" + RULE.replace("不直接删", "不要直接删") + "\n")
    _w(proj.root / "治理" / "目标" / "S1-1 看得懂.md", GOAL)
    _w(proj.root / "笔记" / "总览.md", "# 总览\n\n" + RULE + "\n")                        # 人的笔记：一样的话也不比
    _w(proj.root / "笔记" / "日志" / "2026-08.md", "# 日志 · 2026-08\n\n## 志-0001 · 2026-08-02 10:00 · 人 · 操作 · 总览\n八月的一条\n")
    _w(proj.root / "笔记" / "日志" / "2026-10.md", "# 日志 · 2026-10\n\n## 志-0002 · 2026-10-02 10:00 · 人 · 操作 · 总览\n十月的一条\n")
    for n, day, who in ((1, "2026-08-01", "甲"), (2, "2026-08-05", "甲"), (3, "2026-08-06", "乙")):
        _w(proj.root / "自动化" / "交接" / f"H{n} · {day} · {who}.md", f"# H{n}\n{who} 的交接\n")
    pd = proj.root / "治理" / "计划" / "S1-1 看得懂"
    _w(pd / "P1 · 2026-08-01 · 第一件.md", "目标：S1-1 S2-1 · 动到的模块：源代码\n\n# P1\n")          # 那件做完了
    _w(pd / "P2 · 2026-08-02 · 第二件.md", "目标：S1-1 S2-2\n\n# P2\n")                              # 没做完
    _w(pd / "P3 · 2026-08-03 · 第二件新版.md", "目标：S1-1 S2-2\n\n# P3\n施工计划：施-1 第 2 版\n")
    _w(pd / "P4 · 2026-08-02 · 第二件旧版.md", "目标：S1-1 S2-2\n\n# P4\n施工计划：施-1 第 1 版\n")   # 被新版取代
    _w(pd / "P4 · 2026-08-04 · 撞号了.md", "# P4\n")
    return c


def test_find_the_mess(proj):
    c = _project(proj)
    knobs.set_many(c, {"long_kb": 5})
    _w(proj.root / "使用说明.md", "# 使用说明\n\n" + "\n\n".join("".join(chr(0x4e00 + (i * 997 + j * 31) % 20000) for j in range(300)) for i in range(30)))   # 长、互不相像
    d = tidy.report(c, proj)
    pairs = [(x["a"]["file"], x["b"]["file"]) for x in d["dup"]]
    assert ("AGENTS.md", "治理/戒律/1 通用戒律.md") in pairs or ("治理/戒律/1 通用戒律.md", "AGENTS.md") in pairs
    assert not any("笔记/" in a or "笔记/" in b for a, b in pairs)                        # 人的笔记不比
    assert [x["file"] for x in d["long"]] == ["使用说明.md"]
    assert d["numbers"] == [{"goal": "S1-1 看得懂", "code": "P4", "files": [
        "治理/计划/S1-1 看得懂/P4 · 2026-08-02 · 第二件旧版.md", "治理/计划/S1-1 看得懂/P4 · 2026-08-04 · 撞号了.md"]}]
    kinds = {(x["kind"], Path(x["rel"]).name) for x in d["stale"]}
    assert ("日志", "2026-08.md") in kinds and ("日志", "2026-10.md") not in kinds         # 这个月的不收
    assert ("交接单", "H1 · 2026-08-01 · 甲.md") in kinds and ("交接单", "H2 · 2026-08-05 · 甲.md") not in kinds   # 每人留最新那份
    assert ("交接单", "H3 · 2026-08-06 · 乙.md") not in kinds
    assert ("计划", "P1 · 2026-08-01 · 第一件.md") in kinds and ("计划", "P4 · 2026-08-02 · 第二件旧版.md") in kinds
    assert ("计划", "P2 · 2026-08-02 · 第二件.md") not in kinds and ("计划", "P3 · 2026-08-03 · 第二件新版.md") not in kinds
    assert tidy.last(proj)["counts"]["stale"] == d["counts"]["stale"]                      # 存下来了
    assert archive.candidates(c, proj, days=365) == []                                     # 天数改大了：都还不够旧
    c.close()


def test_put_away_and_bring_back(proj):
    c = _project(proj)
    n_saves = len(snapshot.list_saves(proj))
    r = archive.put_away(c, proj, None, by="人")
    assert len(r["moved"]) == 4 and r["checkpoint"] and len(snapshot.list_saves(proj)) == n_saves + 1   # 收之前存了一档
    assert (proj.root / "归档" / "2026-08" / "笔记" / "日志" / "2026-08.md").is_file()
    assert not (proj.root / "笔记" / "日志" / "2026-08.md").exists()
    assert (proj.root / "归档" / "2026-08" / "自动化" / "交接" / "H1 · 2026-08-01 · 甲.md").read_text(encoding="utf-8") == "# H1\n甲 的交接\n"
    idx = archive.index(proj)
    assert {x["from"] for x in idx} == set(r["moved"]) and all(x["state"] == "归档" for x in idx)
    assert (proj.root / "笔记" / "总览.md").is_file()                                      # 人的笔记不碰
    # 归档后照样查得到
    assert [e["id"] for e in journal.read(proj)][:2] == ["志-0001", "志-0002"]          # 归档自己还记了一条
    assert any(m["month"] == "2026-08" and m["archived"] for m in journal.months(proj))
    hs = {h["code"]: h for h in agents.handovers(proj)}
    assert hs["H1"]["archived"] and not hs["H2"]["archived"]
    groups = {g.get("name"): g for g in files.plans(proj)}
    assert [Path(k["path"]).name for k in groups["已归档"]["children"]] and len(groups["已归档"]["children"]) == 2
    hits, _ = files.proj_search(proj, "八月的一条")
    assert any(h["path"].startswith("归档/") for h in hits)
    assert supervise._in_archive(proj, "自动化/交接/H1 · 2026-08-01 · 甲.md")               # 监管认得是归档，不当成删了
    assert archive.summary(proj)["count"] == 4
    # 拿回来
    _w(proj.root / "自动化" / "交接" / "H1 · 2026-08-01 · 甲.md", "原处又有了")
    b = archive.bring_back(c, proj, ["笔记/日志/2026-08.md", "自动化/交接/H1 · 2026-08-01 · 甲.md"], by="人")
    assert b["back"] == ["笔记/日志/2026-08.md"] and b["skipped"] == ["自动化/交接/H1 · 2026-08-01 · 甲.md"]
    assert (proj.root / "笔记" / "日志" / "2026-08.md").is_file() and archive.summary(proj)["count"] == 3
    c.close()


def test_pages_and_timer(proj):
    c = _project(proj)
    knobs.set_many(c, {"tidy_every_days": 7})
    assert tidy.timed(c, proj) is not None and tidy.timed(c, proj) is None                 # 查过了，七天内不再查
    assert any(e["kind"] == "查乱" for e in journal.read(proj))
    c.close()
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/tidy").json()["counts"]["stale"] == 4
        a = client.get("/api/archive").json()
        assert len(a["candidates"]) == 4 and a["summary"]["count"] == 0
        assert client.post("/api/archive", json={"confirm": False}).status_code == 409    # 要人确认
        r = client.post("/api/archive", json={"rels": ["自动化/交接/H1 · 2026-08-01 · 甲.md"], "confirm": True}).json()
        assert r["moved"] == ["自动化/交接/H1 · 2026-08-01 · 甲.md"]
        assert client.get("/api/handovers/H1").json()["text"] == "# H1\n甲 的交接\n"        # 归档里的也打得开
        assert client.post("/api/archive/back", json={"rels": ["自动化/交接/H1 · 2026-08-01 · 甲.md"]}).json()["back"]
        t = client.put("/api/settings/tidy", json={"patch": {"archive_days": 7, "long_kb": 40}}).json()
        assert t["tidy"]["archive_days"] == 7 and client.get("/api/settings/tidy").json()["knobs"]["long_kb"] == 40
