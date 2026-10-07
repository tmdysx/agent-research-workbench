"""网页接口 + WebSocket：点的能存住，别的进程写的、放进文件夹的，都能推到网页上。"""
import threading
import time

from fastapi.testclient import TestClient

import store
from main import create_app

DEFAULTS = ["想法", "蓝图", "戒律", "源代码", "测试", "文献", "论文", "实验", "汇报", "素材"]   # 固定七个（10-06 起）+ 新项目的起步模块


def test_page_and_state(proj):
    with TestClient(create_app(proj)) as client:
        r = client.get("/")
        assert r.status_code == 200 and "<nav" in r.text
        s = client.get("/api/state").json()
        assert s["blueprint"] == [] and s["project"]["name"] == proj.root.name     # 没写蓝图、没起名：用文件夹名
        assert [m["name"] for m in s["modules"]] == DEFAULTS          # 启动时建好固定七个 + 起步模块
        assert client.get("/api/ping").json()["root"] == str(proj.root)


def test_human_writes_persist_and_web_never_deletes(proj):
    with TestClient(create_app(proj)) as client:
        s = client.post("/api/modules", json={"name": "检索页"}).json()
        assert any(m["name"] == "检索页" and m["created_by"] == "人" for m in s["modules"])
        assert (proj.materials / "检索页").is_dir()
        assert client.post("/api/modules", json={"name": "检索页"}).status_code == 409
        assert client.post("/api/modules", json={"name": "a/b"}).status_code == 400
        assert client.post("/api/modules/检索页/trash").status_code in (404, 405)   # 网页不删东西
        client.put("/api/note", json={"text": "记一笔"})
    with TestClient(create_app(proj)) as client:                   # 「重启」
        s = client.get("/api/state").json()
        assert "检索页" in [m["name"] for m in s["modules"]]
        assert s["note"]["text"] == "记一笔"


def test_tree_preview_and_raw(proj):
    with TestClient(create_app(proj)) as client:
        d = proj.materials / "文献"
        (proj.root / "根.json").write_text('{"项目": "示例"}', encoding="utf-8")   # 项目根的文件：没挂链接就不给看
        (d / "精读").mkdir()
        (d / "精读" / "a.md").write_text("# 标题\n正文", encoding="utf-8")
        (d / "旧.txt").write_bytes("中文 GBK 文件".encode("gbk"))
        (d / "图.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        t = client.get("/api/modules/文献/tree").json()
        assert [i["name"] for i in t["items"]] == ["精读", "图.png", "旧.txt"]  # 文件夹在前；10-07 起模块里不再自动补 内置/
        assert next(i for i in t["items"] if i["name"] == "精读")["children"][0]["path"] == "精读/a.md"
        p = client.get("/api/modules/文献/preview", params={"path": "精读/a.md"}).json()
        assert p["kind"] == "text" and p["text"].startswith("# 标题")
        p = client.get("/api/modules/文献/preview", params={"path": "旧.txt"}).json()
        assert p["text"] == "中文 GBK 文件" and p["encoding"] == "gb18030"
        assert client.get("/api/modules/文献/preview", params={"path": "图.png"}).json()["kind"] == "image"
        assert client.get("/files/文献/图.png").content.startswith(b"\x89PNG")
        # 越界一律拒
        assert client.get("/api/modules/文献/preview", params={"path": "../../根.json"}).status_code == 404
        assert client.get("/api/modules/文献/preview", params={"path": "@/根.json"}).status_code == 404
        assert client.get("/api/modules/不存在/tree").status_code == 404


def test_links_show_up_in_module(proj):
    with TestClient(create_app(proj)) as client:
        (proj.root / "根.json").write_text('{"项目": "自动化科研交互界面"}', encoding="utf-8")
        (proj.materials / "论文" / ".链接.txt").write_text("根.json\n", encoding="utf-8")
        t = client.get("/api/modules/论文/tree").json()
        assert t["items"][-1]["path"] == "@/根.json" and t["items"][-1]["link"] is True
        p = client.get("/api/modules/论文/preview", params={"path": "@/根.json"}).json()
        assert "自动化科研交互界面" in p["text"]
        (proj.root / "a.html").write_text("<script>1</script>", encoding="utf-8")
        (proj.materials / "论文" / ".链接.txt").write_text("根.json\na.html\n", encoding="utf-8")
        r = client.get("/files/论文/@/a.html")
        assert "sandbox" in r.headers["content-security-policy"]         # 资料里的网页在沙箱里跑


def test_answer_endpoint(proj):
    c = store.connect(proj.db_path)
    store.ask_human(c, "要不要做手机？", by="agent:x")
    c.close()
    with TestClient(create_app(proj)) as client:
        s = client.get("/api/state").json()
        assert [q["code"] for q in s["pending"]] == ["D-01"]
        s = client.post("/api/pending/D-01/answer", json={"text": "不做"}).json()
        assert s["pending"] == [] and s["decisions"][0]["text"] == "不做"


def test_stale_server_record_is_ignored(proj):
    """记录文件说开在某端口，但那儿其实没人——不能当成「已经开着了」。"""
    import main
    proj.index_dir.mkdir(parents=True, exist_ok=True)
    (proj.index_dir / "server.json").write_text('{"port": 1}', encoding="utf-8")
    assert main._running_port(proj, 1) is None


def _collect(ws, seconds=4.0):
    got = []
    def run():
        end = time.time() + seconds
        try:
            while time.time() < end:
                got.append(ws.receive_json())
        except Exception:                 # 测试结束连接关了，收不到就算了
            pass
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=seconds)
    return got


