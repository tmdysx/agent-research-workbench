"""用临时假材料验内容工作台：只读、旧稿、版本、身份与 Windows 路径保护。"""
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from fastapi.testclient import TestClient

import content_modules as cm
import journal
import library
import mcp_server
import outline
import store
from main import create_app
from project import Project, FIXED_NAMES, GOVERNANCE_NAMES


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.delenv("RC_DB", raising=False)
    p = Project(tmp_path)
    for module in cm.MODULES:
        base = p.materials / module
        base.mkdir(parents=True)
        if module == "文献":
            specs = [("downloads", "下载列表", "Downloads", "downloads", "下载清单.md"),
                     ("reading", "精读", "Reading", "reading", "解读"),
                     ("originals", "原文", "Originals", "originals", "原文"),
                     ("notes", "专属笔记", "Notes", "notes", "解读")]
        else:
            roots = ["正文/引言", "项目文书"] if module == "论文" else list(cm.ROOTS[module])
            specs = [(f"s{i}", r.split("/")[-1], f"Section {i}", "documents", r) for i, r in enumerate(roots)]
        sections = [{"id": i, "title": t, "en": en, "kind": k, "folder": f, "templates": []} for i, t, en, k, f in specs]
        if module != "文献":
            sections[0]["templates"] = ["工作台/模板/空稿.md"]
            put(base / sections[0]["templates"][0], "# 占位模板\n")
        put(base / cm.CONFIG, json.dumps({"version": 1, "sections": sections}, ensure_ascii=False))
    return p


def save(p, module="论文", path="正文/引言/稿.md", text="新稿\n", revision="", **extra):
    c = store.connect(p.db_path)
    try:
        return cm.write_document(c, p, module, path, text, revision, str(p.root),
                                 by=extra.pop("by", "人"), source=extra.pop("source", "http"), **extra)
    finally:
        c.close()


def hashes(root):
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in root.rglob("*") if f.is_file()}


