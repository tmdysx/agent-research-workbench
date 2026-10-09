"""移到入口（10-08）：资料/<模块>/ 里放错的普通材料挪回外部资料入口重新分拣，记下原位置、能一键放回。
网页阅读页按钮和 MCP move_to_inbox 走同一个函数；只在临时项目里验证。"""
import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import builtin
import file_actions
import intake
import journal
import project
import store
from main import create_app

REL = "资料/文献/子/旧稿.md"
BODY = "这是放错的稿\n"


@pytest.fixture
def case(tmp_path, monkeypatch):
    p = project.Project(tmp_path / "项目")
    monkeypatch.setenv("RC_DB", str(p.root / "索引" / "state.db"))
    project.ensure_skeleton(p)
    f = p.root / REL
    f.parent.mkdir(parents=True)
    f.write_text(BODY, encoding="utf-8")
    conn = store.connect(p.db_path)
    store.sync_folders(conn, p)
    yield p, conn, f
    conn.close()


def _read(p, f):
    return file_actions.preview_file(p, f, f.relative_to(p.root).as_posix())


def web(p, conn, f, **changes):
    a = _read(p, f)["inbox_action"]
    request = {"path": a["path"], "key": a["project"], "revision": a["revision"]}
    request.update(changes)
    return file_actions.move_to_inbox(conn, p, request.pop("path"), by="人", source=file_actions.WEB, **request)


def agent(p, conn, rel, reason="放错模块了，挪回去重新分"):
    return file_actions.move_to_inbox(conn, p, rel, by="agent:甲", source=file_actions.MCP, reason=reason)


def _rows(conn):
    return conn.execute("SELECT COUNT(*) FROM intake").fetchone()[0]


def _box(p):
    return p.materials / "_外部资料入口"


def test_move_to_inbox_and_put_it_back(case):
    p, conn, f = case
    out = _read(p, f)
    a = out["inbox_action"]
    assert a["applicable"] and a["allowed"] and a["revision"] == out["delete_action"]["revision"]
    assert (a["path"], a["module"], a["folder"], a["project"]) == (REL, "文献", "子", out["delete_action"]["project"])
    r = web(p, conn, f)
    assert not f.exists() and (_box(p) / "旧稿.md").read_text(encoding="utf-8") == BODY
    assert (r["from"], r["to"], r["back"], r["by"]) == (REL, "资料/_外部资料入口/旧稿.md", {"module": "文献", "folder": "子"}, "人")
    it = intake.get(conn, r["item"]["id"])
    assert it["orig"] == REL and it["status"] == "waiting" and it["created_by"] == "人"
    assert it["candidates"] == [{"module": "文献", "conf": "高", "reason": "原来在这里", "by": "原位置", "folder": "子"}]
    assert intake.origin(it) == it["candidates"][0]
    e = journal.read(p)[-1]
    assert (e["kind"], e["scope"], e["by"], e["id"]) == ("移到外部资料入口", "文献", "人", r["log_id"])
    assert REL in e["body"] and f"#{it['id']}" in e["body"] and a["revision"] in e["body"] and "放回原处" in e["body"]
    placed = intake.place(conn, p, it["id"], "文献", folder="子")
    assert f.read_text(encoding="utf-8") == BODY and not (_box(p) / "旧稿.md").exists()
    assert placed["item"]["sorted_to"] == "文献/子/旧稿.md" and intake.get(conn, it["id"])["status"] == "sorted"
    e = journal.read(p)[-1]
    assert (e["kind"], e["scope"], e["id"]) == ("放进来", "文献", placed["log_id"]) and "（放回原处）" in e["body"]


def test_module_root_file_goes_back_to_the_root(case):
    p, conn, _ = case
    g = p.materials / "文献" / "根.md"
    g.write_text("模块根上的稿", encoding="utf-8")
    r = agent(p, conn, "资料/文献/根.md")
    assert r["back"] == {"module": "文献", "folder": ""}
    assert r["item"]["candidates"] == [{"module": "文献", "conf": "高", "reason": "原来在这里", "by": "原位置"}]
    assert "文献 模块根目录" in journal.read(p)[-1]["body"]
    intake.place(conn, p, r["item"]["id"], "文献", by="agent:甲", reason="放回原处")
    assert g.read_text(encoding="utf-8") == "模块根上的稿"


