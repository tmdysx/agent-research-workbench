"""文献阅读页（文献 S2-3 · S2-5 · S2-7）和「对话里说验收」。
作者 2026-09-28：「我觉得那个pdf没有内嵌感觉不好用，还有不用去自动化页交付，我让你执行就可以执行了」。"""
import json

import anyio
from fastapi.testclient import TestClient

import blueprint
import deliveries
import store
from main import create_app
from test_autopilot import _setup
from test_library import make_pdf
from test_mcp import _call


def test_pdfjs_is_served_from_the_app(proj):
    with TestClient(create_app(proj)) as client:
        r = client.get("/lib/pdfjs/pdf.min.mjs")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/javascript")
        assert r.headers["access-control-allow-origin"] == "*"                     # 沙箱里的图解也能用
        assert client.get("/lib/pdfjs/pdf.worker.min.mjs").status_code == 200
        assert client.get("/lib/pdfjs/没有.mjs").status_code == 404
        assert client.get("/lib/%2E%2E/%2E%2E/backend/main.py").status_code == 404   # 出不了 工具库/下载/


def _one_paper(client):
    return client.post("/api/library/文献/add", files={"file": ("p.pdf", make_pdf("A paper", "A paper"), "application/pdf")}).json()


def test_note_while_reading_goes_into_the_papers_notes(proj):
    (proj.materials / "文献").mkdir(parents=True)
    with TestClient(create_app(proj)) as client:
        x = _one_paper(client)
        base = "/api/library/文献/" + x["code"]
        assert client.get(base + "/notes").json() == {"items": []}
        assert client.post(base + "/note", json={"page": 2}).status_code == 400                       # 原句、写的都没有
        assert client.post(base + "/note", json={"page": 2, "quote": "x", "color": "紫"}).status_code == 400
        assert client.post(base + "/note", json={"page": 0, "quote": "x"}).status_code == 400
        n = client.post(base + "/note", json={"page": 2, "quote": "  class-specific\n feature  selection ", "color": "绿"}).json()
        assert (n["page"], n["color"], n["by"], n["quote"]) == (2, "绿", "人", "class-specific feature selection")
        client.post(base + "/note", json={"page": 5, "text": "这里的式子\n和第 3 节对不上"})
        items = client.get(base + "/notes").json()["items"]
        assert [(i["page"], i["color"], i["quote"], i["text"]) for i in items] == [
            (2, "绿", "class-specific feature selection", ""), (5, "黄", "", "这里的式子\n和第 3 节对不上")]
        f = proj.materials / "文献" / x["folder"] / "文本" / "笔记.md"
        text = f.read_text(encoding="utf-8")
        assert text.startswith(f"# {x['code']} 笔记\n") and text.count("## 第 ") == 2 and "> class-specific feature selection\n" in text
        assert "笔记.md" in client.get("/api/library/文献").json()["items"][0]["parts"]["文本"]


