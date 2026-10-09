"""外部资料入口 Intake：进来先放外部资料入口、同一个文件只存一份、人点了或 agent 写了原因才挪（放错的能挪回来，见 test_file_inbox）；新项目只复制程序本身。"""
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


def test_free_name_never_overwrites(tmp_path):
    """指纹名也被占了：再往后数（10-08 修：以前直接覆盖）；入口里等分拣的名字（taken）也算占了，不分大小写。"""
    sha = "abcdef0123456789"
    (tmp_path / "a.md").write_text("1", encoding="utf-8")
    assert intake._free_name(tmp_path, "a.md", sha) == "a（abcdef）.md"
    (tmp_path / "a（abcdef）.md").write_text("2", encoding="utf-8")
    assert intake._free_name(tmp_path, "a.md", sha) == "a（abcdef-2）.md"
    assert intake._free_name(tmp_path, "b.md", sha, {"B.md", "b（abcdef）.md"}) == "b（abcdef-2）.md"
    assert intake._free_name(tmp_path, "c.md", sha) == "c.md"


def test_agent_sorting_needs_a_reason(proj):
    with TestClient(create_app(proj)) as client:
        client.post("/api/inbox", files=[("files", ("x.pdf", PDF))])
    c = store.connect(proj.db_path)
    iid = intake.waiting(c)[0]["id"]
    for bad in ("", "  \n "):
        with pytest.raises(store.Refused, match="写一句为什么"):
            intake.place(c, proj, iid, "文献", by="agent:x", reason=bad)
    assert intake.get(c, iid)["status"] == "waiting" and (proj.materials / "_外部资料入口" / "x.pdf").exists()
    r = intake.place(c, proj, iid, "文献", by="agent:x", reason="首页有期刊名")
    assert r["item"]["sorted_by"] == "agent:x" and (proj.materials / "文献" / "x.pdf").read_bytes() == PDF
    import journal
    e = journal.read(proj)[-1]
    assert (e["by"], e["kind"], e["scope"], e["id"]) == ("agent:x", "放进来", "文献", r["log_id"])
    assert "选的是 规则 给的候选" in e["body"] and "原因：首页有期刊名" in e["body"]
    c.close()


@pytest.fixture
def box(proj, monkeypatch):
    """建好骨架的临时项目：模块（含 想法 蓝图 戒律 源代码）都登记过。"""
    import project
    monkeypatch.setenv("RC_DB", str(proj.root / "索引" / "state.db"))
    project.ensure_skeleton(proj)
    c = store.connect(proj.db_path)
    store.sync_folders(c, proj)
    yield c
    c.close()


GOVERNED = [("蓝图", "", "x.md"), ("戒律", "", "x.md"), ("源代码", "", "x.py"), ("想法", "", "x.md"),
            ("蓝图", "", "S1-9 新目标.md"), ("戒律", "", "2 项目戒律补充.md"),
            ("论文", "技能", "SKILL.md"), ("论文", "技能/深一层", "x.md"), ("文献", "解读", "x.md"),
            ("论文", "内置", "x.md"), ("论文", "正文/内置", "x.md"),
            ("论文", "", "需求.md"), ("论文", "", "戒律.md"), ("论文", "", "蓝图.md"), ("论文", "", "下载清单.md"), ("论文", "", "想法.md")]