def test_name_collision_gets_a_fingerprint_and_put_back_keeps_the_old_name(case):
    p, conn, f = case
    _box(p).mkdir(parents=True, exist_ok=True)
    (_box(p) / "旧稿.md").write_text("另一份同名的", encoding="utf-8")
    intake.sync(conn, p)
    r = web(p, conn, f)
    sha6 = hashlib.sha256(BODY.encode("utf-8")).hexdigest()[:6]
    assert r["to"] == f"资料/_外部资料入口/旧稿（{sha6}）.md" and (p.root / r["to"]).read_text(encoding="utf-8") == BODY
    assert (_box(p) / "旧稿.md").read_text(encoding="utf-8") == "另一份同名的"
    intake.place(conn, p, r["item"]["id"], "文献", folder="子")
    assert f.read_text(encoding="utf-8") == BODY and not (p.root / r["to"]).exists()


def test_waiting_twin_is_refused_and_nothing_changes(case):
    p, conn, f = case
    _box(p).mkdir(parents=True, exist_ok=True)
    (_box(p) / "别名.md").write_text(BODY, encoding="utf-8")
    intake.sync(conn, p)
    rows, version = _rows(conn), store.version(conn)
    with pytest.raises(store.Refused, match="一模一样的「别名.md」"):
        web(p, conn, f)
    assert f.read_text(encoding="utf-8") == BODY and _rows(conn) == rows and store.version(conn) == version
    assert journal.read(p) == [] and sorted(x.name for x in _box(p).iterdir()) == ["别名.md"]


@pytest.mark.parametrize("rel", ["笔记/总览.md", "治理/需求/文献.md", "backend/x.py", "资料/_外部资料入口/x.md", "资料/x.md"])
def test_not_applicable_outside_module_materials(case, rel):
    p, conn, _ = case
    t = p.root / rel
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text("原文", encoding="utf-8")
    a = _read(p, t)["inbox_action"]
    assert a["applicable"] is False and a["allowed"] is False and not a["revision"]
    with pytest.raises(store.Refused, match="只有 资料/<模块>/"):
        agent(p, conn, rel)
    assert t.read_text(encoding="utf-8") == "原文" and _rows(conn) == 0


@pytest.mark.parametrize("rel,why", [
    ("资料/蓝图/草图.md", "固定的治理模块"), ("资料/源代码/a.py", "固定的治理模块"),
    ("资料/戒律/x.md", "固定的治理模块"), ("资料/想法/x.md", "固定的治理模块"),
    ("资料/文献/工作台/工作台.json", "由程序管理"), ("资料/文献/历史/旧.md", "由程序管理"),
    ("资料/文献/__pycache__/x.pyc", "由程序管理"),
    ("资料/文献/解读/L1 标题/信息.json", "文献解读（解读/）"), ("资料/文献/技能/SKILL.md", "模块技能"),
    ("资料/文献/需求.md", "由程序维护"), ("资料/文献/下载清单.md", "由程序维护"),
    ("资料/文献/.隐藏.md", "隐藏"), ("资料/文献/.藏/x.md", "隐藏"),
    ("资料/文献/" + "长" * 41 + "/x.md", "不能当分拣去向"),
])
def test_program_managed_files_are_refused(case, rel, why):
    p, conn, _ = case
    t = p.root / rel
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text("保护原文", encoding="utf-8")
    a = _read(p, t)["inbox_action"]
    assert a["applicable"] and not a["allowed"] and why in a["reason"] and not a["revision"]
    token = _read(p, t)["delete_action"]["revision"] or "0" * 64        # 网页带着一个格式对的版本也挡在检查上
    for move in (lambda: agent(p, conn, rel), lambda: web(p, conn, t, revision=token)):
        with pytest.raises(store.Refused, match=why):
            move()
    assert t.read_text(encoding="utf-8") == "保护原文" and _rows(conn) == 0 and journal.read(p) == []


