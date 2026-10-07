"""扫描（S1-8 S2-42 实时 · S2-43 走到哪扫到哪；作者 10-02「像我玩游戏一样，走到哪里就扫描到哪里」）：
系统通知为主（watchfiles）；你在看的、agent 在干的、一直盯着的那几片变了马上扫、通知网页；别处只记一笔，走进去再扫；
兜底只扫有账的；没有系统通知退回隔一会儿扫热的；自定义「不看」的不理。"""
import asyncio
import time

from fastapi.testclient import TestClient

import claims
import main
import scanmap
import store
import supervise
from main import Hub, create_app, watch


class _Hub(Hub):
    def __init__(self):
        super().__init__()
        self.got = []

    async def broadcast(self, msg):
        self.got.append((time.monotonic(), msg))


def _ready(proj, *mods):
    c = store.connect(proj.db_path)
    store.migrate(c)
    for m in mods:
        (proj.materials / m).mkdir(parents=True, exist_ok=True)
    store.sync_folders(c, proj)
    c.close()


async def _until(hub, t0, limit, ok):
    while time.monotonic() - t0 < limit:
        hit = [m for t, m in hub.got if t >= t0 and ok(m)]
        if hit:
            return hit[0]
        await asyncio.sleep(0.02)
    return None


def _run(proj, scenario, realtime=True):
    async def go():
        hub = _Hub()
        task = asyncio.create_task(watch(proj, hub, interval=0.05, realtime=realtime))
        await asyncio.sleep(1.4)                           # 第一遍走完、系统通知挂上、一秒后那回补扫也过了
        try:
            return await scenario(hub)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    return asyncio.run(go())


def _files(m, area=None):
    return m["type"] == "files" and (area is None or area in m["areas"])


def test_paths_fall_into_areas(proj):
    a = lambda r: scanmap.area_of(proj, r)
    assert a("资料/文献/x.pdf") == "资料/文献" and a("资料/文献/深/y.md") == "资料/文献"
    assert a("backend/main.py") == "核心" and a("模板.html") == "核心"
    assert a("治理/目标/S1-8 转得起来.md") == "治理" and a("笔记/总览.md") == "笔记"
    assert a("新想法.md") == "根目录" and a("资料/散的.md") == "资料" and a("资料/文献") == "资料"
    assert scanmap.structural(proj, "资料/新模块") and scanmap.structural(proj, "笔记")
    assert not scanmap.structural(proj, "资料/文献/x.pdf")
    assert scanmap.focus_areas(proj, "mod", "文献") == {"资料/文献"}
    assert scanmap.focus_areas(proj, "auto", "") == {"自动化", "治理"}
    assert scanmap.builtin_skip(proj, "索引/state.db") and scanmap.builtin_skip(proj, "存档/C1 好节点/资料/x.md")
    assert scanmap.builtin_skip(proj, ".claude/worktrees/w1/a.py") and not scanmap.builtin_skip(proj, "存档/C1 好节点")


def test_a_change_reaches_the_page_within_a_second(proj):
    _ready(proj)

    async def go(hub):
        t0 = time.monotonic()
        (proj.root / "新想法.md").write_text("x", encoding="utf-8")       # 根目录多了东西：结构变了，不管冷热马上看
        m = await _until(hub, t0, 5.0, _files)
        return m and time.monotonic() - t0
    took = _run(proj, go)
    assert took and took < 1.5                             # 系统通知：不用等兜底


def test_without_notifications_it_still_scans_every_little_while(proj):
    _ready(proj)

    async def go(hub):
        t0 = time.monotonic()
        (proj.root / "新想法.md").write_text("x", encoding="utf-8")
        m = await _until(hub, t0, 5.0, _files)
        return m and time.monotonic() - t0
    took = _run(proj, go, realtime=False)
    assert took and took < 2.0


def test_where_you_look_is_live_elsewhere_waits_until_you_walk_in(proj):
    _ready(proj, "文献", "实验")

    async def go(hub):
        hub.focus["网页"] = ("mod", "文献")
        hub.poke.set()
        await asyncio.sleep(0.2)
        t0 = time.monotonic()
        (proj.materials / "文献" / "a.md").write_text("看着的", encoding="utf-8")
        hot = await _until(hub, t0, 1.5, lambda m: _files(m, "资料/文献"))
        t1 = time.monotonic()
        (proj.materials / "实验" / "b.csv").write_text("1,2", encoding="utf-8")
        await asyncio.sleep(1.0)
        cold_files = [m for t, m in hub.got if t >= t1 and _files(m, "资料/实验")]
        dirty = scanmap.state(proj)["dirty"].get("资料/实验", 0)
        told = next((m for t, m in hub.got if t >= t1 and m["type"] in ("dirty", "files") and m["dirty"].get("资料/实验")), None)   # 账跟着通知走
        t2 = time.monotonic()
        hub.focus["网页"] = ("mod", "实验")                 # 走进实验：有账，先扫
        hub.poke.set()
        walked = await _until(hub, t2, 1.5, lambda m: _files(m, "资料/实验"))
        return hot, cold_files, dirty, told, walked, dict(scanmap.state(proj)["dirty"])
    hot, cold_files, dirty, told, walked, after = _run(proj, go)
    assert hot is not None                                 # 在看的那片：1.5 秒内到网页
    assert cold_files == [] and dirty >= 1 and told["dirty"]["资料/实验"] >= 1   # 冷的：不叫网页重画，只记一笔
    assert walked is not None and "资料/实验" not in after                        # 走进去：扫了，账清了


