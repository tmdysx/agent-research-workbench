"""自动更新：网页里写着自己的版本；网页文件一改，连着的网页收到「ui」自己刷新（作者 2026-09-27：「自动更新网页」）。"""
import time

from fastapi.testclient import TestClient

import main
from main import create_app


def test_page_knows_its_version_and_hears_when_it_changes(proj, tmp_path, monkeypatch):
    page = tmp_path / "模板.html"
    page.write_text("<!doctype html><html><head><title>x</title></head><body></body></html>", encoding="utf-8")
    monkeypatch.setattr(main, "PAGE", page)
    with TestClient(create_app(proj, watch_interval=0.1)) as client:
        v1 = main.ui_version()
        html = client.get("/").text
        assert f'<meta name="rc-ui" content="{v1}">' in html and html.count("rc-ui") == 1
        assert client.get("/api/ping").json()["ui"] == v1
        with client.websocket_connect("/ws") as ws:
            hello = ws.receive_json()
            assert hello["type"] == "hello" and hello["ui"] == v1
            time.sleep(0.3)
            page.write_text(page.read_text(encoding="utf-8").replace("<title>x</title>", "<title>改过了</title>"), encoding="utf-8")
            end = time.time() + 5
            got = None
            while time.time() < end:
                m = ws.receive_json()
                if m.get("type") == "ui":
                    got = m
                    break
            assert got and got["ui"] == main.ui_version() != v1