@pytest.mark.parametrize("module,folder,name", GOVERNED)
def test_agents_cannot_sort_into_places_only_people_decide(box, proj, module, folder, name):
    """10-08：agent 分拣只放普通材料的位置；治理模块、模块根上程序维护的文件、技能/、解读/、内置/ 要人在网页上点。人点照旧。"""
    c = box
    f = proj.materials / "_外部资料入口" / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("入口里的", encoding="utf-8")
    intake.sync(c, proj)
    iid = next(x["id"] for x in intake.waiting(c) if x["name"] == name)
    target = proj.materials / module / folder if folder else proj.materials / module
    had_folder = target.exists()
    with pytest.raises(store.Refused, match="agent 不能直接分拣.*要放这类位置请让人在网页上点"):
        intake.place(c, proj, iid, module, folder=folder, by="agent:x", reason="想放这里")
    assert f.read_text(encoding="utf-8") == "入口里的" and intake.get(c, iid)["status"] == "waiting"
    assert not (target / name).exists() and target.exists() == had_folder          # 文件夹也没建
    r = intake.place(c, proj, iid, module, folder=folder)                            # 人点：照原样放进去
    assert r["item"]["status"] == "sorted" and r["item"]["sorted_by"] == "人"
    assert (proj.materials / r["item"]["sorted_to"]).read_text(encoding="utf-8") == "入口里的" and not f.exists()


def test_agents_cannot_sort_a_hidden_name_to_a_module_root(box, proj, tmp_path):
    """上传进来的 .链接.txt 放到模块根就成了链接文件：agent 不能直接放。"""
    c = box
    tmp = tmp_path / "上传中"
    tmp.write_text("资料/文献\n", encoding="utf-8")
    it = intake.receive(c, proj, tmp, ".链接.txt", by="人")["item"]
    with pytest.raises(store.Refused, match="隐藏文件"):
        intake.place(c, proj, it["id"], "论文", by="agent:x", reason="想放这里")
    assert not (proj.materials / "论文" / ".链接.txt").exists()


@pytest.mark.parametrize("module,folder,name", [("论文", "", "稿.md"), ("论文", "正文", "稿.md"), ("文献", "原文", "a.pdf"),
                                                ("论文", "", "需求-旧.md"), ("实验", "技能说明", "x.md")])
def test_agents_still_sort_ordinary_materials(box, proj, module, folder, name):
    c = box
    f = proj.materials / "_外部资料入口" / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("普通材料", encoding="utf-8")
    intake.sync(c, proj)
    iid = next(x["id"] for x in intake.waiting(c) if x["name"] == name)
    if not store.find_module(c, module):
        pytest.skip(f"骨架里没有「{module}」模块")
    r = intake.place(c, proj, iid, module, folder=folder, by="agent:x", reason="是普通材料")
    assert (proj.materials / r["item"]["sorted_to"]).read_text(encoding="utf-8") == "普通材料"


def test_governed_follows_windows_case_rules(monkeypatch):
    """Windows 上不分大小写：需求.MD、VENV/ 也算；别的系统按原样比。"""
    monkeypatch.setattr(intake, "CASELESS", False)
    assert intake.governed("论文", "", "需求.MD") == "" and not intake.not_a_place("VENV")
    monkeypatch.setattr(intake, "CASELESS", True)
    assert intake.governed("论文", "", "需求.MD") and intake.governed("论文", "", "下载清单.MD")
    assert intake.not_a_place("VENV") and intake.not_a_place("Node_Modules") and intake.governed("论文", "a/VENV", "x.md")
    with pytest.raises(store.Refused, match="不能当去向"):
        intake._folder(None, "论文", "Node_Modules")


def test_failed_commit_puts_the_file_back(box, proj, monkeypatch):
    """os.replace 成了、提交没成：文件挪回入口，库里也没记分拣。"""
    import contextlib
    import sqlite3
    c = box
    f = proj.materials / "_外部资料入口" / "稿.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("稿", encoding="utf-8")
    intake.sync(c, proj)
    iid = intake.waiting(c)[0]["id"]
    real_tx = store.tx

    @contextlib.contextmanager
    def failing_tx(conn):
        with real_tx(conn):
            yield conn
            raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(intake.store, "tx", failing_tx)
    with pytest.raises(sqlite3.OperationalError):
        intake.sort(c, proj, iid, "论文", by="agent:x")
    monkeypatch.setattr(intake.store, "tx", real_tx)
    assert f.read_text(encoding="utf-8") == "稿" and not (proj.materials / "论文" / "稿.md").exists()
    assert intake.get(c, iid)["status"] == "waiting"