def test_empty_workspace_no_write_or_index(workspace, monkeypatch):
    p = workspace
    before = hashes(p.root)
    def forbidden(*args, **kwargs):
        pytest.fail("只读 GET 不得连接数据库、扫描文献或运行外部命令")
    monkeypatch.setattr(store, "connect", forbidden)
    monkeypatch.setattr(library, "scan", forbidden)
    monkeypatch.setattr(library, "entries", forbidden)
    monkeypatch.setattr(library, "pair", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    client = TestClient(create_app(p))  # 不启动旧服务 lifespan；检验 GET 自身。
    server = mcp_server.build(p)
    for module in cm.MODULES:
        data = client.get(f"/api/content/{module}")
        assert data.status_code == 200, data.text
        assert data.json()["module"] == module and not data.json()["problems"]
        native = json.loads(server._tool_manager.get_tool("get_content_workspace").fn(module=module))
        assert native == data.json()
        assert all(s["files"] == [] for s in native["sections"])
    template = client.get("/api/content/论文/document", params={"path": "工作台/模板/空稿.md"})
    assert template.status_code == 200 and not template.json()["editable"]
    assert not p.index_dir.exists() and hashes(p.root) == before


def test_missing_module_and_config_are_explicit(workspace):
    (workspace.materials / "文献" / cm.CONFIG).unlink()
    data = cm.workspace(workspace, "文献")
    assert len(data["sections"]) == 3 and data["problems"] and not data["config_revision"]
    (workspace.materials / "论文" / cm.CONFIG).unlink()
    assert cm.workspace(workspace, "论文")["problems"]
    with pytest.raises(cm.Invalid):
        cm.workspace(workspace, "不存在")


def test_literature_only_metadata_unique_reader_ownership(workspace, monkeypatch):
    base = workspace.materials / "文献"
    put(base / "下载清单.md", "假下载清单")
    put(base / "原文/L1 占位.pdf", "假 PDF 正文不可读取")
    put(base / "解读/L1 占位/信息.json", json.dumps({"编号": "L1", "原文": "原文/L1 占位.pdf"}, ensure_ascii=False))
    put(base / "解读/L1 占位/文本/讲解.md", "假论文正文不可批量读取")
    put(base / "解读/L1 占位/文本/笔记.md", "假人的专属笔记不可读取")
    put(base / "解读/L1 占位/批注.json", "假批注不可读取")
    original_open = Path.open
    def metadata_only(f, *args, **kwargs):
        assert f.name in ("工作台.json", "信息.json"), f
        return original_open(f, *args, **kwargs)
    monkeypatch.setattr(Path, "open", metadata_only)
    data = cm.workspace(workspace, "文献")
    kinds = {s["kind"]: s["files"] for s in data["sections"]}
    assert len(kinds["downloads"]) == 1 and len(kinds["notes"]) == 2
    assert kinds["originals"][0]["reader_code"] == "L1"
    assert kinds["reading"][0]["reader_code"] == "L1"
    assert all(not x["editable"] for xs in kinds.values() for x in xs)
    assert {x["name"] for x in kinds["reading"]} == {"讲解.md"}


def test_duplicate_or_wrong_l_metadata_no_ambiguous_reader(workspace):
    base = workspace.materials / "文献"
    for name, code in (("L1 一", "L1"), ("L1 二", "L1"), ("L2 三", "L99")):
        put(base / f"解读/{name}/信息.json", json.dumps({"编号": code}))
        put(base / f"解读/{name}/文本/笔记.md", "合成笔记")
    result = cm.workspace(workspace, "文献")
    notes = next(s for s in result["sections"] if s["kind"] == "notes")["files"]
    assert len(notes) == 3 and all("reader_code" not in x for x in notes)
    assert any("L1" in x for x in result["problems"])
    assert any("编号" in x for x in result["problems"])


def test_missing_and_unlinked_original_flags_do_not_change_sources_or_notes_reader(workspace, monkeypatch):
    base = workspace.materials / "文献"
    for name, code, original in (("L1 缺原文", "L1", "原文/L1 明确原文.pdf"),
                                 ("L2 未关联", "L2", "")):
        info = {"编号": code}
        if original:
            info["原文"] = original
        put(base / f"解读/{name}/信息.json", json.dumps(info, ensure_ascii=False))
        put(base / f"解读/{name}/文本/讲解.md", "合成解读不能读取")
        put(base / f"解读/{name}/文本/笔记.md", "合成笔记不能读取")
    # 同一模块的同号但不同名字、其他模块的同名同号均不能冒充明确原文路径。
    put(base / "原文/L1 另一文件.pdf", "合成另一个文件")
    put(workspace.materials / "论文/原文/L1 明确原文.pdf", "合成另模块同号原文")
    before = hashes(workspace.root)
    original_open = Path.open
    def metadata_only(f, *args, **kwargs):
        assert f.name in ("工作台.json", "信息.json"), f
        return original_open(f, *args, **kwargs)
    monkeypatch.setattr(Path, "open", metadata_only)
    monkeypatch.setattr(library, "scan", lambda *a: pytest.fail("缺失提示不得扫描"))
    monkeypatch.setattr(library, "pair", lambda *a: pytest.fail("缺失提示不得配对或重写"))
    result = cm.workspace(workspace, "文献")
    rows = [f for s in result["sections"] if s["kind"] in ("reading", "notes") for f in s["files"]]
    for f in rows:
        assert f["reader_code"] in ("L1", "L2")
        if f["reader_code"] == "L1":
            assert f["missing_original"] and not f.get("unlinked_original")
        else:
            assert f["unlinked_original"] and not f.get("missing_original")
    assert any("L1（解读/L1 缺原文/信息.json）" in p and "缺失" in p for p in result["problems"])
    assert any("L2（解读/L2 未关联/信息.json）" in p and "未关联" in p for p in result["problems"])
    monkeypatch.setattr(Path, "open", original_open)
    assert hashes(workspace.root) == before and not workspace.index_dir.exists()


@pytest.mark.parametrize("truncation", ["count", "depth"])
def test_truncated_original_projection_reports_unconfirmed_not_missing(workspace, monkeypatch, truncation):
    base = workspace.materials / "文献"
    put(base / "解读/L1 已关联/信息.json", json.dumps({"编号": "L1", "原文": "原文/未列入.pdf"}, ensure_ascii=False))
    put(base / "解读/L1 已关联/文本/笔记.md", "合成笔记")
    walk = cm._walk
    def truncated(p, module_base, folder, module, problems, budget, depth=0):
        if folder == base / "原文":
            problems.append("文件过多，只显示前 2000 项" if truncation == "count" else "目录层数过深，未继续展开")
            return []
        return walk(p, module_base, folder, module, problems, budget, depth)
    monkeypatch.setattr(cm, "_walk", truncated)
    data = cm.workspace(workspace, "文献")
    notes = next(s for s in data["sections"] if s["kind"] == "notes")["files"]
    assert notes[0]["reader_code"] == "L1" and notes[0]["original_unconfirmed"]
    assert not notes[0].get("missing_original") and not notes[0].get("unlinked_original")
    assert any("L1（解读/L1 已关联/信息.json）" in p and "尚未确认" in p for p in data["problems"])


def test_linked_original_already_listed_not_marked_missing_when_list_truncated(workspace, monkeypatch):
    base = workspace.materials / "文献"
    put(base / "原文/L1 已列入.pdf", "合成原文")
    put(base / "解读/L1 已关联/信息.json", json.dumps({"编号": "L1", "原文": "原文/L1 已列入.pdf"}, ensure_ascii=False))
    put(base / "解读/L1 已关联/文本/笔记.md", "合成笔记")
    walk = cm._walk
    def truncated(p, module_base, folder, module, problems, budget, depth=0):
        rows = walk(p, module_base, folder, module, problems, budget, depth)
        if folder == base / "原文":
            problems.append("文件过多，只显示前 2000 项")
        return rows
    monkeypatch.setattr(cm, "_walk", truncated)
    data = cm.workspace(workspace, "文献")
    note = next(s for s in data["sections"] if s["kind"] == "notes")["files"][0]
    assert note["reader_code"] == "L1"
    assert not any(note.get(k) for k in ("missing_original", "unlinked_original", "original_unconfirmed"))


def test_raw_sha_crlf_bom_and_old_history(workspace):
    target = workspace.materials / "论文/正文/引言/稿.md"
    target.parent.mkdir(parents=True)
    old = b"\xef\xbb\xbf" + "初稿\r\n".encode()
    target.write_bytes(old)
    document = cm.read_document(workspace, "论文", "正文/引言/稿.md")
    assert document["revision"] == hashlib.sha256(old).hexdigest()
    assert document["text"] == "初稿\r\n" and document["editable"]
    saved = save(workspace, text="新版\n", revision=document["revision"], reason="保留原文")
    assert saved["revision"] == hashlib.sha256("新版\n".encode()).hexdigest()
    histories = list((workspace.materials / "论文/历史/内容工作台").rglob("稿.md"))
    assert len(histories) == 1 and histories[0].read_bytes() == old
    meta = json.loads(histories[0].with_name("稿.md.保存信息.json").read_text(encoding="utf-8"))
    assert meta["by"] == "人" and meta["source"] == "http" and meta["revision"] == document["revision"]
    log = journal.read(workspace)[-1]
    assert log["by"] == "人" and "http" in log["body"] and "保留原文" in log["body"]


def test_same_name_stale_revision_and_inplace_change_no_side_effect(workspace):
    doc = save(workspace, text="甲甲")
    before = journal.read(workspace)
    with pytest.raises(cm.Conflict):
        save(workspace, text="同名", revision="")
    target = workspace.materials / "论文/正文/引言/稿.md"
    stamp = target.stat()
    target.write_bytes("乙乙".encode())
    os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    with pytest.raises(cm.Conflict):
        save(workspace, text="过时", revision=doc["revision"])
    assert target.read_text(encoding="utf-8") == "乙乙" and journal.read(workspace) == before
    assert not (workspace.materials / "论文/历史").exists()


@pytest.mark.parametrize("module,path", [
    ("文献", "原文/L1.pdf"), ("文献", "解读/L1/文本/笔记.md"),
    ("论文", "工作台/模板/空稿.md"), ("论文", "../测试/数据集/a.md"),
    ("论文", "正文/../../笔记/总览.md"), ("论文", "正文/历史/a.md"),
    ("论文", "正文/内置/a.md"), ("论文", "正文/a.pdf"),
    ("论文", "正文/CON.txt"), ("论文", "正文/CON .txt"),
    ("论文", "正文/a.md:stream"), ("论文", "正文/a.md."),
    ("论文", "正文/a.md "), ("论文", "正文//a.md"),
    ("论文", "正文/./a.md"), ("论文", "正文/.隐藏/a.md"),
    ("测试", "其他/a.md"), ("论文", "C:/外面/a.md"),
    ("测试", "数据集/_私有/a.md"), ("论文", "笔记/总览.md"),
    ("论文", "正文/VENV/private.py"), ("测试", "测试代码/NODE_MODULES/private.py"),
])
def test_fixed_write_scope_and_windows_names(workspace, module, path):
    c = store.connect(workspace.db_path)
    try:
        before = hashes(workspace.root)
        with pytest.raises(cm.Invalid):
            cm.write_document(c, workspace, module, path, "无权限", "", str(workspace.root), by="人", source="http")
        assert hashes(workspace.root) == before and journal.read(workspace) == []
    finally:
        c.close()


def test_wrong_root_and_full_revision(workspace, tmp_path):
    other = tmp_path / "另一个项目"
    other.mkdir()
    c = store.connect(workspace.db_path)
    try:
        for root, revision in ((str(other), ""), ("", ""), (str(workspace.root), "a" * 12)):
            with pytest.raises(cm.Invalid):
                cm.write_document(c, workspace, "论文", "正文/a.md", "假稿", revision, root, by="人", source="http")
        assert journal.read(workspace) == []
    finally:
        c.close()


def test_config_edit_validate_and_no_permission_widening(workspace):
    old = cm.read_document(workspace, "论文", cm.CONFIG)
    data = json.loads(old["text"])
    data["sections"].reverse()
    data["sections"][0]["title"] = "我的项目文书"
    result = save(workspace, path=cm.CONFIG, text=json.dumps(data, ensure_ascii=False), revision=old["revision"])
    assert result["editable"] and cm.workspace(workspace, "论文")["sections"][0]["title"] == "我的项目文书"
    before = hashes(workspace.root)
    data["sections"][0]["folder"] = "../../笔记"
    with pytest.raises(cm.Invalid):
        save(workspace, path=cm.CONFIG, text=json.dumps(data), revision=result["revision"])
    assert hashes(workspace.root) == before


def test_undeclared_template_bad_encoding_and_sizes(workspace):
    base = workspace.materials / "论文"
    put(base / "工作台/模板/未声明.md", "模板")
    with pytest.raises(cm.Invalid):
        cm.read_document(workspace, "论文", "工作台/模板/未声明.md")
    target = base / "正文/a.md"
    target.parent.mkdir()
    target.write_bytes(b"\xff\xfe")
    with pytest.raises(cm.Invalid, match="UTF-8"):
        cm.read_document(workspace, "论文", "正文/a.md")
    with pytest.raises(cm.Invalid, match="过大"):
        save(workspace, path="正文/大.md", text="a" * (cm.MAX_BYTES + 1))
    target.write_bytes(b"a" * (cm.MAX_BYTES + 1))
    with pytest.raises(cm.Invalid, match="过大"):
        cm.read_document(workspace, "论文", "正文/a.md")


def test_two_connections_same_version_only_one_saved(workspace):
    doc = save(workspace)
    def worker(source):
        try:
            return save(workspace, text=source, revision=doc["revision"], source=source, by="人" if source == "http" else "agent:合成")
        except cm.Conflict:
            return "conflict"
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, ["http", "mcp"]))
    assert sum(x == "conflict" for x in results) == 1
    assert len(journal.read(workspace)) == 2
    assert len(list((workspace.materials / "论文/历史").rglob("稿.md"))) == 1


