"""笔记本：网页上的一切，最后都落成笔记（作者 2026-09-23：「网页版就是一个笔记本」）。

- 笔记存在项目根的 `笔记/` 文件夹，**按模块一个文件**：`笔记/总览.md`、`笔记/<模块名>.md`
- **每条有编号**（`文献-003`），带时间、谁、什么事——编号好找，改和删都方便
- 你在网页上做的事（放进模块、拍板、加模块、装技能、要删什么…）自动记一条进对应模块的笔记
- **凡是复制给 agent 的，整段存进 `笔记/历史/`，永不删**；改一条、删一条之前，原文也先记进 `笔记/历史/改动记录.md`
- 都是普通 md 文件：agent 直接能读，能进 git
- **截图、录屏**（作者 2026-09-27：「笔记要有截图功能」「笔记要专门有截图和录屏的文件夹」）：
  随堂笔记里截的、贴的先放 `笔记/截图/.草稿/`、`笔记/录屏/.草稿/`（跟没记下的字一样是草稿，去掉就没了）；
  记下时跟着那条的编号挪进 `笔记/截图/总-007.png`、`笔记/录屏/总-008.mp4`，录屏旁边还有 5 张画面
  `总-008-画面1.jpg`…（agent 大多看不了视频，看这几张）；正文末尾写上链接
"""
from __future__ import annotations

import atomic
import os
import re
import struct
import uuid
from datetime import datetime
from pathlib import Path

import store
from project import Project, check_name

DIR = "笔记"
HIST = "历史"
MAIN = "总览"
SHOTS = "截图"
VIDEOS = "录屏"
DRAFT = ".草稿"
IMG_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}
IMG_MAX = 20 * 1024 * 1024
VIDEO_MAX = 4 * 1024 ** 3
FRAMES = 5
_FRAME = re.compile(r"-画面(\d+)\.(jpg|png)$")
_HEAD =re.compile(r"^## (\S+?-\d{3,}) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?) · (.+?)\s*$")


def note_dir(p: Project) -> Path:
    return p.root / DIR


def _file(p: Project, scope: str) -> Path:
    if scope != MAIN:
        check_name(scope)                            # 模块名就是文件名，照文件夹名的规矩
    return note_dir(p) / f"{scope}.md"


def _prefix(scope: str) -> str:
    return "总" if scope == MAIN else scope


def parse(text: str) -> list[dict]:
    """把一个笔记文件拆成一条条：{id, at, by, kind, body}。"""
    out, cur = [], None
    for line in text.splitlines():
        m = _HEAD.match(line)
        if m:
            cur = {"id": m.group(1), "at": m.group(2), "by": m.group(3), "kind": m.group(4), "body": []}
            out.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    for e in out:
        e["body"] = "\n".join(e["body"]).strip()
    return out


def _render(scope: str, entries: list[dict]) -> str:
    head = f"# {scope} · 笔记\n\n> 每条有编号。网页上改和删之前，原文先记进 笔记/历史/改动记录.md。\n"
    return head + "".join(f"\n## {e['id']} · {e['at']} · {e['by']} · {e['kind']}\n{e['body']}\n" for e in entries)


def _clean(body: str) -> str:
    # 正文里以「## 」开头的行会被当成新的一条，降一级成「### 」
    return "\n".join("#" + l if l.startswith("## ") else l for l in (body or "").strip().splitlines())


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    atomic.replace(tmp, path)


def read(p: Project, scope: str) -> list[dict]:
    f = _file(p, scope)
    return parse(f.read_text(encoding="utf-8")) if f.is_file() else []


def scopes(p: Project, modules: list[str]) -> list[dict]:
    """笔记本的目录：总览 + 每个模块（没记过的也列出来）+ 笔记/ 里别的笔记文件。"""
    names = [MAIN] + [m for m in modules if m != MAIN]
    d = note_dir(p)
    if d.is_dir():
        names += sorted(f.stem for f in d.glob("*.md") if f.stem not in names)
    out = []
    for n in names:
        es = read(p, n)
        out.append({"scope": n, "count": len(es), "latest": es[-1]["at"] if es else None})
    return out


def _next_id(conn, p: Project, scope: str) -> str:
    """编号只增不减：删掉的号也不再用（记在库里 meta 表）。"""
    key = f"note_seq:{scope}"
    n = int(store._meta(conn, key) or 0)
    for e in read(p, scope):
        m = re.search(r"-(\d+)$", e["id"])
        if m:
            n = max(n, int(m.group(1)))
    store._set_meta(conn, key, str(n + 1))
    return f"{_prefix(scope)}-{n + 1:03d}"


