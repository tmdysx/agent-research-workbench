"""文献库（文献 S2-1、S2-2）：原文/ ↔ 解读/ 一一对应（L 号 + 指纹）；拖进来复制入库；下载清单下好的也入库；标签、分组、阅读状态。
作者 2026-09-27：「原文所有的原文一个文件夹，然后另一个文件夹专门放解释，然后一一对应」。"""
import json

from fastapi.testclient import TestClient

import downloads
import library
import store
from main import create_app


def make_pdf(text: str, title: str = "") -> bytes:
    """最小的一页 PDF（第一页有 text；带 Title 的话 PDF 自带标题）。"""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Title ({title}) >>".encode()]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    return bytes(out)


def test_drop_a_pdf_in_and_both_folders_line_up(proj, tmp_path):
    (proj.materials / "文献").mkdir(parents=True)
    trial = proj.materials / "文献" / "试验品" / "1-s2.0-S0957417423009570-main.pdf"
    trial.parent.mkdir()
    trial.write_bytes(make_pdf("Expert Systems with Applications doi:10.1016/j.eswa.2023.120462", "A trial paper about feature selection"))
    with TestClient(create_app(proj)) as client:
        assert client.get("/api/library/文献").json() == {"items": [], "problems": [], "states": ["没读", "在读", "读完"]}
        assert client.post("/api/library/文献/add", files={"file": ("x.pdf", b"hello", "application/pdf")}).status_code == 400
        x = client.post("/api/library/文献/add", files={"file": (trial.name, trial.read_bytes(), "application/pdf")}).json()
        assert x["code"] == "L1" and x["pdf"] == "原文/L1 A trial paper about feature selection.pdf"
        assert x["folder"] == "解读/L1 A trial paper about feature selection" and x["lamp"] == "ok"
        d = proj.materials / "文献" / x["folder"]
        assert all((d / part).is_dir() for part in ("文本", "图片", "图解"))
        info = json.loads((d / "信息.json").read_text(encoding="utf-8"))
        assert info["DOI"] == "10.1016/j.eswa.2023.120462" and info["指纹"] and info["阅读状态"] == "没读" and info["作者"] == "查不到"
        assert trial.is_file()                                                             # 试验品原件还在
        again = client.post("/api/library/文献/add", files={"file": ("copy.pdf", trial.read_bytes(), "application/pdf")}).json()
        assert again["code"] == "L1" and len(list((proj.materials / "文献" / "原文").glob("*.pdf"))) == 1   # 同一篇不重复入库

        # 原文改了名（连 L 号都去掉）：按指纹还对得上，信息.json 跟着改名字，不会当成新的一篇
        o = proj.materials / "文献" / "原文"
        (o / "L1 A trial paper about feature selection.pdf").rename(o / "我改的名字.pdf")
        r = client.get("/api/library/文献").json()
        assert [(i["code"], i["pdf"], i["lamp"]) for i in r["items"]] == [("L1", "原文/我改的名字.pdf", "ok")] and r["problems"] == []
        assert json.loads((d / "信息.json").read_text(encoding="utf-8"))["原文"] == "原文/我改的名字.pdf"

        # 对不上的亮灯：有原文没解读（带 L 号的）、有解读没原文
        (o / "L7 孤儿.pdf").write_bytes(make_pdf("orphan"))
        (proj.materials / "文献" / "解读" / "L9 没原文").mkdir()
        r = client.get("/api/library/文献").json()
        assert {p["text"] for p in r["problems"]} == {"L7 孤儿.pdf 有原文没解读", "L9 有解读没原文（解读/L9 没原文）"}
        (o / "L7 孤儿.pdf").unlink()
        (proj.materials / "文献" / "解读" / "L9 没原文").rmdir()

        # 下载清单下好的（原文/下-1 …pdf）自己入库，下载清单那一行跟着改名字、照样是绿的
        c = store.connect(proj.db_path)
        downloads.add(c, proj, "文献", title="Attention", url="https://arxiv.org/abs/1706.03762")
        c.close()
        src = tmp_path / "dl.pdf"
        src.write_bytes(make_pdf("Attention is all you need"))
        dl = downloads.take(proj, "文献", "下-1", src)
        assert dl["lamp"] == "ok" and dl["at"].startswith("资料/文献/原文/L2 ")          # L 号（号不回收：L9 用过，但这里没留下文件夹）
        r = client.get("/api/library/文献").json()
        assert [i["code"] for i in r["items"]] == ["L1", "L2"]

        # 管文献：标签、分组、阅读状态写回 信息.json
        assert client.put("/api/library/文献/L1", json={"阅读状态": "随便"}).status_code == 400
        x = client.put("/api/library/文献/L1", json={"标签": "试验、特征选择", "分组": ["ESWA"], "阅读状态": "在读"}).json()
        assert x["info"]["标签"] == ["试验", "特征选择"] and x["info"]["分组"] == ["ESWA"] and x["info"]["阅读状态"] == "在读"
        t = client.get("/api/modules/文献/tree").json()
        titles = {s["title"]: [n.get("label") for n in s["items"]] for s in t["sections"]}
        assert titles["工作台"] == ["下载列表", "文献库"]
        assert t["default"] == "#文献库:文献"
        assert [i["code"] for i in client.get("/api/library/文献").json()["items"]] == ["L1", "L2"]


def test_numbers_are_never_reused(proj):
    (proj.materials / "文献" / "原文").mkdir(parents=True)
    c = store.connect(proj.db_path)
    store.migrate(c)
    o = proj.materials / "文献" / "原文"
    (o / "a.pdf").write_bytes(make_pdf("one"))
    (o / "b.pdf").write_bytes(make_pdf("two"))
    assert library.scan(c, proj, "文献") == ["L1", "L2"]
    for f in (proj.materials / "文献" / "原文").glob("L2*"):
        f.unlink()
    import shutil
    for d in (proj.materials / "文献" / "解读").glob("L2*"):
        shutil.rmtree(d)
    (o / "c.pdf").write_bytes(make_pdf("three"))
    assert library.scan(c, proj, "文献") == ["L3"]
    c.close()
