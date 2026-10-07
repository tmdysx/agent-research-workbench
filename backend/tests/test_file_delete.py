"""文件阅读页删除：只在临时项目里验证真实移入/还原与普通文件记录。"""
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import anyio
import pytest
from fastapi.testclient import TestClient

import file_actions
import files
import journal
import project
import store
import trash
from main import create_app


@pytest.fixture
def case(tmp_path, monkeypatch):
    p = project.Project(tmp_path / "项目")
    monkeypatch.setenv("RC_DB", str(p.root / "索引" / "state.db"))
    project.ensure_skeleton(p)
    f = p.materials / "文献" / "旧稿.md"
    f.write_text("这是原稿\n", encoding="utf-8")
    conn = store.connect(p.db_path)
    yield p, conn, f
    conn.close()


def take(p, conn, f, **changes):
    a = file_actions.preview_action(p, f)
    request = {"path": a["path"], "project": a["project"], "revision": a["revision"], "reason": "人选择不要这份旧稿"}
    request.update(changes)
    return file_actions.move_file(conn, p, **request)


def test_move_restore_and_agent_readable_files(case):
    p, conn, f = case
    a = file_actions.preview_action(p, f)
    assert a["allowed"] and len(a["revision"]) == 64
    r = take(p, conn, f)
    assert not f.exists() and (p.root / r["to"]).read_text(encoding="utf-8") == "这是原稿\n"
    assert r["code"] == "X1" and r["status"] == "在回收站" and r["log_id"] == "志-0001"
    item = trash.read(p)[0]
    assert item["by"] == "人" and item["fields"]["原来在"] == "资料/文献/旧稿.md"
    assert item["fields"]["为什么"] == "人选择不要这份旧稿" and item["fields"]["从哪来"] == "网页文件阅读页"
    entry = journal.recent(p)[0]
    assert entry["kind"] == "删除文件" and entry["scope"] == "文献" and entry["by"] == "人"
    assert "X1" in entry["body"] and a["revision"] in entry["body"] and "资料/文献/旧稿.md" in entry["body"]
    # 机器正本不依赖索引：关连接之后直接读清单和月日志仍有路径、操作者和编号。
    assert "X1" in (p.root / r["record_path"]).read_text(encoding="utf-8")
    trash.restore(conn, p, r["code"], by="人")
    assert f.read_text(encoding="utf-8") == "这是原稿\n" and trash.read(p)[0]["status"] == "已还原"


def test_unchanged_root_core_file_is_reversible(case):
    p, conn, _ = case
    f = p.root / "自定义.js"
    f.write_text("const x=1;", encoding="utf-8")
    r = take(p, conn, f)
    assert r["from"] == ["自定义.js"]
    trash.restore(conn, p, r["code"], by="人")
    assert f.read_text() == "const x=1;"


def test_revision_change_rejects_without_trash(case):
    p, conn, f = case
    a = file_actions.preview_action(p, f)
    f.write_text("刚修改过的稿\n", encoding="utf-8")
    with pytest.raises(store.Refused, match="发生变化"):
        file_actions.move_file(conn, p, a["path"], a["project"], a["revision"])
    assert f.read_text(encoding="utf-8") == "刚修改过的稿\n" and trash.read(p) == [] and journal.read(p) == []


def test_same_size_replacement_and_inode_change_rejects(case):
    p, conn, f = case
    a = file_actions.preview_action(p, f)
    old = f.stat()
    replacement = f.with_suffix(".new")
    replacement.write_text("这是新稿\n", encoding="utf-8")
    os.utime(replacement, ns=(old.st_atime_ns, old.st_mtime_ns))
    os.replace(replacement, f)
    with pytest.raises(store.Refused, match="发生变化"):
        file_actions.move_file(conn, p, a["path"], a["project"], a["revision"])
    assert trash.read(p) == []


def _rewrite_same_size_in_place(f, text):
    before = f.stat()
    data = text.replace("\n", os.linesep).encode("utf-8")
    assert len(data) == before.st_size
    with f.open("r+b") as target:
        target.write(data)
    os.utime(f, ns=(before.st_atime_ns, before.st_mtime_ns))
    return before, f.stat()