def test_websocket_pushes_agent_writes_and_new_files(proj):
    """agent 从另一个进程加模块、往文件夹里放文件：网页的 WebSocket 都要收到通知。"""
    with TestClient(create_app(proj, watch_interval=0.05)) as client:
        with client.websocket_connect("/ws") as ws:
            hello = ws.receive_json()
            other = store.connect(proj.db_path)
            store.add_module(other, proj, "agent 加的", by="agent:claude-code", source="agent")
            other.close()
            (proj.materials / "论文" / "草稿.md").write_text("新写的", encoding="utf-8")
            got = _collect(ws, 1.5)
            assert any(m["type"] == "changed" and m["v"] > hello["v"] for m in got)
            assert any(m["type"] == "files" for m in got)


def test_search_and_guide(proj):
    with TestClient(create_app(proj)) as client:
        (proj.materials / "文献" / "笔记.md").write_text("第一行\n这里提到 熔炉 这个词\n", encoding="utf-8")
        (proj.materials / "实验" / "熔炉记录.csv").write_text("a,b\n", encoding="utf-8")
        r = client.get("/api/search", params={"q": "熔炉"}).json()
        by = {h["path"]: h for h in r["files"]}
        assert by["资料/文献/笔记.md"]["top"] == "资料" and by["资料/文献/笔记.md"]["lines"][0]["line"] == 2
        assert "资料/实验/熔炉记录.csv" in by                            # 文件名命中
        (proj.materials / "蓝图" / "S1-1 甲.md").write_text("| S2-1 | store 数据库 | 做完 |", encoding="utf-8")
        assert client.get("/api/search", params={"q": "store"}).json()["notes"][0]["kind"] == "蓝图"
        assert client.get("/api/search", params={"q": "  "}).json()["files"] == []
        assert client.get("/api/guide").json()["text"].startswith("#")
        assert client.get("/api/guide", params={"lang": "en"}).json()["text"].startswith("#")


def test_settings_change_module_info_and_order(proj):
    """设置 → 模块：改英文名、一句话、第二栏顺序；固定的三个永远在最前；改了记进笔记本。"""
    import journal
    import notebook
    with TestClient(create_app(proj)) as client:
        (proj.materials / "实验" / "戒律.md").write_text("| 实-1 | 不重切 | x |", encoding="utf-8")
        m = client.put("/api/modules/文献/info", json={"en": " Papers  we read ", "one_line": "别人写的"}).json()
        assert (m["en"], m["one_line"]) == ("Papers we read", "别人写的")
        assert client.put("/api/modules/不存在/info", json={"en": "x"}).status_code == 400
        r = client.put("/api/modules-order", json={"names": ["实验", "蓝图", "论文", "文献"]}).json()
        assert r["names"] == ["想法", "蓝图", "戒律", "源代码", "测试", "文献", "论文", "实验", "汇报", "素材"]    # 固定的七个不跟着排；没排到的接在后面
        s = client.get("/api/state").json()
        assert [x["name"] for x in s["modules"]] == r["names"]
        assert {x["name"]: x["rules"] for x in s["modules"]}["实验"] is True
        kinds = [e["kind"] for e in journal.read(proj)]            # 网页上点的操作记进日志，不进人的笔记
        assert "改了模块设置" in kinds and "改了模块顺序" in kinds and notebook.read(proj, "总览") == []


def test_add_module_with_english_name_and_english_word_list(proj):
    """设置 → 模块「加一个」带英文名；纯英文界面的对照表跟网页一起发出来（没有这个文件也不报错）。"""
    with TestClient(create_app(proj)) as client:
        s = client.post("/api/modules", json={"name": "数据", "en": "Data", "one_line": "原始数据"}).json()
        m = {x["name"]: x for x in s["modules"]}["数据"]
        assert (m["en"], m["one_line"]) == ("Data", "原始数据")
        r = client.get("/界面英文.js")
        assert r.status_code == 200 and "javascript" in r.headers["content-type"]
