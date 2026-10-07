"""插件（总蓝图 S1-11 玩家自己组装）：插件/<名字>/插件.md 一份卡；检查过了、人点了启用，才用它把 PPT 转成 PDF 照原样显示。
作者 2026-09-29：「就是不装插件就这样显示，装了之后能不能原版显示?」
测试里用一个假插件（Python 小脚本假装转换），不真开 PowerPoint。"""
import sys

import pytest
from fastapi.testclient import TestClient

import plugins
from main import create_app

CONV = r'''import sys
from pathlib import Path
n = Path(__file__).with_name("转了几次.txt")
n.write_text(str(int(n.read_text()) + 1 if n.exists() else 1))
src, out = sys.argv[1], sys.argv[2]
Path(out).write_bytes(b"%PDF-1.4 fake " + Path(src).read_bytes()[:10] if "坏" not in src else b"not a pdf")
'''


@pytest.fixture
def plug(tmp_path, monkeypatch):
    d = tmp_path / "插件"
    one = d / "假PPT"
    one.mkdir(parents=True)
    (one / "转.py").write_text(CONV, encoding="utf-8")
    py = f'"{sys.executable}"'
    (one / "插件.md").write_text(
        "---\n名字: 假PPT\n一句话: 测试用\n版本: 1\n管哪些文件: .pptx .ppt\n转成: pdf\n"
        f"检查: {py} -c \"print('用 假的')\"\n转换: {py} 转.py {{输入}} {{输出}}\n---\n# 假PPT\n", encoding="utf-8")
    monkeypatch.setattr(plugins, "DIR", d)
    plugins._CHECKED.clear()
    return one


def _times(one):
    f = one / "转了几次.txt"
    return int(f.read_text()) if f.exists() else 0


def test_list_check_and_convert_cache(proj, plug):
    assert [x["name"] for x in plugins.list_plugins()] == ["假PPT"]
    assert plugins.check("假PPT") == {"ok": True, "msg": "用 假的"}
    d = proj.materials / "汇报"
    d.mkdir(parents=True)
    src = d / "讲 稿.pptx"                           # 名字里有空格也照样传得过去
    src.write_bytes(b"PPTXDATA-0123456789")
    assert plugins.converter_for(src)["name"] == "假PPT"
    assert plugins.converter_for(d / "a.docx") is None
    f = plugins.convert(proj, "假PPT", src)
    assert f.parent == proj.index_dir / "预览缓存" and f.read_bytes().startswith(b"%PDF-1.4 fake PPTXDATA")
    assert plugins.convert(proj, "假PPT", src) == f and _times(plug) == 1      # 没改过：不重转
    src.write_bytes(b"PPTXDATA-changed")
    assert plugins.convert(proj, "假PPT", src) != f and _times(plug) == 2      # 改了：重转
    assert src.read_bytes() == b"PPTXDATA-changed"                            # 原文件不动


def test_bad_output_is_not_kept(proj, plug):
    d = proj.materials / "汇报"
    d.mkdir(parents=True)
    (d / "坏.pptx").write_bytes(b"x")
    with pytest.raises(RuntimeError, match="没转出来"):
        plugins.convert(proj, "假PPT", d / "坏.pptx")
    assert list((proj.index_dir / "预览缓存").iterdir()) == []              # 转坏的不留


def test_check_fails_when_program_missing(plug):
    md = plug / "插件.md"
    md.write_text(md.read_text(encoding="utf-8").replace("print('用 假的')", "import sys; print('没有 PowerPoint'); sys.exit(1)"),
                  encoding="utf-8")
    assert plugins.check("假PPT") == {"ok": False, "msg": "没有 PowerPoint"}


def test_only_after_human_enables(proj, plug):
    d = proj.materials / "汇报"
    d.mkdir(parents=True)
    (d / "g.pptx").write_bytes(b"PPTX")
    (d / "老.ppt").write_bytes(b"\xd0\xcf\x11\xe0 old")
    (d / "a.docx").write_bytes(b"PK")
    with TestClient(create_app(proj)) as client:
        pv = client.get("/api/modules/汇报/preview", params={"path": "g.pptx"}).json()
        assert pv["plugin"] == {"name": "假PPT", "one_line": "测试用", "ok": True, "msg": "用 假的", "enabled": False, "ready": False}
        assert client.get("/files/汇报/g.pptx", params={"as": "pdf"}).status_code == 403    # 没启用不转
        assert _times(plug) == 0
        assert client.post("/api/plugins/假PPT/enable", json={"on": True}).json()["enabled"] is True
        r = client.get("/files/汇报/g.pptx", params={"as": "pdf"})
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert r.headers["content-disposition"].startswith("inline") and r.content.startswith(b"%PDF")
        assert client.get("/api/project/preview", params={"path": "资料/汇报/g.pptx"}).json()["plugin"]["ready"] is True
        old = client.get("/api/modules/汇报/preview", params={"path": "老.ppt"}).json()      # 老 .ppt：核心列不出字，插件照样能转
        assert old["kind"] == "pptx" and "插件" in old["error"] and old["plugin"]["enabled"] is True
        assert client.post("/api/plugins/convert", json={"module": "汇报", "path": "老.ppt"}).json()["ok"] is True
        assert client.get("/files/汇报/a.docx", params={"as": "pdf"}).status_code == 404
        lst = client.get("/api/plugins").json()
        assert lst[0]["name"] == "假PPT" and lst[0]["enabled"] is True and lst[0]["folder"] == "插件/假PPT/"
        assert client.post("/api/plugins/没这个/enable", json={"on": True}).status_code == 404
