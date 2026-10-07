"""工具安装能力同一正本、版本、内置继承与路径边界。只用临时项目。"""
import json
import os
import shutil
from pathlib import Path

import anyio
import pytest
from fastapi.testclient import TestClient

import tool_guides
from conftest import BACKEND
from main import create_app

BASE = "工具库/安装指南/"                      # 10-07 统一内置：工具库/内置/ 去掉了这一层


def seed(root, text="# 软件\n\n输入→调用→输出。\n", items=None):
    folder = root / BASE
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "软件.md").write_bytes(text.encode("utf-8"))
    records = items if items is not None else [{"id": "sample", "name": "样例", "name_en": "Sample",
        "group": "科研工具", "summary": "临时非科研项目也可复用", "guide": BASE + "软件.md",
        "official": "https://example.com/manual", "download": "https://example.com/download",
        "targets": ["tool:T1", "plugin:示例"]}]
    (folder / "catalog.json").write_text(json.dumps({"version": 1, "items": records}, ensure_ascii=False), encoding="utf-8")
    return records


def test_readonly_no_install_guess_and_version_tracks_real_changes(proj, monkeypatch):
    import tools
    monkeypatch.setattr(tools, "check", lambda *a: pytest.fail("读取指南不能执行工具检查"))
    seed(proj.root)
    with TestClient(create_app(proj)) as client:
        old = client.get("/api/tools/guides/sample").json()
        catalog = client.get("/api/tools/guides").json()
        assert catalog["errors"] == [] and catalog["items"][0]["revision"] == old["revision"]
        assert "installed" not in old and "ok" not in old
        assert old["targets"] == ["tool:T1", "plugin:示例"]
        (proj.root / old["path"]).write_bytes("# 最新人工修改\n".encode("utf-8"))
        new = client.get("/api/tools/guides/sample").json()
        assert new["text"] == "# 最新人工修改\n" and new["revision"] != old["revision"]
        assert client.get("/api/tools/guides/unknown").status_code == 404
        assert client.get("/api/tools/guides/document", params={"path": old["path"]}).json() == tool_guides.document(proj.root, old["path"])


def test_resources_only_approved_builtin_docs_images_and_source_preserved(proj):
    text = "# 图\n![四步](图.svg)\n[另页](子页.md)\n[官方](https://example.com)\n![越界](../../../私密.png)\n[危险](javascript:alert(1))\n"
    seed(proj.root, text)
    (proj.root / BASE / "图.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    (proj.root / BASE / "子页.md").write_text("# 子页", encoding="utf-8")
    got = tool_guides.read(proj.root, "sample")
    assert got["text"] == text
    assert got["resources"] == [{"source": "图.svg", "target": BASE + "图.svg", "kind": "image"},
                               {"source": "子页.md", "target": BASE + "子页.md", "kind": "document"}]
    assert [x["source"] for x in got["resource_errors"]] == ["../../../私密.png"]


@pytest.mark.parametrize("path", ["../README.md", "C:/secret.md", "/secret.md", "自动化/agent/G1.md",
    BASE + "../secret.md", BASE + "foo:stream.md", BASE + ".hidden.md", BASE + "..\\secret.md"])
def test_document_path_rejects_outside_hidden_and_streams(proj, path):
    seed(proj.root)
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/tools/guides/document", params={"path": path}).status_code == 400


def test_linked_directory_is_rejected_even_when_it_points_to_allowed_folder(proj, tmp_path):
    seed(proj.root)
    base = proj.root / BASE
    link = base / "联接"
    real = tmp_path / "真实"
    real.mkdir(); (real / "软件.md").write_text("秘密", encoding="utf-8")
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("本机无法创建链接")
        import subprocess
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(real)], capture_output=True)
        if result.returncode:
            pytest.skip("本机无法创建临时目录联接")
    with pytest.raises(ValueError, match="链接|联接"):
        tool_guides.document(proj.root, BASE + "联接/软件.md")


