"""存档：一档一个文件夹，全部文件记指纹、按存法真复制；比得出变了什么；复活时换下来的进回收站、笔记不倒回；
断电不坏档；定性以后才能彻底删；删模块空的直接删、有文件先问。"""
import json

import pytest
from fastapi.testclient import TestClient

import snapshot
import store
import trash
from main import create_app


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(proj):
    _w(proj.materials / "论文" / "第1章.md", "第一版")
    _w(proj.materials / "实验" / "结果.json", "{}")
    _w(proj.root / "计划" / "P1.md", "计划")
    _w(proj.root / "笔记" / "总览.md", "# 总览 · 笔记\n")
    _w(proj.root / "AGENTS.md", "规矩")
    _w(proj.root / "backend" / "__pycache__" / "x.pyc", "缓存")
    _w(proj.root / "大数据" / "原始.csv", "很大")
    _w(proj.root / "存档忽略.txt", "# 能重新下载的\n大数据\n")


def test_three_modes_record_all_fingerprints_and_copy_what_was_asked(proj):
    _project(proj)
    c = store.connect(proj.db_path)
    m1 = snapshot.save(c, proj, name="改论文前", mode="自定义", picks=["资料/论文", "AGENTS.md"], by="人")
    assert m1["code"] == "C1" and m1["grade"] == "黄档" and m1["copied_files"] == 2
    f1 = proj.root / "存档" / "C1 改论文前"
    assert snapshot.old_file(proj, "C1", "资料/论文/第1章.md")[0].read_text(encoding="utf-8") == "第一版"   # 内容在对象库（10-03 起），取得出来
    assert not (f1 / "文件").exists()
    fp = json.loads((f1 / "指纹.json").read_text(encoding="utf-8"))["files"]
    assert "资料/实验/结果.json" in fp and fp["资料/实验/结果.json"][3] == 0                        # 没复制的也记了指纹
    assert not any(k.split("/")[0] in ("大数据", "索引", "存档") or "__pycache__" in k for k in fp)   # 忽略的、工具自己的不记

    m2 = snapshot.save(c, proj, name="全量", mode="全量", by="agent:x",
                       checks=[{"name": "pytest", "ok": True, "detail": "48 过"}])
    assert m2["code"] == "C2" and m2["grade"] == "绿档" and m2["copied_files"] == m2["total_files"]
    m3 = snapshot.save(c, proj, name="记号", mode="只记指纹", by="人")
    assert m3["copied_files"] == 0 and not (proj.root / "存档" / "C3 记号" / "文件").exists()
    assert snapshot.last_picks(c) == ["资料/论文", "AGENTS.md"]                                 # 记住上次勾的
    text = (proj.root / "存档" / "清单.md").read_text(encoding="utf-8")
    assert "## C2 · 全量" in text and "pytest 过了（48 过）" in text
    with pytest.raises(store.Refused, match="至少一个"):
        snapshot.save(c, proj, name="空", mode="自定义", picks=[], by="人")
    c.close()


def test_half_written_save_leaves_nothing_behind(proj, monkeypatch):
    _project(proj)
    c = store.connect(proj.db_path)
    calls = []

    def boom(src, dst):
        calls.append(src)
        if len(calls) == 2:
            raise KeyboardInterrupt("存到一半断电")
        return real(src, dst)

    real = snapshot._copy_hash
    monkeypatch.setattr(snapshot, "_copy_hash", boom)
    with pytest.raises(KeyboardInterrupt):
        snapshot.save(c, proj, name="断电", mode="全量", by="人")
    assert snapshot.list_saves(proj) == [] and not (proj.root / "存档" / ".正在存").exists()
    monkeypatch.setattr(snapshot, "_copy_hash", real)
    assert snapshot.save(c, proj, name="再来", mode="全量", by="人")["code"] == "C1"              # 没用掉编号
    c.close()


