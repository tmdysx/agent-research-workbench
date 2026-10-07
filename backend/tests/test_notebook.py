"""笔记本：按模块一个文件、每条有编号、改删先留原文、复制的都进历史；网页上做的事自动记一笔。"""
from fastapi.testclient import TestClient

import notebook
import store
from main import create_app


def test_numbered_entries_edit_delete_keep_history(proj):
    c = store.connect(proj.db_path)
    a = notebook.add(c, proj, "总览", "第一条")
    b = notebook.add(c, proj, "总览", "第二条\n## 这行不能变成新的一条")
    d = notebook.add(c, proj, "文献", "文献的第一条", kind="放进来")
    assert (a["id"], b["id"], d["id"]) == ("总-001", "总-002", "文献-001")
    assert [e["id"] for e in notebook.read(proj, "总览")] == ["总-001", "总-002"]
    assert "### 这行不能变成新的一条" in notebook.read(proj, "总览")[1]["body"]
    notebook.edit(c, proj, "总览", "总-001", "改过的第一条")
    notebook.remove(c, proj, "总览", "总-002")
    assert [(e["id"], e["body"]) for e in notebook.read(proj, "总览")] == [("总-001", "改过的第一条")]
    log = (proj.root / "笔记" / "历史" / "改动记录.md").read_text(encoding="utf-8")
    assert "原来是：\n第一条" in log and "删了 总-002" in log            # 改和删之前，原文都留着
    assert notebook.add(c, proj, "总览", "再记一条")["id"] == "总-003"   # 删掉的号不再用
    assert (proj.root / "笔记" / "文献.md").read_text(encoding="utf-8").startswith("# 文献 · 笔记")
    c.close()


def test_copy_goes_to_history_and_resets_since(proj):
    c = store.connect(proj.db_path)
    notebook.add(c, proj, "总览", "复制前记的")
    assert [e["body"] for e in notebook.since_last_copy(c, proj, [])] == ["复制前记的"]
    name = notebook.archive_copy(c, proj, "# 给 agent 的指令\n做这个", [])
    assert (proj.root / "笔记" / "历史" / name).read_text(encoding="utf-8").startswith("# 给 agent 的指令")
    assert name in [h["name"] for h in notebook.history(proj)]
    assert notebook.since_last_copy(c, proj, []) == []                    # 复制过的不再算「新记的」
    notebook.add(c, proj, "总览", "复制后同一分钟里又记的")
    assert [e["body"] for e in notebook.since_last_copy(c, proj, [])] == ["复制后同一分钟里又记的"]
    c.close()


def test_web_actions_go_to_the_log_and_notes_keep_what_people_write(proj):
    """作者 2026-09-29：「笔记分两个模块，一个是机器的日志，一个是人的笔记」。"""
    with TestClient(create_app(proj)) as client:
        client.post("/api/modules", json={"name": "检索页"})
        assert client.get("/api/notes/检索页").json()["entries"] == []
        e = client.get("/api/log").json()["entries"][-1]
        assert (e["id"], e["kind"], e["scope"], e["by"]) == ("志-0001", "新建模块", "检索页", "人")
        client.post("/api/inbox", files=[("files", ("run.py", b"print(1)\n"))])
        items = client.get("/api/inbox").json()["items"]
        client.post(f"/api/inbox/{items[0]['id']}/sort", json={"module": "源代码"})
        log = client.get("/api/log").json()["entries"]
        src = [e for e in log if e["scope"] == "源代码"]
        assert src[0]["kind"] == "放进来" and "run.py" in src[0]["body"] and "把握 高" in src[0]["body"]
        assert "放进外部资料入口" in [e["kind"] for e in log]
        assert client.get("/api/notes/源代码").json()["entries"] == []
        assert client.post("/api/notes/总览", json={"text": "x", "kind": "改了核心"}).status_code == 400   # 机器记的不进笔记
        assert client.get("/api/log").json()["months"][0]["count"] == len(log)
        # 日志是笔记本里的另一个文件夹（作者：「日志和笔记放笔记模块就行，放两个文件夹不就好了？」）
        month = client.get("/api/notes").json()["log"][0]
        assert month["count"] == len(log) and (proj.root / "笔记" / "日志" / f"{month['month']}.md").is_file()
        assert not (proj.root / "日志").exists()
        assert "日志" not in [s["scope"] for s in client.get("/api/notes").json()["scopes"]]
        r = client.post("/api/notes/文献", json={"text": "请删除模块「文献」", "kind": "删除请求"}).json()
        assert r["id"] == "文献-001" and r["kind"] == "删除请求"
        client.put("/api/notes/文献/文献-001", json={"text": "算了，不删了"})
        assert client.get("/api/notes/文献").json()["entries"][0]["body"] == "算了，不删了"
        client.post("/api/notes/文献/文献-001/delete")
        assert client.get("/api/notes/文献").json()["entries"] == []
        idx = client.get("/api/notes").json()
        assert idx["scopes"][0]["scope"] == "总览" and {"文献", "源代码", "检索页"} <= {s["scope"] for s in idx["scopes"]}
        assert client.post("/api/notes/copy", json={"text": "复制的内容"}).json()["history"].endswith("复制给agent.md")
        assert client.get("/api/notes/_系统").status_code == 400            # 笔记名照文件名的规矩