@pytest.mark.parametrize("marked", [REL, "资料/文献/子"])
def test_builtin_marks_must_be_removed_first(case, marked):
    p, conn, f = case
    builtin.replace_marks(p.root, [marked], builtin.read_marks(p.root)["revision"])
    a = _read(p, f)["inbox_action"]
    why = "小锁" if marked == REL else "设置 → 内置"
    assert a["applicable"] and not a["allowed"] and why in a["reason"]
    with pytest.raises(store.Refused, match=why):
        agent(p, conn, REL)
    assert f.exists() and _rows(conn) == 0
    builtin.replace_marks(p.root, [], builtin.read_marks(p.root)["revision"])
    assert _read(p, f)["inbox_action"]["allowed"]
    agent(p, conn, REL)
    assert not f.exists()


@pytest.mark.parametrize("line", [REL, "资料/文献/子"])
def test_files_held_by_a_link_are_refused(case, line):
    p, conn, f = case
    (p.materials / "论文" / ".链接.txt").write_text(line + "\n", encoding="utf-8")
    a = _read(p, f)["inbox_action"]
    assert not a["allowed"] and ".链接.txt" in a["reason"] and "「论文」" in a["reason"]
    with pytest.raises(store.Refused, match="链接"):
        agent(p, conn, REL)
    assert f.exists() and _rows(conn) == 0


def test_stale_wrong_project_or_missing_revision_refused(case):
    p, conn, f = case
    a = _read(p, f)["inbox_action"]
    with pytest.raises(store.Refused, match="项目已经切换"):
        web(p, conn, f, key=a["project"] + "-另一个")
    with pytest.raises(store.Refused, match="缺少文件阅读版本"):
        web(p, conn, f, revision=None)
    with pytest.raises(store.Refused, match="缺少文件阅读版本"):
        web(p, conn, f, revision="")
    f.write_text("刚改过的稿\n", encoding="utf-8")
    with pytest.raises(store.Refused, match="发生变化"):
        file_actions.move_to_inbox(conn, p, REL, by="人", source=file_actions.WEB, key=a["project"], revision=a["revision"])
    assert f.read_text(encoding="utf-8") == "刚改过的稿\n" and _rows(conn) == 0 and journal.read(p) == []


def test_agent_must_give_a_reason_and_is_recorded(case):
    p, conn, f = case
    for bad in ("", " \n "):
        with pytest.raises(store.Refused, match="要写为什么"):
            agent(p, conn, REL, reason=bad)
    with pytest.raises(store.Refused, match="原位置"):
        file_actions.move_to_inbox(conn, p, REL, by="原位置", source=file_actions.MCP, reason="r")
    assert f.exists() and _rows(conn) == 0
    r = agent(p, conn, REL, reason="是论文的稿子\n放错到文献了")
    assert r["by"] == "agent:甲" and r["reason"] == "是论文的稿子 / 放错到文献了" and r["item"]["created_by"] == "agent:甲"
    e = journal.read(p)[-1]
    assert e["by"] == "agent:甲" and "是论文的稿子 / 放错到文献了" in e["body"] and file_actions.MCP in e["body"]
    assert "阅读版本" not in e["body"]
    ev = conn.execute("SELECT actor, target FROM event WHERE action = '移到外部资料入口'").fetchone()
    assert (ev["actor"], ev["target"]) == ("agent:甲", f"#{r['item']['id']}")


def test_failed_move_rolls_back(case, monkeypatch):
    p, conn, f = case
    real = os.replace
    def full(src, dst):
        if "_外部资料入口" in str(dst):
            raise OSError("磁盘满了")
        return real(src, dst)
    monkeypatch.setattr(intake.os, "replace", full)
    version = store.version(conn)
    with pytest.raises(store.Refused, match="没挪成，文件还在原处"):
        agent(p, conn, REL)
    assert f.read_text(encoding="utf-8") == BODY and _rows(conn) == 0 and store.version(conn) == version
    assert journal.read(p) == []


