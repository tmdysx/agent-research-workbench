"""外部资料入口 Intake：进来先放外部资料入口、同一个文件只存一份、人点了才挪；新项目只复制程序本身。"""
import pytest
from fastapi.testclient import TestClient

import intake
import new_project
import store
from main import create_app
from project import CODE_DIR

PDF = b"%PDF-1.4 fake paper"
PY = b"print('hello')\n"


def test_upload_dedupe_rule_and_sort(proj):
    with TestClient(create_app(proj)) as client:
        r = client.post("/api/inbox", files=[("files", ("论文A.pdf", PDF)), ("files", ("子目录/run.py", PY))]).json()
        assert sorted(r["added"]) == ["run.py", "论文A.pdf"] and r["dup"] == []
        assert (proj.materials / "_外部资料入口" / "run.py").read_bytes() == PY
        r = client.post("/api/inbox", files=[("files", ("另一个名字.pdf", PDF))]).json()
        assert r["dup"] == ["论文A.pdf"] and r["added"] == []          # 内容一样：不存第二份
        s = client.get("/api/state").json()
        assert s["inbox"] == 2
        assert "_外部资料入口" not in [m["name"] for m in s["modules"]]         # 外部资料入口不算模块
        items = {i["name"]: i for i in client.get("/api/inbox").json()["items"]}
        assert items["run.py"]["candidates"][0] == {"module": "源代码", "conf": "高", "reason": "是代码文件", "by": "规则"}
        assert items["论文A.pdf"]["candidates"][0]["module"] == "文献"
        r = client.post(f"/api/inbox/{items['run.py']['id']}/sort", json={"module": "源代码"})
        assert r.status_code == 200 and len(r.json()["items"]) == 1
        assert (proj.materials / "源代码" / "run.py").read_bytes() == PY
        assert not (proj.materials / "_外部资料入口" / "run.py").exists()
        assert client.post(f"/api/inbox/{items['run.py']['id']}/sort", json={"module": "文献"}).status_code == 400
        assert client.get("/api/state").json()["inbox"] == 1


def test_agent_suggestions_are_checked(proj):
    with TestClient(create_app(proj)) as client:
        client.post("/api/inbox", files=[("files", ("x.pdf", PDF))])
    c = store.connect(proj.db_path)
    iid = intake.waiting(c)[0]["id"]
    ok = intake.suggest(c, iid, [{"module": "文献", "confidence": "高", "reason": "首页有期刊名"},
                                 {"module": "论文", "confidence": "低", "reason": "也可能是自己的稿子"}], by="agent:x")
    assert [x["module"] for x in ok["candidates"]] == ["文献", "论文"] and ok["candidates"][0]["by"] == "agent:x"
    for bad in ([{"module": "不存在", "confidence": "高", "reason": "r"}],
                [{"module": "文献", "confidence": "85%", "reason": "r"}],
                [{"module": "文献", "confidence": "高", "reason": ""}],
                []):
        with pytest.raises(store.Refused):
            intake.suggest(c, iid, bad, by="agent:x")
    c.close()


def test_files_dropped_straight_into_the_folder_count_too(proj):
    import project as P
    P.ensure_skeleton(proj)
    c = store.connect(proj.db_path)
    (proj.materials / "_外部资料入口").mkdir(parents=True)
    (proj.materials / "_外部资料入口" / "手放的.bib").write_text("@article{x}", encoding="utf-8")
    assert store.get_state(c, proj)["inbox"] == 1
    it = intake.waiting(c)[0]
    assert it["created_by"] == "文件夹里发现的" and it["candidates"][0]["module"] == "文献"
    (proj.materials / "_外部资料入口" / "手放的.bib").unlink()
    assert store.get_state(c, proj)["inbox"] == 0
    c.close()