def test_agent_work_makes_a_module_hot(proj):
    _ready(proj, "实验")
    c = store.connect(proj.db_path)
    assert "资料/实验" not in scanmap.hot_areas(c, proj, [])
    claims.claim(c, "实验", "S2-1", "agent:甲", ["实验"])
    hot = scanmap.hot_areas(c, proj, [])
    assert "甲 在干" in hot["资料/实验"] and hot["治理"] == hot["笔记"] == "一直盯着"
    claims.claim(c, claims.CORE, "", "agent:甲", [claims.CORE])
    assert "甲 拿着核心锁" in scanmap.hot_areas(c, proj, [])["核心"]
    c.close()


def test_the_sweep_only_walks_areas_with_changes(proj, monkeypatch):
    _ready(proj, "文献", "实验", "图表")
    (proj.materials / "实验" / "旧.csv").write_text("1", encoding="utf-8")
    walked = []
    real = scanmap.walk_area
    monkeypatch.setattr(scanmap, "walk_area", lambda p, a, r: walked.append(a) or real(p, a, r))

    async def go(hub):
        (proj.materials / "实验" / "旧.csv").unlink()      # 冷的模块里删了文件（没进回收站）
        await asyncio.sleep(1.0)
        c = store.connect(proj.db_path)
        before = [r["rule"] for r in supervise.listing(c)["open"]]
        c.close()
        walked.clear()
        scanmap.state(proj)["next_sweep"] = 0               # 到点兜底
        hub.poke.set()
        t0 = time.monotonic()
        m = await _until(hub, t0, 2.0, lambda m: _files(m, "资料/实验"))
        await asyncio.sleep(0.3)
        c = store.connect(proj.db_path)
        after = [r["rule"] for r in supervise.listing(c)["open"]]
        c.close()
        return m, before, after, set(walked)
    m, before, after, seen = _run(proj, go)
    assert 2 not in before                                 # 没扫之前不误报，也不知道
    assert m is not None and 2 in after                    # 兜底时监管报出来
    assert "资料/实验" in seen and "资料/图表" not in seen and "资料/文献" not in seen   # 没账的不碰


def test_folders_set_to_ignore_are_left_alone(proj):
    _ready(proj, "实验")
    scanmap.write_rules(proj, 30, [{"path": "资料/实验/原始", "mode": "不看", "note": "几万个文件"}])
    (proj.materials / "实验" / "原始").mkdir()

    async def go(hub):
        hub.focus["网页"] = ("mod", "实验")
        hub.poke.set()
        await asyncio.sleep(0.3)
        t0 = time.monotonic()
        (proj.materials / "实验" / "原始" / "a.bin").write_bytes(b"0" * 10)
        await asyncio.sleep(1.0)
        return [m for t, m in hub.got if t >= t0 and m["type"] in ("files", "dirty")]
    assert _run(proj, go) == []                            # 在看着的模块里，不看的文件夹照样不理
    assert "资料/实验/原始/a.bin" not in scanmap.walk_area(proj, "资料/实验", scanmap.read_rules(proj)["rules"])


def test_a_big_area_says_scanning_first(proj, monkeypatch):
    _ready(proj, "大")
    monkeypatch.setattr(main, "BIG_SCAN", 0.0)            # 测试里当它很大：一扫就先说「扫着」
    for i in range(300):
        (proj.materials / "大" / f"{i}.txt").write_text("x", encoding="utf-8")

    async def go(hub):
        await asyncio.sleep(0.5)
        (proj.materials / "大" / "新.txt").write_text("y", encoding="utf-8")   # 冷的：记账
        await asyncio.sleep(0.6)
        t0 = time.monotonic()
        hub.focus["网页"] = ("mod", "大")
        hub.poke.set()
        done = await _until(hub, t0, 3.0, lambda m: _files(m, "资料/大"))
        busy = [t for t, m in hub.got if t >= t0 and m["type"] == "scanning" and "资料/大" in m["areas"]]
        return done, busy, [t for t, m in hub.got if t >= t0 and _files(m, "资料/大")]
    done, busy, fin = _run(proj, go)
    assert done is not None and busy and busy[0] <= fin[0]