def test_diff_old_file_and_restore(proj):
    _project(proj)
    c = store.connect(proj.db_path)
    snapshot.save(c, proj, name="全量", mode="全量", by="人")
    snapshot.save(c, proj, name="记号", mode="只记指纹", by="人")
    _w(proj.materials / "论文" / "第1章.md", "改坏了")
    _w(proj.materials / "论文" / "第2章.md", "后来加的")
    (proj.materials / "实验" / "结果.json").unlink()
    _w(proj.root / "笔记" / "总览.md", "# 总览 · 笔记\n\n## 总-001 · 后来记的\n")

    d = snapshot.diff(proj, "C1")
    assert d["added"] == ["资料/论文/第2章.md"]
    assert [x["path"] for x in d["changed"]] == ["笔记/总览.md", "资料/论文/第1章.md"]
    assert [x["path"] for x in d["removed"]] == ["资料/实验/结果.json"] and d["removed"][0]["copy"]
    path, got = snapshot.old_file(proj, "C2", "资料/论文/第1章.md")                               # C2 只记了指纹，从 C1 拿
    assert got == "C1" and path.read_text(encoding="utf-8") == "第一版"

    with pytest.raises(store.NeedConfirm) as w:                                                  # 先问
        snapshot.restore(c, proj, "C1", by="人")
    assert w.value.info["counts"] == [1, 1, 1]
    r = snapshot.restore(c, proj, "C1", by="人", confirm=True)
    assert (r["replaced"], r["restored"], r["trashed"]) == (1, 1, 1)
    assert (proj.materials / "论文" / "第1章.md").read_text(encoding="utf-8") == "第一版"
    assert (proj.materials / "实验" / "结果.json").exists() and not (proj.materials / "论文" / "第2章.md").exists()
    assert "后来记的" in (proj.root / "笔记" / "总览.md").read_text(encoding="utf-8")            # 笔记不倒回
    x = {e["code"]: e for e in trash.read(proj)}[r["trash_code"]]
    assert x["fields"]["从哪来"] == "复活 C1 换下来的"                                            # 换下来的在回收站，一批一个号
    trash.restore(c, proj, r["trash_code"], by="人", swap=True)                                  # 反悔：还原那一批
    assert (proj.materials / "论文" / "第1章.md").read_text(encoding="utf-8") == "改坏了"

    _w(proj.materials / "论文" / "第1章.md", "又改")
    r = snapshot.restore(c, proj, "C2", by="人", paths=["资料/论文/第1章.md"], confirm=True)      # 只复活一个文件，副本在 C1
    assert r["replaced"] == 1 and (proj.materials / "论文" / "第1章.md").read_text(encoding="utf-8") == "第一版"
    with pytest.raises(store.Refused, match="只记了指纹"):
        snapshot.restore(c, proj, "C2", by="人", confirm=True)
    c.close()


def test_settle_purge_remove_and_module_remove_over_http(proj):
    with TestClient(create_app(proj)) as client:
        _w(proj.materials / "论文" / "旧稿.md", "旧")
        c = store.connect(proj.db_path)
        old = trash.move(c, proj, "资料/论文/旧稿.md", by="人", reason="不要了")["code"]
        c.close()
        r = client.post("/api/trash/purge", json={"codes": [old]})
        assert r.status_code == 409 and "收不回来" in r.json()["detail"]                              # 10-07 起不用先定性存档，但要先警告
        s = client.post("/api/checkpoints", json={"name": "安全点", "mode": "只记指纹"}).json()
        client.post(f"/api/checkpoints/{s['code']}/settle")
        assert client.get("/api/trash").json()["cutoff"] == s["at"]
        r = client.post("/api/trash/purge", json={"codes": [old]})
        assert r.status_code == 409 and "收不回来" in r.json()["detail"]                              # 先警告
        assert client.post("/api/trash/purge", json={"codes": [old], "confirm": True}).status_code == 200
        assert trash.read(proj)[0]["status"] == "已彻底删掉"

        assert client.post(f"/api/checkpoints/{s['code']}/remove", json={}).status_code == 409        # 定性过的要确认
        rm = client.post(f"/api/checkpoints/{s['code']}/remove", json={"confirm": True}).json()
        assert client.get("/api/checkpoints").json()["saves"] == [] and rm["trash_code"].startswith("X")

        assert client.post("/api/modules/实验/remove", json={}).status_code == 200                      # 空的直接删
        assert not (proj.materials / "实验").exists()
        _w(proj.materials / "汇报" / "a.pdf", "x")                                                     # 10-06 起文献是固定模块，拿起步模块试
        r = client.post("/api/modules/汇报/remove", json={})
        assert r.status_code == 409 and r.json()["confirm"]["files"] == 1 and (proj.materials / "汇报").exists()
        s = client.post("/api/modules/汇报/remove", json={"confirm": True}).json()
        assert "汇报" not in [m["name"] for m in s["modules"]]
        assert client.post("/api/modules/文献/remove", json={"confirm": True}).status_code == 400      # 文献也是固定的
        assert client.post("/api/modules/蓝图/remove", json={"confirm": True}).status_code == 400      # 固定的不能删
        assert any(e["fields"].get("从哪来") == "设置里删模块" for e in trash.read(proj))


