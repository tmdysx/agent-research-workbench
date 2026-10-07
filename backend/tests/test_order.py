"""目录两种排法：结构 · 时间（作者 10-01：「蓝图和任何的目录都有有两中排序方式，一种是结构，一种是时间，这个很重要，方便查验」）。
排是网页里排的；这里查两样：目录给了排时间要用的修改时间，网页上每个模块目录、计划页都有那个切换。"""
import time


def test_every_file_in_a_directory_carries_its_time(proj):
    import files
    d = proj.materials / "文献" / "子"
    d.mkdir(parents=True)
    (d / "旧.md").write_text("旧", encoding="utf-8")
    time.sleep(0.02)
    (proj.materials / "文献" / "新.md").write_text("新", encoding="utf-8")
    t = files.tree(proj, "文献")
    flat, stack = [], list(t["items"])
    while stack:
        n = stack.pop()
        stack += n.get("children") or []
        if not n["dir"]:
            flat.append(n)
    assert {n["name"] for n in flat} >= {"旧.md", "新.md"} and all(n.get("mtime") for n in flat)
    by = {n["name"]: n["mtime"] for n in flat}
    assert by["新.md"] >= by["旧.md"]


def test_the_page_has_the_switch_on_every_directory_and_on_plans(proj):
    from fastapi.testclient import TestClient
    from main import create_app
    with TestClient(create_app(proj)) as client:
        page = client.get("/").text
    assert "ordSeg('m:' + m.name)" in page and "ordSeg('plans')" in page and "treeByTime" in page
    assert "k === 'plans' ? 'time' : 'struct'" in page            # 计划没选过还是按时间（作者 09-29 选的），别的默认按结构
