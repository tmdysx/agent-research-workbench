"""开源项目：外部资料入口的 GitHub 压缩包收进工具页（工具 S2-3、S2-4；作者 10-01「为啥外部资料入口的东西不能直接分配到工具？」）。"""
import zipfile

import pytest

import intake
import repos
import store

MIT = "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy"
AGPL = "GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3, 19 November 2007"


def _zip(path, root, files):
    with zipfile.ZipFile(path, "w") as z:
        for name, text in files.items():
            z.writestr(f"{root}/{name}", text)
    return path


@pytest.fixture
def lib(tmp_path, monkeypatch):
    d = tmp_path / "工具库" / "开源项目"
    monkeypatch.setattr(repos, "DIR", d)
    return d


def test_licenses_decide_what_we_may_borrow(tmp_path):
    a = repos.inspect(_zip(tmp_path / "a-main.zip", "a-main", {"LICENSE": MIT, "README.md": "# A\n\n[![x](b)](c) [y](z)\n\nA tool that renders charts for agents. See https://github.com/someone/a\n", "s/SKILL.md": "x"}))
    assert (a["name"], a["license"], a["borrow"], a["link"]) == ("a", "MIT", "能抄", "https://github.com/someone/a")
    assert a["one_line"].startswith("A tool that renders charts") and any(h.startswith("技能 1") for h in a["has"])
    b = repos.inspect(_zip(tmp_path / "b-main.zip", "b-main", {"LICENSE": AGPL, "README.md": "# B"}))
    assert (b["license"], b["borrow"]) == ("AGPL-3.0", "不许抄")
    c = repos.inspect(_zip(tmp_path / "c-main (1).zip", "c-main", {"README.md": "# C"}))
    assert (c["name"], c["license"], c["borrow"]) == ("c", "没许可证", "不许抄")
    assert repos.borrow("MPL-2.0") == "只借思路" and repos.borrow("CC-BY-NC-4.0") == "不许抄" and repos.borrow("BSD-3-Clause") == "能抄"


def test_one_line_skips_lead_ins_names_and_calls_to_action(tmp_path):
    """工具 S2-14：「……是：」这种引子句、光一个名字、光一个网址、「Sign up →」都不算；开头加粗的那句 HTML 拆开看（三省六部就是这样）。"""
    readme = ("<h1>⚔️ 三省六部 · Edict</h1>\n\n<p align=center>\n  <strong>我用 1300 年前的帝国制度，重新设计了 AI 多 Agent 协作架构。<br>结果发现，古人比现代 AI 框架更懂分权制衡。</strong>\n</p>\n"
              "<p><b>Sign up for the waitlist →</b> and more words to make it long enough here</p>\n\n## 为什么\n\n大多数 Multi-Agent 框架的套路是：\n")
    a = repos.inspect(_zip(tmp_path / "edict-main.zip", "edict-main", {"LICENSE": MIT, "README.md": readme}))
    assert a["one_line"].startswith("我用 1300 年前的帝国制度") and "结果发现" in a["one_line"]
    b = repos.inspect(_zip(tmp_path / "d-main.zip", "d-main", {"README.md": "# D\n\nhttps://d.io\n\nBilld Pro\n\n大多数框架的套路是：\n\n跨平台远程桌面控制，实现了类似的功能。\n"}))
    assert b["one_line"] == "跨平台远程桌面控制，实现了类似的功能。"


def test_a_zip_from_the_intake_becomes_an_open_source_card(proj, lib, tmp_path):
    conn = store.connect(proj.db_path)
    try:
        src = _zip(tmp_path / "up.zip", "cool-mcp-main", {"LICENSE": MIT, "README.md": "# cool\n\nAn MCP server that lets agents drive a CAD program."})
        it = intake.receive(conn, proj, src, "cool-mcp-main.zip", by="人")["item"]
        assert intake.get(conn, it["id"])["candidates"][0]["module"] == intake.OSS             # 压缩包：规则先给「工具/开源项目」
        x = repos.take(conn, proj, it["id"], by="agent:a")
        assert (x["code"], x["name"], x["borrow"], x["state"]) == ("O1", "cool-mcp", "能抄", "收着")
        assert (lib / "原件" / "cool-mcp-main.zip").is_file() and not (intake.inbox_dir(proj) / "cool-mcp-main.zip").exists()
        assert intake.get(conn, it["id"])["status"] == "sorted"
        with pytest.raises(store.Refused, match="分拣过"):
            repos.take(conn, proj, it["id"])
        doc = intake.receive(conn, proj, _w(tmp_path / "n.txt"), "说明.txt", by="人")["item"]
        with pytest.raises(store.Refused, match="不是压缩包"):
            repos.take(conn, proj, doc["id"])
        y = repos.write_notes("O1", "它干什么：让 agent 开 CAD。能借：MCP 的写法。怎么用：借思路。", by="agent:a")
        assert y["notes"].startswith("# O1 cool-mcp · 解读") and "能不能借：MIT → 能抄" in y["notes"]
        assert y["state"] == "看过"                                                  # 写了解读就算看过了
    finally:
        conn.close()


def _w(path):
    path.write_text("不是压缩包", encoding="utf-8")
    return path
