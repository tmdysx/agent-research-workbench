"""下载清单：agent 找到的论文列成清单，人点链接直达去下，下好的变绿；开放获取的程序直接下，自己下的从「下载」文件夹捡进来。
作者 2026-09-27：「我是想要一个下载页面有链接和勾选就行，就是下载好的就是绿色，有链接直达就行了？」
测试不上网：直接下用本机临时开的小服务器，OpenAlex 换成假的。"""
import http.server
import json
import threading
import time

import anyio
from fastapi.testclient import TestClient

import downloads
from main import create_app
from test_mcp import _call

PDF = b"%PDF-1.4\n% test\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class _H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body, kind = (PDF, "application/pdf") if self.path.endswith(".pdf") else (b"<html>login</html>", "text/html")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def _server():
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def _until(fn, secs=8):
    end = time.time() + secs
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(0.1)
    return fn()


def test_list_links_and_green_when_downloaded(proj, monkeypatch, tmp_path):
    (proj.materials / "文献").mkdir(parents=True)
    monkeypatch.setattr(downloads, "lookup_oa", lambda doi, timeout=15: "" if doi.endswith("closed") else "https://example.org/free.pdf")
    srv, base = _server()
    try:
        with TestClient(create_app(proj)) as client:
            add = lambda **kw: client.post("/api/downloads/文献", json=kw)
            assert add(title="x").status_code == 400                                   # 链接、DOI 都没有
            assert add(title="x", url="ftp://a/b.pdf").status_code == 400
            a = add(title="开放的", url=f"{base}/paper.pdf", why="需-1 要").json()
            b = add(title="假的", url=f"{base}/login").json()
            c = add(title="只有 DOI", doi="https://doi.org/10.1016/j.eswa.2023.closed").json()
            d = add(title="arXiv", url="https://arxiv.org/abs/2401.00001").json()
            assert [x["code"] for x in (a, b, c, d)] == ["下-1", "下-2", "下-3", "下-4"]
            assert add(title="又一次", url=f"{base}/paper.pdf").json()["code"] == "下-1"          # 同一个链接不重复排
            assert c["url"] == "https://doi.org/10.1016/j.eswa.2023.closed" and c["doi"] == "10.1016/j.eswa.2023.closed"
            assert d["direct"] == "https://arxiv.org/pdf/2401.00001" and a["direct"] == a["url"] and b["direct"] == ""
            assert _until(lambda: downloads.get(proj, "文献", "下-3")["state"] == "还没下" and downloads.get(proj, "文献", "下-3").get("msg"))
            assert "没有合法的免费版" in downloads.get(proj, "文献", "下-3")["msg"]

            # 直接下：下好了变绿，文件在 原文/；不是 PDF 的不留、红灯
            assert client.post("/api/downloads/文献/下-1/fetch").status_code == 200
            got = _until(lambda: (x := downloads.get(proj, "文献", "下-1"))["at"].startswith("资料/文献/原文/L") and x)   # 下好了马上入库，编 L 号
            assert got["lamp"] == "ok" and got["at"] == "资料/文献/原文/L1 开放的.pdf" and (proj.root / got["at"]).read_bytes() == PDF
            assert client.post("/api/downloads/文献/下-2/fetch").status_code == 400          # 没有能直接下的地址
            (proj.materials / "文献" / "下载清单.md").write_text(
                (proj.materials / "文献" / "下载清单.md").read_text(encoding="utf-8").replace(f"{base}/login |  |  |", f"{base}/login |  | {base}/login |"),
                encoding="utf-8")                                                          # 假装它有个「直链」，下来是网页
            client.post("/api/downloads/文献/下-2/fetch")
            bad = _until(lambda: (x := downloads.get(proj, "文献", "下-2"))["state"] == "失败" and x)
            assert bad["lamp"] == "bad" and "不是 PDF" in bad["msg"] and not list((proj.materials / "文献" / "原文").glob("下-2*"))

            # 勾「下好了」：选一个下好的 PDF 给这一行；不是 PDF 不收
            r = client.post("/api/downloads/文献/下-4/file", files={"file": ("a.pdf", PDF, "application/pdf")}).json()
            assert r["lamp"] == "ok" and r["at"] == "资料/文献/原文/L1 开放的.pdf"                 # 跟 下-1 一模一样：不重复入库
            assert client.post("/api/downloads/文献/下-3/file", files={"file": ("a.pdf", b"hello", "application/pdf")}).status_code == 400

            items = client.get("/api/downloads/文献").json()["items"]
            assert [x["lamp"] for x in items] == ["ok", "bad", "", "ok"]
            t = client.get("/api/modules/文献/tree").json()
            row = next(n for n in t["sections"][0]["items"] if n["label"] == "下载列表")
            assert row["path"] == "#下载:文献"
            assert sum(x["lamp"] == "ok" for x in items) == 2
    finally:
        srv.shutdown()