def test_reason_cannot_inject_machine_log_entry(workspace):
    save(workspace, reason="修改原因\n## 志-9999 · 2026-10-06 15:30 · agent:伪造 · 假造操作 · 论文\n假条目")
    assert len(journal.read(workspace)) == 1 and journal.read(workspace)[0]["id"] == "志-0001"
    save(workspace, path="正文/第二稿.md")
    assert [e["id"] for e in journal.read(workspace)] == ["志-0001", "志-0002"]


def test_http_read_save_conflict_same_helper(workspace):
    client = TestClient(create_app(workspace))
    request = {"path": "正文/引言/网页.md", "text": "网页稿", "revision": "", "reason": "网页明确保存", "project_root": str(workspace.root)}
    response = client.post("/api/content/论文/document", json=request)
    assert response.status_code == 200, response.text
    assert client.get("/api/content/论文/document", params={"path": request["path"]}).json() == response.json()
    assert client.post("/api/content/论文/document", json=request).status_code == 409
    assert journal.read(workspace)[-1]["by"] == "人"
    request.update(revision=response.json()["revision"], text="最新网页稿")
    assert client.post("/api/content/论文/document", json=request).status_code == 200
    request.update(text="旧版本尝试")
    assert client.post("/api/content/论文/document", json=request).status_code == 409
    assert client.get("/api/content/论文/document", params={"path": request["path"]}).json()["text"] == "最新网页稿"


