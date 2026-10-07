"""回收站：agent 照删除请求挪进 回收站/（按原路径原样放、清单记 X 号），能原样还原；网页只看。"""
import pytest
from fastapi.testclient import TestClient

import notebook
import store
import trash
from main import create_app


def test_move_list_restore_and_requests(proj):
    with TestClient(create_app(proj)) as client:
        (proj.materials / "文献" / "旧稿.pdf").write_bytes(b"%PDF old")
        client.post("/api/notes/文献", json={"text": "请删除 资料/文献/旧稿.pdf", "kind": "删除请求"})
        got = client.get("/api/trash").json()
        assert [r["id"] for r in got["requests"]] == ["文献-001"] and got["items"] == []

        c = store.connect(proj.db_path)
        r = trash.move(c, proj, "资料/文献/旧稿.pdf", by="agent:x", reason="人说旧稿不要了", request="文献-001")
        assert r["code"] == "X1" and not (proj.materials / "文献" / "旧稿.pdf").exists()
        assert (proj.root / r["to"]).read_bytes() == b"%PDF old"                    # 按原路径原样放着
        got = client.get("/api/trash").json()
        assert got["requests"] == [] and got["items"][0]["status"] == "在回收站"      # 请求对上了，不再算待删
        assert got["items"][0]["fields"]["原来在"] == "资料/文献/旧稿.pdf"

        for bad, why in [("资料/文献/没有这个.pdf", "找不到"), ("索引/state.db", "不许挪"), ("../外面.txt", "项目里面"),
                         ("笔记/历史/改动记录.md", "不许挪"), ("回收站/清单.md", "不许挪")]:
            with pytest.raises(store.Refused, match=why):
                trash.move(c, proj, bad, by="agent:x", reason="试试")
        with pytest.raises(store.Refused, match="为什么"):
            trash.move(c, proj, "资料/文献", by="agent:x", reason=" ")

        (proj.materials / "文献" / "旧稿.pdf").write_bytes(b"new")               # 原位置又有了同名的 → 先问人，不动
        with pytest.raises(store.NeedConfirm, match="已经有"):
            trash.restore(c, proj, "X1", by="agent:x")
        assert (proj.materials / "文献" / "旧稿.pdf").read_bytes() == b"new"
        r = trash.restore(c, proj, "X1", by="人", swap=True)                  # 人确认了：现有的先挪进回收站（X2），再还原
        assert r["back_to"] == "资料/文献/旧稿.pdf" and r["swapped"] == "X2"
        assert (proj.materials / "文献" / "旧稿.pdf").read_bytes() == b"%PDF old"
        items = {e["code"]: e for e in trash.read(proj)}
        assert items["X1"]["status"] == "已还原" and "还原于" in items["X1"]["fields"]
        assert items["X2"]["fields"]["从哪来"] == "还原 X1 换下来的"
        with pytest.raises(store.Refused, match="已经已还原"):
            trash.restore(c, proj, "X1", by="agent:x")
        assert trash.move(c, proj, "资料/文献/旧稿.pdf", by="agent:x", reason="又不要了")["code"] == "X3"   # 号不回收
        c.close()


def test_qa_page_has_pending_answers_and_decisions(proj):
    c = store.connect(proj.db_path)
    q1 = store.ask_human(c, "图用 PDF 还是 PNG？", by="agent:x")
    store.answer(c, q1["code"], "PDF")
    store.ask_human(c, "封面什么颜色？", by="agent:x", context="查过：A-01 不管颜色")
    c.close()
    with TestClient(create_app(proj)) as client:
        qa = client.get("/api/qa").json()
        assert [p["code"] for p in qa["pending"]] == ["D-02"]
        assert [d["code"] for d in qa["decisions"]] == ["A-01"] and qa["answers"] == []
