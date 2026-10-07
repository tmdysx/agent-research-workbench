"""离固化还差什么（S1-6 S2-12；作者 10-02「固化通用核心什么时候固化好？」）：四条固化条件各一盏灯，现算。"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

import freeze
import journal
import store
from main import create_app


def test_four_lamps_before_freezing(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    s = freeze.status(c, proj)
    lamps = {x["key"]: x for x in s["items"]}
    assert list(lamps) == ["final", "iface", "paper", "core"] and s["ready"] is False
    assert lamps["iface"]["ok"] is False and "0 天前" in lamps["iface"]["now"]          # 头一回：从今天数
    with store.tx(c):                                                                 # 指纹没变、已经过了两周：亮
        store._set_meta(c, "iface_since", (date.today() - timedelta(days=15)).isoformat())
    assert {x["key"]: x for x in freeze.status(c, proj)["items"]}["iface"]["ok"] is True
    with store.tx(c):                                                                 # 指纹变了：从今天重新数
        store._set_meta(c, "iface_sig", "changed")
    assert {x["key"]: x for x in freeze.status(c, proj)["items"]}["iface"]["ok"] is False
    assert lamps["core"]["ok"] is True                                                # 测试项目没改过核心
    journal.add(c, proj, "改了 main.py", kind="改了核心")
    core = {x["key"]: x for x in freeze.status(c, proj)["items"]}["core"]
    assert core["ok"] is False and "改了 1 次核心" in core["now"] and "main.py" in core["more"]
    c.close()


def test_people_mark_the_paper_done(proj):
    with TestClient(create_app(proj)) as client:
        assert {x["key"]: x for x in client.get("/api/freeze").json()["items"]}["paper"]["ok"] is False
        d = client.post("/api/freeze/paper", json={"done": True}).json()
        paper = {x["key"]: x for x in d["items"]}["paper"]
        assert paper["ok"] is True and paper["now"].startswith(date.today().isoformat())
        d = client.post("/api/freeze/paper", json={"done": False}).json()
        assert {x["key"]: x for x in d["items"]}["paper"]["ok"] is False
