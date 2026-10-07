"""世界树（S1-8 S2-55、S2-56；作者 10-03「全量存档天然就可以当一个独立的进程用来探索……验收了世界树存档分支的果实demo之后，
如果合适就合并进主干……识别改动的代码之后合并进主项目」）：长枝 = 那一档整份取出来放在项目旁边、自己的库；结果实；
合回主干时只枝改的换上、两边改的三方合并、合不开的不覆盖、枝的记录收档、合前合后各存一档；砍掉进 .回收。"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import claims
import snapshot
import store
import worldtree
from main import create_app
from project import Project


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _setup(proj):
    _w(proj.root / "backend" / "a.py", "x = 1\n")
    _w(proj.root / "模板.html", "<p>一</p>\n<p>二</p>\n<p>三</p>\n<p>四</p>\n<p>五</p>\n")
    _w(proj.root / "AGENTS.md", "规矩\n")
    _w(proj.root / "使用说明.md", "第一行\n")
    _w(proj.root / "旧的.txt", "要删的\n")
    _w(proj.materials / "论文" / "第1章.md", "第一版\n")
    c = store.connect(proj.db_path)
    store.migrate(c)
    return c


def test_a_branch_is_a_whole_copy_beside_the_project(proj):
    c = _setup(proj)
    b = worldtree.grow(c, proj, name="试新界面", by="agent:G1", why="换个首页")
    root = Path(b["path"])
    assert root.parent == worldtree.forest(proj) and root.name == "枝-1 试新界面" and b["base"] == "C1"
    assert (root / "模板.html").read_text(encoding="utf-8").startswith("<p>一</p>")
    assert (root / "资料" / "论文" / "第1章.md").is_file() and (root / "索引" / "state.db").is_file()
    assert json.loads((root / "枝.json").read_text(encoding="utf-8"))["state"] == "长着"
    assert worldtree.is_branch(Project(root))["code"] == "枝-1" and worldtree.is_branch(proj) is None
    assert snapshot.pins(proj) == {"枝-1": "C1"}
    bc = store.connect(root / "索引" / "state.db")
    assert store._meta(bc, "auto_launch") == "0"                             # 枝自己不自动开窗口
    bc.close()
    for i in range(12):                                                       # 清旧档时，长出枝的那一档留着
        snapshot.save(c, proj, name=f"后来{i}", mode="全量", by="人")
    assert "C1" in [m["code"] for m in snapshot.list_saves(proj)]
    assert [x["code"] for x in worldtree.list_branches(proj)] == ["枝-1"]
    c.close()


def test_fruit_then_merge_takes_only_what_the_branch_changed(proj):
    c = _setup(proj)
    b = worldtree.grow(c, proj, name="改网页", by="agent:G1")
    root = Path(b["path"])
    bp = Project(root)
    _w(root / "backend" / "a.py", "x = 2\n")                                  # 只枝改：直接换上
    _w(root / "模板.html", "<p>一 枝改的</p>\n<p>二</p>\n<p>三</p>\n<p>四</p>\n<p>五</p>\n")   # 两边改不同行：三方合并
    _w(root / "使用说明.md", "枝写的\n")                                        # 两边改同一行：合不开
    (root / "旧的.txt").unlink()                                               # 枝删了
    _w(root / "自动化" / "交付" / "J1 S1-1 S2-1.md", "枝上的交付\n")             # 枝的记录：收档，不并进主干编号
    _w(proj.root / "模板.html", "<p>一</p>\n<p>二</p>\n<p>三</p>\n<p>四</p>\n<p>五 主干改的</p>\n")
    _w(proj.root / "使用说明.md", "主干写的\n")
    _w(proj.root / "AGENTS.md", "规矩（主干改）\n")                             # 主干自己改的：不动
    with pytest.raises(store.Refused):
        worldtree.bear_fruit(c, proj, demo="看首页", checks=[], by="agent:G1")   # 主干上结不了果实
    bc = store.connect(bp.db_path)
    f = worldtree.bear_fruit(bc, bp, demo="开枝的网页看首页第一行", checks=[{"name": "测试", "ok": True}], by="agent:G5")
    bc.close()
    assert f["state"] == "结果了" and worldtree.get(proj, "枝-1")["demo"].startswith("开枝的网页")
    ch = worldtree.changes(proj, "枝-1")
    assert ch["take"] == ["backend/a.py"] and ch["delete"] == ["旧的.txt"]
    assert sorted(ch["both"]) == ["使用说明.md", "模板.html"] and ch["records"] == ["自动化/交付/J1 S1-1 S2-1.md"]
    assert ch["trunk_only"] >= 1
    n_before = len(snapshot.list_saves(proj))
    r = worldtree.merge(c, proj, "枝-1", by="agent:G1")
    assert (proj.root / "backend" / "a.py").read_text(encoding="utf-8") == "x = 2\n"
    page = (proj.root / "模板.html").read_text(encoding="utf-8")
    assert "一 枝改的" in page and "五 主干改的" in page and r["merged"] == ["模板.html"]
    assert (proj.root / "使用说明.md").read_text(encoding="utf-8") == "主干写的\n"     # 合不开的不覆盖
    assert [x["path"] for x in r["conflicts"]] == ["使用说明.md"]
    assert "<<<<<<<" in (proj.root / "自动化" / "世界树" / "枝-1" / "冲突" / "使用说明.md").read_text(encoding="utf-8")
    assert not (proj.root / "旧的.txt").exists() and r["deleted"] == ["旧的.txt"]   # 进回收站
    assert (proj.root / "AGENTS.md").read_text(encoding="utf-8") == "规矩（主干改）\n"
    assert not (proj.root / "自动化" / "交付" / "J1 S1-1 S2-1.md").exists()
    assert (proj.root / "自动化" / "世界树" / "枝-1" / "记录" / "自动化" / "交付" / "J1 S1-1 S2-1.md").is_file()
    assert len(snapshot.list_saves(proj)) == n_before + 2 and r["before"] != r["after"]
    assert worldtree.get(proj, "枝-1")["state"] == "合了" and snapshot.pins(proj) == {}
    gone = Path(worldtree.get(proj, "枝-1")["path"])
    assert not root.exists() and gone.parent.name == ".回收" and (gone / "枝.json").is_file()   # 合完枝挪进 .回收，能拿回来
    with pytest.raises(store.Refused):
        worldtree.merge(c, proj, "枝-1", by="agent:G1")
    c.close()


def test_core_lock_blocks_merging_core_files_and_cut_goes_to_recycle(proj):
    c = _setup(proj)
    b = worldtree.grow(c, proj, name="改后台", by="人")
    _w(Path(b["path"]) / "backend" / "a.py", "x = 3\n")
    claims.take_core(c, "agent:G7", "别的活")
    with pytest.raises(store.Refused, match="核心锁"):
        worldtree.merge(c, proj, "枝-1", by="agent:G1")
    assert (proj.root / "backend" / "a.py").read_text(encoding="utf-8") == "x = 1\n"
    x = worldtree.cut(c, proj, "枝-1", by="人", why="方向不对")
    assert x["state"] == "砍了" and ".回收" in x["path"] and Path(x["path"]).is_dir()
    assert not (worldtree.forest(proj) / "枝-1 改后台").exists() and snapshot.pins(proj) == {}
    c.close()


def test_the_page_grows_lists_and_merges(proj):
    c = _setup(proj)
    c.close()
    with TestClient(create_app(proj)) as client:
        b = client.post("/api/worldtree", json={"name": "页面长的", "why": "试试"}).json()
        assert b["code"] == "枝-1"
        _w(Path(b["path"]) / "AGENTS.md", "枝改的规矩\n")
        d = client.get("/api/worldtree").json()
        assert d["branches"][0]["code"] == "枝-1" and d["here"] is None
        assert client.get("/api/worldtree/枝-1/changes").json()["take"] == ["AGENTS.md"]
        r = client.post("/api/worldtree/枝-1/merge", json={"confirm": True}).json()
        assert r["took"] == ["AGENTS.md"]
        assert (proj.root / "AGENTS.md").read_text(encoding="utf-8") == "枝改的规矩\n"
        assert client.get("/api/worldtree/枝-9/changes").status_code >= 400


def test_send_an_agent_to_a_branch_and_send_the_fruit_back(proj):
    import agents
    c = _setup(proj)
    agents.create(c, proj, "sonnet", "写代码的", by="人", program="Claude Code（Sonnet 5.5）")
    _w(proj.root / "治理" / "目标" / "S1-1 看得懂.md",
       "# S1-1 看得懂\n\n**一句话**\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n| S2-1 | 第一件 | 项目 需-1 | 测试 | 没做 |\n")
    b = worldtree.grow(c, proj, name="派活", by="agent:G1")
    root = Path(b["path"])
    r = worldtree.assign(c, proj, "枝-1", "sonnet", "S1-1", "S2-1", by="agent:G1", open_window=False)
    assert r["launch"]["title"].startswith("枝-1 · ") and r["task"] == "S1-1 S2-1"
    text = (root / "索引" / "开工" / f"start-{r['agent']}.ps1").read_text(encoding="utf-8-sig")
    assert root.as_posix() in text and (root / "backend" / "mcp_server.py").as_posix() in (root / "索引" / "开工" / f"mcp-claude-{r['agent']}.json").read_text(encoding="utf-8")
    held = worldtree.held(worldtree.get(proj, "枝-1"))
    assert [(h["goal"], h["sub"]) for h in held] == [("S1-1", "S2-1")] and not claims.active(c)   # 领在枝的库里，主干不占
    with pytest.raises(store.Refused):
        worldtree.reject(c, proj, "枝-1", by="agent:G1", why="还没结果")
    bp = Project(root)
    bc = store.connect(bp.db_path)
    worldtree.bear_fruit(bc, bp, demo="看一眼", checks=[], by="agent:sonnet")
    x = worldtree.reject(c, proj, "枝-1", by="agent:G1", why="首页标题不对")
    assert x["state"] == "长着" and worldtree.is_branch(bp)["rejected"][0]["why"] == "首页标题不对"
    bc.close()
    c.close()


def test_two_branches_each_have_their_own_core_lock(proj):
    """几根枝上的 agent 能同时改核心（各有各的核心锁），主干的核心锁不受影响。"""
    c = _setup(proj)
    b1 = worldtree.grow(c, proj, name="甲", by="agent:G1")
    b2 = worldtree.grow(c, proj, name="乙", by="agent:G1", base="C1")
    assert b2["base"] == "C1" and snapshot.pins(proj) == {"枝-1": "C1", "枝-2": "C1"}
    claims.take_core(c, "agent:G7", "主干上改")
    for b, who in ((b1, "agent:G5"), (b2, "agent:G6")):
        bc = store.connect(Path(b["path"]) / "索引" / "state.db")
        claims.take_core(bc, who, "枝上改")                                   # 不撞主干的、也不撞另一根枝的
        assert claims.holds_core(bc, who) and not claims.holds_core(bc, "agent:G7")
        bc.close()
    assert claims.holds_core(c, "agent:G7")
    c.close()