@pytest.mark.skipif(os.name != "nt", reason="复现 Windows 原地等长改写并恢复 mtime，全部 stat 字段不变")
def test_real_windows_same_stat_changed_body_rejects_old_http_revision(case):
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        old = client.get("/api/project/preview", params={"path": "资料/文献/旧稿.md"}).json()
        action = old["delete_action"]
        assert action["allowed"] and old["text"] == f.read_bytes().decode("utf-8")
        before, after = _rewrite_same_size_in_place(f, "这是新稿\n")
        assert file_actions._stamp(before) == file_actions._stamp(after)
        request = {k: action[k] for k in ("path", "project", "revision")}
        version = store.version(conn)
        denied = client.post("/api/files/trash", json=request)
        assert denied.status_code == 400 and "发生变化" in denied.text
        assert f.read_text(encoding="utf-8") == "这是新稿\n"
        assert client.get("/api/trash").json()["items"] == [] and client.get("/api/log").json()["entries"] == []
        assert not (p.root / "回收站").exists() and store.version(conn) == version
        fresh = client.get("/api/project/preview", params={"path": action["path"]}).json()
        new = fresh["delete_action"]
        assert fresh["text"] == f.read_bytes().decode("utf-8") and new["allowed"] and new["revision"] != action["revision"]
        moved = client.post("/api/files/trash", json={k: new[k] for k in ("path", "project", "revision")})
        assert moved.status_code == 200 and moved.json()["code"] == "X1"
        assert client.post("/api/trash/X1/restore", json={"confirm": False}).status_code == 200
        assert f.read_text(encoding="utf-8") == "这是新稿\n" and trash.read(p)[0]["status"] == "已还原"


def test_same_size_change_after_output_checks_rechecks_body_before_move(case, monkeypatch):
    p, conn, f = case
    action = file_actions.preview_action(p, f)
    real = file_actions._outputs
    def changed(conn, p, rel):
        real(conn, p, rel)
        before, after = _rewrite_same_size_in_place(f, "这是新稿\n")
        if os.name == "nt":
            assert file_actions._stamp(before) == file_actions._stamp(after)
    monkeypatch.setattr(file_actions, "_outputs", changed)
    version = store.version(conn)
    with pytest.raises(store.Refused, match="刚刚发生变化"):
        file_actions.move_file(conn, p, action["path"], action["project"], action["revision"])
    assert f.read_text(encoding="utf-8") == "这是新稿\n" and not trash.read(p) and not journal.read(p)
    assert not (p.root / "回收站").exists() and store.version(conn) == version


@pytest.mark.parametrize("stage", ["preview", "move"])
@pytest.mark.parametrize("restore_mtime", [False, True])
def test_chunked_revision_refuses_change_during_body_read(case, monkeypatch, stage, restore_mtime):
    p, conn, f = case
    f.write_bytes(b"a" * (2 * 1024 * 1024 + 7))
    action = file_actions.preview_action(p, f)
    assert action["allowed"]
    before = f.stat()
    real_open = Path.open
    reads = []
    class ChangingRead:
        def __init__(self, source):
            self.source = source
        def __enter__(self):
            self.source.__enter__()
            return self
        def __exit__(self, *args):
            return self.source.__exit__(*args)
        def fileno(self):
            return self.source.fileno()
        def seek(self, offset):
            return self.source.seek(offset)
        def read(self, size):
            assert 0 < size <= 1024 * 1024
            reads.append(size)
            data = self.source.read(size)
            if len(reads) == 1:
                with real_open(f, "r+b") as target:
                    target.write(b"b")
                mtime = before.st_mtime_ns if restore_mtime else before.st_mtime_ns + 1_000_000_000
                os.utime(f, ns=(before.st_atime_ns, mtime))
                if os.name == "nt" and restore_mtime:
                    assert file_actions._stamp(f.stat()) == file_actions._stamp(before)
            return data
    def changing_open(target, mode="r", *args, **kwargs):
        source = real_open(target, mode, *args, **kwargs)
        return ChangingRead(source) if target == f and mode == "rb" else source
    monkeypatch.setattr(Path, "open", changing_open)
    version = store.version(conn)
    if stage == "preview":
        current = file_actions.preview_action(p, f)
        assert not current["allowed"] and not current["revision"] and "读取期间" in current["reason"]
    else:
        with pytest.raises(store.Refused, match="读取期间"):
            file_actions.move_file(conn, p, action["path"], action["project"], action["revision"])
    with real_open(f, "rb") as current:
        assert len(reads) >= 3 and current.read(1) == b"b"
    assert not trash.read(p) and not journal.read(p) and not (p.root / "回收站").exists()
    assert store.version(conn) == version