def test_picks_up_what_you_download_yourself(proj, monkeypatch, tmp_path):
    (proj.materials / "文献").mkdir(parents=True)
    dl = tmp_path / "Downloads"
    dl.mkdir()
    (dl / "以前的.pdf").write_bytes(PDF)                                                  # 点之前就在的不算
    monkeypatch.setattr(downloads, "downloads_dir", lambda: dl)
    monkeypatch.setattr(downloads, "lookup_oa", lambda doi, timeout=15: "")
    import store
    c = store.connect(proj.db_path)
    store.migrate(c)
    downloads.add(c, proj, "文献", title="要登录的", doi="10.1000/xyz")
    c.close()
    downloads.watch(proj, "文献", "下-1", timeout=8, poll=0.1, settle=0.3)
    assert downloads.get(proj, "文献", "下-1")["state"] == "等你下"
    time.sleep(0.3)
    (dl / "新下的.pdf.crdownload").write_bytes(PDF[:5])                                   # 浏览器还没下完：不算
    time.sleep(0.5)
    (dl / "新下的.pdf.crdownload").rename(dl / "新下的.pdf")
    got = _until(lambda: (x := downloads.get(proj, "文献", "下-1"))["at"].startswith("资料/文献/原文/L") and x)
    assert got and got["lamp"] == "ok" and got["at"] == "资料/文献/原文/L1 要登录的.pdf"
    assert (dl / "新下的.pdf").is_file() and (dl / "以前的.pdf").is_file()                  # 原件不动