def test_log_failure_still_moves_with_warning(case, monkeypatch):
    p, conn, f = case
    def fail(*args, **kwargs):
        raise OSError("测试日志不可写")
    monkeypatch.setattr(journal, "add", fail)
    r = web(p, conn, f)
    assert not f.exists() and r["log_id"] is None and "日志写入失败" in r["warning"]
    assert intake.get(conn, r["item"]["id"])["status"] == "waiting"


def test_suggest_keeps_the_original_place_first(case):
    p, conn, f = case
    iid = web(p, conn, f)["item"]["id"]
    it = intake.suggest(conn, iid, [{"module": "论文", "confidence": "中", "reason": "像自己的稿子"}], by="agent:乙", p=p)
    assert [(c["by"], c["module"]) for c in it["candidates"]] == [("原位置", "文献"), ("agent:乙", "论文")]
    detail = conn.execute("SELECT detail FROM event WHERE action = '给分拣建议' ORDER BY id DESC").fetchone()[0]
    assert detail == "论文（中）"
    with pytest.raises(store.Refused, match="原位置"):
        intake.suggest(conn, iid, [{"module": "论文", "confidence": "中", "reason": "x"}], by="原位置", p=p)
    placed = intake.place(conn, p, iid, "论文", by="agent:乙", reason="确实是稿子")
    assert (p.materials / "论文" / "旧稿.md").read_text(encoding="utf-8") == BODY
    e = journal.read(p)[-1]
    assert e["by"] == "agent:乙" and "把握 中" in e["body"] and "原因：确实是稿子" in e["body"] and placed["log_id"] == e["id"]


def test_http_preview_move_list_and_put_back(case):
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        module = client.get("/api/modules/文献/preview", params={"path": "子/旧稿.md"}).json()
        full = client.get("/api/project/preview", params={"path": REL}).json()
        a = module["inbox_action"]
        assert a == full["inbox_action"] and a["allowed"] and a["revision"] == module["delete_action"]["revision"]
        r = client.post("/api/files/inbox", json={k: a[k] for k in ("path", "project", "revision")})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["to"] == "资料/_外部资料入口/旧稿.md" and not f.exists()
        items = client.get("/api/inbox").json()["items"]
        assert [i["id"] for i in items] == [data["item"]["id"]] and items[0]["candidates"][0]["by"] == "原位置"
        log = client.get("/api/log").json()["entries"][-1]
        assert log["id"] == data["log_id"] and log["kind"] == "移到外部资料入口"
        back = client.post(f"/api/inbox/{data['item']['id']}/sort", json={"module": "文献", "folder": "子"})
        assert back.status_code == 200 and back.json()["items"] == []
        assert f.read_text(encoding="utf-8") == BODY
        assert "放回原处" in client.get("/api/log").json()["entries"][-1]["body"]


def test_http_refusals_are_400_without_side_effects(case):
    p, conn, f = case
    blue = p.materials / "蓝图" / "草图.md"
    blue.write_text("蓝图里的", encoding="utf-8")
    with TestClient(create_app(p)) as client:
        a = client.get("/api/project/preview", params={"path": REL}).json()["inbox_action"]
        body = {k: a[k] for k in ("path", "project", "revision")}
        for bad, why in ((body | {"revision": "1" * 64}, "发生变化"), (body | {"project": "别的项目"}, "项目已经切换"),
                         (body | {"revision": ""}, "缺少"), (body | {"path": "资料/蓝图/草图.md"}, "治理模块")):
            r = client.post("/api/files/inbox", json=bad)
            assert r.status_code == 400 and why in r.json()["detail"], r.text
        assert client.post("/api/files/inbox", json={"path": REL}).status_code == 422
        assert f.exists() and blue.exists() and client.get("/api/inbox").json()["items"] == []
        assert client.get("/api/log").json()["entries"] == []


