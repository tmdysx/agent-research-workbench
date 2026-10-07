"""存档是总入口（S1-8 S2-54；作者 10-03「改良存档模块，让存档和日志蓝图想法模块融合成一个有机整体」，选了「存档是总入口」）：
一档 = 一个时间节点，跟上一档之间冒出的想法、定下的需求、加的件、交付、日志、拍板、改了的文件现算；一件事出生、做完在哪一档。"""
import json

from fastapi.testclient import TestClient

import snapshot
import store
import timeline
from main import create_app


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _at(proj, code, at):                                            # 把一档的时间改成想要的（测试里造时间线）
    folder = snapshot._folder(proj, code)
    m = json.loads((folder / "档.json").read_text(encoding="utf-8"))
    m["at"] = at
    (folder / "档.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")


def _setup(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    need = "| | 要什么功能 | 要什么效果 | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n"
    _w(proj.root / "治理" / "需求" / "项目.md", "# 项目需求\n\n" + need + "| 需-1 | 第一条 | 看得见 | 作者 | S1-1 | 文献 |\n")
    goal = "# S1-1 看得懂\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n"
    _w(proj.root / "治理" / "目标" / "S1-1 看得懂.md", goal + "| S2-1 | 第一件 | 项目 需-1 | 测试 | 没做 |\n")
    idea = "# 想法\n\n| | 时间 | 想法 | 从哪来 | 关于 | 去向 |\n|---|---|---|---|---|---|\n"
    _w(proj.materials / "想法" / "想法.md", idea + "| 想-1 | 2026-10-03 10:00 | 早的想法 | 自己写 | 整个项目 |  |\n")
    snapshot.save(c, proj, name="一", mode="全量", by="人")
    _at(proj, "C1", "2026-10-03 10:30")
    _w(proj.root / "治理" / "需求" / "项目.md", "# 项目需求\n\n" + need + "| 需-1 | 第一条 | 看得见 | 作者 | S1-1 | 文献 |\n| 需-2 | 第二条 | 也看得见 | 作者 | S1-1 | 文献 |\n")
    _w(proj.root / "治理" / "目标" / "S1-1 看得懂.md", goal + "| S2-1 | 第一件 | 项目 需-1 | 测试 | 做完（J1） |\n| S2-2 | 第二件 | 项目 需-2 | 测试 | 没做 |\n")
    _w(proj.materials / "想法" / "想法.md", idea + "| 想-1 | 2026-10-03 10:00 | 早的想法 | 自己写 | 整个项目 |  |\n| 想-2 | 2026-10-03 11:00 | 后来的想法 | 自己写 | 整个项目 |  |\n")
    _w(proj.root / "自动化" / "交付" / "J1 S1-1 S2-1.md", "---\n编号: J1\n目标: S1-1\n小目标: S2-1\n做什么: 第一件\n状态: 做完\n时间: 2026-10-03 11:10\n谁: agent:甲\n存档: C1\n---\n# J1\n")
    _w(proj.root / "笔记" / "日志" / "2026-10.md", "# 2026-10 · 日志\n\n## 志-1 · 2026-10-03 11:20 · agent:甲 · 交付 · 蓝图\n\n交了第一件\n")
    with store.tx(c):
        c.execute("INSERT INTO note(kind, code, text, ref, created_by, created_at, updated_at) VALUES('决定', 'A-1', '定了', 'D-1', '人', "
                  "'2026-10-03T11:15:00', '2026-10-03T11:15:00')")
    snapshot.save(c, proj, name="二", mode="全量", by="人")
    _at(proj, "C2", "2026-10-03 12:00")
    return c


def test_a_checkpoint_knows_what_happened_since_the_last_one(proj):
    c = _setup(proj)
    ns = timeline.nodes(proj)
    assert [n["code"] for n in ns] == ["C1", "C2", timeline.NOW] and ns[1]["prev"] == "C1"
    n = timeline.node(c, proj, "C2")
    assert [x["code"] for x in n["ideas"]] == ["想-2"]                              # 早的那条在 C1 之前
    assert [x["key"] for x in n["needs"]] == ["项目 需-2"]                          # 拿两档的 治理/ 比出来
    assert [x["key"] for x in n["items"]] == ["S1-1 S2-2"]
    assert [x["code"] for x in n["deliveries"]] == ["J1"] and [x["id"] for x in n["logs"]] == ["志-1"]
    assert [(x["code"], x["ref"]) for x in n["decisions"]] == [("A-1", "D-1")]
    assert "治理/需求/项目.md" in n["files"]["changed"] and n["counts"]["needs"] == 1
    first = timeline.node(c, proj, "C1")
    assert first["prev"] == "" and [x["code"] for x in first["ideas"]] == ["想-1"]
    assert timeline.life(c, proj, goal="S1-1", sub="S2-1") == {"born": "C1", "done": "C2"}   # 出生在 C1，交付在 C1 之后、C2 之前
    assert timeline.life(c, proj, goal="S1-1", sub="S2-2") == {"born": "C2", "done": ""}
    assert timeline.life(c, proj, idea="想-2")["born"] == "C2" and timeline.where(proj, "2099-01-01 00:00") == timeline.NOW
    c.close()


def test_the_page_reads_the_timeline(proj):
    c = _setup(proj)
    c.close()
    with TestClient(create_app(proj)) as client:
        nodes = client.get("/api/timeline").json()["nodes"]
        assert [n["code"] for n in nodes] == ["C1", "C2", "现在"] and nodes[1]["counts"]["deliveries"] == 1
        assert client.get("/api/timeline/C2").json()["items"][0]["key"] == "S1-1 S2-2"
        assert client.get("/api/timeline/life", params={"goal": "S1-1", "sub": "S2-1"}).json()["done"] == "C2"
        assert client.get("/api/timeline/C9").status_code >= 400
