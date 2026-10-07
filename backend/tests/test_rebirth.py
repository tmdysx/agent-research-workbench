"""清理 → 重生（S1-8 S2-64；需-30）：全量备份（带 / 不带存档）两边对上、世界树在、库能打开、进度到 100、
跑着再点拒、磁盘不够拒、后台重启过的标断了；重生计划就是 治理/计划/ 里开头写着「重生:」的。"""
import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import rebirth
import store
from main import create_app
from project import Project


def _w(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.write_bytes if isinstance(data, bytes) else lambda t: path.write_text(t, encoding="utf-8"))(data)


@pytest.fixture
def home(tmp_path):
    """项目放在 tmp/项目，世界树在 tmp/项目 世界树，备份就落在 tmp/ 下。"""
    p = Project(tmp_path / "项目")
    c = store.connect(p.db_path)
    store.migrate(c)
    store.log(c, "人", "试一条", None, None)
    c.commit()
    _w(p.root / "README.md", "# 试\n")
    _w(p.root / "资料" / "文献" / "a.pdf", b"%PDF" + b"x" * 3_000_000)          # 比一块（1 MB）大，进度分几次走
    _w(p.root / "存档" / "C1 第一档" / "档.json", '{"code": "C1"}')
    _w(p.root / "存档" / ".对象" / "ab" / "abcdef", b"y" * 1000)
    _w(p.root / "很" / ("深" * 40) / ("长" * 40) / "f.txt", "长路径")
    (p.root / "空的").mkdir()
    _w(tmp_path / "项目 世界树" / "枝-1 试" / "README.md", "# 枝\n")
    rebirth._job.clear()
    yield p
    c.close()
    _wait()
    rebirth._job.clear()


def _wait(limit=60):
    t = time.time()
    while rebirth.running() and time.time() - t < limit:
        time.sleep(0.05)
    assert not rebirth.running()


def _files(d: Path) -> dict:
    return {f.relative_to(d).as_posix(): f.stat().st_size for f in d.rglob("*") if f.is_file()}


def test_full_backup_with_saves_matches_both_sides(home):
    s = rebirth.sizes(home, fresh=True)
    assert s["with_saves"]["bytes"] - s["without_saves"]["bytes"] == len('{"code": "C1"}'.encode()) + 1000
    assert s["forest"] is True
    r = rebirth.start(home, with_saves=True, by="人")
    assert r["state"] in ("数文件", "复制", "核对", "好了")
    _wait()
    job = rebirth.status(home)
    assert job["state"] == "好了", job
    assert job["done_bytes"] == job["total_bytes"] and job["done_files"] == job["total_files"]   # 进度到 100
    res = job["result"]
    assert res["ok"] and res["db_ok"] is True and not res["missing"] and not res["extra"]
    dest = Path(job["dest"])
    assert dest.parent == home.root.parent and dest.name.startswith("项目 · 全量备份 ")
    src, got = _files(home.root), _files(dest / "项目")
    after = ("索引/state.db", "自动化/重生/", "笔记/日志/")        # 库另外核；备份记录和日志是复制完才写的
    src = {k: v for k, v in src.items() if not k.startswith(after)}
    got_db = got.pop("索引/state.db")
    assert got_db > 0 and src == {k: v for k, v in got.items()}           # 库以外每个文件都在、大小一样
    assert (dest / "项目 世界树" / "枝-1 试" / "README.md").read_text(encoding="utf-8") == "# 枝\n"
    assert (dest / "项目" / "空的").is_dir()
    c = sqlite3.connect(dest / "项目" / "索引" / "state.db")
    assert c.execute("SELECT count(*) FROM event WHERE action='试一条'").fetchone()[0] == 1
    c.close()
    h = rebirth.history(home)
    assert h[0]["dest"] == job["dest"] and h[0]["state"] == "好了" and h[0]["with_saves"] is True


def test_backup_without_saves_leaves_saves_out(home):
    rebirth.start(home, with_saves=False, by="人")
    _wait()
    job = rebirth.status(home)
    assert job["state"] == "好了", job
    dest = Path(job["dest"]) / "项目"
    assert not (dest / "存档").exists()
    assert (dest / "资料" / "文献" / "a.pdf").stat().st_size == 3_000_004
    assert rebirth.history(home)[0]["with_saves"] is False


def test_one_at_a_time_and_disk_must_fit(home):
    with pytest.raises(store.Refused, match="磁盘不够"):
        rebirth.start(home, with_saves=True, by="人", _free=1000)
    rebirth._job.update(state="复制", dest="x", dest_name="x")
    with pytest.raises(store.Refused, match="已经在备份"):
        rebirth.start(home, with_saves=True, by="人")
    rebirth._job.clear()


def test_interrupted_backup_shows_broken(home):
    rebirth._save_live(home, {"dest": "某处", "dest_name": "某处", "state": "复制", "at": "2026-10-04 10:00"})   # 后台重启：线程没了，进度文件还在
    assert rebirth.history(home)[0]["state"] == "断了"


def test_rebirth_plans_are_plans_marked_rebirth(home):
    d = home.root / "治理" / "计划" / "S1-8 转得起来"
    _w(d / "P1 · 2026-10-04 · 开启新纪元.md", "---\n谁: G1\n时间: 2026-10-04\n重生: 整个项目\n状态: 暂停\n---\n\n# 计划：开启新纪元\n\n正文\n")
    _w(d / "P2 · 2026-10-04 · 别的.md", "---\n谁: G1\n状态: 做完\n---\n\n# 别的\n")
    ps = rebirth.plans(home)
    assert [x["title"] for x in ps] == ["计划：开启新纪元"]
    assert ps[0]["state"] == "暂停" and ps[0]["kind"] == "整个项目" and ps[0]["code"] == "P1" and "正文" in ps[0]["text"]


def test_api_asks_before_backup_then_runs(home):
    with TestClient(create_app(home)) as client:
        r = client.post("/api/rebirth/backup", json={"with_saves": False})
        assert r.status_code == 409 and "不带存档" in r.json()["detail"] and "还剩" in r.json()["detail"]
        assert client.get("/api/rebirth/size").json()["without_saves"]["files"] > 0
        r = client.post("/api/rebirth/backup", json={"with_saves": False, "confirm": True})
        assert r.status_code == 200, r.text
        _wait()
        d = client.get("/api/rebirth").json()
        assert d["job"]["state"] == "好了" and d["history"][0]["with_saves"] is False