def test_other_project_and_missing_revision_reject(case, tmp_path):
    p, conn, f = case
    other = project.Project(tmp_path / "另一个项目")
    project.ensure_skeleton(other)
    twin = other.materials / "文献" / f.name
    twin.write_text("另一份原稿", encoding="utf-8")
    token = file_actions.preview_action(other, twin)
    with pytest.raises(store.Refused, match="项目已经切换"):
        file_actions.move_file(conn, p, token["path"], token["project"], token["revision"])
    with pytest.raises(store.Refused, match="缺少"):
        take(p, conn, f, revision="")
    assert f.exists() and twin.exists() and trash.read(p) == []


def test_repeated_delete_does_not_create_second_item(case):
    p, conn, f = case
    a = file_actions.preview_action(p, f)
    take(p, conn, f)
    with pytest.raises(store.Refused, match="已经移走"):
        file_actions.move_file(conn, p, a["path"], a["project"], a["revision"])
    assert len(trash.read(p)) == 1 and len(journal.read(p)) == 1


@pytest.mark.parametrize("rel", ["../外部.md", "a/../../外部.md", "/外部.md", "C:/外部.md", "资料//文献/旧稿.md", "资料/文献/./旧稿.md", "资料/文献/旧稿.md.", "资料/文献/旧稿.md ", "资料/CON.txt", "资料/文献/旧稿.md:stream"])
def test_bad_paths_do_not_move(case, rel):
    p, conn, f = case
    with pytest.raises(store.Refused):
        take(p, conn, f, path=rel)
    assert f.exists() and trash.read(p) == []


@pytest.mark.parametrize("rel", ["笔记/总览.md", "笔记/历史/副本.md", "笔记/日志/2026-10.md", "回收站/清单.md", "存档/C1/清单.md", "归档/旧稿.md", "索引/settings.json", ".git/config", "backend/__pycache__/x.pyc"])
def test_protected_files_have_explanation_and_reject(case, rel):
    p, conn, f = case
    guarded = p.root / rel
    guarded.parent.mkdir(parents=True, exist_ok=True)
    guarded.write_text("保护原文", encoding="utf-8")
    a = file_actions.preview_action(p, guarded)
    assert a["allowed"] is False and a["reason"] and not a["revision"]
    with pytest.raises(store.Refused):
        take(p, conn, f, path=rel)
    assert guarded.read_text(encoding="utf-8") == "保护原文" and f.exists()


def test_directory_and_fixed_module_are_not_deleted(case):
    p, conn, f = case
    for folder in (p.materials / "文献", p.materials / "蓝图", p.materials / "戒律", p.materials / "源代码"):
        action = file_actions.preview_action(p, folder)
        assert action["allowed"] is False and "不能删除文件夹" in action["reason"]
        with pytest.raises(store.Refused, match="不能删除文件夹"):
            take(p, conn, f, path=folder.relative_to(p.root).as_posix())
    assert f.exists()


def test_metadata_is_readonly_and_tracks_central_governance_alias(case):
    p, conn, _ = case
    f = p.root / "治理" / "需求" / "文献.md"
    f.parent.mkdir(parents=True)
    f.write_text("需求原文", encoding="utf-8")
    old = p.materials / "文献" / "需求.md"
    resolved = files.resolve(p, "文献", "需求.md")
    version = store.version(conn)
    out = file_actions.preview_file(p, resolved, "需求.md", original=old)
    assert out["text"] == "需求原文" and out["path"] == "需求.md"
    assert out["delete_action"]["path"] == "治理/需求/文献.md" and out["delete_action"]["allowed"]
    assert not old.exists() and not (p.root / "回收站").exists() and not journal.read(p)
    assert store.version(conn) == version


