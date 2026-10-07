"""手工工具卡只写临时项目；覆盖安全、项目隔离与真实跨进程编号。"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest

import tools


@pytest.fixture
def lib(tmp_path):
    return tmp_path / "一个普通项目" / "工具库"


def test_manual_card_is_plain_file_and_does_not_run_install_or_commands(lib, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("保存手工工具不能查程序、执行命令或安装")

    monkeypatch.setattr(tools.subprocess, "run", forbidden)
    monkeypatch.setattr(tools, "find_exe", forbidden)
    card = tools.create("示例编辑器", one_line="编辑项目文件", url="https://example.org/editor",
                        install="下载安装包\n```sh\nnever-run-this --install\n```",
                        how="打开已有文件；内容 <script>也只保存</script>", by="人", lib=lib)
    assert card["code"] == "T1" and card["name"] == "示例编辑器"
    assert card["manual"] is True and card["source"] == "手工添加" and card["by"] == "人"
    assert card["url"] == "https://example.org/editor" and card["check"] == ""
    assert card["state"] == "未检查" and datetime.fromisoformat(card["created_at"])
    assert "never-run-this --install" in card["body"] and "<script>也只保存</script>" in card["body"]
    assert (lib / card["file"]).is_file() and tools.list_tools(lib) == [card]
    assert tools.check(card["code"], lib) == {"ok": None, "msg": "未检查"}


def test_minimal_manual_card_remains_unknown_and_cannot_be_marked_installed(lib):
    card = tools.create("示例工具", one_line="记录用途", lib=lib)
    assert card["kind"] == "外部工具" and card["url"] == ""
    assert card["body"].count("（未填写）") == 3
    original = (lib / card["file"]).read_bytes()
    for state in ("", "装好了", "已安装", "可用"):
        with pytest.raises(ValueError, match="不能标为装好了"):
            tools.set_state(card["code"], state, lib)
        assert (lib / card["file"]).read_bytes() == original
    tools.set_state(card["code"], "未检查", lib)
    assert tools.list_tools(lib)[0]["state"] == "未检查"
    with pytest.raises(TypeError):
        tools.create("拒绝检查命令", one_line="示例", lib=lib, check_cmd="never-run-this")


@pytest.mark.parametrize("field,value", [
    ("name", ""), ("name", "   "), ("name", "x" * 41), ("name", "../越界"),
    ("name", "C:\\越界"), ("name", "子目录/文件"), ("name", "<标签>"),
    ("name", "名字\n检查: never-run-this"), ("name", "坏\x00名字"),
    ("one_line", ""), ("one_line", "x" * 201), ("one_line", "说明\n检查: never-run-this"),
    ("one_line", "说明\u0085检查: never-run-this"), ("one_line", "说明\u2028检查: never-run-this"),
    ("name", "名字\u2029检查: never-run-this"), ("by", "人\u2028检查: never-run-this"),
    ("kind", "网页链接"), ("url", "javascript:alert(1)"), ("url", "file:///C:/private"),
    ("url", "data:text/html,hello"), ("url", "ftp://example.org/file"), ("url", "https:///path"),
    ("url", "https://user:password@example.org/"), ("url", "https://@example.org/"),
    ("url", "https://example.org/\n坏"), ("url", "https://example.org/with space"),
    ("url", "https://example.org:broken/"), ("url", "https://example.org/" + "x" * 2048),
    ("url", 'https://example.org/<script>'), ("url", 'https://example.org/"bad'),
    ("install", "x" * 20001), ("how", "x" * 20001), ("install", "坏\x00内容"),
    ("how", "坏\x1b内容"), ("by", "人\n来源: agent"),
])
def test_invalid_manual_fields_are_rejected_before_any_file_is_created(lib, field, value):
    fields = {"name": "示例工具", "one_line": "记录用途", "lib": lib, field: value}
    with pytest.raises(ValueError):
        tools.create(**fields)
    assert not lib.exists()


def test_lengths_http_url_and_multiline_text_at_allowed_boundaries(lib):
    card = tools.create("名" * 40, one_line="用" * 200, kind="技术栈", url="http://localhost:8770/guide",
                        install="a" * 19998 + "\r\n", how="b" * 20000, lib=lib)
    assert card["kind"] == "技术栈" and card["url"] == "http://localhost:8770/guide"
    assert "b" * 20000 in card["body"]
    with pytest.raises(TypeError):
        tools.create("缺项目", one_line="示例")
    with pytest.raises(ValueError, match="明确工具库"):
        tools.create("缺项目", one_line="示例", lib=None)


def test_duplicate_carries_original_card_and_both_creators_keep_legacy_behavior(lib):
    original = tools.create("Shared Tool", one_line="原用途", lib=lib)
    saved = (lib / original["file"]).read_bytes()
    with pytest.raises(tools.Duplicate) as exc:
        tools.create("shared tool", one_line="不得覆盖", lib=lib)
    assert exc.value.card == original
    with pytest.raises(ValueError, match="已经有这张卡"):
        tools.propose("SHARED TOOL", one_line="不得覆盖", why="示例", install="手工安装", lib=lib)
    assert (lib / original["file"]).read_bytes() == saved
    proposed = tools.propose("另一工具", one_line="旧流程", why="记录需求", install="手工下载安装",
                             kind="技术栈", by="agent:test", lib=lib)
    assert set(proposed) == {"code", "name", "file"} and proposed["code"] == "T2"
    old_card = tools.list_tools(lib)[1]
    assert not old_card["manual"] and old_card["state"] == "待你装"
    assert "## 为什么要" in old_card["body"] and "## 怎么装（你来装）" in old_card["body"]
    assert tools.check("T2", lib) == {"ok": None, "msg": "不用装（内置）"}
    tools.set_state("T2", "", lib)
    assert tools.list_tools(lib)[1]["state"] == ""


def test_numbering_preserves_old_cards_even_with_non_card_files(lib):
    lib.mkdir(parents=True)
    old_file = lib / "T9 留下的原文件.md"
    old_file.write_text("原有内容", encoding="utf-8")
    # The filename reserves T9 even if its frontmatter has another old identifier.
    old_file.write_text("---\n编号: T3\n名字: 旧卡\n检查:\n---\n原有内容", encoding="utf-8")
    saved = old_file.read_bytes()
    card = tools.create("新工具", one_line="记录用途", lib=lib)
    assert card["code"] == "T10" and old_file.read_bytes() == saved


def test_only_complete_cards_are_published_and_publish_is_exclusive(lib, monkeypatch):
    real_link = tools.os.link
    existing = "---\n编号: T1\n名字: Concurrent\n检查:\n---\n完整旧内容\n"
    observed = []

    def competing_writer(draft, target):
        # A reader must see no partial T-card while its complete draft is still being prepared.
        observed.append(tools.list_tools(lib))
        assert "来源: 手工添加" in draft.read_text(encoding="utf-8")
        if target.name.startswith("T1 "):
            target.write_text(existing, encoding="utf-8")
        real_link(draft, target)

    monkeypatch.setattr(tools.os, "link", competing_writer)
    card = tools.create("新卡", one_line="不覆盖已有文件", lib=lib)
    assert card["code"] == "T2" and card["body"].startswith("# T2 新卡")
    assert observed[0] == [] and len(observed[1]) == 1
    assert (lib / "T1 新卡.md").read_text(encoding="utf-8") == existing
    assert not list(lib.glob("*.tmp"))


def test_failed_publication_does_not_leave_a_false_tool_card(lib, monkeypatch):
    def fail(*args):
        raise OSError("测试文件系统拒绝写入")

    monkeypatch.setattr(tools.os, "link", fail)
    with pytest.raises(OSError, match="拒绝写入"):
        tools.create("未保存的卡", one_line="不留下半张卡", lib=lib)
    assert tools.list_tools(lib) == [] and not list(lib.glob("*.tmp"))


def test_project_cache_and_invalidation_do_not_mix_same_number(tmp_path, monkeypatch):
    first, second = tmp_path / "first" / "工具库", tmp_path / "second" / "工具库"
    tools.create("第一个项目", one_line="A", lib=first)
    tools.create("第二个项目", one_line="B", lib=second)
    calls = []

    def checking(code, lib=None):
        calls.append((code, lib))
        return {"ok": None, "msg": tools.list_tools(lib)[0]["name"]}

    monkeypatch.setattr(tools, "_check", checking)
    tools.forget()
    assert tools.check_cached("T1", lib=first)["msg"] == "第一个项目"
    assert tools.check_cached("T1", lib=second)["msg"] == "第二个项目"
    assert len(calls) == 2
    monkeypatch.setattr(tools, "LIB", first)
    assert tools.check_cached("T1")["msg"] == "第一个项目" and len(calls) == 2
    assert tools.check_cached("T1", lib=first)["msg"] == "第一个项目" and len(calls) == 2
    tools.forget("T1", first)
    tools.check_cached("T1", lib=second)
    assert len(calls) == 2
    tools.check_cached("T1", lib=first)
    assert len(calls) == 3
    tools.forget()


def test_file_checks_use_the_explicit_project_and_default_calls_remain_compatible(tmp_path, monkeypatch):
    lib = tmp_path / "project" / "工具库"
    lib.mkdir(parents=True)
    (lib / "T1 文件.md").write_text("---\n编号: T1\n名字: 文件\n检查: 文件 needed.txt\n---\n", encoding="utf-8")
    (lib.parent / "needed.txt").write_text("本项目", encoding="utf-8")
    monkeypatch.setattr(tools, "LIB", lib)
    monkeypatch.setattr(tools, "CODE_DIR", tmp_path / "other-core")
    assert tools.check("T1", lib)["ok"] is True
    assert tools.check("T1")["ok"] is False


def test_api_create_read_check_and_installed_are_isolated_between_projects(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from main import create_app
    from project import Project

    first = Project(tmp_path / "项目甲")
    second = Project(tmp_path / "项目乙")
    unrelated = tmp_path / "不是当前项目" / "工具库"
    default_card = tools.create("别的项目工具", one_line="不能漏到当前项目", lib=unrelated)
    original = (unrelated / default_card["file"]).read_bytes()
    monkeypatch.setattr(tools, "LIB", unrelated)

    def forbidden(*args, **kwargs):
        raise AssertionError("手工工具 API 不能启动程序或安装")

    monkeypatch.setattr(tools, "find_exe", forbidden)
    monkeypatch.setattr(tools.subprocess, "run", forbidden)
    monkeypatch.setattr(tools.subprocess, "Popen", forbidden)
    tools.forget()
    with TestClient(create_app(first)) as a, TestClient(create_app(second)) as b:
        assert a.get("/api/tools").json()["items"] == b.get("/api/tools").json()["items"] == []
        response = a.post("/api/tools", json={"name": "甲工具", "one_line": "甲项目用途",
                                              "url": "https://example.org/alpha", "install": "never-run-this --install"})
        assert response.status_code == 201
        alpha = response.json()
        assert alpha["code"] == "T1" and alpha["manual"] is True and alpha["by"] == "人"
        assert alpha["source"] == "手工添加" and alpha["url"] == "https://example.org/alpha"
        assert alpha["created_at"] and "never-run-this --install" in alpha["body"]
        assert a.get("/api/tools").json()["items"] == [alpha]
        assert b.get("/api/tools").json()["items"] == []
        beta_response = b.post("/api/tools", json={"name": "乙工具", "one_line": "乙项目用途", "kind": "技术栈"})
        assert beta_response.status_code == 201
        beta = beta_response.json()
        assert beta["code"] == "T1" and beta["name"] == "乙工具"
        assert a.get("/api/tools").json()["items"] == [alpha]
        assert b.get("/api/tools").json()["items"] == [beta]
        for client, card, project in ((a, alpha, first), (b, beta, second)):
            f = project.root / "工具库" / card["file"]
            saved = f.read_bytes()
            checked = client.post("/api/tools/T1/check")
            assert checked.status_code == 200 and checked.json() == {"ok": None, "msg": "未检查"}
            refused = client.post("/api/tools/T1/installed")
            assert refused.status_code == 400 and "不能标记装好了" in refused.json()["detail"]
            assert f.read_bytes() == saved
            assert client.post("/api/tools/T99/check").status_code == 404
            assert tools.list_tools(project.root / "工具库") == [card]
        duplicate = a.post("/api/tools", json={"name": "甲工具", "one_line": "不能覆盖"})
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["existing"] == alpha
        assert a.get("/api/tools").json()["items"] == [alpha]
        entries = a.get("/api/log").json()["entries"]
        assert sum(item["kind"] == "手工添加工具" for item in entries) == 1
    # A new client reads the same plain record; the default library remains byte-for-byte unchanged.
    with TestClient(create_app(first)) as refreshed:
        assert refreshed.get("/api/tools").json()["items"] == [alpha]
    assert (unrelated / default_card["file"]).read_bytes() == original


@pytest.mark.parametrize("payload,status", [
    ({"name": "../越界", "one_line": "用途"}, 400),
    ({"name": "示例", "one_line": ""}, 400),
    ({"name": "示例", "one_line": "用途", "url": "javascript:alert(1)"}, 400),
    ({"name": "示例", "one_line": "用途", "url": "https://user:pass@example.org/"}, 400),
    ({"name": "示例", "one_line": "用途", "kind": "非法分类"}, 400),
    ({"name": "示例", "one_line": "用途\u2028检查: never-run-this"}, 400),
    ({"name": "示例", "one_line": "用途", "check": "never-run-this"}, 422),
    ({"name": "示例", "one_line": "用途", "by": "agent:自己冒充人"}, 422),
    ({"name": "示例", "one_line": "用途", "lib": "C:/outside"}, 422),
    ({"name": "示例"}, 422),
    ({"name": None, "one_line": "用途"}, 422),
])
def test_api_invalid_or_extra_fields_do_not_write_cards(tmp_path, monkeypatch, payload, status):
    from fastapi.testclient import TestClient
    from main import create_app
    from project import Project

    def forbidden(*args, **kwargs):
        raise AssertionError("错误输入不能执行程序")

    monkeypatch.setattr(tools.subprocess, "run", forbidden)
    project = Project(tmp_path / "手工接口校验")
    with TestClient(create_app(project)) as client:
        response = client.post("/api/tools", json=payload)
        assert response.status_code == status, response.text
        assert client.get("/api/tools").json()["items"] == []
    assert not (project.root / "工具库").exists()


_WORKER = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import tools
lib=Path(sys.argv[2]); name=sys.argv[3]
try:
    if sys.argv[4] == 'manual':
        card=tools.create(name, one_line='temporary process fixture', lib=lib)
    else:
        card=tools.propose(name, one_line='temporary process fixture', why='regression test', install='manual only', lib=lib)
    print(json.dumps({'created': True, 'code': card['code'], 'name': card['name']}))
except tools.Duplicate as err:
    print(json.dumps({'created': False, 'code': err.card['code'], 'name': err.card['name']}))
'''


def _run_worker(lib, name, mode):
    result = subprocess.run([sys.executable, "-c", _WORKER, str(Path(tools.__file__).parent), str(lib), name, mode],
                            capture_output=True, text=True, timeout=30,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_real_processes_share_manual_and_propose_numbering_without_overwrites(lib):
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(_run_worker, lib, f"Process-{n}", "manual" if n % 2 else "propose") for n in range(8)]
        results = [job.result() for job in jobs]
    assert {item["code"] for item in results} == {f"T{n}" for n in range(1, 9)}
    cards = tools.list_tools(lib)
    assert len(cards) == 8 and {card["name"] for card in cards} == {f"Process-{n}" for n in range(8)}
    for card in cards:
        assert card["body"].startswith(f"# {card['code']} {card['name']}")
        assert card["state"] == ("未检查" if card["manual"] else "待你装")


def test_real_process_duplicate_race_preserves_one_complete_card(lib):
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_worker, lib, "Same Name", "manual" if n % 2 else "propose") for n in range(4)]
        results = [job.result() for job in jobs]
    assert sum(item["created"] for item in results) == 1
    assert {item["code"] for item in results} == {"T1"}
    cards = tools.list_tools(lib)
    assert len(cards) == 1 and cards[0]["body"].startswith("# T1 Same Name")


def _workorder_project(root, mention="登记普通项目任务"):
    """只在测试目录建非科研目标及已连接的本地记录，不启动员工。"""
    from project import Project
    import store

    project = Project(root)
    bp = project.materials / "蓝图"
    bp.mkdir(parents=True)
    (bp / "S0 终极目标.md").write_text(
        "# S0 终极目标\n\n**管理一个普通项目。**\n\n| S1 | 目标 |\n|---|---|\n| S1-1 示例 | 完成普通任务 |\n",
        encoding="utf-8")
    (bp / "S1-1 示例.md").write_text(
        "# S1-1 示例\n\n**完成普通项目任务。**\n\n怎么算做到：输出本地说明。\n\n"
        "| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
        f"| S2-1 | {mention} | 本地说明内容正确 | 没做 |\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# 戒律\n- 必停：彻底删除、公开发布\n", encoding="utf-8")
    (root / ".mcp.json").write_text('{"mcpServers":{"research-console":{}}}', encoding="utf-8")
    conn = store.connect(project.db_path)
    try:
        with store.tx(conn):
            store.log(conn, "agent:temporary-fixture", "看全貌")
    finally:
        conn.close()
    return project


def _legacy_tool(lib, code, name, *, check="", kind="外部工具"):
    lib.mkdir(parents=True, exist_ok=True)
    (lib / f"{code} {name}.md").write_text(
        f"---\n编号: {code}\n名字: {name}\n类别: {kind}\n一句话: 临时回归\n检查: {check}\n---\n# {code} {name}\n",
        encoding="utf-8")


def _no_tool_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("备料或准备检查不能执行手工安装命令/启动员工")

    monkeypatch.setattr(tools, "find_exe", forbidden)
    monkeypatch.setattr(tools.subprocess, "run", forbidden)
    monkeypatch.setattr(tools.subprocess, "Popen", forbidden)
    import readiness
    monkeypatch.setattr(readiness, "_claude_cli", lambda: None)
    tools.forget()


@pytest.mark.parametrize("reference", ["code", "name"])
def test_workorder_api_materials_and_readiness_use_current_project_library(tmp_path, monkeypatch, reference):
    """共享后台绑定两个项目，同号 T41 及默认库 T99 不得串到开工单。"""
    from fastapi.testclient import TestClient
    from main import create_app
    import workorders

    decoy = tmp_path / "共享代码项目" / "工具库"
    _legacy_tool(decoy, "T41", "错误默认工具", check="文件 ready.txt")
    _legacy_tool(decoy, "T99", "错误默认卡")
    (decoy.parent / "ready.txt").write_text("default marker", encoding="utf-8")
    monkeypatch.setattr(tools, "LIB", decoy)
    _no_tool_execution(monkeypatch)
    projects = []
    for label in ("甲", "乙"):
        name = f"{label}项目文件工具"
        mention = ("T41" if reference == "code" else name) + "，另一个项目的 T99 不应备进来"
        project = _workorder_project(tmp_path / f"普通项目{label}", mention)
        _legacy_tool(project.root / "工具库", "T41", name, check="文件 ready.txt")
        projects.append(project)
    (projects[0].root / "ready.txt").write_text("only project A", encoding="utf-8")
    before = {f.name: f.read_bytes() for f in decoy.glob("*.md")}
    assert tools.check_cached("T41", lib=decoy)["ok"] is True  # 先污染默认库同号缓存。

    with TestClient(create_app(projects[0], tasks=False, global_keys=False)) as a, \
            TestClient(create_app(projects[1], tasks=False, global_keys=False)) as b:
        for client, project, label, expected in ((a, projects[0], "甲", "ok"), (b, projects[1], "乙", "bad")):
            assert workorders.derive(project, ["S1-1 S2-1"])["tools"] == ["T41"]
            result = client.post("/api/workorders", json={"name": "临时备料", "target": ["S1-1 S2-1"]})
            assert result.status_code == 200, result.text
            data = result.json()
            code = data["wo"]["code"]
            assert data["wo"]["tools"] == ["T41"]
            options = client.get(f"/api/workorders/{code}/options").json()["tools"]
            assert [(t["code"], t["name"]) for t in options] == [("T41", f"{label}项目文件工具")]
            assert [(t["code"], t["name"]) for t in client.get("/api/tools").json()["items"]] == [
                ("T41", f"{label}项目文件工具")]
            cleared = client.put(f"/api/workorders/{code}", json={"tools": []})
            assert cleared.status_code == 200 and cleared.json()["wo"]["tools"] == []
            filled = client.post(f"/api/workorders/{code}/fill")
            assert filled.status_code == 200 and filled.json()["wo"]["tools"] == ["T41"]
            fresh = client.get(f"/api/workorders/{code}").json()
            device = next(d for d in fresh["panel"]["devices"] if d["key"] == "tools")
            assert device["lamp"] == expected
            assert "错误默认" not in str(device) and "T99" not in str(device)
            if expected == "ok":
                assert device["summary"] == "1/1 接通" and fresh["panel"]["ready"] is True
                assert client.post(f"/api/workorders/{code}/start").status_code == 200
            else:
                assert f"{label}项目文件工具 没接通" in device["summary"]
                assert fresh["panel"]["ready"] is False
                assert client.post(f"/api/workorders/{code}/start").status_code == 400
    assert tools.check_cached("T41", lib=projects[0].root / "工具库")["ok"] is True
    assert tools.check_cached("T41", lib=projects[1].root / "工具库")["ok"] is False
    assert {f.name: f.read_bytes() for f in decoy.glob("*.md")} == before


@pytest.mark.parametrize("use,kind,expected", [
    ("listed", "外部工具", "bad"),
    ("mentioned-code", "外部工具", "bad"),
    ("mentioned-name", "外部工具", "bad"),
    ("unused", "外部工具", "warn"),
    ("unused", "技术栈", "bad"),
])
def test_manual_unknown_is_not_ready_when_needed_but_does_not_block_unrelated_work(
        tmp_path, monkeypatch, use, kind, expected):
    import readiness
    import store
    import workorders

    _no_tool_execution(monkeypatch)
    mention = {"mentioned-code": "使用 T1", "mentioned-name": "使用临时登记工具"}.get(use, "整理本地说明")
    project = _workorder_project(tmp_path / "普通项目", mention)
    card = tools.create("临时登记工具", one_line="只记录工具说明", kind=kind,
                        install="never-run-this --install", lib=project.root / "工具库")
    assert tools.check_cached(card["code"], lib=project.root / "工具库") == {"ok": None, "msg": "未检查"}
    conn = store.connect(project.db_path)
    try:
        wo = workorders.create(conn, project, "临时准备", ["S1-1 S2-1"])
        # 显式列卡和只在任务正文提到卡都必须判为实际要用。
        wo = workorders.update(conn, project, wo["code"], {"tools": [card["code"]] if use == "listed" else []})
        panel = readiness.panel(conn, project, wo)
        device = next(d for d in panel["devices"] if d["key"] == "tools")
        assert device["lamp"] == expected and "未检查" in device["summary"]
        assert "接通" not in device["summary"] and not any(c["lamp"] == "ok" for c in device["checks"])
        assert panel["ready"] is (expected != "bad")
        if expected == "bad":
            assert panel["red"] == ["工具"]
            with pytest.raises(store.Refused, match="工具"):
                workorders.start(conn, project, wo["code"])
            assert workorders.get(project, wo["code"])["stored"] == "备料"
        else:
            assert workorders.start(conn, project, wo["code"])["stored"] == "在跑"
    finally:
        conn.close()


def test_manual_blank_check_cannot_be_promoted_by_stale_true_cache(tmp_path, monkeypatch):
    import readiness
    import store
    import workorders

    _no_tool_execution(monkeypatch)
    project = _workorder_project(tmp_path / "普通项目", "使用 T1")
    tools.create("临时登记工具", one_line="没有配置检查", lib=project.root / "工具库")
    seen = []

    def stale_check(code, max_age=600, lib=None):
        seen.append((code, lib))
        return {"ok": True, "msg": "旧缓存"}

    monkeypatch.setattr(tools, "check_cached", stale_check)
    conn = store.connect(project.db_path)
    try:
        wo = workorders.create(conn, project, "临时准备", ["S1-1 S2-1"])
        panel = readiness.panel(conn, project, wo)
        device = next(d for d in panel["devices"] if d["key"] == "tools")
        assert seen == [("T1", project.root / "工具库")]
        assert device["lamp"] == "bad" and "未检查" in device["summary"] and panel["ready"] is False
    finally:
        conn.close()


@pytest.mark.parametrize("unknown", [{"ok": None, "msg": "没有检查结果"}, {}])
def test_unknown_result_for_nonempty_check_is_not_counted_as_available(tmp_path, monkeypatch, unknown):
    import readiness
    import store
    import workorders

    _no_tool_execution(monkeypatch)
    project = _workorder_project(tmp_path / "普通项目", "使用 T1")
    _legacy_tool(project.root / "工具库", "T1", "临时检查卡", check="文件 ready.txt")
    monkeypatch.setattr(tools, "check_cached", lambda code, max_age=600, lib=None: unknown)
    conn = store.connect(project.db_path)
    try:
        wo = workorders.create(conn, project, "临时准备", ["S1-1 S2-1"])
        panel = readiness.panel(conn, project, wo)
        device = next(d for d in panel["devices"] if d["key"] == "tools")
        assert device["lamp"] == "bad" and "未检查" in device["summary"] and panel["ready"] is False
    finally:
        conn.close()


def test_legacy_blank_checks_and_confirmed_proposal_keep_existing_readiness(tmp_path, monkeypatch):
    import readiness
    import store
    import workorders

    _no_tool_execution(monkeypatch)
    project = _workorder_project(tmp_path / "普通项目", "使用 T1 和 T2")
    lib = project.root / "工具库"
    _legacy_tool(lib, "T1", "旧内置卡", kind="技术栈")
    proposed = tools.propose("旧提案卡", one_line="旧流程", why="本地记录", install="只写说明", lib=lib)
    assert proposed["code"] == "T2"
    tools.set_state("T2", "", lib)
    conn = store.connect(project.db_path)
    try:
        wo = workorders.create(conn, project, "旧流程兼容", ["S1-1 S2-1"])
        panel = readiness.panel(conn, project, wo)
        device = next(d for d in panel["devices"] if d["key"] == "tools")
        assert device["lamp"] == "ok" and device["summary"] == "2/2 接通" and panel["ready"] is True
        assert workorders.start(conn, project, wo["code"])["stored"] == "在跑"
    finally:
        conn.close()