def test_agent_puts_papers_on_the_list(proj):
    (proj.materials / "文献").mkdir(parents=True)
    got = anyio.run(_call, proj, [
        ("add_download", {"title": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762", "why": "需-9 图解要用"}),
        ("add_download", {"title": "x"}),
        ("get_overview", {}),
    ])
    assert "下-1" in got[0] and got[1].startswith("没排进去")
    assert "## 下载清单：1 篇还没下好" in got[2] and "文献 下-1 Attention Is All You Need" in got[2]
    x = downloads.get(proj, "文献", "下-1")
    assert x["by"] == "agent:test-agent" and x["why"] == "需-9 图解要用" and x["direct"] == "https://arxiv.org/pdf/1706.03762"


def test_list_looks_like_the_v3_one(proj, monkeypatch):
    """作者 09-28：「下载清单可以参考一下这个格式」——按出版社分组、每组一句去哪下；作者 · 年 · 期刊；存成什么名字。"""
    (proj.materials / "文献").mkdir(parents=True)
    old = ("# 下载清单\n\n| | 标题 | 链接 | DOI | 免费直链 | 为什么要 | 谁加的 | 放在 |\n|---|---|---|---|---|---|---|---|\n"
           "| 下-1 | Nearest neighbor pattern classification | https://doi.org/10.1109/TIT.1967.1053964 | 10.1109/TIT.1967.1053964 |  | 旧的一行 | 人 |  |\n")
    (proj.materials / "文献" / "下载清单.md").write_text(old, encoding="utf-8")        # 旧的 8 格表：照样读，写的时候换成新表头

    def fake(doi, timeout=15):
        downloads._META[doi] = {"authors": "Kevin Beyer; Jonathan Goldstein等", "year": "1999",
                                "venue": "Lecture Notes in Computer Science · 卷 1540", "title": "When Is Nearest Neighbor Meaningful?"}
        return ""
    monkeypatch.setattr(downloads, "lookup_oa", fake)
    with TestClient(create_app(proj)) as client:
        add = lambda **kw: client.post("/api/downloads/文献", json=kw).json()
        a = add(doi="10.1007/3-540-49257-7_15")                                       # 只给 DOI：标题、作者、年、期刊 OpenAlex 补
        b = add(title="R: A Language and Environment", url="https://www.r-project.org/", note="软件手册，不必下 PDF",
                authors="R Core Team", year="2025")
        c = add(title="Feature Selection: A Data Perspective", doi="10.1145/3136625")
        assert a["code"] == "下-2" and c["code"] == "下-4"
        got = _until(lambda: (x := downloads.get(proj, "文献", "下-2"))["authors"] and x)
        assert got["title"] == "When Is Nearest Neighbor Meaningful?" and got["year"] == "1999" and got["venue"].startswith("Lecture Notes")
        items = {x["code"]: x for x in client.get("/api/downloads/文献").json()["items"]}
        assert [items[k]["group"] for k in ("下-1", "下-2", "下-3", "下-4")] == ["IEEE", "Springer · Nature · BMC", "其它 · 没有 DOI", "ACM"]
        assert "IEEE Xplore" in items["下-1"]["howto"] and items["下-3"]["note"] == "软件手册，不必下 PDF" and items["下-3"]["authors"] == "R Core Team"
        assert items["下-4"]["save_as"] == "下-4 Feature Selection A Data Perspective.pdf"
        text = (proj.materials / "文献" / "下载清单.md").read_text(encoding="utf-8")
        assert "| 放在 | 作者 | 年 | 期刊 | 备注 |" in text and "| 放在 |\n" not in text      # 表头换新了
        assert items["下-1"]["why"] == "旧的一行" and items["下-1"]["lamp"] == ""

        # 照「存成」的名字放进 原文/：刷新清单就认出是 下-4，入库成 L 号，作者、年、期刊带进 信息.json
        downloads._META["10.1145/3136625"] = {"authors": "Jundong Li; Kewei Cheng等", "year": "2017", "venue": "ACM Computing Surveys · 卷 50", "title": ""}
        downloads._set(proj, "文献", "下-4", authors="Jundong Li; Kewei Cheng等", year="2017", venue="ACM Computing Surveys · 卷 50")
        (proj.materials / "文献" / "原文").mkdir(exist_ok=True)
        (proj.materials / "文献" / "原文" / items["下-4"]["save_as"]).write_bytes(PDF)
        x = {i["code"]: i for i in client.get("/api/downloads/文献").json()["items"]}["下-4"]
        assert x["lamp"] == "ok" and x["at"].startswith("资料/文献/原文/L1 ")
        lib = client.get("/api/library/文献").json()["items"][0]
        assert lib["title"] == "Feature Selection: A Data Perspective" and lib["info"]["作者"] == "Jundong Li; Kewei Cheng等"
        assert lib["info"]["年份"] == "2017" and lib["info"]["DOI"] == "10.1145/3136625"


def test_arxiv_gets_its_info_and_no_false_alarm(proj, monkeypatch):
    """arXiv 的 DOI OpenAlex 不收（404）：不报错，去 arXiv 自己那补作者、年；本来能直接下的不提示「没有免费版」。"""
    import urllib.error
    (proj.materials / "文献").mkdir(parents=True)

    def oa(doi, timeout=15):
        if doi.startswith("10.48550/"):
            raise urllib.error.HTTPError("https://api.openalex.org", 404, "Not Found", {}, None)
        raise urllib.error.HTTPError("https://api.openalex.org", 404, "Not Found", {}, None)
    monkeypatch.setattr(downloads, "lookup_oa", oa)
    monkeypatch.setattr(downloads, "lookup_arxiv", lambda aid, timeout=15: {
        "authors": "Ashish Vaswani; Noam Shazeer等", "year": "2017", "venue": "arXiv", "title": "Attention Is All You Need"} if aid == "1706.03762" else {})
    with TestClient(create_app(proj)) as client:
        add = lambda **kw: client.post("/api/downloads/文献", json=kw).json()
        a = add(url="https://arxiv.org/abs/1706.03762v7", doi="10.48550/arXiv.1706.03762")
        b = add(title="只有链接", url="https://arxiv.org/pdf/1706.03762")                    # 同一篇：链接不一样也按 DOI 认不出，算两行
        c = add(title="查不到的", doi="10.9999/nothing")
        got = _until(lambda: (x := downloads.get(proj, "文献", a["code"]))["authors"] and x)
        assert got["title"] == "Attention Is All You Need" and got["year"] == "2017" and got["venue"] == "arXiv"
        assert got["direct"] == "https://arxiv.org/pdf/1706.03762v7" and not got.get("msg")        # 带版本号的就下那一版
        assert _until(lambda: downloads.get(proj, "文献", b["code"])["authors"]) == "Ashish Vaswani; Noam Shazeer等"
        miss = _until(lambda: (x := downloads.get(proj, "文献", c["code"])).get("msg") and x)
        assert miss["msg"].startswith("OpenAlex 里查不到这个 DOI；没有合法的免费版") and "HTTP Error" not in miss["msg"]


def test_info_found_after_download_reaches_the_library(proj, monkeypatch):
    """先下好入库、后查回作者年期刊：文献库那篇 信息.json 里还写「查不到」的跟着补上，写了的不动。"""
    (proj.materials / "文献").mkdir(parents=True)
    monkeypatch.setattr(downloads, "lookup_oa", lambda doi, timeout=15: "")
    import library
    import store
    c = store.connect(proj.db_path)
    store.migrate(c)
    x = downloads.add(c, proj, "文献", title="Some Paper", doi="10.1000/abc")
    c.close()
    src = proj.root / "dl.pdf"
    src.write_bytes(PDF)
    got = downloads.take(proj, "文献", x["code"], src)
    lib = library.entries(proj, "文献")[0][0]
    assert got["at"].startswith("资料/文献/原文/L1 ") and lib["info"]["作者"] == "查不到"
    lib_dir = proj.materials / "文献" / lib["folder"]
    info = json.loads((lib_dir / "信息.json").read_text(encoding="utf-8"))
    info["期刊"] = "我自己写的"
    (lib_dir / "信息.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    downloads._META["10.1000/abc"] = {"authors": "A. Author; B. Author", "year": "2020", "venue": "Some Journal", "title": ""}
    monkeypatch.setattr(downloads, "lookup_oa", lambda doi, timeout=15: "")
    downloads.find_free(proj, "文献", x["code"])
    info = json.loads((lib_dir / "信息.json").read_text(encoding="utf-8"))
    assert info["作者"] == "A. Author; B. Author" and info["年份"] == "2020" and info["期刊"] == "我自己写的"


def test_filename_like_pdf_titles_are_not_used(proj, monkeypatch):
    """PDF 自带的「标题」其实是排版时的文件名（guyon03a.dvi）：不认；清单上写了标题的用清单的。"""
    from test_library import make_pdf
    import library
    import store
    (proj.materials / "文献").mkdir(parents=True)
    monkeypatch.setattr(downloads, "lookup_oa", lambda doi, timeout=15: "")
    c = store.connect(proj.db_path)
    store.migrate(c)
    x = downloads.add(c, proj, "文献", title="An Introduction to Variable and Feature Selection", url="https://www.jmlr.org/papers/volume3/guyon03a/guyon03a.pdf")
    src = proj.root / "guyon03a.pdf"
    src.write_bytes(make_pdf("An Introduction", "guyon03a.dvi"))
    got = downloads.take(proj, "文献", x["code"], src)
    assert got["at"] == "资料/文献/原文/L1 An Introduction to Variable and Feature Se.pdf" or got["at"].startswith("资料/文献/原文/L1 An Introduction")
    other = proj.root / "外面的.pdf"
    other.write_bytes(make_pdf("Something", "paper_v3"))
    y = library.add(c, proj, "文献", other, name="我的草稿.pdf")                               # 不在清单上：用文件名
    c.close()
    assert y["title"] == "我的草稿"
    assert library.pdf_meta(other)[0] == "" and library.entries(proj, "文献")[0][0]["title"] == "An Introduction to Variable and Feature Selection"
