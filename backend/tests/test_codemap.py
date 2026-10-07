"""代码地图（S1-1 S2-21；作者 10-02「我想做的可视化是这个」）：后台给的文件和行数、全文、搜索、函数和谁用到它、git 改过几次和没交的改动。"""
import subprocess

import pytest
from fastapi.testclient import TestClient

import codemap
import files
import vcs
from main import create_app


def _code(proj):
    d = proj.materials / "代码"
    (d / "子").mkdir(parents=True)
    (d / "a.py").write_text('"""算账的。"""\n\n\ndef foo(x):\n    return x + 1\n\n\nclass Bar:\n    pass\n', encoding="utf-8")
    (d / "子" / "b.py").write_text('"""用 foo 的。"""\nfrom a import foo\n\nprint(foo(2))  # 用一下\n', encoding="utf-8")
    (d / "c.js").write_text("// 网页那边\nfunction hello() { return '你好'; }\nconst bye = () => 1;\n", encoding="utf-8")
    (d / "说明.md").write_text("# 不是程序\n", encoding="utf-8")
    return d


def test_files_text_search_and_who_uses_what(proj):
    _code(proj)
    d = codemap.listing(proj, "代码")
    got = {f["rel"]: f for f in d["files"]}
    assert set(got) == {"资料/代码/a.py", "资料/代码/子/b.py", "资料/代码/c.js"}            # 只要程序文件
    a = got["资料/代码/a.py"]
    assert a["lines"] == 9 and a["lang"] == "py" and a["says"] == "算账的。" and a["dir"] == "资料/代码"
    assert got["资料/代码/子/b.py"]["dir"] == "资料/代码/子" and d["lines"] == 9 + 4 + 3
    t = codemap.text(proj, "资料/代码/c.js")
    assert t["lines"][1] == "function hello() { return '你好'; }" and not t["cut"]
    with pytest.raises(files.Denied):
        codemap.text(proj, "../外面.py")                                                  # 出不了项目
    s = codemap.search(proj, "代码", "FOO")
    assert {(h["rel"], h["line"]) for h in s["hits"]} == {("资料/代码/a.py", 4), ("资料/代码/子/b.py", 1), ("资料/代码/子/b.py", 2), ("资料/代码/子/b.py", 4)}
    assert codemap.search(proj, "代码", "c.j")["names"] == ["资料/代码/c.js"]
    assert codemap.defs(proj, "资料/代码/a.py")["defs"] == [{"name": "foo", "line": 4, "kind": "函数"}, {"name": "Bar", "line": 8, "kind": "类"}]
    assert [x["name"] for x in codemap.defs(proj, "资料/代码/c.js")["defs"]] == ["hello", "bye"]
    u = codemap.uses(proj, "代码", "foo", "资料/代码/a.py", 4)
    assert [(h["rel"], h["line"]) for h in u["hits"]] == [("资料/代码/子/b.py", 1), ("资料/代码/子/b.py", 2), ("资料/代码/子/b.py", 4)]   # 定义那行不算；说明里提到的也算（按字找）
    with pytest.raises(files.Denied):
        codemap.uses(proj, "代码", "foo(); rm")


def test_git_history_and_uncommitted_changes(proj):
    if vcs._git() is None:
        pytest.skip("这台电脑没有 git")
    d = _code(proj)
    git = vcs._git()
    subprocess.run([git, "init", "-q", str(proj.root)], check=True)
    assert vcs.commit(proj, ["资料"], agent="agent:甲", message="J1 · 试")
    (d / "a.py").write_text('"""算账的。"""\n\n\ndef foo(x):\n    return x + 2\n\n\nclass Bar:\n    pass\n# 加一行\n', encoding="utf-8")
    (d / "新.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    got = {f["rel"]: f for f in codemap.listing(proj, "代码")["files"]}
    assert got["资料/代码/a.py"]["commits"] == 1 and got["资料/代码/a.py"]["who"] == "agent:甲"
    assert got["资料/代码/新.py"]["commits"] == 0
    m = codemap.diff(proj)["marks"]
    assert m["资料/代码/a.py"] == [[5, 1, "改"], [10, 1, "加"]]
    assert m["资料/代码/新.py"] == [[1, 2, "新"]]


def test_the_page_gets_it_through_the_api(proj):
    _code(proj)
    with TestClient(create_app(proj)) as client:
        d = client.get("/api/modules/代码/codemap/files").json()
        assert len(d["files"]) == 3
        assert client.get("/api/codemap/text", params={"path": "资料/代码/a.py"}).json()["lines"][3] == "def foo(x):"
        assert client.get("/api/codemap/text", params={"path": "../x.py"}).status_code >= 400
        assert client.get("/api/modules/代码/codemap/search", params={"q": "hello"}).json()["hits"][0]["line"] == 2
        assert client.get("/api/codemap/defs", params={"path": "资料/代码/a.py"}).json()["defs"][0]["name"] == "foo"
        assert len(client.get("/api/modules/代码/codemap/uses", params={"word": "foo", "path": "资料/代码/a.py", "line": 4}).json()["hits"]) == 3
        assert "marks" in client.get("/api/codemap/diff").json()
        assert client.get("/代码地图.js").status_code == 200


def test_importance_puts_what_everyone_uses_on_top(proj):
    """重要性金字塔（S1-1 S2-24；作者 10-03「最重要的核心代码放最上面，这样依次往下」）：被用得多的、入口、有测试守着的分高；测试、文字说明在最底下。"""
    d = proj.materials / "代码"
    (d / "tests").mkdir(parents=True)
    (d / "core.py").write_text("X = 1\n", encoding="utf-8")
    for n in ("a", "b", "c"):
        (d / f"{n}.py").write_text(f"import core\nfrom core import X\n\n\ndef {n}():\n    return X\n", encoding="utf-8")
    (d / "main.py").write_text("import a\nimport b\n\nif __name__ == \"__main__\":\n    a.a()\n", encoding="utf-8")
    (d / "page.html").write_text('<script src="app.js"></script>\n', encoding="utf-8")
    (d / "app.js").write_text("const x = 1;\n", encoding="utf-8")
    (d / "tests" / "test_core.py").write_text("import core\nimport a\n", encoding="utf-8")
    (d / "说明.md").write_text("用 core.py 和 main.py\n", encoding="utf-8")
    got = {f["name"]: f for f in codemap.listing(proj, "代码")["files"]}
    core = got["core.py"]
    assert core["fan_in"] == 3 and core["tests"] == 1 and set(core["users"]) == {"资料/代码/a.py", "资料/代码/b.py", "资料/代码/c.py"}
    assert got["main.py"]["entry"] and got["app.js"]["fan_in"] == 1 and got["a.py"]["fan_in"] == 1
    assert got["test_core.py"]["is_test"]
    rank = sorted(got, key=lambda n: -got[n]["score"])
    assert rank[0] == "core.py" and rank[-1] in ("test_core.py", "c.py")
    assert got["test_core.py"]["score"] < got["c.py"]["score"]