def test_file_change_during_preview_disables_delete(case, monkeypatch):
    p, conn, f = case
    real = files.preview_path
    def changed(target, rel):
        out = real(target, rel)
        f.write_text("网页读取时另一个人已经修改", encoding="utf-8")
        return out
    monkeypatch.setattr(files, "preview_path", changed)
    out = file_actions.preview_file(p, f, "旧稿.md")
    assert out["delete_action"]["allowed"] is False and "读取期间" in out["delete_action"]["reason"]
    assert not out["delete_action"]["revision"] and not trash.read(p)


def test_same_size_change_during_preview_with_restored_mtime_disables_delete(case, monkeypatch):
    p, conn, f = case
    real = files.preview_path
    def changed(target, rel):
        out = real(target, rel)
        before, after = _rewrite_same_size_in_place(f, "这是新稿\n")
        if os.name == "nt":
            assert file_actions._stamp(before) == file_actions._stamp(after)
        return out
    monkeypatch.setattr(files, "preview_path", changed)
    out = file_actions.preview_file(p, f, "旧稿.md")
    assert out["text"] == "这是原稿" + os.linesep and f.read_text(encoding="utf-8") == "这是新稿\n"
    assert not out["delete_action"]["allowed"] and not out["delete_action"]["revision"]
    assert "读取期间" in out["delete_action"]["reason"] and not trash.read(p) and not journal.read(p)


def _link(link, target, *, junction=False):
    if junction:
        if os.name != "nt":
            pytest.skip("Windows目录联接专用测试")
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as exc:
            pytest.skip("本机未授予符号链接权限：" + str(exc))


@pytest.mark.parametrize("junction", [False, True])
def test_linked_source_directory_refused_even_if_resolved_inside(case, junction):
    p, conn, f = case
    link = p.materials / "快捷"
    _link(link, f.parent, junction=junction)
    original = link / f.name
    try:
        out = file_actions.preview_file(p, original.resolve(), f.name, original=original)
        assert out["delete_action"]["allowed"] is False and "联接" in out["delete_action"]["reason"]
        with pytest.raises(store.Refused, match="联接"):
            take(p, conn, f, path=original.relative_to(p.root).as_posix())
        assert f.exists() and not trash.read(p)
    finally:
        os.rmdir(link) if junction else link.unlink()


@pytest.mark.parametrize("junction", [False, True])
def test_linked_trash_output_refused_without_external_change(case, tmp_path, junction):
    p, conn, f = case
    outside = tmp_path / "外部垃圾箱"
    outside.mkdir()
    link = p.root / "回收站"
    _link(link, outside, junction=junction)
    try:
        with pytest.raises(store.Refused, match="联接"):
            take(p, conn, f)
        assert f.exists() and list(outside.iterdir()) == [] and not journal.read(p)
    finally:
        os.rmdir(link) if junction else link.unlink()


def test_log_failure_reports_move_and_preserves_readable_manifest(case, monkeypatch):
    p, conn, f = case
    def fail(*args, **kwargs):
        raise OSError("测试日志不可写")
    monkeypatch.setattr(journal, "add", fail)
    r = take(p, conn, f)
    assert not f.exists() and r["status"] == "在回收站" and "warning" in r and r["log_id"] is None
    assert trash.read(p)[0]["fields"]["原来在"] == "资料/文献/旧稿.md"
    trash.restore(conn, p, r["code"], by="人")
    assert f.exists()


def test_reason_is_clean_and_bounded(case):
    p, conn, f = case
    with pytest.raises(store.Refused, match="原因"):
        take(p, conn, f, reason=" " * 3)
    with pytest.raises(store.Refused, match="原因"):
        take(p, conn, f, reason="a" * 2001)
    r = take(p, conn, f, reason=" 第一行\n第二行 ")
    assert trash.read(p)[0]["fields"]["为什么"] == "第一行 / 第二行"


def test_record_remains_readable_without_index(case):
    p, conn, f = case
    r = take(p, conn, f)
    # 只读正本函数不接数据库连接。
    assert trash.read(p)[0]["code"] == r["code"] and journal.read(p)[0]["id"] == r["log_id"]