def test_notes_can_be_rewritten_and_deleted_while_reading(proj):
    (proj.materials / "文献").mkdir(parents=True)
    with TestClient(create_app(proj)) as client:
        x = _one_paper(client)
        base = "/api/library/文献/" + x["code"] + "/note"
        a = client.post(base, json={"page": 2, "quote": "a quote", "color": "绿"}).json()
        b = client.post(base, json={"page": 3, "text": "第一段\n\n第二段"}).json()
        c = client.post(base, json={"page": 4, "text": "要删的"}).json()
        assert (a["i"], b["i"], c["i"]) == (0, 1, 2) and b["text"] == "第一段\n\n第二段"                # 分段留着
        url = base + "s/"
        assert client.put(url + "1", json={"at": "2000-01-01 00:00", "text": "x"}).status_code == 400        # 对不上：别处改过
        assert client.put(url + "9", json={"at": b["at"], "text": "x"}).status_code == 400
        assert client.put(url + "1", json={"at": b["at"], "text": " ", "color": "黄"}).status_code == 400       # 没原句又空着：要删就点删
        assert client.put(url + "1", json={"at": b["at"], "text": "x", "color": "紫"}).status_code == 400
        e = client.put(url + "1", json={"at": b["at"], "text": "改过的\n\n两段", "color": "蓝"}).json()
        assert (e["page"], e["color"], e["by"], e["at"], e["text"]) == (3, "蓝", "人", b["at"], "改过的\n\n两段")
        assert e["edited"].startswith("改过（人 ")
        q = client.put(url + "0", json={"at": a["at"], "text": "", "color": "红"}).json()                     # 有原句的可以把字清空
        assert q["quote"] == "a quote" and q["text"] == "" and q["color"] == "红"
        assert client.delete(url + "2", params={"at": c["at"]}).json()["text"] == "要删的"
        items = client.get("/api/library/文献/" + x["code"] + "/notes").json()["items"]
        assert [(n["i"], n["page"], n["color"]) for n in items] == [(0, 2, "红"), (1, 3, "蓝")]
        d = proj.materials / "文献" / x["folder"] / "文本"
        hist = (d / ".笔记历史.md").read_text(encoding="utf-8")
        assert hist.count("\n改之前 · ") == 2 and "删之前" in hist and "要删的" in hist and "第一段\n\n第二段" in hist
        assert ".笔记历史.md" not in client.get("/api/library/文献").json()["items"][0]["parts"]["文本"]    # 阅读页不列它
        client.post(base, json={"page": 5, "text": "改完还能接着记"})
        assert [n["page"] for n in client.get("/api/library/文献/" + x["code"] + "/notes").json()["items"]] == [2, 3, 5]
        text = (d / "笔记.md").read_text(encoding="utf-8")
        assert "\n\n## 第 3 页 · 蓝 · 人 · " in text and "\n\n改过的\n\n两段\n" in text and "\n\n改完还能接着记\n" in text   # 样子跟新记的一样


def test_marks_and_scribbles_sit_on_top_and_the_pdf_is_untouched(proj):
    (proj.materials / "文献").mkdir(parents=True)
    with TestClient(create_app(proj)) as client:
        x = _one_paper(client)
        base = "/api/library/文献/" + x["code"] + "/marks"
        pdf = proj.materials / "文献" / x["pdf"]
        before = pdf.read_bytes()
        assert client.get(base).json() == {"items": []}
        for bad in ({"page": 1, "kind": "涂改液"}, {"page": 1, "kind": "笔", "points": [[1, 2]]}, {"page": 1, "kind": "笔", "points": [[1, 2, 3], [4, 5, 6]]},
                    {"page": 0, "kind": "高亮", "rects": [[1, 2, 3, 4]]}, {"page": 1, "kind": "高亮", "rects": []},
                    {"page": 1, "kind": "便签", "at": [3, 4], "text": " "}, {"page": 1, "kind": "便签", "text": "没位置"},
                    {"page": 1, "kind": "笔", "color": "紫", "points": [[1, 2], [3, 4]]}):
            assert client.post(base, json=bad).status_code in (400, 422), bad
        hl = client.post(base, json={"page": 2, "kind": "高亮", "color": "绿", "rects": [[37.64, 83.3, 251.1, 11.7]], "text": " a  quote "}).json()
        st = client.post(base, json={"page": 2, "kind": "便签", "at": [475, 158.5], "text": "看第 3 节"}).json()
        pen = client.post(base, json={"page": 3, "kind": "笔", "color": "红", "points": [[1, 2], [3, 4], [5, 6]], "width": 99}).json()
        assert (hl["id"], st["id"], pen["id"]) == ("批-1", "批-2", "批-3")
        assert hl["rects"] == [[37.6, 83.3, 251.1, 11.7]] and hl["text"] == "a quote" and hl["by"] == "人"
        assert st["color"] == "黄" and pen["width"] == 12.0                                        # 太粗的压到 12
        assert client.delete(base + "/批-2").json()["kind"] == "便签"
        assert client.delete(base + "/批-2").status_code == 400
        again = client.post(base, json={"page": 1, "kind": "笔", "points": [[0, 0], [9, 9]]}).json()
        assert again["id"] == "批-4"                                                              # 号不回收
        assert [m["id"] for m in client.get(base).json()["items"]] == ["批-1", "批-3", "批-4"]
        f = proj.materials / "文献" / x["folder"] / "批注.json"
        text = f.read_text(encoding="utf-8")
        assert json.loads(text)["下一个"] == 5 and text.count("\n") < 12                           # 一条批注一行
        assert pdf.read_bytes() == before                                                           # 原版 PDF 一个字节没动
        assert client.post("/api/library/文献/" + x["code"] + "/note", json={"page": 1, "text": "蓝色的", "color": "蓝"}).json()["color"] == "蓝"


