"""工具库（T 卡）· 自动化答疑（Q）· 工作流（W）：网页只查、只看；干活的是 agent。"""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

import tools
from main import create_app

CARD = """---
编号: {code}
名字: {name}
一句话: 测试用
检查: {check}
在哪: {where}
---
# {code} {name}

## 怎么调
照抄这里
"""


def _lib(tmp_path, monkeypatch, cards):
    lib = tmp_path / "工具库"
    lib.mkdir()
    for code, name, check, where in cards:
        (lib / f"{code} {name}.md").write_text(CARD.format(code=code, name=name, check=check, where=where), encoding="utf-8")
    monkeypatch.setattr(tools, "LIB", lib)                  # 在临时工具库上测，不动真的
    return lib


def test_tool_cards_are_listed_in_number_order_and_checked(proj, tmp_path, monkeypatch):
    py_dir = str(Path(sys.executable).parent)
    _lib(tmp_path, monkeypatch, [("T10", "十号", "python --version", py_dir),
                                 ("T2", "二号", "python --version", py_dir),
                                 ("T3", "找不到", "没有这个程序xyz --version", "")])
    (tools.LIB / "说明.md").write_text("不是卡片", encoding="utf-8")          # 没有 T 编号的不算
    with TestClient(create_app(proj)) as client:
        items = client.get("/api/tools").json()["items"]
        assert [t["code"] for t in items] == ["T2", "T3", "T10"]
        assert items[0]["body"].startswith("# T2 二号") and "照抄这里" in items[0]["body"]
        ok = client.post("/api/tools/T2/check").json()
        assert ok["ok"] is True and "Python" in ok["version"] and ok["path"]
        bad = client.post("/api/tools/T3/check").json()
        assert bad["ok"] is False and "没找到" in bad["msg"]
        assert client.post("/api/tools/T99/check").status_code == 404


def test_real_tool_library_cards_are_well_formed():
    """自带的卡片：编号不重、都写了检查命令和怎么调。"""
    items = tools.list_tools()
    codes = [t["code"] for t in items]
    assert codes[:4] == ["T1", "T2", "T3", "T4"] and len(codes) == len(set(codes))
    ext = [t for t in items if t["kind"] == "外部工具"]
    stack = [t for t in items if t["kind"] == "技术栈"]
    assert ext and all(t["check"] and "## 怎么调" in t["body"] for t in ext)       # 外部工具：写清怎么调
    assert stack and all("## 用在哪" in t["body"] for t in stack)                   # 技术栈：写清用在哪


def test_check_strips_quotes_and_builtin_needs_no_install(proj, tmp_path, monkeypatch):
    py_dir = str(Path(sys.executable).parent)
    lib = _lib(tmp_path, monkeypatch, [("T1", "带引号", 'python -c "print(1.25)"', py_dir)])
    (lib / "T2 内置.md").write_text("---\n编号: T2\n名字: 内置\n类别: 技术栈\n检查:\n---\n# T2 内置\n", encoding="utf-8")
    assert tools.check("T1")["version"] == "1.25"                                  # 引号去掉了，python 真的执行了那句
    assert tools.check("T2") == {"ok": None, "msg": "不用装（内置）"}
    assert [t["kind"] for t in tools.list_tools()] == ["外部工具", "技术栈"]


def test_runs_are_logged_apart_from_notes_and_shown(proj):
    """跑工作流：每圈记进 自动化/日志/，编号 W1-1.1、W1-1.2…；新开一次是 W1-2；笔记本里不多东西。"""
    import runs
    import store
    c = store.connect(proj.db_path)
    try:                                                   # 没有在跑的开工单：报不了「在跑」
        runs.report(c, proj, "W1", by="agent:x", goal="S1-5 S2-2", did="偷跑")
        raise AssertionError("没交给 agent 也记上了")
    except store.Refused as e:
        assert "开工单" in str(e)
    import workorders
    wo = workorders.create(c, proj, "试", [])
    wo["stored"] = "在跑"
    workorders._write(proj, wo)
    a = runs.report(c, proj, "W1", by="agent:x", goal="S1-5 S2-2", did="写了计划 P2", result="计划写完")
    b = runs.report(c, proj, "W1", by="agent:x", run=a["run"], goal="S1-5 S2-2", did="等人点头", status="停了等你")
    n = runs.report(c, proj, "W1", by="agent:x", goal="S1-1 S2-3", did="开始", status="在跑")
    assert (a["code"], b["code"], n["code"]) == ("W1-1.1", "W1-1.2", "W1-2.1")
    for bad in (dict(workflow="W9"), dict(workflow="W1", status="随便"), dict(workflow="W1", run="W1-7")):
        wf = bad.pop("workflow")
        try:
            runs.report(c, proj, wf, by="agent:x", **bad)
            raise AssertionError(bad)
        except store.Refused:
            pass
    st = store.get_state(c, proj)
    assert st["auto"]["code"] == "W1-2" and st["auto"]["status"] == "在跑"          # 在跑的优先
    assert st["auto_settings"]["level"] == 1 and st["auto_settings"]["rounds"] == 5   # 默认半自动、最多 5 圈
    c.close()
    assert (proj.root / "自动化" / "日志" / "W1 自动推进" / "W1-1.md").is_file()
    assert not (proj.root / "笔记").exists()
    with TestClient(create_app(proj)) as client:
        auto = client.get("/api/auto").json()
        assert [w["code"] for w in auto["workflows"]][:1] == ["W1"]
        r1 = next(r for r in auto["runs"] if r["code"] == "W1-1")
        assert r1["status"] == "停了等你" and [x["code"] for x in r1["rounds"]] == ["W1-1.1", "W1-1.2"]
        assert client.put("/api/settings", json={"level": 2, "rounds": 8}).json()["level"] == 2
        assert client.put("/api/settings", json={"level": 5, "rounds": 8}).status_code == 400
        assert client.get("/api/log").json()["entries"][-1]["kind"] == "改了自动化设置"   # 人在网页上改设置：日志里记一条（人的笔记只放人写的）