def test_content_is_stored_once_and_every_save_is_whole(proj):
    """S1-8 S2-53（作者 10-03「只有要有分支的节点要全量；不分支的记录改动的地方就行」）：内容按 sha256 只存一份，
    新存一档只多存改了的；哪一档都能取出一整份；没人用的内容清理时收掉；网页、agent 复活默认只换程序和规矩。"""
    _project(proj)
    _w(proj.root / "backend" / "main.py", "print(1)")
    c = store.connect(proj.db_path)
    m1 = snapshot.save(c, proj, name="一", mode=snapshot.offered("核心"), by="人")
    objs = lambda: sorted(f for f in (proj.root / "存档" / ".对象").glob("*/*") if f.is_file())
    n1 = len(objs())
    assert m1["mode"] == "全量" and m1["objects"] and m1["copied_files"] == m1["total_files"] and m1["new_bytes"] > 0
    assert not (proj.root / m1["folder"] / "文件").exists()                       # 一档自己不再抄文件
    _w(proj.materials / "论文" / "第1章.md", "第二版")
    m2 = snapshot.save(c, proj, name="二", mode="全量", by="人")
    assert len(objs()) == n1 + 1 and m2["new_bytes"] == len("第二版".encode("utf-8"))   # 只多存了改了的那一个
    for code, want in (("C1", "第一版"), ("C2", "第二版")):                        # 哪一档都取得出那时候的样子
        assert snapshot.old_file(proj, code, "资料/论文/第1章.md")[0].read_text(encoding="utf-8") == want
    est = snapshot.estimate(proj, "全量", [])
    assert est["new_bytes"] == 0                                                  # 没改东西：再存一档不用多存
    _w(proj.materials / "实验" / "结果.json", '{"a": 1}')
    _w(proj.root / "backend" / "main.py", "print(2)")
    with pytest.raises(store.NeedConfirm) as w:                                   # 网页、agent 默认只换程序和规矩
        snapshot.restore(c, proj, "C2", by="人", whole=False)
    assert w.value.info["replace"] == ["backend/main.py"]
    with pytest.raises(store.NeedConfirm) as w:                                   # 明说整份：资料也回去
        snapshot.restore(c, proj, "C2", by="人", whole=True)
    assert "资料/实验/结果.json" in w.value.info["replace"]
    snapshot.remove(c, proj, "C1", by="人")                                       # C1 挪进回收站 → 它独用的「第一版」没人用了
    assert snapshot.gc_objects(proj)["removed"] == 1 and len(objs()) == n1
    c.close()


def test_old_copies_move_into_the_object_store(proj):
    """老档的 文件/ 迁进对象库：先核 sha256、一样的只留一份，迁完逐档取得出来；对不上的原样留着、写出来。"""
    import hashlib
    _project(proj)
    c = store.connect(proj.db_path)
    for name in ("老一", "老二"):                                                 # 造两个老样子的档：文件/ 里各抄一份
        m = snapshot.save(c, proj, name=name, mode="全量", by="人")
        folder = proj.root / m["folder"]
        files = json.loads((folder / "指纹.json").read_text(encoding="utf-8"))["files"]
        for rel, v in files.items():
            src = snapshot.obj_path(proj, v[2])
            dst = folder / "文件" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        meta = json.loads((folder / "档.json").read_text(encoding="utf-8"))
        meta.pop("objects")
        (folder / "档.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    import shutil
    shutil.rmtree(proj.root / "存档" / ".对象")
    bad = proj.root / "存档" / "C2 老二" / "文件" / "AGENTS.md"
    bad.write_text("被改坏的副本", encoding="utf-8")                              # 副本跟清单对不上
    out = snapshot.migrate_objects(c, proj)
    assert out["deduped"] > 0 and any("AGENTS.md" in x for x in out["mismatch"])
    assert out["checkpoints"] == ["C1"] and bad.is_file()                         # 对不上的那档原样留着
    got = snapshot.old_file(proj, "C1", "资料/论文/第1章.md")[0]
    assert got.read_text(encoding="utf-8") == "第一版" and ".对象" in str(got)
    assert not (proj.root / "存档" / "C1 老一" / "文件").exists()
    for f in (proj.root / "存档" / ".对象").glob("*/*"):                          # 对象名就是内容的 sha256
        assert hashlib.sha256(f.read_bytes()).hexdigest() == f.name
    c.close()