def test_rules_round_trip_and_old_modes_move_over(proj):
    rules = [{"path": "资料/实验/原始", "mode": "不看", "note": "几万个文件"}, {"path": "笔记", "mode": "一直盯着", "note": ""}]
    r = scanmap.write_rules(proj, 10, rules)
    assert r == {"sweep": 10, "rules": rules} == scanmap.read_rules(proj)
    assert "兜底：每 10 分钟" in (proj.root / scanmap.RULES_FILE).read_text(encoding="utf-8")
    assert scanmap.rule_for(r["rules"], "资料/实验/原始/a/b.bin")["mode"] == "不看"
    assert scanmap.classify(proj, "资料/实验/原始/a.bin", r["rules"], {"资料/实验"}) == "skip"
    assert scanmap.classify(proj, "笔记/x.md", r["rules"], set()) == "hot"
    assert scanmap.classify(proj, "资料/文献/x.md", r["rules"], set()) == "cold"
    for bad in ([{"path": "x", "mode": "慢扫"}], [{"path": "../外面", "mode": "不看"}], [{"path": "x", "mode": "不看"}] * 2):
        try:
            scanmap.write_rules(proj, 30, bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    (proj.root / scanmap.RULES_FILE).unlink()
    c = store.connect(proj.db_path)
    store.migrate(c)
    with store.tx(c):
        store._set_meta(c, "scan_modes", '{"实验": "只看最上一层", "视频": "慢扫"}')
    scanmap.migrate(c, proj)
    got = {x["path"]: x["mode"] for x in scanmap.read_rules(proj)["rules"]}
    assert got == {"资料/实验": "不看", "资料/视频": "走到才扫"}
    c.close()


def test_settings_page_reads_and_saves_the_rules(proj):
    _ready(proj, "实验")
    with TestClient(create_app(proj)) as client:
        d = client.get("/api/scan").json()
        assert d["sweep"] == 30 and d["sweeps"] == [10, 30, 60] and d["modes"] == ["一直盯着", "走到才扫", "不看"]
        assert d["builtin"] and d["rules"] == []
        d = client.put("/api/scan", json={"sweep": 60, "rules": [{"path": "资料/实验/原始", "mode": "不看", "note": "大"}]}).json()
        assert d["sweep"] == 60 and d["rules"][0]["path"] == "资料/实验/原始"
        assert client.put("/api/scan", json={"sweep": 5, "rules": []}).status_code >= 400
        assert client.post("/api/scan/now", json={"area": "资料/实验"}).json() == {"ok": True}
        m = next(x for x in client.get("/api/state").json()["modules"] if x["name"] == "实验")
        assert m["dirty"] == 0 and "scan" not in m


def test_the_tick_tree_says_how_each_thing_is_scanned(proj):
    """设置 → 扫描那棵勾选的树（S1-8 S2-44；作者 10-02「可以勾选任意模块的文件自定义扫描的方案」）。"""
    _ready(proj, "实验", "文献")
    (proj.materials / "实验" / "原始").mkdir()
    (proj.materials / "实验" / "原始" / "a.bin").write_bytes(b"0")
    (proj.materials / "实验" / "记录.md").write_text("x", encoding="utf-8")
    for d in ("治理", "存档/C1 好节点", "索引"):
        (proj.root / d).mkdir(parents=True, exist_ok=True)
    rules = lambda: scanmap.read_rules(proj)["rules"]
    top = {x["name"]: x for x in scanmap.children(proj, "", rules())["items"]}
    assert "索引" not in top                                                       # 库、缓存不列
    assert (top["治理"]["mode"], top["治理"]["why"]) == ("一直盯着", "自带")
    assert top["存档"]["locked"] and not top["存档"]["open"] and top["资料"]["mode"] == "走到才扫"
    scanmap.set_paths(proj, ["资料/实验/原始", "资料/实验/记录.md"], "不看", "大")
    scanmap.set_paths(proj, ["资料/文献"], "一直盯着")
    kids = {x["name"]: x for x in scanmap.children(proj, "资料/实验", rules())["items"]}
    assert (kids["原始"]["mode"], kids["原始"]["why"], kids["原始"]["own"]) == ("不看", "你设的：大", True)
    assert kids["记录.md"]["mode"] == "不看" and not kids["记录.md"]["dir"]
    inner = scanmap.children(proj, "资料/实验/原始", rules())["items"][0]
    assert (inner["mode"], inner["why"], inner["own"]) == ("不看", "跟着 资料/实验/原始", False)       # 跟着上面的
    walked = scanmap.walk_area(proj, "资料/实验", rules())
    assert "资料/实验/记录.md" not in walked and "资料/实验/原始/a.bin" not in walked              # 单个文件也能不看
    assert scanmap.how(proj, rules(), "资料/文献", True)["mode"] == "一直盯着"
    scanmap.set_paths(proj, ["资料/实验/记录.md"], "")                             # 去掉自定义
    assert {r["path"] for r in rules()} == {"资料/实验/原始", "资料/文献"}
    for bad in (["存档/C1 好节点"], ["../外面"]):
        try:
            scanmap.set_paths(proj, bad, "不看")
            raise AssertionError(bad)
        except ValueError:
            pass
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/scan/dir", params={"path": "资料"}).json()["path"] == "资料"
        d = client.post("/api/scan/set", json={"paths": ["资料/文献"], "mode": ""}).json()
        assert [r["path"] for r in d["rules"]] == ["资料/实验/原始"]
        assert client.post("/api/scan/set", json={"paths": ["资料/x"], "mode": "慢扫"}).status_code >= 400
