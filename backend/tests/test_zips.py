"""全站「看一眼」和看压缩包里面（S1-10 S2-11、工具 S2-10；作者 10-01：「我觉得这个预览功能应该全站可用才对啊」「工具中的那个开源项目应该也要能查看」）。"""
import zipfile

import pytest

import zips

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def _zip(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("proj-main/README.md", "# 项目\n\n一个能让 agent 画图的工具。")
        z.writestr("proj-main/LICENSE", "MIT License\n\nPermission is hereby granted, free of charge")
        z.writestr("proj-main/web/index.html", "<script>alert(1)</script>")
        z.writestr("proj-main/docs/shot.png", PNG)
        z.writestr("proj-main/bin/tool.exe", b"MZ\x00\x00\x00")
    return path


def test_inside_a_zip_without_unpacking(tmp_path):
    z = _zip(tmp_path / "proj-main.zip")
    d = zips.entries(z)
    assert d["readme"] == "README.md" and d["total"] == 5 and [x["name"] for x in d["items"]][0] == "bin/tool.exe"
    assert zips.read(z, "README.md")["text"].startswith("# 项目")
    h = zips.read(z, "web/index.html")
    assert h["kind"] == "text" and "<script>" in h["text"]                       # 网页当文字看，不在本机网页里跑
    assert zips.read(z, "docs/shot.png")["kind"] == "image" and zips.read(z, "bin/tool.exe")["kind"] == "binary"
    assert zips.image(z, "docs/shot.png") == (PNG, "image/png")
    with pytest.raises(FileNotFoundError):
        zips.image(z, "web/index.html")                                          # 不是图片的不当图片给
    with pytest.raises(FileNotFoundError):
        zips.read(z, "../../外面.txt")
    assert not (tmp_path / "proj-main").exists()                                 # 没解开


def test_the_shared_preview_and_the_page_know_zips(proj):
    from fastapi.testclient import TestClient
    from main import create_app
    (proj.root / "工具库" / "开源项目" / "原件").mkdir(parents=True)
    _zip(proj.root / "工具库" / "开源项目" / "原件" / "proj-main.zip")
    with TestClient(create_app(proj)) as client:
        p = client.get("/api/project/preview", params={"path": "工具库/开源项目/原件/proj-main.zip"}).json()
        assert p["kind"] == "zip" and p["zip"]["license"] == "MIT" and p["zip"]["path"] == "工具库/开源项目/原件/proj-main.zip"
        assert client.get("/api/zip", params={"path": "工具库/开源项目/原件/proj-main.zip"}).json()["readme"] == "README.md"
        assert client.get("/api/zip", params={"path": "工具库/开源项目/原件/proj-main.zip", "inner": "没有.md"}).status_code == 404
        assert client.get("/zfiles", params={"path": "工具库/开源项目/原件/proj-main.zip", "inner": "docs/shot.png"}).content == PNG
        assert client.get("/zfiles", params={"path": "工具库/开源项目/原件/proj-main.zip", "inner": "web/index.html"}).status_code == 404
        assert client.get("/api/zip", params={"path": "../外面.zip"}).status_code in (400, 403, 404)
        page = client.get("/").text
    assert "function peekOpen(" in page and "function pathish(" in page and "data-peek=\"资料/_外部资料入口/" in page   # 全站看一眼、入口的「看一眼」
    assert 'optgroup label="内置 · 工具"' in page                                                                   # 去向里有内置的工具