def test_two_simultaneous_web_moves_create_one_item(case):
    p, conn, f = case
    with TestClient(create_app(p)) as client:
        a = client.get("/api/project/preview", params={"path": REL}).json()["inbox_action"]
        body = {k: a[k] for k in ("path", "project", "revision")}
        barrier = threading.Barrier(2)
        def move_once():
            barrier.wait(timeout=5)
            return client.post("/api/files/inbox", json=body)
        with ThreadPoolExecutor(max_workers=2) as workers:
            responses = list(workers.map(lambda _: move_once(), range(2)))
        assert sorted(r.status_code for r in responses) == [200, 400]
    assert _rows(conn) == 1 and len([e for e in journal.read(p) if e["kind"] == "移到外部资料入口"]) == 1
    assert (_box(p) / "旧稿.md").read_text(encoding="utf-8") == BODY and not f.exists()


def _symlink(link, target):
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as exc:
        pytest.skip("本机未授予符号链接权限：" + str(exc))


def test_symlinked_source_is_refused(case):
    p, conn, f = case
    link = p.materials / "文献" / "快捷"
    _symlink(link, f.parent)
    original = link / f.name
    out = file_actions.preview_file(p, original.resolve(), "快捷/旧稿.md", original=original)
    assert not out["inbox_action"]["allowed"]
    with pytest.raises(store.Refused, match="联接"):
        agent(p, conn, "资料/文献/快捷/旧稿.md")
    assert f.read_text(encoding="utf-8") == BODY and _rows(conn) == 0


def test_symlinked_intake_folder_is_refused_and_nothing_lands_outside(case, tmp_path):
    p, conn, f = case
    outside = tmp_path / "项目外"
    outside.mkdir()
    _symlink(_box(p), outside)
    with pytest.raises(store.Refused, match="联接"):
        agent(p, conn, REL)
    assert f.read_text(encoding="utf-8") == BODY and list(outside.iterdir()) == [] and _rows(conn) == 0
    assert journal.read(p) == []


def test_real_short_root_move_and_put_back(case):
    p, conn, f = case
    if os.name != "nt":
        pytest.skip("Windows 8.3根路径专用测试")
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(p.root), buffer, len(buffer))
    if not length or length >= len(buffer) or os.path.normcase(buffer.value) == os.path.normcase(str(p.root)):
        pytest.skip("当前卷没有可用的8.3项目根别名")
    short = project.Project(Path(buffer.value))
    with TestClient(create_app(short)) as client:
        a = client.get("/api/modules/文献/preview", params={"path": "子/旧稿.md"}).json()["inbox_action"]
        assert a["allowed"], a
        r = client.post("/api/files/inbox", json={k: a[k] for k in ("path", "project", "revision")})
        assert r.status_code == 200, r.text
        assert client.post(f"/api/inbox/{r.json()['item']['id']}/sort", json={"module": "文献", "folder": "子"}).status_code == 200
    assert f.read_text(encoding="utf-8") == BODY


def test_hidden_file_reason_is_its_own(case):
    p, conn, _ = case
    t = p.materials / "文献" / ".隐藏.md"
    t.write_text("藏着的", encoding="utf-8")
    assert _read(p, t)["inbox_action"]["reason"] == "点开头的隐藏文件和文件夹不移到入口"
    with pytest.raises(store.Refused) as e:
        agent(p, conn, "资料/文献/.隐藏.md")
    assert str(e.value) == "点开头的隐藏文件和文件夹不移到入口" and t.exists() and _rows(conn) == 0


def test_dangling_symlink_in_the_intake_is_not_overwritten(case):
    p, conn, f = case
    _box(p).mkdir(parents=True, exist_ok=True)
    _symlink(_box(p) / "旧稿.md", p.root / "不存在的目标.md")
    r = agent(p, conn, REL)
    sha6 = hashlib.sha256(BODY.encode("utf-8")).hexdigest()[:6]
    assert r["to"] == f"资料/_外部资料入口/旧稿（{sha6}）.md" and (p.root / r["to"]).read_text(encoding="utf-8") == BODY
    assert (_box(p) / "旧稿.md").is_symlink() and not (p.root / "不存在的目标.md").exists()