def test_orphan_box_file_is_not_overwritten(case):
    p, conn, f = case
    destination = p.root / "回收站" / f"{datetime.now():%Y-%m-%d %H%M} X1" / f.relative_to(p.root)
    destination.parent.mkdir(parents=True)
    destination.write_text("异常中断前留下的原文", encoding="utf-8")
    with pytest.raises(store.Refused, match="已经有文件"):
        take(p, conn, f)
    assert f.exists() and destination.read_text(encoding="utf-8") == "异常中断前留下的原文" and not trash.read(p)


def test_changed_immediately_before_move_refused(case, monkeypatch):
    p, conn, f = case
    real = file_actions._outputs
    def changing(conn, p, rel):
        real(conn, p, rel)
        f.write_text("复核前刚收到的新内容", encoding="utf-8")
    monkeypatch.setattr(file_actions, "_outputs", changing)
    with pytest.raises(store.Refused, match="刚刚发生变化"):
        take(p, conn, f)
    assert f.read_text(encoding="utf-8") == "复核前刚收到的新内容" and not trash.read(p)


@pytest.mark.parametrize("junction", [False, True])
def test_linked_log_output_refused_before_move(case, tmp_path, junction):
    p, conn, f = case
    outside = tmp_path / "外部日志"
    outside.mkdir()
    link = p.root / "笔记" / "日志"
    link.parent.mkdir()
    _link(link, outside, junction=junction)
    try:
        with pytest.raises(store.Refused, match="联接"):
            take(p, conn, f)
        assert f.exists() and list(outside.iterdir()) == [] and not trash.read(p)
    finally:
        os.rmdir(link) if junction else link.unlink()


def test_http_preview_delete_log_and_restore_same_files(case):
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        module = client.get("/api/modules/文献/preview", params={"path": "旧稿.md"})
        full = client.get("/api/project/preview", params={"path": "资料/文献/旧稿.md"})
        assert module.status_code == full.status_code == 200
        action = module.json()["delete_action"]
        assert action == full.json()["delete_action"] and action["allowed"] and module.json()["text"] == f.read_bytes().decode("utf-8")
        assert not trash.read(p) and not journal.read(p)
        result = client.post("/api/files/trash", json={k: action[k] for k in ("path", "project", "revision")} | {"reason": "网页上选中旧稿删除"})
        assert result.status_code == 200, result.text
        data = result.json()
        item = client.get("/api/trash").json()["items"][0]
        log = client.get("/api/log").json()["entries"][-1]
        assert item["code"] == data["code"] == "X1" and item["by"] == log["by"] == "人"
        assert item["fields"]["原来在"] == "资料/文献/旧稿.md" and item["fields"]["为什么"] == "网页上选中旧稿删除"
        assert log["id"] == data["log_id"] and log["at"] and log["kind"] == "删除文件"
        assert "X1" in log["body"] and action["revision"] in log["body"]
        assert client.post("/api/trash/X1/restore", json={"confirm": False}).status_code == 200
        assert f.read_text(encoding="utf-8") == "这是原稿\n"
        assert client.get("/api/trash").json()["items"][0]["status"] == "已还原"
        assert client.get("/api/log").json()["entries"][-1]["kind"] == "从回收站还原"


def test_http_changed_or_other_root_has_no_side_effect(case):
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        action = client.get("/api/project/preview", params={"path": "资料/文献/旧稿.md"}).json()["delete_action"]
        request = {k: action[k] for k in ("path", "project", "revision")}
        wrong = client.post("/api/files/trash", json=request | {"project": request["project"] + "-另一个项目"})
        assert wrong.status_code == 400 and "项目已经切换" in wrong.text
        f.write_text("刚编辑的最新稿", encoding="utf-8")
        changed = client.post("/api/files/trash", json=request)
        assert changed.status_code == 400 and "发生变化" in changed.text
        assert f.read_text(encoding="utf-8") == "刚编辑的最新稿" and client.get("/api/trash").json()["items"] == []
        assert client.get("/api/log").json()["entries"] == []


