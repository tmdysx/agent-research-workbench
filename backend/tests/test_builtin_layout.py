"""统一内置（10-07；作者：「我想统一内置模块，去掉每个模块自己的内置模块统一管理」「每个模块都干净一点，文件分拣可以精确到每个模块的具体文件夹」）：
老样子的 内置/ 搬回模块自己的文件夹、设置和链接跟着改、第三方原件不动、空的进回收站、能重复跑；
清单能勾整个文件夹，新建项目照清单 + 所选模块带，新项目里没有 内置/；启动时发现老样子先存档再搬。测试只碰临时项目。"""
import json

import pytest
from fastapi.testclient import TestClient

import builtin
import new_project
import store
import supervise
import trash
from main import create_app
from project import Project


def _w(root, rel, text="示例"):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    (f.write_bytes if isinstance(text, bytes) else lambda x: f.write_text(x, encoding="utf-8"))(text)
    return f


@pytest.fixture
def old(tmp_path):
    """10-07 以前的样子：到处都有 内置/。"""
    root = tmp_path / "老项目"
    _w(root, "backend/main.py", "# 应用核心\n")
    _w(root, "backend/builtin_resources.json", json.dumps({"version": 1, "paths": []}))
    _w(root, "模板.html", "<html>示例</html>")
    _w(root, "资料/周报/内置/通用/工作台.json", json.dumps({"templates": ["内置/通用/模板/引言.md"]}, ensure_ascii=False))
    _w(root, "资料/周报/内置/通用/模板/引言.md", "# 引言模板")
    _w(root, "资料/周报/内置/论文证据卡.md", "见 [引言模板](通用/模板/引言.md)")
    _w(root, "资料/周报/正文/引言.md", "作者自己的正文")
    _w(root, "资料/文献/内置/科研/来源/sources.lock.json", json.dumps({"local_path": "资料/文献/内置/科研/来源/aris/LICENSE"}, ensure_ascii=False))
    _w(root, "资料/文献/内置/科研/来源/aris/LICENSE", "MIT 原件，写着 资料/文献/内置/科研 也不能改")
    _w(root, "资料/文献/内置/科研/README.md", "上游原文在项目资料/文献/内置/科研/来源")
    _w(root, "资料/天气/内置/样例.md", "天气模板")
    _w(root, "资料/天气/样例.md", "模块里本来就有一份同名的、内容不一样")
    _w(root, "资料/天气/内置/同样.md", "一样的")
    _w(root, "资料/天气/方法/同样.md", "一样的")
    _w(root, "插件/网页终端/内置/安装指南.md", "看 [通用安装](../../../工具库/内置/安装指南/通用安装.md)")
    _w(root, "工具库/内置/安装指南/通用安装.md", "# 通用安装")
    _w(root, "工具库/内置/安装指南/catalog.json", json.dumps({"guide": "工具库/内置/安装指南/通用安装.md"}, ensure_ascii=False))
    _w(root, "README.md", "[安装](工具库/内置/安装指南/通用安装.md)")
    _w(root, "治理/需求/内置/.gitkeep", "")
    _w(root, "笔记/内置/.gitkeep", "")
    _w(root, "资料/PPT/历史/某次/内置/旧.md", "历史里的不搬")
    return root


def _migrate(root):
    p = Project(root)
    c = store.connect(p.db_path)
    store.migrate(c)
    try:
        return builtin.migrate_layout(c, p, by="agent:test")
    finally:
        c.close()