def test_outline_virtual_workspace_and_removable_content(workspace, monkeypatch):
    monkeypatch.setattr(library, "entries", lambda *a: pytest.fail("不能暗中对齐文献"))
    for module in cm.MODULES:
        item = {"name": "老链接.md", "path": "老链接.md", "dir": False, "link": False}
        result = outline.sections(workspace, module, [item])
        assert result["default"] == ("#文献库:文献" if module == "文献" else "#工作区:all")
        assert result["sections"][-1]["items"] == [item]
        assert (module in FIXED_NAMES) == (module in {"测试", "文献", "论文"})
        assert (module in GOVERNANCE_NAMES) == (module in {'测试', '文献', '论文'})


def test_new_literature_outline_keeps_old_virtual_links_without_pair(workspace, monkeypatch):
    base = workspace.materials / "文献"
    put(base / "下载清单.md", "假清单")
    put(base / "原文/L1 占位.pdf", "假PDF")
    put(base / "解读/L1 占位/信息.json", json.dumps({"编号": "L1", "原文": "原文/L1 占位.pdf"}))
    put(base / "解读/L1 占位/文本/笔记.md", "合成笔记")
    monkeypatch.setattr(library, "entries", lambda *a: pytest.fail("新outline不得对齐文献"))
    monkeypatch.setattr(library, "pair", lambda *a: pytest.fail("新outline不得对齐文献"))
    monkeypatch.setattr(library, "scan", lambda *a: pytest.fail("新outline不得扫描文献"))
    entries = outline.sections(workspace, "文献", [])
    paths = {n["path"] for s in entries["sections"] for n in s["items"]}
    assert paths == {"#下载:文献", "#文献库:文献"}
    assert entries["default"] == "#文献库:文献"