def test_file_changed_between_first_read_and_recheck(case, monkeypatch):
    p, conn, f = case
    real, seen = file_actions._content, []
    def drifting(*args):
        seen.append(1)
        return real(*args) if len(seen) == 1 else "0" * 64          # 复查时读出来的跟第一次不一样
    monkeypatch.setattr(file_actions, "_content", drifting)
    with pytest.raises(store.Refused, match="刚刚发生变化"):
        agent(p, conn, REL)
    assert len(seen) == 2 and f.read_text(encoding="utf-8") == BODY and _rows(conn) == 0 and journal.read(p) == []


def test_module_folder_without_a_database_row_is_refused(case, monkeypatch):
    p, conn, _ = case
    t = p.materials / "新来的" / "x.md"
    t.parent.mkdir()
    t.write_text("还没登记的模块", encoding="utf-8")
    monkeypatch.setattr(file_actions.store, "sync_folders", lambda *a, **k: None)    # 库里还没这个模块
    with pytest.raises(store.Refused, match="「新来的」不是模块文件夹"):
        agent(p, conn, "资料/新来的/x.md")
    assert t.exists() and _rows(conn) == 0


@pytest.mark.parametrize("where", ["_content", "_linked_by"])
def test_os_errors_before_the_move_are_refusals(case, monkeypatch, where):
    p, conn, f = case
    def busy(*args, **kwargs):
        raise PermissionError(13, "文件被别的程序占着")
    monkeypatch.setattr(file_actions, where, busy)
    with pytest.raises(store.Refused, match="没挪成，文件还在原处"):
        agent(p, conn, REL)
    assert f.read_text(encoding="utf-8") == BODY and _rows(conn) == 0


def test_failed_commit_puts_the_file_back_where_it_was(case, monkeypatch):
    """os.replace 成了、事务提交没成：文件挪回原处，入口里没有、库里也没有。"""
    import contextlib
    import sqlite3
    p, conn, f = case
    real_tx, moved = store.tx, []
    real_replace = os.replace
    def replace(src, dst):
        real_replace(src, dst)
        moved.append(dst)
    @contextlib.contextmanager
    def failing_tx(c):
        with real_tx(c):
            yield c
            if moved:
                raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(intake.os, "replace", replace)
    monkeypatch.setattr(intake.store, "tx", failing_tx)
    with pytest.raises(sqlite3.OperationalError):
        agent(p, conn, REL)
    monkeypatch.setattr(intake.store, "tx", real_tx)
    assert moved and f.read_text(encoding="utf-8") == BODY and not (_box(p) / "旧稿.md").exists() and _rows(conn) == 0


def test_canonical_rel_uses_the_names_on_disk(case, monkeypatch):
    p, conn, f = case
    g = p.materials / "文献" / "Sub" / "Old.md"
    g.parent.mkdir()
    g.write_text("大小写", encoding="utf-8")
    assert file_actions._canonical(p, "资料/文献/sub/old.md") == "资料/文献/sub/old.md"    # 分大小写的磁盘上：那是另一个（不存在的）文件
    monkeypatch.setattr(intake, "CASELESS", True)
    assert file_actions._canonical(p, "资料/文献/sub/old.md") == "资料/文献/Sub/Old.md"
    assert file_actions._canonical(p, "资料/文献/Sub/Old.md") == "资料/文献/Sub/Old.md"
    assert file_actions._canonical(p, REL) == REL
    assert file_actions._canonical(p, "资料/文献/没有/x.md") == "资料/文献/没有/x.md"     # 找不到：原样，后面的检查会拒
    (p.materials / "文献" / "Sub" / "OLD.md").write_text("另一份", encoding="utf-8")
    assert file_actions._canonical(p, "资料/文献/Sub/old.md") == "资料/文献/Sub/old.md"    # 对上不止一个：原样