def test_http_note_view_is_readable_but_delete_disabled(case):
    p, conn, f = case
    note = p.root / "笔记" / "总览.md"
    note.parent.mkdir(exist_ok=True)
    note.write_text("人写的笔记", encoding="utf-8")
    with TestClient(create_app(p)) as client:
        response = client.get("/api/project/preview", params={"path": "笔记/总览.md"})
        assert response.status_code == 200 and response.json()["text"] == "人写的笔记"
        a = response.json()["delete_action"]
        assert not a["allowed"] and a["reason"]
        denied = client.post("/api/files/trash", json={"path": a["path"], "project": a["project"], "revision": "1" * 64})
        assert denied.status_code == 400 and note.read_text(encoding="utf-8") == "人写的笔记"


def test_http_old_governance_path_deletes_only_current_read_version(case):
    p, conn, f = case
    central = p.root / "治理" / "需求" / "文献.md"
    central.parent.mkdir(parents=True)
    central.write_text("集中现版", encoding="utf-8")
    old = p.materials / "文献" / "需求.md"
    old.write_text("仍保留的旧原文", encoding="utf-8")
    with TestClient(create_app(p)) as client:
        got = client.get("/api/modules/文献/preview", params={"path": "需求.md"}).json()
        assert got["text"] == "集中现版" and got["delete_action"]["path"] == "治理/需求/文献.md"
        response = client.post("/api/files/trash", json={k: got["delete_action"][k] for k in ("path", "project", "revision")})
        assert response.status_code == 200 and response.json()["from"] == ["治理/需求/文献.md"]
        assert not central.exists() and old.read_text(encoding="utf-8") == "仍保留的旧原文"
        assert client.post("/api/trash/X1/restore", json={"confirm": False}).status_code == 200
        assert central.read_text(encoding="utf-8") == "集中现版"


def test_http_delete_goes_to_the_bin_and_purge_still_asks_first(case):
    """网页删文件先进回收站；彻底删要人再确认一次（10-07 起不用先定性存档：「垃圾桶的东西应该可以直接删吧？」）。"""
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        got = client.get("/api/project/preview", params={"path": "资料/文献/旧稿.md"}).json()["delete_action"]
        moved = client.post("/api/files/trash", json={k: got[k] for k in ("path", "project", "revision")}).json()
        response = client.post("/api/trash/purge", json={"codes": [moved["code"]]})
        assert response.status_code == 409 and "收不回来" in response.text
        assert (p.root / moved["to"]).read_text(encoding="utf-8") == "这是原稿\n"
        assert client.get("/api/trash").json()["items"][0]["status"] == "在回收站"
        assert client.post("/api/trash/purge", json={"codes": [moved["code"]], "confirm": True}).status_code == 200
        assert not (p.root / moved["to"]).exists()
        assert client.get("/api/trash").json()["items"][0]["status"] == "已彻底删掉"


async def _read_log_stdio(p):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Implementation
    params = StdioServerParameters(command=sys.executable,
        args=["-B", str(Path(__file__).resolve().parents[1] / "mcp_server.py"), "--project", str(p.root)],
        env={**os.environ, "RC_OFFLINE": "1", "RC_DB": str(p.db_path)})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, client_info=Implementation(name="file-delete-reader", version="0")) as session:
            await session.initialize()
            result = await session.call_tool("read_log", {"limit": 30})
            assert not result.isError
            return result.content[0].text


def test_real_stdio_agent_reads_web_delete_and_restore_records(case):
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        action = client.get("/api/project/preview", params={"path": "资料/文献/旧稿.md"}).json()["delete_action"]
        response = client.post("/api/files/trash", json={k: action[k] for k in ("path", "project", "revision")} | {"reason": "人希望agent看到这次删除"})
        assert response.status_code == 200
        moved = response.json()
        assert client.post(f"/api/trash/{moved['code']}/restore", json={"confirm": False}).status_code == 200
    text = anyio.run(_read_log_stdio, p)
    assert moved["log_id"] in text and "人 · 删除文件 · 文献" in text
    assert "X1" in text and "资料/文献/旧稿.md" in text and "人希望agent看到这次删除" in text
    assert action["revision"] in text and "从回收站还原" in text
    assert f.read_text(encoding="utf-8") == "这是原稿\n" and trash.read(p)[0]["status"] == "已还原"