def test_new_project_copies_only_the_app(tmp_path):
    target = tmp_path / "第二篇论文"
    done = new_project.make(target, CODE_DIR)
    assert (target / "backend" / "main.py").is_file() and (target / "模板.html").is_file()
    assert (target / "启动.bat").is_file() and (target / ".mcp.json").is_file()
    assert (target / "技能库" / "自动化科研交互界面" / "SKILL.md").is_file()
    assert (target / "快捷指令" / "交接给新agent.md").is_file()
    assert '"plansDirectory": "./治理/计划"' in (target / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert (target / "工具库" / "T1 LaTeX.md").is_file()                         # 外部工具卡带上
    assert (target / "工具库" / "T5 FastAPI + uvicorn.md").is_file()            # 应用运行需要的技术栈卡按显式资源清单保留
    assert (target / "backend/tests/test_intake.py").is_file()                  # 应用回归测试属于核心
    assert (target / "资料/测试/工作台/工作台.json").is_file()                   # 新项目带通用测试模块的工作台（10-07 起不再有 内置/）
    assert not [d for d in target.rglob("内置") if d.is_dir()]
    assert [f.name for f in (target / "索引").iterdir()] == ["state.db"]    # 新项目自己新建的库（初始化入门示例用），不是这个项目的
    for mine in ("蓝图.json", "工具库/下载/Blender", "资料/测试/建模"):
        assert not (target / mine).exists(), mine
    for module in ("想法", "蓝图", "戒律", "源代码", "测试", "文献", "论文"):          # 固定七个模块都在，里面没有 内置/（10-07 统一内置）
        assert (target / "资料" / module).is_dir() and not (target / "资料" / module / "内置").exists()
    # AGENTS.md 带的是空白的那份（哪个项目都用得上的规矩 + 技能目录），不带这个项目自己的项目戒律（09-30 起）
    assert "项-1" not in (target / "AGENTS.md").read_text(encoding="utf-8")
    assert not list(target.rglob("__pycache__"))
    assert "backend/" in done
    with pytest.raises(FileExistsError):
        new_project.make(target, CODE_DIR)


def test_sort_into_a_specific_folder_of_a_module(proj):
    """作者 10-07：「资料入口可以分配到具体模块的具体文件夹」——候选和人点的都能带模块里的文件夹；没有就建；不能往上跳、不能放进历史和工作台。"""
    with TestClient(create_app(proj)) as client:
        (proj.materials / "文献" / "原文").mkdir(parents=True, exist_ok=True)
        (proj.materials / "文献" / "历史" / "旧").mkdir(parents=True, exist_ok=True)
        (proj.materials / "文献" / "工作台").mkdir(parents=True, exist_ok=True)
        (proj.materials / "文献" / ".藏起来").mkdir(parents=True, exist_ok=True)
        folders = client.get("/api/inbox/folders", params={"module": "文献"}).json()["folders"]
        assert "原文" in folders and not [f for f in folders if f.split("/")[0] in ("历史", "工作台", ".藏起来")]
        client.post("/api/inbox", files=[("files", ("论文B.pdf", PDF)), ("files", ("跑一下.py", PY)), ("files", ("笔记.txt", b"x"))])
        items = {i["name"]: i for i in client.get("/api/inbox").json()["items"]}
        c = store.connect(proj.db_path)
        it = intake.suggest(c, items["论文B.pdf"]["id"], [{"module": "文献", "folder": "原文", "confidence": "高", "reason": "第一页有作者"}], by="agent:甲", p=proj)
        assert it["candidates"][0]["folder"] == "原文"
        with pytest.raises(store.Refused):
            intake.suggest(c, items["论文B.pdf"]["id"], [{"module": "文献", "folder": "../论文", "confidence": "高", "reason": "x"}], by="agent:甲", p=proj)
        c.close()
        r = client.post(f"/api/inbox/{items['论文B.pdf']['id']}/sort", json={"module": "文献", "folder": "原文"})
        assert r.status_code == 200 and (proj.materials / "文献" / "原文" / "论文B.pdf").read_bytes() == PDF
        r = client.post(f"/api/inbox/{items['跑一下.py']['id']}/sort", json={"module": "源代码", "folder": "脚本/新的"})
        assert r.status_code == 200 and (proj.materials / "源代码" / "脚本" / "新的" / "跑一下.py").read_bytes() == PY   # 没有就建
        for bad in ("../论文", "历史", "工作台/模板", ".藏起来"):
            assert client.post(f"/api/inbox/{items['笔记.txt']['id']}/sort", json={"module": "文献", "folder": bad}).status_code == 400, bad
        assert (proj.materials / "_外部资料入口" / "笔记.txt").exists()