@pytest.mark.parametrize("where", ["正文", "历史", "日志"])
def test_junction_work_history_log_rejected(workspace, tmp_path, where):
    if os.name != "nt":
        pytest.skip("Windows junction regression")
    outside = tmp_path / "外部假目录"
    outside.mkdir()
    link = workspace.materials / "论文" / where if where != "日志" else workspace.root / "笔记/日志"
    link.parent.mkdir(exist_ok=True)
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
    assert result.returncode == 0, result.stderr
    with pytest.raises(cm.Invalid):
        save(workspace)
    assert list(outside.iterdir()) == [] and journal.read(workspace) == []


def test_symlink_file_read_and_save_rejected(workspace, tmp_path):
    target = tmp_path / "外部假稿.md"
    target.write_text("外部稿", encoding="utf-8")
    link = workspace.materials / "论文/正文/链接.md"
    link.parent.mkdir()
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("本机没有创建 Windows symlink 的权限")
    with pytest.raises(cm.Invalid):
        cm.read_document(workspace, "论文", "正文/链接.md")
    with pytest.raises(cm.Invalid):
        save(workspace, path="正文/链接.md")
    assert target.read_text(encoding="utf-8") == "外部稿"


async def _stdio_contract(p):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Implementation
    params = StdioServerParameters(command=sys.executable, args=["-B", str(Path(mcp_server.__file__)), "--project", str(p.root)],
                                  env={**os.environ, "RC_OFFLINE": "1", "RC_DB": str(p.db_path)})
    async with stdio_client(params) as (receive, send):
        async with ClientSession(receive, send, client_info=Implementation(name="content-synthetic-agent", version="1")) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert {"get_content_workspace", "read_content_document", "write_content_document"} <= names
            before = hashes(p.root)
            data = await session.call_tool("get_content_workspace", {"module": "测试"})
            assert json.loads(data.content[0].text) == cm.workspace(p, "测试")
            assert hashes(p.root) == before
            request = {"module": "测试", "path": "测试记录/MCP.md", "text": "MCP假记录", "revision": "", "project_root": str(p.root), "reason": "agent明确保存"}
            result = await session.call_tool("write_content_document", request)
            document = json.loads(result.content[0].text)
            assert document == cm.read_document(p, "测试", request["path"])
            old = await session.call_tool("write_content_document", request)
            assert "没保存" in old.content[0].text
            log = journal.read(p)[-1]
            assert log["by"] == "agent:content-synthetic-agent" and "mcp" in log["body"]
            client = TestClient(create_app(p))
            request.pop("module")
            request.update(revision=document["revision"], text="网页接写MCP稿")
            assert client.post("/api/content/测试/document", json=request).status_code == 200
            read = await session.call_tool("read_content_document", {"module": "测试", "path": request["path"]})
            assert json.loads(read.content[0].text)["text"] == "网页接写MCP稿"


