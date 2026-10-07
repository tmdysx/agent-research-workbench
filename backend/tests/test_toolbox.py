"""工具页分四块（工具 S2-1、S2-2；作者 10-01：「工具这个模块也要分几个小模块，一个是开源项目，一个是技术栈，一个是外部工具和插件」）。"""
import sessions
import store
import toolbox
import tools


def _w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_agent_programs_installed_and_who_came_last(proj, tmp_path, monkeypatch):
    (tmp_path / "codex会话").mkdir()
    monkeypatch.setattr(sessions, "SOURCES", {"Claude Code": tmp_path / "没有", "Codex": tmp_path / "codex会话"})
    monkeypatch.setattr(tools, "find_exe", lambda name, *a, **k: "C:/x/claude.cmd" if name == "claude" else None)
    c = store.connect(proj.db_path)
    try:
        with store.tx(c):
            store.log(c, "agent:codex-mcp-client", "领活", "S1-1 S2-1", None)
            store.log(c, "agent:claude-code#2", "交付", "J1", None)
        got = {a["name"]: a for a in toolbox.agent_programs(c, proj)}
    finally:
        c.close()
    assert got["Claude Code"]["installed"] and got["Claude Code"]["exe"] == "C:/x/claude.cmd" and not got["Claude Code"]["sessions_found"]
    assert got["Codex"]["installed"] and got["Codex"]["exe"] == "" and got["Codex"]["sessions_found"]      # 程序没找到、会话记录在：也算装了
    assert got["Codex"]["last_agent"] == "codex" and got["Claude Code"]["last_agent"] == "claude-code#2"   # 名字去掉了 -mcp-client


def test_the_built_in_tools_module_carries_its_own_needs_and_tasks(proj):
    from fastapi.testclient import TestClient
    from main import create_app
    _w(proj.root / "治理" / "需求" / "工具.md", "# 工具 · 需求\n\n**工具一处看。**\n\n为了：S1-1\n\n| | 要什么功能 | 要什么效果 | 来自 |\n|---|---|---|---|\n| 需-1 | 分块看 | 四块 | 测试 |\n")
    _w(proj.root / "治理" / "任务" / "工具.md", "# 工具 · 任务\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n| S2-1 | 分四块 | 需-1 | 页面上四块 | 没做 |\n")
    with TestClient(create_app(proj)) as client:
        mods = {m["key"]: m for m in client.get("/api/state").json()["panorama"]["modules"]}
        page = client.get("/").text
    t = mods["common:tools"]
    assert t["has_need"] and t["has_blueprint"] and "缺需求" not in t["missing"] and [x["code"] for x in t["tasks"]] == ["S2-1"]
    assert "工具" not in mods                                                     # 不再多出一块「承接模块不可用」
    assert "'s:oss': ['GitHub 开源项目'" in page and "q[2] === 's') TLSEL = 's:' + val" in page   # 四块、#/tools?s=oss 能直接到那一块


def test_web_links_are_read_by_group_and_bad_urls_skipped(tmp_path):
    import links
    f = tmp_path / "网页链接.md"
    f.write_text("# 网页链接\n\n## 找论文\n\n| 名字 | 网址 | 干什么用 |\n|---|---|---|\n| arXiv | https://arxiv.org | 预印本 |\n| 坏的 | 不是网址 | x |\n\n## 空组\n\n| 名字 | 网址 | 干什么用 |\n|---|---|---|\n", encoding="utf-8")
    g = links.groups(f)
    assert [x["group"] for x in g] == ["找论文"] and g[0]["items"] == [{"name": "arXiv", "url": "https://arxiv.org", "what": "预印本"}]
    real = links.groups()
    assert len(real) >= 5 and all(x["url"].startswith("https://") for grp in real for x in grp["items"])   # 应用自带的那份


def test_every_directory_folds_like_folders(proj):
    """目录像文件夹一样能收能展（S1-10 S2-12）：分组标题前面有箭头、记住收了哪些、工具页默认只展开正在看的那块。"""
    from fastapi.testclient import TestClient
    from main import create_app
    with TestClient(create_app(proj)) as client:
        page = client.get("/").text
    assert "function applyFold(" in page and "tpl_fold" in page and "view === 'tools' && h.classList.contains('asec')" in page


def test_the_agent_catalog_lists_both_countries_and_what_is_installed(proj, tmp_path, monkeypatch):
    """市面上的智能体（工具 S2-13；作者 10-01：「你把市面上所有中国和美国的智能体都加上」）。"""
    app = tmp_path / "Programs" / "Trae"
    app.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(tools, "find_exe", lambda name, *a, **k: "C:/x/qwen.cmd" if name == "qwen" else None)
    f = tmp_path / "智能体.md"
    f.write_text("# 智能体\n\n## 美国\n\n| 名字 | 哪家 | 什么样 | 接本应用 | 命令 | Windows 位置 | 官网 |\n|---|---|---|---|---|---|---|\n"
                 "| Cursor | Anysphere | 编辑器 | 能 | cursor-agent |  | https://cursor.com |\n\n## 中国\n\n| 名字 | 哪家 | 什么样 | 接本应用 | 命令 | Windows 位置 | 官网 |\n|---|---|---|---|---|---|---|\n"
                 "| Qwen Code | 阿里通义 | 命令行 | 能 | qwen |  | https://github.com/QwenLM/qwen-code |\n| Trae | 字节跳动 | 编辑器 | 能 |  | %LOCALAPPDATA%\\Programs\\Trae | https://www.trae.cn |\n", encoding="utf-8")
    g = {x["group"]: x["items"] for x in toolbox.catalog(proj, f)}
    assert list(g) == ["美国", "中国"] and not g["美国"][0]["installed"]
    assert [(x["name"], x["installed"]) for x in g["中国"]] == [("Qwen Code", True), ("Trae", True)]   # 命令找到了、Windows 位置在
    real = toolbox.catalog(proj)
    assert {x["group"] for x in real} == {"美国", "中国"} and sum(len(x["items"]) for x in real) >= 40
    conf = toolbox.mcp_config(proj)["mcpServers"]["research-console"]
    assert conf["args"][-1] == str(proj.root) and conf["args"][0].endswith("mcp_server.py")