def test_windows_case_rules_for_program_folders(case, monkeypatch):
    """Windows 上 VENV/、Node_Modules/ 也是缓存，需求.MD 也是需求；记原路径、起入口名用磁盘上的真名。"""
    p, conn, _ = case
    monkeypatch.setattr(intake, "CASELESS", True)
    for rel in ("资料/文献/VENV/x.md", "资料/文献/Node_Modules/x.md", "资料/文献/需求.MD"):
        t = p.root / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text("程序管的", encoding="utf-8")
        with pytest.raises(store.Refused, match="由程序管理|由程序维护"):
            agent(p, conn, rel)
        assert t.exists()
    g = p.materials / "文献" / "Sub" / "Old.md"
    g.parent.mkdir()
    g.write_text("大小写", encoding="utf-8")
    r = agent(p, conn, "资料/文献/sub/old.md")
    assert r["from"] == "资料/文献/Sub/Old.md" and r["to"] == "资料/_外部资料入口/Old.md"
    assert r["item"]["orig"] == "资料/文献/Sub/Old.md" and r["back"] == {"module": "文献", "folder": "Sub"}


def test_move_wording_does_not_mention_the_recycle_bin():
    assert file_actions._as_move("这个文件在项目外，不能从网页移入本项目回收站") == "这个文件在项目外，不能从网页移动"
    assert file_actions._as_move("这里只能删除单个文件") == "这里只能移动单个文件"


def test_links_are_read_once_without_resolving_each_line(case, monkeypatch):
    p, conn, f = case
    (p.materials / "论文" / ".链接.txt").write_text("# 注释\n资料/文献/别的.md\n资料\\文献\\子  # 整个文件夹\n", encoding="utf-8")
    def no(*a, **k):
        raise AssertionError("不该逐行解析链接")
    monkeypatch.setattr(project, "read_links", no)
    assert file_actions._linked_by(p, REL) == ("论文", "资料/文献/子")
    assert file_actions._linked_by(p, "资料/文献/子二/x.md") is None


def test_http_sort_reports_a_log_failure(case, monkeypatch):
    p, conn, f = case
    iid = agent(p, conn, REL)["item"]["id"]
    def fail(*args, **kwargs):
        raise OSError("测试日志不可写")
    with TestClient(create_app(p)) as client:
        monkeypatch.setattr(journal, "add", fail)
        r = client.post(f"/api/inbox/{iid}/sort", json={"module": "文献", "folder": "子"})
        assert r.status_code == 200 and r.json() == {"items": [], "warning": "已经放进去了，日志写入失败"}
    assert f.read_text(encoding="utf-8") == BODY


@pytest.mark.parametrize("line", ["./" + REL, REL.replace("/", "//", 1), "资料/文献/./子/旧稿.md", "./资料/文献/子/"])
def test_links_written_differently_are_still_recognised(case, line):
    """.链接.txt 里写成 ./资料/…、资料//…、资料/./… 的，读的时候都认得：挪走一样会断链，照样拒。"""
    p, conn, f = case
    (p.materials / "论文" / ".链接.txt").write_text(line + "\n", encoding="utf-8")
    assert not _read(p, f)["inbox_action"]["allowed"]
    with pytest.raises(store.Refused, match="链接"):
        agent(p, conn, REL)
    assert f.exists() and _rows(conn) == 0


@pytest.mark.parametrize("rel", ["资料/文献/解读/随手记.md", "资料/文献/解读/草稿/x.md"])
def test_everything_under_reading_records_stays_put_both_ways(case, rel):
    """解读/ 下的文件都不移到入口；agent 也分拣不进 解读/——两头说法一致。"""
    p, conn, f = case
    g = p.root / rel
    g.parent.mkdir(parents=True, exist_ok=True)
    g.write_text("解读里的", encoding="utf-8")
    assert "文献解读（解读/）" in _read(p, g)["inbox_action"]["reason"]
    with pytest.raises(store.Refused, match=r"文献解读（解读/）"):
        agent(p, conn, rel)
    iid = agent(p, conn, REL)["item"]["id"]
    with pytest.raises(store.Refused, match="agent 不能直接分拣"):
        intake.place(conn, p, iid, "文献", folder="解读", by="agent:甲", reason="想放进解读")
    assert intake.get(conn, iid)["status"] == "waiting" and g.exists()