def test_real_stdio_and_http_same_files_identity(workspace):
    anyio.run(_stdio_contract, workspace)

def test_read_during_metadata_preserving_change_refuses(workspace, monkeypatch):
    doc = save(workspace, text="甲甲")
    target = workspace.materials / "论文" / doc["path"]
    original_open = Path.open
    class ChangingRead:
        def __init__(self, f):
            self.f = f
            self.changed = False
        def __enter__(self):
            self.f.__enter__()
            return self
        def __exit__(self, *args):
            return self.f.__exit__(*args)
        def __getattr__(self, key):
            return getattr(self.f, key)
        def read(self, *args):
            data = self.f.read(*args)
            if not self.changed:
                self.changed = True
                st = target.stat()
                with original_open(target, "r+b") as out:
                    out.write("乙乙".encode())
                os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns))
            return data
    def changing_open(path, *args, **kwargs):
        f = original_open(path, *args, **kwargs)
        return ChangingRead(f) if path == target and args and args[0] == "rb" else f
    monkeypatch.setattr(Path, "open", changing_open)
    with pytest.raises(cm.Conflict, match="读取期间"):
        cm.read_document(workspace, "论文", doc["path"])


def test_commit_failure_restores_old_file_and_log(workspace):
    import sqlite3
    doc = save(workspace, text="旧稿")
    old_logs = journal.read(workspace)
    original_log = next((workspace.root / "笔记/日志").glob("*.md")).read_bytes()
    conn = store.connect(workspace.db_path)
    class CommitFailure:
        def __getattr__(self, key):
            return getattr(conn, key)
        def execute(self, statement, *args):
            if statement == "COMMIT":
                raise sqlite3.OperationalError("合成 COMMIT 失败")
            return conn.execute(statement, *args)
    try:
        with pytest.raises(sqlite3.OperationalError, match="合成 COMMIT"):
            cm.write_document(CommitFailure(), workspace, "论文", doc["path"], "失败新稿", doc["revision"],
                              str(workspace.root), by="人", source="http")
        assert not conn.in_transaction
        assert cm.read_document(workspace, "论文", doc["path"])["text"] == "旧稿"
        assert journal.read(workspace) == old_logs
        assert next((workspace.root / "笔记/日志").glob("*.md")).read_bytes() == original_log
        assert conn.execute("SELECT COUNT(*) FROM event").fetchone()[0] == 1
        assert list((workspace.materials / "论文/历史").rglob("稿.md"))
    finally:
        conn.close()


def test_log_replace_failure_restores_doc_without_new_event(workspace, monkeypatch):
    doc = save(workspace, text="旧稿")
    old_log = journal.read(workspace)
    replace = cm.atomic.replace
    def fail_log(src, dst, *args, **kwargs):
        if dst.parent.name == "日志":
            raise OSError("合成日志落盘失败")
        return replace(src, dst, *args, **kwargs)
    monkeypatch.setattr(cm.atomic, "replace", fail_log)
    with pytest.raises(OSError, match="合成日志"):
        save(workspace, text="失败新稿", revision=doc["revision"])
    assert cm.read_document(workspace, "论文", doc["path"])["text"] == "旧稿"
    assert journal.read(workspace) == old_log
    assert not list(workspace.root.rglob(".内容工作台-*"))