def test_plan_only_reads_and_maps_each_kind(old):
    plan = builtin.plan_layout(old)
    to = {m["from"]: m["to"] for m in plan["moves"]}
    assert to["资料/周报/内置/通用/工作台.json"] == "资料/周报/工作台/工作台.json"
    assert to["资料/周报/内置/论文证据卡.md"] == "资料/周报/方法/论文证据卡.md"
    assert to["资料/文献/内置/科研/README.md"] == "资料/文献/方法/科研/README.md"
    assert to["插件/网页终端/内置/安装指南.md"] == "插件/网页终端/安装指南.md"
    assert to["工具库/内置/安装指南/通用安装.md"] == "工具库/安装指南/通用安装.md"
    assert set(plan["empty"]) == {"治理/需求/内置", "笔记/内置"}
    assert "资料/周报/方法" in plan["listed"] and "资料/周报/工作台" not in plan["listed"]   # 工作台随模块带，不进清单
    assert "资料/PPT/历史/某次/内置" not in plan["folders"]                                   # 历史里的不算
    assert (old / "资料/周报/内置/通用/工作台.json").is_file()                                # 只算不动


def test_migrate_moves_rewrites_lists_and_trashes(old):
    r = _migrate(old)
    assert not builtin.legacy_folders(old)
    assert (old / "资料/周报/工作台/模板/引言.md").read_text(encoding="utf-8") == "# 引言模板"
    cfg = json.loads((old / "资料/周报/工作台/工作台.json").read_text(encoding="utf-8"))
    assert cfg["templates"] == ["工作台/模板/引言.md"]                                       # 模块里的相对路径改了
    assert "(../工作台/模板/引言.md)" in (old / "资料/周报/方法/论文证据卡.md").read_text(encoding="utf-8")   # 相对链接按新位置重算
    assert "(../../工具库/安装指南/通用安装.md)" in (old / "插件/网页终端/安装指南.md").read_text(encoding="utf-8")
    assert "(工具库/安装指南/通用安装.md)" in (old / "README.md").read_text(encoding="utf-8")             # 没搬的说明也跟着改
    assert "资料/文献/方法/科研/来源" in (old / "资料/文献/方法/科研/README.md").read_text(encoding="utf-8")  # 前面是中文字也认得
    lock = json.loads((old / "资料/文献/方法/科研/来源/sources.lock.json").read_text(encoding="utf-8"))
    assert lock["local_path"] == "资料/文献/方法/科研/来源/aris/LICENSE"                     # 来源锁里记的路径改了
    assert "资料/文献/内置/科研" in (old / "资料/文献/方法/科研/来源/aris/LICENSE").read_text(encoding="utf-8")   # 第三方原件一个字不动
    assert (old / "资料/天气/样例.md").read_text(encoding="utf-8").startswith("模块里本来就有")
    assert (old / "资料/天气/方法/样例.md").read_text(encoding="utf-8") == "天气模板"
    assert [m["from"] for m in r["same"]] == ["资料/天气/内置/同样.md"]                       # 一样的只留一份
    assert (old / "资料/PPT/历史/某次/内置/旧.md").is_file()
    marks = builtin.read_marks(old)["paths"]
    assert {"资料/周报/方法", "资料/文献/方法", "资料/天气/方法"} <= set(marks)
    assert r["trashed"] and not (old / "治理/需求/内置").exists() and not (old / "资料/周报/内置").exists()
    assert any(x["code"] == r["trashed"] for x in trash.read(Project(old)))
    rec = json.loads((old / builtin.LAYOUT_RECORD).read_text(encoding="utf-8"))
    assert len(rec) == 1 and any(m["from"] == "资料/周报/内置/论文证据卡.md" for m in rec[0]["moves"])
    assert supervise._moved_away(Project(old), "资料/周报/内置/论文证据卡.md")             # 监管认得是搬了
    again = _migrate(old)
    assert again["rounds"] == 0 and len(json.loads((old / builtin.LAYOUT_RECORD).read_text(encoding="utf-8"))) == 1


def test_different_content_with_same_name_is_renamed_not_overwritten(old):
    _w(old, "资料/天气/内置/方法卡.md", "模板版")
    _w(old, "资料/天气/方法/方法卡.md", "模块里已有的版本")
    r = _migrate(old)
    assert (old / "资料/天气/方法/方法卡.md").read_text(encoding="utf-8") == "模块里已有的版本"
    assert (old / "资料/天气/方法/方法卡（内置）.md").read_text(encoding="utf-8") == "模板版"
    assert any(m["to"].endswith("方法卡（内置）.md") for m in r["renamed"])