@pytest.mark.parametrize("rel", ["资料/文献/解读/L1 标题/文本/笔记.md", "资料/文献/解读/L1 标题/文本/.笔记历史.md", "资料/文献/解读/L1 标题/批注.json", "资料/游戏世界/解读/L2 作者选择/文本/笔记.md"])
def test_existing_reading_notes_cannot_bypass_note_history(case, rel):
    p, conn, f = case
    note = p.root / rel
    note.parent.mkdir(parents=True)
    note.write_text("保留人的阅读记录", encoding="utf-8")
    a = file_actions.preview_action(p, note)
    assert not a["allowed"] and "原阅读页" in a["reason"]
    with pytest.raises(store.Refused, match="原阅读页"):
        take(p, conn, f, path=rel)
    assert note.read_text(encoding="utf-8") == "保留人的阅读记录" and f.exists() and not trash.read(p)


def test_two_simultaneous_web_deletes_create_one_real_item(case):
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        action = client.get("/api/project/preview", params={"path": "资料/文献/旧稿.md"}).json()["delete_action"]
        body = {k: action[k] for k in ("path", "project", "revision")}
        barrier = threading.Barrier(2)
        def delete_once():
            barrier.wait(timeout=5)
            return client.post("/api/files/trash", json=body)
        with ThreadPoolExecutor(max_workers=2) as workers:
            responses = list(workers.map(lambda _: delete_once(), range(2)))
        assert sorted(r.status_code for r in responses) == [200, 400]
        assert len(trash.read(p)) == len(journal.read(p)) == 1 and not f.exists()
        assert (p.root / trash.read(p)[0]["fields"]["放在"]).read_text(encoding="utf-8") == "这是原稿\n"


def _short_project(p):
    if os.name != "nt":
        pytest.skip("Windows 8.3根路径专用测试")
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(p.root), buffer, len(buffer))
    if not length or length >= len(buffer) or os.path.normcase(buffer.value) == os.path.normcase(str(p.root)):
        pytest.skip("当前卷没有可用的8.3项目根别名")
    return project.Project(Path(buffer.value))


def test_real_short_root_http_preview_move_and_restore(case):
    p, conn, f = case
    short = _short_project(p)
    assert short.root.resolve() == p.root.resolve() and short.root != p.root
    with TestClient(create_app(short)) as client:
        module = client.get("/api/modules/文献/preview", params={"path": "旧稿.md"})
        full = client.get("/api/project/preview", params={"path": "资料/文献/旧稿.md"})
        assert module.status_code == full.status_code == 200
        action = module.json()["delete_action"]
        assert action == full.json()["delete_action"] and action["allowed"], action
        # 身份仍取状态里的原根，与网页相同；仅文件检查使用展开后的物理根。
        state = client.get("/api/state").json()
        assert action["project"] == os.path.normcase(os.path.abspath(state["project"]["root"])).replace("\\", "/")
        response = client.post("/api/files/trash", json={k: action[k] for k in ("path", "project", "revision")})
        assert response.status_code == 200, response.text
        item = client.get("/api/trash").json()["items"][0]
        assert item["fields"]["原来在"] == "资料/文献/旧稿.md" and not f.exists()
        assert client.post("/api/trash/" + response.json()["code"] + "/restore", json={"confirm": False}).status_code == 200
        assert f.read_text(encoding="utf-8") == "这是原稿\n" and client.get("/api/trash").json()["items"][0]["status"] == "已还原"


def test_short_root_does_not_resolve_away_source_or_output_junctions(case, tmp_path):
    p, conn, f = case
    short = _short_project(p)
    link = p.materials / "快捷"
    _link(link, f.parent, junction=True)
    try:
        out = file_actions.preview_file(short, f.resolve(), f.name, original=short.materials / "快捷" / f.name)
        assert not out["delete_action"]["allowed"] and "联接" in out["delete_action"]["reason"]
        with pytest.raises(store.Refused, match="联接"):
            take(short, conn, short.materials / "文献" / f.name, path="资料/快捷/" + f.name)
    finally:
        os.rmdir(link)
    outside = tmp_path / "外部垃圾箱短根"
    outside.mkdir()
    trash_link = p.root / "回收站"
    _link(trash_link, outside, junction=True)
    try:
        with pytest.raises(store.Refused, match="联接"):
            take(short, conn, short.materials / "文献" / f.name)
        assert f.exists() and list(outside.iterdir()) == []
    finally:
        os.rmdir(trash_link)
