"""截图和录屏：系统截图放进剪贴板的 BMP 转 PNG 要对；截好的、录好的进随堂笔记的草稿；记下时跟着编号进
笔记/截图/、笔记/录屏/（录屏带 5 张画面）；画过的图换掉草稿里那张；快捷键写法；等录屏文件夹里出现新视频。
不按真的键、不挂真的全局快捷键——那些只在正式启动时发生。"""
import functools
import struct
import threading
import time
import zlib

from fastapi.testclient import TestClient

import capture
import hotkeys
import notebook
from main import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32                  # 够当一张「图」了：只看类型和大小，不解码
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def _mp4(seconds=42):
    """一段只有文件头的「MP4」：够读出时长，不能播。"""
    mvhd = b"mvhd" + bytes(4) + struct.pack(">IIII", 0, 0, 1000, seconds * 1000) + bytes(80)
    moov = struct.pack(">I", len(mvhd) + 8) + b"moov" + struct.pack(">I", len(mvhd) + 4) + mvhd
    return b"\x00\x00\x00\x18ftypisom" + bytes(12) + moov


def _dib(w, h, bpp, pixels, top_down=False):
    """pixels[y][x] = (r, g, b)，y 从上往下数；做一张剪贴板里那样的 BMP（BITMAPINFOHEADER + 像素）。"""
    stride = ((w * bpp + 31) // 32) * 4
    rows = []
    for y in (range(h) if top_down else reversed(range(h))):
        row = b"".join(bytes((b, g, r)) + (b"\xff" if bpp == 32 else b"") for r, g, b in pixels[y])
        rows.append(row + b"\x00" * (stride - len(row)))
    head = struct.pack("<IiiHHIIiiII", 40, w, -h if top_down else h, 1, bpp, 0, 0, 0, 0, 0, 0)
    return head + b"".join(rows)


def _decode(png):
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    at, idat, w = 8, b"", 0
    while at < len(png):
        n, t = struct.unpack_from(">I4s", png, at)
        data = png[at + 8:at + 8 + n]
        assert struct.unpack_from(">I", png, at + 8 + n)[0] == zlib.crc32(t + data)
        if t == b"IHDR":
            w, h = struct.unpack_from(">II", data)
        elif t == b"IDAT":
            idat += data
        at += 12 + n
    raw = zlib.decompress(idat)
    out = []
    for y in range(h):
        line = raw[y * (w * 3 + 1):(y + 1) * (w * 3 + 1)]
        assert line[0] == 0
        out.append([tuple(line[1 + 3 * x:4 + 3 * x]) for x in range(w)])
    return out


PIX = [[(255, 0, 0), (0, 255, 0), (0, 0, 255)],
       [(10, 20, 30), (200, 100, 50), (1, 2, 3)]]


def test_clipboard_bitmaps_become_the_same_png():
    for bpp in (24, 32):
        for top_down in (False, True):
            assert _decode(capture.dib_to_png(_dib(3, 2, bpp, PIX, top_down))) == PIX, (bpp, top_down)


def test_hotkey_text():
    assert hotkeys.fmt("alt+ctrl+s") == "Ctrl+Alt+S" and hotkeys.fmt(" ctrl ＋ alt ＋ f5 ") == "Ctrl+Alt+F5"
    assert hotkeys.fmt("") == "" and hotkeys.parse("Ctrl+Alt+R") == (0x2 | 0x1, ord("R"))
    for bad, why in (("Shift+S", "Ctrl、Alt 或 Win"), ("Ctrl+Alt+空格", "当不了快捷键"), ("Hyper+S", "不是 Ctrl")):
        try:
            hotkeys.parse(bad)
        except ValueError as e:
            assert why in str(e), bad
        else:
            raise AssertionError(bad)


def test_drafts_save_into_shot_and_video_folders(proj):
    with TestClient(create_app(proj)) as client:
        up = lambda name, data, ct: client.post("/api/note/drafts", files={"file": (name, data, ct)})
        bad = up("a.txt", b"hello", "text/plain")
        assert bad.status_code == 400 and "只收图片" in bad.json()["detail"]
        a = up("a.png", PNG, "image/png").json()
        x = up("x.png", PNG, "image/png").json()
        v = up("rec.mp4", _mp4(42), "").json()                          # 拖进来的视频有时不带类型：看后缀
        assert a["path"].startswith("笔记/截图/.草稿/") and v["path"].startswith("笔记/录屏/.草稿/")
        assert v["kind"] == "video" and v["seconds"] == 42 and v["frames"] == []
        assert client.get("/pfiles/" + a["path"]).status_code == 200
        # 网页抽的 5 张画面放在录屏旁边；草稿列表里不单列
        frames = [("files", (f"{i}.jpg", JPG, "image/jpeg")) for i in range(5)]
        v = client.post(f"/api/note/drafts/{v['name']}/frames", files=frames).json()
        assert len(v["frames"]) == 5 and v["frames"][0].endswith("-画面1.jpg")
        assert [i["kind"] for i in client.get("/api/note/drafts").json()["items"]] == ["image", "image", "video"]
        assert client.get("/api/state").json()["drafts"] == {"image": 2, "video": 1}
        # 画过的图换掉原来那张；画面也能画
        b = client.put(f"/api/note/drafts/{a['name']}", files={"file": ("a.png", b"\x89PNG-drawn", "image/png")}).json()
        assert b["name"] == a["name"] and (proj.root / a["path"]).read_bytes() == b"\x89PNG-drawn"
        f1 = v["frames"][0].rsplit("/", 1)[1]
        v2 = client.put(f"/api/note/drafts/{f1}", files={"file": ("f.jpg", b"\xff\xd8drawn", "image/jpeg")}).json()
        assert v2["name"] == v["name"] and (proj.root / v["frames"][0]).read_bytes() == b"\xff\xd8drawn"
        # 去掉一张没记下的：草稿直接没了（跟打了又删的字一样），不进回收站
        client.post(f"/api/note/drafts/{x['name']}/drop")
        assert not (proj.root / x["path"]).exists() and not (proj.root / "回收站").exists()
        # 记下：截图、录屏跟着编号走；录屏带着画面和时长
        e = client.post("/api/notes/总览", json={"text": "看这里", "attach": [a["name"], v["name"]]}).json()
        assert e["id"] == "总-001"
        assert e["body"].split("\n") == ["看这里", "", "![截图](笔记/截图/总-001.png)", "[录屏 0:42](笔记/录屏/总-001.mp4)"] + [
            f"![录屏画面 {i}/5](笔记/录屏/总-001-画面{i}.jpg)" for i in range(1, 6)]
        assert (proj.root / "笔记/录屏/总-001-画面5.jpg").exists() and (proj.root / "笔记/截图/总-001.png").exists()
        assert client.get("/api/note/drafts").json()["items"] == []
        # 草稿里没有的名字、单独的画面都不认
        assert client.post("/api/notes/总览", json={"text": "x", "attach": ["../../AGENTS.md"]}).status_code == 400
        assert [s["scope"] for s in notebook.scopes(proj, [])] == ["总览"]      # 截图/ 录屏/ 不会被当成一本笔记
        # 去掉一段录屏，连它的画面一起去掉
        v3 = up("r2.mp4", _mp4(5), "video/mp4").json()
        client.post(f"/api/note/drafts/{v3['name']}/frames", files=[("files", ("1.jpg", JPG, "image/jpeg"))])
        client.post(f"/api/note/drafts/{v3['name']}/drop")
        assert list((proj.root / "笔记/录屏/.草稿").iterdir()) == []


def test_waiting_for_a_new_recording(tmp_path):
    folder = tmp_path / "Screen Recordings"
    folder.mkdir()
    (folder / "old.mp4").write_bytes(b"old")
    before, since, stop = {"old.mp4"}, time.time(), threading.Event()

    def recorder():                                          # 截图工具：过一会儿开始写，写两下才写完
        time.sleep(0.15)
        with open(folder / "new.mp4", "wb") as f:
            f.write(b"part1")
        time.sleep(0.15)
        with open(folder / "new.mp4", "ab") as f:
            f.write(b"part2")

    threading.Thread(target=recorder).start()
    got = capture.wait_video(folder, before, since, stop, timeout=5, poll=0.05, settle=0.4)
    assert got == folder / "new.mp4" and got.read_bytes() == b"part1part2"
    stop.set()                                               # 喊停：马上不等了
    assert capture.wait_video(folder, before | {"new.mp4"}, since, stop, timeout=5, poll=0.05, settle=0.4) is None


def test_capture_lands_in_the_draft(proj, monkeypatch, tmp_path):
    shot = capture.dib_to_png(_dib(3, 2, 32, PIX))
    rec_dir = tmp_path / "录屏在这"
    rec_dir.mkdir()
    pressed = []
    clip = {"seq": 1, "img": None}
    monkeypatch.setattr(capture, "available", lambda: True)
    monkeypatch.setattr(capture, "press", lambda *vks: pressed.append(vks))
    monkeypatch.setattr(capture, "clipboard_seq", lambda: clip["seq"])
    monkeypatch.setattr(capture, "clipboard_image", lambda: clip["img"])
    monkeypatch.setattr(capture, "wait_video", functools.partial(capture.wait_video, poll=0.05, settle=0.3))

    def until(cond, sec=5):
        end = time.time() + sec
        while time.time() < end and not cond():
            time.sleep(0.05)
        assert cond()

    with TestClient(create_app(proj)) as client:
        s = client.put("/api/capture-settings", json={"shot": "alt+ctrl+q", "record": "", "folder": str(rec_dir)}).json()
        assert (s["shot"], s["record"], s["folder"], s["status"]["shot"]) == ("Ctrl+Alt+Q", "", str(rec_dir), "not_running")
        assert client.put("/api/capture-settings", json={"shot": "Ctrl+Alt+Q", "record": "ctrl+alt+q"}).status_code == 400
        assert client.put("/api/capture-settings", json={"folder": "相对路径"}).status_code == 400
        ws = client.websocket_connect("/ws").__enter__()            # 网页开着、随堂笔记开着：截的进正在写的这条（草稿）
        ws.receive_json()
        ws.send_text('{"type": "note", "open": true, "scope": "总览"}')
        time.sleep(0.2)
        # 截图：替你按 Win+Shift+S；剪贴板没变就不拿，变了（来了新图）才拿
        assert client.post("/api/note/capture", json={"kind": "image"}).json()["kind"] == "image"
        assert client.post("/api/note/capture", json={"kind": "video"}).status_code == 409      # 一次只等一件
        until(lambda: pressed)
        assert pressed[0] == (0x5B, 0x10, 0x53)
        time.sleep(0.3)
        assert client.get("/api/note/drafts").json()["items"] == []
        clip.update(seq=2, img=shot)
        until(lambda: client.get("/api/note/capture").json()["kind"] is None)
        [it] = client.get("/api/note/drafts").json()["items"]
        assert it["kind"] == "image" and (proj.root / it["path"]).read_bytes() == shot
        # 按了 Esc：网页喊停，什么都不进
        client.post("/api/note/capture", json={"kind": "image"})
        client.post("/api/note/capture/cancel")
        until(lambda: client.get("/api/note/capture").json()["kind"] is None)
        # 录屏：替你按 Win+Shift+R；录屏文件夹里出现新视频、写完了，复制一份进草稿，原件不动
        client.post("/api/note/capture", json={"kind": "video"})
        until(lambda: len(pressed) == 3)
        assert pressed[2] == (0x5B, 0x10, 0x52)
        (rec_dir / "录屏 2026-09-27.mp4").write_bytes(_mp4(7))
        until(lambda: client.get("/api/note/capture").json()["kind"] is None)
        items = client.get("/api/note/drafts").json()["items"]
        assert [i["kind"] for i in items] == ["image", "video"] and items[1]["seconds"] == 7
        assert (rec_dir / "录屏 2026-09-27.mp4").exists()
        assert "截图进草稿" in [e["action"] for e in client.get("/api/events").json()]
        monkeypatch.setattr(capture, "available", lambda: False)
        r = client.post("/api/note/capture", json={"kind": "image"})
        assert r.status_code == 400 and "Ctrl+V" in r.json()["detail"]
        ws.__exit__(None, None, None)


def test_straight_into_notes_when_the_window_is_closed(proj, monkeypatch, tmp_path):
    """作者：「这些截图和录屏能不能直接进我的笔记之中？」——小窗关着直接记成一条；开着进正在写的这条。"""
    import json
    shot = capture.dib_to_png(_dib(3, 2, 32, PIX))
    rec_dir = tmp_path / "rec"
    rec_dir.mkdir()
    clip = {"seq": 1, "img": None}
    monkeypatch.setattr(capture, "available", lambda: True)
    monkeypatch.setattr(capture, "press", lambda *vks: None)
    monkeypatch.setattr(capture, "clipboard_seq", lambda: clip["seq"])
    monkeypatch.setattr(capture, "clipboard_image", lambda: clip["img"])
    monkeypatch.setattr(capture, "wait_video", functools.partial(capture.wait_video, poll=0.05, settle=0.2))

    def until(cond, sec=5):
        end = time.time() + sec
        while time.time() < end and not cond():
            time.sleep(0.05)
        assert cond()

    with TestClient(create_app(proj)) as client:
        client.put("/api/capture-settings", json={"shot": "Ctrl+Alt+S", "record": "Ctrl+Alt+R", "folder": str(rec_dir)})
        idle = lambda: client.get("/api/note/capture").json()["kind"] is None

        def snap():
            client.post("/api/note/capture", json={"kind": "image"})
            time.sleep(0.1)
            clip.update(seq=clip["seq"] + 1, img=shot)
            until(idle)

        # 网页一个都没开：记进总览，直接一条，不进草稿
        snap()
        [e] = notebook.read(proj, "总览")
        assert (e["id"], e["kind"], e["body"]) == ("总-001", "截图", "![截图](笔记/截图/总-001.png)")
        assert client.get("/api/state").json()["last_capture"]["id"] == "总-001"
        assert client.get("/api/note/drafts").json()["items"] == []
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"type": "note", "open": False, "scope": "文献"}))     # 在文献页，小窗关着
            time.sleep(0.2)
            snap()
            assert [x["id"] for x in notebook.read(proj, "文献")] == ["文献-001"]
            ws.send_text(json.dumps({"type": "note", "open": True, "scope": "文献"}))      # 小窗开着：进正在写的这条
            time.sleep(0.2)
            snap()
            assert len(notebook.read(proj, "文献")) == 1
            assert [i["kind"] for i in client.get("/api/note/drafts").json()["items"]] == ["image"]
            ws.send_text(json.dumps({"type": "note", "open": False, "scope": "文献"}))
            time.sleep(0.2)
            # 录屏也直接记成一条；画面等网页开着时补上
            client.post("/api/note/capture", json={"kind": "video"})
            time.sleep(0.1)
            (rec_dir / "a.mp4").write_bytes(_mp4(9))
            until(idle)
        v = notebook.read(proj, "文献")[-1]
        assert (v["id"], v["kind"], v["body"]) == ("文献-002", "录屏", "[录屏 0:09](笔记/录屏/文献-002.mp4)")
        assert client.get("/api/state").json()["frameless"] == ["笔记/录屏/文献-002.mp4"]
        frames = [("files", (f"{i}.jpg", JPG, "image/jpeg")) for i in range(5)]
        r = client.post("/api/note/saved/frames", params={"path": "笔记/录屏/文献-002.mp4"}, files=frames)
        assert r.status_code == 200
        body = notebook.read(proj, "文献")[-1]["body"].split("\n")
        assert body[0] == "[录屏 0:09](笔记/录屏/文献-002.mp4)" and body[5] == "![录屏画面 5/5](笔记/录屏/文献-002-画面5.jpg)"
        assert client.get("/api/state").json()["frameless"] == []
        log = (proj.root / "笔记/历史/改动记录.md").read_text(encoding="utf-8")
        assert "补上了 文献-002 的录屏画面" in log
        assert client.post("/api/note/saved/frames", params={"path": "笔记/录屏/文献-002.mp4"}, files=frames).status_code == 400
        # 在笔记本里画：换掉那张，原图先留进 笔记/历史/原图/
        put = lambda data, ct: client.put("/api/note/saved/image", params={"path": "笔记/截图/总-001.png"}, files={"file": ("x", data, ct)})
        assert put(b"\x89PNG-1", "image/png").json()["original"] == "笔记/历史/原图/总-001.png"
        assert put(b"\x89PNG-2", "image/png").json()["original"] == "笔记/历史/原图/总-001（第2次改前）.png"
        assert (proj.root / "笔记/截图/总-001.png").read_bytes() == b"\x89PNG-2"
        assert (proj.root / "笔记/历史/原图/总-001.png").read_bytes() == shot
        assert put(JPG, "image/jpeg").status_code == 400
        assert client.put("/api/note/saved/image", params={"path": "AGENTS.md"}, files={"file": ("x", b"x", "image/png")}).status_code == 400