def test_project_tree_is_like_vscode(proj):
    with TestClient(create_app(proj)) as client:
        (proj.root / "笔记").mkdir(exist_ok=True)
        (proj.root / "笔记" / "总览.md").write_text("# 总览", encoding="utf-8")
        (proj.root / "说明.txt").write_text("根目录的文件", encoding="utf-8")
        names = [i["name"] for i in client.get("/api/project/tree").json()["items"]]
        assert "资料" in names and "笔记" in names and "说明.txt" in names
        assert "索引" not in names                                      # 工具自己的库不列
        p = client.get("/api/project/preview", params={"path": "笔记/总览.md"}).json()
        assert p["text"] == "# 总览"
        assert client.get("/api/project/preview", params={"path": "索引/state.db"}).status_code == 404
        assert client.get("/api/project/preview", params={"path": "../外面.txt"}).status_code == 404
        assert client.get("/pfiles/说明.txt").status_code == 200


def test_plans_list_newest_first_with_titles(proj):
    """计划/ 里一份一个文件：标题取第一行「# 」，新改的在前；没有 计划/ 就是空的。"""
    import os
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/plans").json()["items"] == []
        d = proj.root / "计划"
        d.mkdir()
        (d / "old-plan.md").write_text("前言\n# 旧计划\n内容", encoding="utf-8")
        (d / "new-plan.md").write_text("# 新计划\n## 第一步", encoding="utf-8")
        (d / "不是计划.txt").write_text("x", encoding="utf-8")
        os.utime(d / "old-plan.md", (1_700_000_000, 1_700_000_000))
        items = client.get("/api/plans").json()["items"]
        assert [(i["title"], i["path"]) for i in items] == [("新计划", "计划/new-plan.md"), ("旧计划", "计划/old-plan.md")]
        assert client.get("/api/project/preview", params={"path": items[0]["path"]}).json()["text"].startswith("# 新计划")
        # 按蓝图目标分的文件夹：待归位的散文件在前，目标按编号排（S1-10 在 S1-2 后面），里面 P2 在 P10 前面
        for goal, names in {"S1-10 十": ["P1 a.md"], "S1-2 二": ["P10 z.md", "R1 d.md", "P2 b.md", "P3 · 2026-09-27 · 开工单.md"],
                            "S0 总体": ["0 总览.md", "原文 · 2026-09-25 · 整份.md", "P4 存档与复活（09-25）.md"]}.items():
            (d / goal).mkdir()
            for n in names:
                (d / goal / n).write_text("# x", encoding="utf-8")
        items = client.get("/api/plans").json()["items"]
        assert [i["title"] for i in items] == ["新计划", "旧计划", "S0 总体", "S1-2 二", "S1-10 十"]
        assert items[0]["goal"] == "待归位" and items[0]["date"] and items[0]["code"] == ""
        # 起名「P3 · 2026-09-27 · 开工单」：编号、日期、标题分开给，网页按时间排（作者 09-29：「计划……没有时间编码」）
        assert [(k["code"], k["title"]) for k in items[3]["children"]] == [("P2", "b"), ("P3", "开工单"), ("P10", "z"), ("R1", "d")]
        p3 = items[3]["children"][1]
        assert (p3["date"], p3["goal"]) == ("2026-09-27", "S1-2 二")
        s0 = {k["code"]: k for k in items[2]["children"]}
        assert s0["0"]["title"] == "总览" and s0["0"]["date"] == ""                           # 总览没日期：钉在最上面
        assert s0["P4"]["date"].endswith("-09-25") and s0["P4"]["title"] == "存档与复活"       # 旧名的（09-25）也认
        assert (s0["原文"]["date"], s0["原文"]["title"]) == ("2026-09-25", "整份")
        # 样图（.html）也列，标 kind=html；答疑这些只读 .md 的照旧不读它（S1-1 S2-20）
        (d / "S1-2 二" / "R2 · 2026-10-01 · 看板样图.html").write_text("<h1>样图</h1>", encoding="utf-8")
        kids = {k["code"]: k for k in client.get("/api/plans").json()["items"][3]["children"]}
        assert (kids["R2"]["kind"], kids["R2"]["title"], kids["P2"]["kind"]) == ("html", "看板样图", "md")
        import governance_paths as gp
        assert not any(r.endswith(".html") for r in gp.plan_files(proj)) and any(r.endswith(".html") for r in gp.plan_files(proj, html=True))