def test_ask_while_reading_keeps_answers_in_qa_and_logs(proj):
    (proj.materials / "文献").mkdir(parents=True)
    with TestClient(create_app(proj)) as client:
        x = _one_paper(client)
        where = f"文献 {x['code']} 第 3 页「maximal dynamic correlation change」"
        q = client.post("/api/qa/ask", json={"text": "这句什么意思？", "where": where}).json()
        client.post("/api/qa/ask", json={"text": "跟读书无关的问题"})
        log = [e["body"] for e in client.get("/api/log").json()["entries"]]
        assert all(any(b.startswith(code) for b in log) for code in ("问-01", "问-02"))
        assert client.get("/api/notes/总览").json()["entries"] == []
    got = anyio.run(_call, proj, [
        ("answer_person", {"code": q["code"], "answer": "这是测试答案，依据第3页。"}),
        ("answer_person", {"code": "问-02", "answer": "好的"}),
    ])
    assert all("答了" in answer and "也记进了" not in answer for answer in got)
    c = store.connect(proj.db_path)
    questions = {v["code"]: v for v in store.list_asked(c)}
    c.close()
    assert questions[q["code"]]["detail"] == where
    assert questions[q["code"]]["answer"]["created_by"] == "agent:test-agent"
    assert questions[q["code"]]["answer"]["text"] == "这是测试答案，依据第3页。"
    import library
    assert library.notes(proj, "文献", x["code"]) == []
    note = proj.materials / "文献" / x["folder"] / "文本/笔记.md"
    assert not note.exists()
    # 老版本留下的文件既不覆盖，也不因为新问答而追加机器答案。
    note.write_text("# 旧笔记\n\n原有内容保留\n", encoding="utf-8")
    before = note.read_bytes()
    with TestClient(create_app(proj)) as client:
        q2 = client.post("/api/qa/ask", json={"text": "再问一次", "where": where}).json()
    got = anyio.run(_call, proj, [("answer_person", {"code": q2["code"], "answer": "新答案仍在问答"})])
    assert "答了" in got[0] and note.read_bytes() == before


def test_acceptance_said_in_chat_is_recorded_with_the_words(proj, monkeypatch, tmp_path):
    _setup(proj, monkeypatch, tmp_path)
    monkeypatch.setattr(deliveries, "DEFAULT_PASS", False)          # 这条测人手验收 / 打回：关掉默认通过
    c = store.connect(proj.db_path)
    deliveries.deliver(c, proj, goal="S1-1", sub="S2-1", did="列表", checks=[{"name": "拖一篇", "ok": True}], by="agent:test")
    c.close()
    empty, ok, again = anyio.run(_call, proj, [
        ("record_acceptance", {"code": "J1", "said": "  "}),
        ("record_acceptance", {"code": "J1", "said": "J1 可以，验收"}),
        ("record_acceptance", {"code": "J1", "said": "验收"}),
    ])
    assert empty.startswith("没记上") and "原话" in empty
    assert ok.startswith("记上了：J1") and again.startswith("没记上")
    j = deliveries.get(proj, "J1")
    assert j["state"] == "验收通过" and "对话里说的：「J1 可以，验收」，agent:test-agent 记的" in j["body"]
    sub = next(x for x in blueprint.pyramid(proj)["goals"][0]["subs"] if x["code"] == "S2-1")
    assert sub["text"] == "做完（J1 验收）"