def shots_dir(p: Project) -> Path:
    return note_dir(p) / SHOTS


def videos_dir(p: Project) -> Path:
    return note_dir(p) / VIDEOS


def _drafts_of(p: Project, kind: str) -> Path:
    return (shots_dir(p) if kind == "image" else videos_dir(p)) / DRAFT


def _new_name(ext: str) -> str:
    # 到毫秒：按进来的先后排；后面四位随机，同一毫秒也不撞
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}-{uuid.uuid4().hex[:4]}{ext}"


def _frames(f: Path) -> list[Path]:
    """录屏旁边那几张画面（画面1、画面2…按顺序）。"""
    out = []
    for g in f.parent.glob(f"{f.stem}-画面*"):
        m = _FRAME.search(g.name)
        if m and g.name[:m.start()] == f.stem:
            out.append((int(m.group(1)), g))
    return [g for _, g in sorted(out)]


def mp4_seconds(f: Path) -> float | None:
    """MP4 有多长（读文件头里的 mvhd，不解码）；读不出给 None。"""
    try:
        size = f.stat().st_size
        with open(f, "rb") as h:
            data = h.read(8 * 1024 * 1024)
            if b"mvhd" not in data and size > len(data):         # moov 在文件末尾：读最后一段
                h.seek(max(0, size - 8 * 1024 * 1024))
                data = h.read()
        at = data.find(b"mvhd")
        if at < 0:
            return None
        if data[at + 4] == 1:
            scale, dur = struct.unpack_from(">IQ", data, at + 4 + 4 + 16)
        else:
            scale, dur = struct.unpack_from(">II", data, at + 4 + 4 + 8)
        return dur / scale if scale else None
    except (OSError, struct.error, IndexError):
        return None


def _info(p: Project, f: Path, kind: str) -> dict:
    d = {"kind": kind, "name": f.name, "path": f.relative_to(p.root).as_posix(), "bytes": f.stat().st_size}
    if kind == "video":
        d["frames"] = [g.relative_to(p.root).as_posix() for g in _frames(f)]
        d["seconds"] = mp4_seconds(f) if f.suffix.lower() == ".mp4" else None
    return d