def test_folder_tick_carries_everything_inside_and_locks_children(old):
    _migrate(old)
    _w(old, "资料/天气/手册/第一章.md", "一")
    _w(old, "资料/天气/手册/图/a.png", b"\x89PNG")
    m = builtin.read_marks(old)
    builtin.replace_marks(old, m["paths"] + ["资料/天气/手册"], m["revision"])
    state = builtin.mark_state(old, "资料/天气/手册/第一章.md")
    assert state["state"] == "required" and state["origin"] == "folder" and not state["toggle_allowed"]
    assert builtin.mark_state(old, "资料/天气/手册")["kind"] == "folder"
    assert builtin.mark_state(old, "资料/周报/工作台/工作台.json")["origin"] == "module"
    paths = builtin.preview(old)["copied_paths"]
    assert {"资料/天气/手册/第一章.md", "资料/天气/手册/图/a.png", "资料/周报/工作台/模板/引言.md"} <= set(paths)
    assert "资料/周报/正文/引言.md" not in paths                                              # 没勾的正文不带
    assert not any("/内置/" in x for x in paths)


def test_new_project_has_no_builtin_folders_and_keeps_folder_ticks(old, tmp_path):
    _migrate(old)
    target = tmp_path / "下一个"
    new_project.make(target, old, business_modules=["天气"])
    assert not [d for d in target.rglob("内置") if d.is_dir()]
    assert (target / "资料/天气/方法/样例.md").is_file() and not (target / "资料/周报").exists()   # 只带选了的业务模块
    marks = json.loads((target / builtin.MARKS_FILE).read_text(encoding="utf-8"))["paths"]
    assert "资料/天气/方法" in marks                                                          # 勾的文件夹，下一代接着带
    skip = tmp_path / "不选天气"
    new_project.make(skip, old, business_modules=[])
    assert not (skip / "资料/天气/方法").exists()


def test_new_module_gets_no_builtin_folder(tmp_path):
    p = Project(tmp_path / "新的")
    with TestClient(create_app(p)) as client:
        assert client.post("/api/modules", json={"name": "天气"}).status_code == 200
    assert (p.materials / "天气").is_dir() and not (p.materials / "天气" / "内置").exists()
    assert not [d for d in p.root.rglob("内置") if d.is_dir()]


def test_startup_saves_a_snapshot_then_migrates_old_layout(old):
    p = Project(old)
    with TestClient(create_app(p)) as client:
        client.get("/api/ping")
    assert not builtin.legacy_folders(old)
    assert (old / "资料/周报/工作台/工作台.json").is_file()
    assert list((old / "存档").glob("C* 统一内置前"))                                       # 搬之前先存了一档


def test_locked_file_brings_its_business_module_by_default(old, tmp_path):
    """作者 10-07：「我发现加锁之后的模块也无法复制到新文件夹」——业务模块里有加锁的东西，新建时这个模块默认选上；明确取消才不带。"""
    _migrate(old)
    _w(old, "资料/宣传片/成果/片子.mp4", b"\x00\x00\x00\x18ftypmp42")
    m = builtin.read_marks(old)
    builtin.replace_marks(old, m["paths"] + ["资料/宣传片/成果/片子.mp4"], m["revision"])
    options = {o["name"]: o["selected"] for o in new_project.preview(old)["business_options"]}
    assert options["宣传片"] is True
    target = tmp_path / "默认"
    new_project.make(target, old)                                       # 不指定（新项目.bat 也是这样）
    assert (target / "资料/宣传片/成果/片子.mp4").read_bytes() == b"\x00\x00\x00\x18ftypmp42"
    off = tmp_path / "明确不要"
    new_project.make(off, old, business_modules=[n for n, on in options.items() if on and n != "宣传片"])
    assert not (off / "资料/宣传片").exists()