def test_last_hash_check_preserves_external_update(workspace, monkeypatch):
    doc = save(workspace, text="旧稿")
    original = cm._log_outputs
    calls = []
    def mutate_on_final_guard(p):
        calls.append(1)
        result = original(p)
        if len(calls) == 2:
            (p.materials / "论文" / doc["path"]).write_text("外部刚修改", encoding="utf-8")
        return result
    monkeypatch.setattr(cm, "_log_outputs", mutate_on_final_guard)
    with pytest.raises(cm.Conflict, match="保存前"):
        save(workspace, text="不能覆盖", revision=doc["revision"])
    assert cm.read_document(workspace, "论文", doc["path"])["text"] == "外部刚修改"
    assert len(journal.read(workspace)) == 1 and not list(workspace.root.rglob(".内容工作台-*"))


def test_root_and_child_short_path_rules(workspace):
    if os.name != "nt":
        pytest.skip("Windows 8.3 path regression")
    import ctypes
    def short(path):
        output = ctypes.create_unicode_buffer(32768)
        count = ctypes.windll.kernel32.GetShortPathNameW(str(path), output, len(output))
        assert count and count < len(output)
        return Path(output.value)
    doc = save(workspace)
    alias_project = Project(short(workspace.root))
    assert cm.read_document(alias_project, "论文", doc["path"]) == cm.read_document(workspace, "论文", doc["path"])
    folder = workspace.materials / "论文/正文/很长的合成正文目录名字"
    put(folder / "一个测试正文.md", "短路径合成测试")
    alias = short(folder).name
    if alias.casefold() == folder.name.casefold():
        pytest.skip("此磁盘未生成子目录的 8.3 别名，根兼容已实际核对")
    with pytest.raises(cm.Invalid, match="完整名称"):
        cm.read_document(workspace, "论文", f"正文/{alias}/一个测试正文.md")
    with pytest.raises(cm.Invalid, match="完整名称"):
        save(workspace, path=f"正文/{alias}/另一个正文.md")


async def _real_stdio_http_race(p):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Implementation
    doc = save(p, module="测试", path="测试记录/竞争.md", text="共同旧稿")
    parameters = StdioServerParameters(command=sys.executable,
        args=["-B", str(Path(mcp_server.__file__)), "--project", str(p.root)],
        env={**os.environ, "RC_OFFLINE": "1", "RC_DB": str(p.db_path)})
    async with stdio_client(parameters) as (receive, send):
        async with ClientSession(receive, send, client_info=Implementation(name="content-race-agent", version="1")) as session:
            await session.initialize()
            client = TestClient(create_app(p))
            request = {"path": doc["path"], "text": "网页竞争稿", "revision": doc["revision"], "project_root": str(p.root)}
            results = []
            async def http_save():
                response = await anyio.to_thread.run_sync(lambda: client.post("/api/content/测试/document", json=request))
                results.append(response.status_code == 200)
                assert response.status_code in (200, 409), response.text
            async def mcp_save():
                response = await session.call_tool("write_content_document", request | {"module": "测试", "text": "agent竞争稿"})
                text = response.content[0].text
                results.append(not text.startswith("没保存"))
                assert text.startswith("没保存") or json.loads(text)["revision"] != doc["revision"]
            async with anyio.create_task_group() as group:
                group.start_soon(http_save)
                group.start_soon(mcp_save)
            assert sum(results) == 1
            assert len(journal.read(p)) == 2
            assert len(list((p.materials / "测试/历史").rglob("竞争.md"))) == 1


def test_real_stdio_http_compete_same_revision(workspace):
    anyio.run(_real_stdio_http_race, workspace)


def test_literature_three_sections_and_legacy_four_remain_compatible(workspace):
    base = workspace.materials / "文献"
    old = json.loads((base / cm.CONFIG).read_text(encoding="utf-8"))
    assert len(cm.validate_config("文献", old)["sections"]) == 4
    new = {"version": 1, "sections": [s for s in old["sections"] if s["kind"] != "notes"]}
    put(base / cm.CONFIG, json.dumps(new, ensure_ascii=False))
    before = hashes(workspace.root)
    result = cm.workspace(workspace, "文献")
    assert [s["kind"] for s in result["sections"]] == ["downloads", "reading", "originals"]
    assert not result["problems"] and hashes(workspace.root) == before
    with pytest.raises(cm.Invalid):
        cm.validate_config("文献", {"sections": new["sections"][:2], "version": 1})
    duplicate = dict(new["sections"][0], id="duplicate")
    with pytest.raises(cm.Invalid):
        cm.validate_config("文献", {"sections": new["sections"] + [duplicate], "version": 1})