def test_linked_folders_are_never_a_destination(case):
    """资料/论文/做法 其实链到 资料/论文/技能：agent 写「做法」也分拣不进去（人点也不行，链接文件夹看不出指去哪）。"""
    p, conn, f = case
    (p.materials / "论文" / "技能").mkdir()
    _symlink(p.materials / "论文" / "做法", p.materials / "论文" / "技能")
    iid = agent(p, conn, REL)["item"]["id"]
    for by in ("agent:甲", "人"):
        with pytest.raises(store.Refused, match="链接文件夹"):
            intake.place(conn, p, iid, "论文", folder="做法", by=by, reason="试一下")
    assert intake.get(conn, iid)["status"] == "waiting" and (_box(p) / "旧稿.md").exists()
    assert not any((p.materials / "论文" / "技能").iterdir())


def test_sorting_errors_from_the_disk_are_refusals(case, monkeypatch):
    """分拣时文件被别的程序占着（Windows 常见）：agent 收到「没放：…」，网页收到 400，文件还在入口。"""
    import mcp_server
    p, conn, f = case
    iid = agent(p, conn, REL)["item"]["id"]
    def locked(src, dst):
        raise PermissionError("被别的程序占着")
    monkeypatch.setattr(intake.os, "replace", locked)
    with pytest.raises(store.Refused, match="没放成，文件还在入口：.*被别的程序占着"):
        intake.place(conn, p, iid, "论文", by="agent:甲", reason="是稿子")
    with TestClient(create_app(p)) as client:
        r = client.post(f"/api/inbox/{iid}/sort", json={"module": "论文", "folder": ""})
        assert r.status_code == 400 and "没放成" in r.json()["detail"]
    assert intake.get(conn, iid)["status"] == "waiting" and (_box(p) / "旧稿.md").read_text(encoding="utf-8") == BODY


def test_failed_commit_never_overwrites_a_file_that_came_back(case, monkeypatch):
    """挪成了、提交没成，可原处这时又有了文件：不挪回去盖掉它，挪走的那份留在入口（下回对账会登记）。"""
    import contextlib
    import sqlite3
    p, conn, f = case
    real_tx, moved = store.tx, []
    real_replace = os.replace
    def replace(src, dst):
        real_replace(src, dst)
        moved.append(dst)
    @contextlib.contextmanager
    def failing_tx(c):
        with real_tx(c):
            yield c
            if moved:
                f.write_text("刚又写回来的\n", encoding="utf-8")
                raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(intake.os, "replace", replace)
    monkeypatch.setattr(intake.store, "tx", failing_tx)
    with pytest.raises(sqlite3.OperationalError):
        agent(p, conn, REL)
    monkeypatch.setattr(intake.store, "tx", real_tx)
    assert f.read_text(encoding="utf-8") == "刚又写回来的\n"
    assert (_box(p) / "旧稿.md").read_text(encoding="utf-8") == BODY and _rows(conn) == 0


def test_agent_sorting_is_checked_against_the_real_folder_name(case, monkeypatch):
    """Windows 上「6B8A~1」这类短文件名其实就是 技能/：按磁盘真名再看一遍，agent 照样分拣不进去。"""
    p, conn, f = case
    (p.materials / "论文" / "技能").mkdir()
    base = p.materials / "论文"
    assert intake._real_folder(p, "论文", base / "技能" / "新" / "深") == "技能/新/深"   # 已有的按真名，没建的照写的
    assert intake._real_folder(p, "论文", base) == ""
    iid = agent(p, conn, REL)["item"]["id"]
    monkeypatch.setattr(intake, "_real_folder", lambda p_, m, d: "技能" if d.name == "别名" else intake.os.path.basename(d))
    with pytest.raises(store.Refused, match="agent 不能直接分拣"):
        intake.place(conn, p, iid, "论文", folder="别名", by="agent:甲", reason="短文件名")
    assert intake.get(conn, iid)["status"] == "waiting" and not (base / "别名").exists()   # 查完才建文件夹：拒了就什么都不建