def _stream_in(src, dest: Path, limit: int, too_big: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    n = 0
    try:
        with open(tmp, "wb") as w:
            while chunk := src.read(1024 * 1024):
                n += len(chunk)
                if n > limit:
                    raise store.Refused(too_big)
                w.write(chunk)
        if not n:
            raise store.Refused("文件是空的")
        atomic.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def _kind_ext(content_type: str | None, filename: str | None) -> tuple[str, str]:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in IMG_TYPES:
        return "image", IMG_TYPES[ct]
    if ct in VIDEO_TYPES:
        return "video", VIDEO_TYPES[ct]
    ext = Path(filename or "").suffix.lower()                    # 有的浏览器拖进来的视频不带类型，看后缀
    if ext in VIDEO_TYPES.values():
        return "video", ext
    raise store.Refused("随堂笔记只收图片（png、jpg、webp、gif）和录屏（mp4、webm）")


def stage(p: Project, src, content_type: str | None, filename: str | None = None) -> dict:
    """贴进来、拖进来、截的一张图或者一段录屏：先放草稿，记下时才挪进 笔记/截图/ 或 笔记/录屏/。src 是能 read() 的东西。"""
    kind, ext = _kind_ext(content_type, filename)
    f = _drafts_of(p, kind) / _new_name(ext)
    if kind == "image":
        _stream_in(src, f, IMG_MAX, "图片太大了，20 MB 以内")
    else:
        _stream_in(src, f, VIDEO_MAX, "录屏太大了，4 GB 以内")
    return _info(p, f, kind)


def stage_video_file(p: Project, path: Path) -> dict:
    """系统截图工具录好的视频：复制一份进草稿，原件不动。"""
    with open(path, "rb") as src:
        return stage(p, src, None, path.name)


def drafts(p: Project) -> list[dict]:
    """随堂笔记里还没记下的截图和录屏（录屏旁边的画面跟着录屏，不单列），按进来的先后排。"""
    out = []
    for kind, exts in (("image", set(IMG_TYPES.values())), ("video", set(VIDEO_TYPES.values()))):
        d = _drafts_of(p, kind)
        if d.is_dir():
            out += [_info(p, f, kind) for f in d.iterdir()
                    if f.is_file() and f.suffix.lower() in exts and not _FRAME.search(f.name)]
    return sorted(out, key=lambda x: x["name"])


def draft_counts(p: Project) -> dict:
    items = drafts(p)
    return {"image": sum(1 for x in items if x["kind"] == "image"), "video": sum(1 for x in items if x["kind"] == "video")}


def _draft(p: Project, name: str) -> tuple[Path, str]:
    """按名字找草稿（截图、录屏、录屏的画面都行）→ (文件, image | video | frame)。"""
    if "/" in name or "\\" in name or name.startswith(".") or not name:
        raise store.Refused(f"草稿里没有：{name}")
    for kind in ("image", "video"):
        f = _drafts_of(p, kind) / name
        if f.is_file():
            return f, ("frame" if kind == "video" and _FRAME.search(name) else kind)
    raise store.Refused(f"草稿里没有：{name}")


def _video_of(frame: Path) -> Path:
    stem = frame.name[:_FRAME.search(frame.name).start()]
    for v in frame.parent.iterdir():
        if v.stem == stem and v.suffix.lower() in VIDEO_TYPES.values():
            return v
    raise store.Refused("找不到这张画面的录屏")


def replace_draft(p: Project, name: str, src, content_type: str | None) -> dict:
    """画过的图换掉草稿里原来那张（截图或者录屏的画面）。名字不变，后缀跟着新的走。"""
    f, kind = _draft(p, name)
    if kind == "video":
        raise store.Refused("录屏不能这样换；要画就画它的画面")
    ext = IMG_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if ext not in (".png", ".jpg"):
        raise store.Refused("画过的图要是 png 或 jpg")
    to = f.with_suffix(ext)
    _stream_in(src, to, IMG_MAX, "图片太大了，20 MB 以内")
    if to != f:
        f.unlink()
    return _info(p, _video_of(to), "video") if kind == "frame" else _info(p, to, "image")


def save_frames(p: Project, name: str, sources: list) -> dict:
    """网页从录屏里抽的画面（最多 5 张）：放在录屏旁边，叫「<录屏名>-画面1.jpg」…；再抽一次就换掉旧的。
    sources = [(能 read() 的东西, content_type), …]"""
    f, kind = _draft(p, name)
    if kind != "video":
        raise store.Refused("只有录屏才有画面")
    if not 1 <= len(sources) <= FRAMES:
        raise store.Refused(f"画面要 1 到 {FRAMES} 张")
    exts = [IMG_TYPES.get((ct or "").split(";")[0].strip().lower()) for _, ct in sources]
    if any(e not in (".jpg", ".png") for e in exts):
        raise store.Refused("画面要是 jpg 或 png")
    for g in _frames(f):
        g.unlink()
    for i, ((src, _), ext) in enumerate(zip(sources, exts), 1):
        _stream_in(src, f.with_name(f"{f.stem}-画面{i}{ext}"), IMG_MAX, "画面太大了")
    return _info(p, f, "video")


def drop_draft(p: Project, name: str) -> None:
    """去掉一张还没记下的截图 / 一段录屏（连它的画面）。它只是草稿（跟打了又删的字一样），不进回收站。"""
    f, kind = _draft(p, name)
    if kind == "frame":
        raise store.Refused("画面跟着录屏走，不单独去掉")
    for g in (_frames(f) if kind == "video" else []):
        g.unlink()
    f.unlink()


def _clock(sec: float | None) -> str:
    if not sec:
        return ""
    s = int(round(sec))
    return f" {s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f" {s // 60}:{s % 60:02d}"


def add(conn, p: Project, scope: str, body: str, *, by: str = "人", kind: str = "笔记",
        attach: list[str] | None = None) -> dict:
    body = _clean(body)
    items = [_draft(p, n) for n in (attach or [])]
    if any(k == "frame" for _, k in items):
        raise store.Refused("画面跟着录屏走，不单独记")
    if not body and not items:
        raise store.Refused("笔记是空的")
    with store.tx(conn):                              # 拿库的写锁当「笔记本的锁」：两个进程同时记也不会乱号
        entries = read(p, scope)
        eid = _next_id(conn, p, scope)
        lines, n = [], {"image": 0, "video": 0}
        for f, k in items:                            # 跟着这条的编号走：总-007.png、总-007-2.png、总-008.mp4
            n[k] += 1
            stem = eid if n[k] == 1 else f"{eid}-{n[k]}"
            if k == "image":
                to = shots_dir(p) / f"{stem}{f.suffix.lower()}"
                os.replace(f, to)
                lines.append(f"![截图]({DIR}/{SHOTS}/{to.name})")
            else:
                to = videos_dir(p) / f"{stem}{f.suffix.lower()}"
                frames = _frames(f)
                sec = mp4_seconds(f) if f.suffix.lower() == ".mp4" else None
                os.replace(f, to)
                lines.append(f"[录屏{_clock(sec)}]({DIR}/{VIDEOS}/{to.name})")
                for i, g in enumerate(frames, 1):
                    gt = videos_dir(p) / f"{stem}-画面{i}{g.suffix.lower()}"
                    os.replace(g, gt)
                    lines.append(f"![录屏画面 {i}/{len(frames)}]({DIR}/{VIDEOS}/{gt.name})")
        if lines:
            body = (body + "\n\n" if body else "") + "\n".join(lines)
        e = {"id": eid, "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "by": by, "kind": kind, "body": body}
        entries.append(e)
        _write(_file(p, scope), _render(scope, entries))
        store.log(conn, by, "记笔记", e["id"], kind)
    return e


def _history(p: Project, name: str) -> Path:
    return note_dir(p) / HIST / name


def _append_change(p: Project, line: str) -> None:
    f = _history(p, "改动记录.md")
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as w:
        w.write(line)


def edit(conn, p: Project, scope: str, eid: str, body: str, *, by: str = "人") -> dict:
    body = _clean(body)
    if not body:
        raise store.Refused("改完不能是空的；要删请点「删」")
    with store.tx(conn):
        entries = read(p, scope)
        e = next((x for x in entries if x["id"] == eid), None)
        if not e:
            raise store.Refused(f"{scope} 的笔记里没有 {eid}")
        _append_change(p, f"\n## {datetime.now():%Y-%m-%d %H:%M} · {by} 改了 {eid}（{scope}）\n原来是：\n{e['body']}\n")
        e["body"] = body
        _write(_file(p, scope), _render(scope, entries))
        store.log(conn, by, "改笔记", eid, scope)
    return e


def remove(conn, p: Project, scope: str, eid: str, *, by: str = "人") -> None:
    with store.tx(conn):
        entries = read(p, scope)
        e = next((x for x in entries if x["id"] == eid), None)
        if not e:
            raise store.Refused(f"{scope} 的笔记里没有 {eid}")
        _append_change(p, f"\n## {datetime.now():%Y-%m-%d %H:%M} · {by} 删了 {eid}（{scope}）\n原文：\n"
                          f"## {e['id']} · {e['at']} · {e['by']} · {e['kind']}\n{e['body']}\n")
        _write(_file(p, scope), _render(scope, [x for x in entries if x["id"] != eid]))
        store.log(conn, by, "删笔记", eid, scope)


def _num(eid: str) -> int:
    m = re.search(r"-(\d+)$", eid)
    return int(m.group(1)) if m else 0


def archive_copy(conn, p: Project, text: str, modules: list[str], *, by: str = "人") -> str:
    """复制给 agent 的，整段留一份在 笔记/历史/，永不删。返回文件名。
    同时记下每本笔记复制到了第几号：之后「新记的」只算比这个号大的——按编号算，不按时间，同一分钟里也不会错。"""
    with store.tx(conn):
        now = datetime.now()
        f = _history(p, f"{now:%Y-%m-%d %H-%M-%S} 复制给agent.md")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        for s in scopes(p, modules):
            top = max((_num(e["id"]) for e in read(p, s["scope"])), default=0)
            store._set_meta(conn, f"note_copied:{s['scope']}", str(top))
        store._set_meta(conn, "note_last_copy", now.strftime("%Y-%m-%d %H:%M:%S"))
        store.log(conn, by, "复制给 agent", f.name)
    return f.name


def since_last_copy(conn, p: Project, modules: list[str]) -> list[dict]:
    """上次复制给 agent 以后新记的笔记（导出指令时带上）。"""
    out = []
    for s in scopes(p, modules):
        done = int(store._meta(conn, f"note_copied:{s['scope']}") or 0)
        out += [{**e, "scope": s["scope"]} for e in read(p, s["scope"]) if _num(e["id"]) > done]
    return sorted(out, key=lambda e: (e["at"], e["scope"], _num(e["id"])))


def history(p: Project) -> list[dict]:
    d = note_dir(p) / HIST
    if not d.is_dir():
        return []
    return [{"name": f.name, "size": f.stat().st_size} for f in sorted(d.glob("*.md"), reverse=True)]


# ---------------------------------------------------------------- 直接记下的截图、录屏：补画面、在笔记本里画

def frameless(p: Project) -> list[str]:
    """已经记下、还没有画面的录屏（小窗关着时快捷键录的：记下那会儿网页还没抽画面）。网页开着就补上。"""
    d = videos_dir(p)
    if not d.is_dir():
        return []
    exts = set(VIDEO_TYPES.values())
    return sorted(f.relative_to(p.root).as_posix() for f in d.iterdir()
                  if f.is_file() and f.suffix.lower() in exts and not _frames(f))


def _saved(p: Project, rel: str, folders: tuple[Path, ...], exts: set[str]) -> Path:
    f = (p.root / (rel or "").replace("\\", "/")).resolve()
    if f.parent not in [x.resolve() for x in folders] or not f.is_file() or f.suffix.lower() not in exts:
        raise store.Refused(f"笔记里没有这个：{rel}")
    return f


def add_frames(conn, p: Project, video: str, sources: list, *, by: str = "人") -> dict | None:
    """给已经记下的录屏补上画面：放在录屏旁边，那条笔记末尾补上链接（改动记录里记一笔）。sources = [(能 read() 的, content_type), …]"""
    f = _saved(p, video, (videos_dir(p),), set(VIDEO_TYPES.values()))
    if _frames(f):
        raise store.Refused("这段录屏已经有画面了")
    if not 1 <= len(sources) <= FRAMES:
        raise store.Refused(f"画面要 1 到 {FRAMES} 张")
    exts = [IMG_TYPES.get((ct or "").split(";")[0].strip().lower()) for _, ct in sources]
    if any(e not in (".jpg", ".png") for e in exts):
        raise store.Refused("画面要是 jpg 或 png")
    for i, ((src, _), ext) in enumerate(zip(sources, exts), 1):
        _stream_in(src, f.with_name(f"{f.stem}-画面{i}{ext}"), IMG_MAX, "画面太大了")
    frames = _frames(f)
    link = f"]({DIR}/{VIDEOS}/{f.name})"
    d = note_dir(p)
    with store.tx(conn):
        for nf in sorted(d.glob("*.md")) if d.is_dir() else []:
            entries = parse(nf.read_text(encoding="utf-8"))
            e = next((x for x in entries if link in x["body"]), None)
            if not e:
                continue
            lines = e["body"].split("\n")
            at = next(i for i, l in enumerate(lines) if link in l) + 1
            lines[at:at] = [f"![录屏画面 {i}/{len(frames)}]({DIR}/{VIDEOS}/{g.name})" for i, g in enumerate(frames, 1)]
            _append_change(p, f"\n## {datetime.now():%Y-%m-%d %H:%M} · 网页补上了 {e['id']} 的录屏画面（{nf.stem}）\n原来是：\n{e['body']}\n")
            e["body"] = "\n".join(lines)
            _write(nf, _render(nf.stem, entries))
            store.log(conn, by, "补上录屏画面", e["id"], nf.stem)
            return e
    return None


def replace_saved_image(conn, p: Project, rel: str, src, content_type: str | None, *, by: str = "人") -> dict:
    """笔记本里画过的截图（或录屏画面）换掉原来那张。原图先留进 笔记/历史/原图/（改之前原文先留底）。"""
    f = _saved(p, rel, (shots_dir(p), videos_dir(p)), set(IMG_TYPES.values()))
    ext = IMG_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if ext != f.suffix.lower():
        raise store.Refused(f"画过的图要跟原来一样是 {f.suffix}")
    keep = _history(p, "原图") / f.name
    n = 1
    while keep.exists():
        n += 1
        keep = keep.with_name(f"{f.stem}（第{n}次改前）{f.suffix}")
    keep.parent.mkdir(parents=True, exist_ok=True)
    with store.tx(conn):
        keep.write_bytes(f.read_bytes())
        _stream_in(src, f, IMG_MAX, "图片太大了，20 MB 以内")
        _append_change(p, f"\n## {datetime.now():%Y-%m-%d %H:%M} · {by} 在 {f.name} 上画了\n原图留在：{keep.relative_to(p.root).as_posix()}\n")
        store.log(conn, by, "画截图", f.name, None)
    return {"path": f.relative_to(p.root).as_posix(), "original": keep.relative_to(p.root).as_posix()}