def test_missing_conflicting_and_invalid_catalog_records_do_not_become_facts(proj):
    rows = seed(proj.root)
    rows += [{**rows[0], "id": "missing", "guide": BASE + "不存在.md"},
             {**rows[0], "id": "conflict", "summary": "甲"}, {**rows[0], "id": "conflict", "summary": "乙"},
             {**rows[0], "id": "danger", "official": "javascript:alert(1)"}]
    seed(proj.root, items=rows)
    got = tool_guides.listing(proj.root)
    assert [x["id"] for x in got["items"]] == ["sample", "missing"]
    assert got["items"][1]["missing"] and got["items"][1]["revision"] == ""
    assert len(got["errors"]) == 4
    (proj.root / BASE / "catalog.json").write_text("broken JSON", encoding="utf-8")
    bad = tool_guides.listing(proj.root)
    assert bad["items"] == [] and bad["errors"]


def test_legacy_empty_project_remains_readable(proj):
    assert tool_guides.listing(proj.root) == {"version": 1, "items": [], "errors": []}
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/tools").status_code == 200
        assert client.get("/api/tools/catalog").status_code == 200
        assert client.get("/api/tools/links").status_code == 200


def test_real_mcp_and_web_return_identical_document_without_database_index(proj):
    from test_mcp import _call
    seed(proj.root)
    backend = proj.root / "backend"
    shutil.copytree(BACKEND, backend, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    listed, read, linked = anyio.run(_call, proj, [("list_tool_guides", {}),
        ("read_tool_guide", {"key": "sample"}), ("read_tool_guide", {"path": BASE + "软件.md"})], backend)
    with TestClient(create_app(proj)) as client:
        assert json.loads(listed) == client.get("/api/tools/guides").json()
        assert json.loads(read) == client.get("/api/tools/guides/sample").json()
        assert json.loads(linked) == client.get("/api/tools/guides/document", params={"path": BASE + "软件.md"}).json()


def test_builtin_guides_survive_two_new_projects_without_software_binaries(tmp_path):
    import new_project
    src = tmp_path / "种子"
    src.mkdir(); seed(src)
    (src / "工具库/下载/本机Blender").mkdir(parents=True)
    (src / "工具库/下载/本机Blender/blender.exe").write_bytes(b"private-binary")
    first, second = tmp_path / "新项目1", tmp_path / "新项目2"
    new_project.make(first, src=src)
    new_project.make(second, src=first)
    assert tool_guides.read(second, "sample")["text"] == tool_guides.read(src, "sample")["text"]
    assert not (first / "工具库/下载/本机Blender/blender.exe").exists()
    assert not (second / "工具库/下载/本机Blender/blender.exe").exists()


def test_app_images_use_existing_local_builtin_files_and_keep_source(proj):
    rows = seed(proj.root)
    image = proj.root / BASE / "应用图片" / "官方.svg"
    image.parent.mkdir(); image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    rows[0].update(image=BASE + "应用图片/官方.svg", image_kind="icon", image_source="https://example.com/brand")
    seed(proj.root, items=rows)
    got = tool_guides.listing(proj.root)
    assert not got["errors"] and got["items"][0]["image"] == BASE + "应用图片/官方.svg"
    assert got["items"][0]["image_source"] == "https://example.com/brand"
    rows[0]["image"] = "https://example.com/remote.svg"
    seed(proj.root, items=rows)
    invalid = tool_guides.listing(proj.root)
    assert "image" not in invalid["items"][0] and invalid["errors"]
    rows[0]["image"] = BASE + "../private.svg"
    seed(proj.root, items=rows)
    assert "image" not in tool_guides.listing(proj.root)["items"][0]


def test_linked_official_image_preserves_outer_link_and_resolves_inner_image(proj):
    seed(proj.root, "[![原样官方标识](logo.svg)](https://example.com/official)\n")
    (proj.root / BASE / "logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    got = tool_guides.read(proj.root, "sample")
    assert got["resources"] == [{"source": "logo.svg", "target": BASE + "logo.svg", "kind": "image"}]
    assert got["resource_errors"] == []
    assert "https://example.com/official" in got["text"]


def test_original_asset_license_can_be_read_as_plain_text_in_the_same_view(proj):
    seed(proj.root, "[原许可](LICENSE.txt)\n")
    original = "Copyright Original author\n\nRedistribution permitted under conditions.\n"
    (proj.root / BASE / "LICENSE.txt").write_bytes(original.encode("utf-8"))
    doc = tool_guides.read(proj.root, "sample")
    assert doc["resources"] == [{"source": "LICENSE.txt", "target": BASE + "LICENSE.txt", "kind": "document"}]
    assert tool_guides.document(proj.root, BASE + "LICENSE.txt")["text"] == original


def test_region_routes_are_explicit_keep_default_and_share_web_mcp_source(proj):
    from test_mcp import _call
    rows = seed(proj.root)
    (proj.root / BASE / "国内.md").write_text("# 国内\n镜像下载不等于账号可用。", encoding="utf-8")
    (proj.root / BASE / "国外.md").write_text("# 国外\n从官方入口安装。", encoding="utf-8")
    rows[0]["routes"] = [{"id": "cn", "label": "国内方案", "guide": BASE + "国内.md"},
                          {"id": "global", "label": "国外方案", "guide": BASE + "国外.md"}]
    seed(proj.root, items=rows)
    backend = proj.root / "backend"
    shutil.copytree(BACKEND, backend, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    listed, read = anyio.run(_call, proj, [("list_tool_guides", {}),
        ("read_tool_guide", {"key": "sample", "route": "cn"})], backend)
    with TestClient(create_app(proj)) as client:
        assert json.loads(listed) == client.get("/api/tools/guides").json()
        domestic = client.get("/api/tools/guides/sample", params={"route": "cn"}).json()
        assert json.loads(read) == domestic
        assert domestic["text"].startswith("# 国内") and domestic["selected_route"] == "cn"
        assert domestic["targets"] == rows[0]["targets"] and "installed" not in domestic
        assert client.get("/api/tools/guides/sample").json()["text"].startswith("# 软件")
        assert client.get("/api/tools/guides/sample", params={"route": "missing"}).status_code == 404
        previous = domestic["revision"]
        (proj.root / BASE / "国内.md").write_text("# 国内新正文", encoding="utf-8")
        assert client.get("/api/tools/guides/sample", params={"route": "cn"}).json()["revision"] != previous


def test_conflicting_missing_or_unsafe_routes_and_logo_never_become_facts(proj):
    rows = seed(proj.root)
    rows[0].update(logo="https://example.com/remote.svg", routes=[
        {"id": "cn", "label": "甲", "guide": BASE + "软件.md"},
        {"id": "cn", "label": "乙", "guide": BASE + "软件.md"},
        {"id": "unknown", "label": "缺文件", "guide": BASE + "无.md"},
        {"id": "bad", "label": "坏入口", "guide": BASE + "软件.md", "download": "javascript:alert(1)"}])
    seed(proj.root, items=rows)
    catalog = tool_guides.listing(proj.root)
    item = catalog["items"][0]
    assert "logo" not in item
    assert [x["id"] for x in item["routes"]] == ["unknown"]
    assert item["routes"][0]["missing"] and not item["routes"][0]["revision"]
    assert len(catalog["errors"]) == 5
    with pytest.raises(KeyError):
        tool_guides.read(proj.root, "sample", "cn")
    with pytest.raises(ValueError):
        tool_guides.read(proj.root, "sample", "unknown")


def test_resource_section_preserves_local_guide_without_install_targets(proj):
    rows = seed(proj.root)
    logo = proj.root / BASE / "logo.svg"
    logo.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    rows[0].update(section="s:oss", targets=[], logo=BASE + "logo.svg", logo_source="https://example.com/brand")
    seed(proj.root, items=rows)
    item = tool_guides.listing(proj.root)["items"][0]
    assert item["section"] == "s:oss" and item["targets"] == [] and item["logo"] == BASE + "logo.svg"
    rows[0]["targets"] = ["tool:T1"]
    seed(proj.root, items=rows)
    bad = tool_guides.listing(proj.root)
    assert bad["items"] == [] and "不能关联安装检查" in bad["errors"][0]["message"]


def test_original_official_ico_can_be_referenced_without_reencoding(proj):
    rows = seed(proj.root)
    logo = proj.root / BASE / "official.ico"
    original = b"\x00\x00\x01\x00\x00\x00"
    logo.write_bytes(original)
    rows[0]["logo"] = BASE + "official.ico"
    seed(proj.root, items=rows)
    got = tool_guides.listing(proj.root)
    assert got["errors"] == [] and got["items"][0]["logo"] == BASE + "official.ico"
    assert logo.read_bytes() == original