def test_file_outside_materials_is_noticed(proj):
    """在项目根新建个 Word（资料/ 外面），网页也要自己刷新；空的、被占着的都不能把后端弄坏。"""
    import files
    before = files.proj_signature(proj)
    (proj.root / "666.docx").write_bytes(b"")
    assert files.proj_signature(proj) != before
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/project/preview", params={"path": "666.docx"}).status_code == 200
        assert client.get("/api/search", params={"q": "666"}).status_code == 200



def test_old_machine_entries_move_from_notes_to_the_log(proj):
    """09-29 以前机器记的也在笔记里：启动时搬进 日志/，笔记只留人写的；改之前整份留底，号不回收。"""
    import journal
    c = store.connect(proj.db_path)
    notebook.add(c, proj, "总览", "人写的")
    notebook.add(c, proj, "总览", "改了 backend", by="agent:x", kind="改了核心")
    notebook.add(c, proj, "总览", "装了技能", kind="装技能")
    notebook.add(c, proj, "文献", "请删掉旧稿", kind="删除请求")
    assert journal.split_from_notes(c, proj, ["文献"]) == 2
    assert [e["body"] for e in notebook.read(proj, "总览")] == ["人写的"]
    assert [e["kind"] for e in notebook.read(proj, "文献")] == ["删除请求"]
    log = journal.read(proj)
    assert [(e["id"], e["kind"], e["by"]) for e in log] == [("志-0001", "改了核心", "agent:x"), ("志-0002", "装技能", "人")]
    assert "原先记在笔记 总-002" in log[0]["body"]
    hist = proj.root / "笔记" / "历史"
    assert any(f.name.startswith("分出日志前 · 总览") for f in hist.iterdir())
    assert "笔记和日志分开" in (hist / "改动记录.md").read_text(encoding="utf-8")
    assert journal.split_from_notes(c, proj, ["文献"]) == 0                  # 再跑一遍不动
    assert notebook.add(c, proj, "总览", "新的")["id"] == "总-004"            # 搬走的号不再用
    assert journal.add(c, proj, "又一条", kind="存档")["id"] == "志-0003"
    c.close()
