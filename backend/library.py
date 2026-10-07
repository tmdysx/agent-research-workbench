"""文献库：原版文件都在 原文/，解释都在 解读/，一一对应（L 号 + 指纹）。程序做，不绕 agent。

作者 2026-09-27：「原文所有的原文一个文件夹，然后另一个文件夹专门放解释，然后一一对应」「一个精读的pdf要有一个文件夹对应，
分别存文本，图片和那个2d或者3d的解释图」。计划：计划/文献/P1（文献 S2-1 文献库、S2-2 管文献）。
- 入库：拖进来的 PDF 复制进 原文/（原件不动，文-1）；原文/ 里还没编号的（下载清单下好的）也入库。编 L 号（号不回收）、
  改名「L3 短标题.pdf」，建 解读/L3 短标题/（信息.json + 文本/ · 图片/ · 图解/）；第一页读得出 DOI 就填上
- 一一对应：先看 信息.json 记的原文在不在；不在就按 L 号找；再不在按指纹（sha256）找——原文改了名也对得回来；
  还对不上的只亮灯（有原文没解读 · 有解读没原文），不自动删
- 管文献：标签、分组、阅读状态写回 信息.json；搜、筛、排序在网页上做
"""
from __future__ import annotations

import hashlib
import json
import atomic
import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

import project as proj
import store
from project import Project

ORIG, READ = "原文", "解读"
PARTS = ("文本", "图片", "图解")
INFO = "信息.json"
STATES = ("没读", "在读", "读完")
_L = re.compile(r"^L(\d+)(?:\s+(.*))?$")
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)")
_LOCK = threading.Lock()
_SHA: dict[tuple[str, int, int], str] = {}          # (路径, 大小, 改动时间) → 指纹：没变的文件不重算


def dirs(p: Project, module: str) -> tuple[Path, Path]:
    d = p.materials / module
    return d / ORIG, d / READ


def enabled(p: Project, module: str) -> bool:
    o, r = dirs(p, module)
    return o.is_dir() or r.is_dir()


def sha(f: Path) -> str:
    st = f.stat()
    k = (str(f), st.st_size, st.st_mtime_ns)
    if k not in _SHA:
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        _SHA[k] = h.hexdigest()
    return _SHA[k]


def short(title: str) -> str:
    t = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", title or "")
    return " ".join(t.split())[:40].rstrip(" .") or "未命名"


def num(name: str) -> int | None:
    m = _L.match(Path(name).stem if name.lower().endswith(".pdf") else name)
    return int(m.group(1)) if m else None


def pdf_meta(f: Path) -> tuple[str, str]:
    """PDF 自带的标题、第一页里的 DOI（pdfminer.six，T11）。读不出就空着。"""
    title = doi = ""
    try:
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfparser import PDFParser
        with open(f, "rb") as fh:
            info = PDFDocument(PDFParser(fh)).info
        raw = (info[0].get("Title") if info else b"") or b""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-16") if raw.startswith(b"\xfe\xff") else raw.decode("latin-1", "ignore")
        title = str(raw).strip()
        if re.search(r"\.(dvi|tex|docx?|pdf|ps|eps|indd)$", title, re.I) or re.fullmatch(r"(?=.*[\d_.])[A-Za-z0-9_\-.]+", title):
            title = ""                                   # 像文件名的（guyon03a.dvi、paper_v3）不是标题
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text
        m = _DOI.search(extract_text(str(f), maxpages=1) or "")
        doi = m.group(1).rstrip(".,;)]") if m else ""
    except Exception:
        pass
    return title, doi


def _info(folder: Path) -> dict:
    try:
        return json.loads((folder / INFO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_info(folder: Path, info: dict) -> None:
    f = folder / INFO
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atomic.replace(tmp, f)


def _is_pdf(f: Path) -> bool:
    try:
        with open(f, "rb") as h:
            return h.read(5).startswith(b"%PDF")
    except OSError:
        return False


def _next(conn, p: Project, module: str) -> int:
    o, r = dirs(p, module)
    used = [n for d in (o, r) if d.is_dir() for x in d.iterdir() if (n := num(x.name)) is not None]
    n = max([int(store._meta(conn, f"library_seq:{module}") or 0)] + used) + 1
    store._set_meta(conn, f"library_seq:{module}", str(n))
    return n


# ---------------------------------------------------------------- 一一对应

def _folders(p: Project, module: str) -> list[Path]:
    r = dirs(p, module)[1]
    return sorted((x for x in r.iterdir() if x.is_dir() and not x.name.startswith(".")), key=lambda x: (num(x.name) or 0, x.name)) if r.is_dir() else []


def _pdfs(p: Project, module: str) -> list[Path]:
    o = dirs(p, module)[0]
    return sorted(x for x in o.iterdir() if x.is_file() and x.suffix.lower() == ".pdf" and not x.name.startswith(".")) if o.is_dir() else []


def pair(p: Project, module: str) -> tuple[list[dict], list[Path]]:
    """→ (每篇：解读文件夹对上的原文；还没入库的原文)。对上了但 信息.json 记的名字旧了，顺手改成新名字。"""
    pdfs = _pdfs(p, module)
    free = {f.name: f for f in pdfs}
    out = []
    folders = _folders(p, module)
    for d in folders:
        info = _info(d)
        f = free.get(info.get("原文", "").split("/")[-1])
        if f is None and num(d.name) is not None:                # 按 L 号
            f = next((x for x in free.values() if num(x.name) == num(d.name)), None)
        if f is None and info.get("指纹"):                       # 按指纹：原文改了名也认得
            f = next((x for x in free.values() if sha(x) == info["指纹"]), None)
        if f is not None:
            free.pop(f.name)
            if info.get("原文", "").split("/")[-1] != f.name:
                info["原文"] = f"{ORIG}/{f.name}"
                _write_info(d, info)
        out.append({"folder": d, "pdf": f, "info": info})
    return out, list(free.values())


def add(conn, p: Project, module: str, src: Path, *, name: str = "", by: str = "人") -> dict:
    """拖进来的：复制进 原文/ 入库（同一时间只入一篇，免得号撞了）。"""
    with _LOCK:
        return ingest(conn, p, module, src, name=name, by=by)


def ingest(conn, p: Project, module: str, src: Path, *, name: str = "", by: str = "人") -> dict:
    """入库一篇：src 在 原文/ 外面就复制进来（原件不动），在里面就就地改名。同一篇（指纹一样）不重复入库。"""
    o, r = dirs(p, module)
    if not _is_pdf(src):
        raise store.Refused("这不是 PDF")
    fp = sha(src)
    for e in pair(p, module)[0]:
        if e["info"].get("指纹") == fp and e["pdf"] is not None and e["pdf"] != src:
            if src.parent.resolve() == o.resolve():                # 原文/ 里多了一份一模一样的：挪进 原文/.重复/（不删）
                (o / ".重复").mkdir(exist_ok=True)
                os.replace(src, o / ".重复" / src.name)
                _relink_downloads(p, module, f"资料/{module}/{ORIG}/{src.name}", e["pdf"])
            return entry(p, module, e)                            # 已经有这一篇了
    title, doi = pdf_meta(src)
    rs, rr = src.resolve(), p.root.resolve()
    old = rs.relative_to(rr).as_posix() if rs.is_relative_to(rr) else ""
    row = _download_row(p, module, old, name or src.name)                   # 下载清单里的哪一行：作者、年、期刊跟着带进来
    if row:
        doi = doi or row.get("doi", "")
        if row.get("title") and row["title"] not in (row.get("doi"), row.get("url")):
            title = row["title"]                         # 清单上写了标题（人、agent 或 OpenAlex 给的）：比 PDF 自带的可靠
    base = Path(name or src.name).stem
    base = re.sub(r"^(下-\d+|L\d+)\s+", "", base)
    title = title if len(title) >= 8 and not title.lower().startswith(("microsoft word", "untitled")) else base
    with store.tx(conn):
        n = _next(conn, p, module)
        s = short(title)
        o.mkdir(parents=True, exist_ok=True)
        dst = o / f"L{n} {s}.pdf"
        if src.parent.resolve() == o.resolve():
            os.replace(src, dst)
        else:
            tmp = o / f".L{n}.入库中"
            shutil.copyfile(src, tmp)
            atomic.replace(tmp, dst)
        d = r / f"L{n} {s}"
        for part in PARTS:
            (d / part).mkdir(parents=True, exist_ok=True)
        info = {"编号": f"L{n}", "标题": title, "原文": f"{ORIG}/{dst.name}", "指纹": fp, "DOI": doi or "查不到",
                "作者": (row or {}).get("authors") or "查不到", "年份": (row or {}).get("year") or "查不到",
                "期刊": (row or {}).get("venue") or "查不到", "链接": f"https://doi.org/{doi}" if doi else "",
                "标签": [], "分组": [], "阅读状态": "没读", "加入时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "谁加的": by, "补信息": ""}
        _write_info(d, info)
        store.log(conn, by, "入库", f"L{n}", title[:60])
    if old or row:                                                # 下载清单那一行跟着改名字，照样是绿的
        _relink_downloads(p, module, old, dst, code=(row or {}).get("code", ""))
    return get(p, module, f"L{n}")


def _download_row(p: Project, module: str, old: str, name: str) -> dict | None:
    """这个 PDF 是下载清单里的哪一篇：「放在」对得上，或者文件名是清单上建议的「下-3 …」（你照着存进 原文/ 的）。"""
    try:
        import downloads
        xs = downloads.list_all(p, module)
    except Exception:
        return None
    m = re.match(r"^(下-\d+)\s", Path(name).name)
    return next((x for x in xs if old and x["at"] == old), None) or \
        next((x for x in xs if m and x["code"] == m.group(1) and x["lamp"] != "ok"), None)


def fill_info(p: Project, module: str, pdf_rel: str, fields: dict) -> bool:
    """下载清单后补回来的作者、年、期刊：这篇已经入库了，信息.json 里还空着或写「查不到」的跟着补上（写了的不动）。"""
    target = (p.root / pdf_rel).resolve()
    for e in pair(p, module)[0]:
        if e["pdf"] is not None and e["pdf"].resolve() == target:
            info, changed = e["info"], False
            for k, v in fields.items():
                if v and info.get(k) in (None, "", "查不到"):
                    info[k], changed = v, True
            if changed:
                _write_info(e["folder"], info)
            return changed
    return False


def _relink_downloads(p: Project, module: str, old: str, new: Path, *, code: str = "") -> None:
    try:
        import downloads
        rel = new.resolve().relative_to(p.root.resolve()).as_posix()
        for x in downloads.list_all(p, module):
            if (old and x["at"] == old) or (code and x["code"] == code):
                downloads._set(p, module, x["code"], at=rel)
    except Exception:
        pass


def scan(conn, p: Project, module: str) -> list[str]:
    """原文/ 里还没入库的（没编号、也对不上任何一篇）入库。带 L 号却没解读的不动，只亮灯。"""
    if not enabled(p, module):
        return []
    with _LOCK:
        _, loose = pair(p, module)
        done = []
        for f in loose:
            if num(f.name) is None:
                done.append(ingest(conn, p, module, f, by="程序")["code"])
        return done


def entry(p: Project, module: str, e: dict) -> dict:
    info, d, f = e["info"], e["folder"], e["pdf"]
    code = info.get("编号") or (f"L{num(d.name)}" if num(d.name) else d.name)
    parts = {part: sorted(x.name for x in (d / part).iterdir() if x.is_file() and not x.name.startswith("."))
             if (d / part).is_dir() else [] for part in PARTS}
    return {"code": code, "n": num(code) or 0, "title": info.get("标题") or d.name, "folder": f"{READ}/{d.name}",
            "pdf": f"{ORIG}/{f.name}" if f else "", "lamp": "ok" if f else "bad",
            "problem": "" if f else "有解读没原文", "info": info, "parts": parts}


def entries(p: Project, module: str) -> tuple[list[dict], list[dict]]:
    """→ (每篇, 对不上的)。"""
    got, loose = pair(p, module)
    items = [entry(p, module, e) for e in got]
    problems = [{"code": x["code"], "text": f"{x['code']} 有解读没原文（{x['folder']}）"} for x in items if not x["pdf"]]
    problems += [{"code": f.name, "text": f"{f.name} 有原文没解读" if num(f.name) else f"{f.name} 还没入库"} for f in loose]
    items.sort(key=lambda x: x["n"])
    return items, problems


def get(p: Project, module: str, code: str) -> dict:
    x = next((i for i in entries(p, module)[0] if i["code"] == code), None)
    if x is None:
        raise store.Refused(f"文献库里没有 {code}")
    return x


# ---------------------------------------------------------------- 边读边记（文献 S2-5）：一条笔记一段，带页码、原句、颜色、谁写的

NOTE_FILE = "笔记.md"
PAPER_WHERE = re.compile(r"^(\S+) (L\d+) 第 (\d+) 页(?:「(.*)」)?")     # 阅读页里问的出处：「文献 L1 第 3 页「原句」」
COLORS = ("黄", "绿", "红", "蓝", "黑", "—")
_NOTE = re.compile(r"^## 第 (\d+) 页 · (\S+) · (.+?) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2})(?: · (改过.*?))?\s*$")
NOTE_HISTORY = ".笔记历史.md"        # 改之前、删之前的原样留在这（点开头：阅读页不列它）


def _note_file(p: Project, module: str, code: str) -> Path:
    return p.materials / module / get(p, module, code)["folder"] / "文本" / NOTE_FILE


def _note_blocks(f: Path) -> tuple[list[str], list[tuple[re.Match, list[str]]]]:
    """→ (开头那几行, [(标题行, 这一条下面的行)])"""
    head, blocks = [], []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _NOTE.match(line)
        if m:
            blocks.append((m, []))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            head.append(line)
    return head, blocks


def _note_entry(i: int, m: re.Match, body: list[str]) -> dict:
    quote, text, in_quote = [], [], True
    for line in body:
        if in_quote and line.startswith("> "):
            quote.append(line[2:].strip())
        elif line.strip() or text:
            in_quote = False
            text.append(line)
    return {"i": i, "page": int(m.group(1)), "color": m.group(2), "by": m.group(3), "at": m.group(4), "edited": m.group(5) or "",
            "quote": " ".join(quote), "text": "\n".join(text).strip()}


def _note_block(page: int, color: str, by: str, at: str, edited: str, quote: str, text: str) -> str:
    return (f"## 第 {page} 页 · {color} · {by} · {at}" + (f" · {edited}" if edited else "") + "\n"
            + (f"> {quote}\n" if quote else "") + (f"\n{text}\n" if text else ""))


def notes(p: Project, module: str, code: str) -> list[dict]:
    f = _note_file(p, module, code)
    if not f.is_file():
        return []
    return [_note_entry(i, m, body) for i, (m, body) in enumerate(_note_blocks(f)[1])]


def _rewrite_notes(conn, p: Project, module: str, code: str, i: int, at: str, *, why: str, by: str, new: dict | None) -> dict:
    """改一条（new 给了）或删一条（new 是 None）：先对上是不是那一条，原样留进 .笔记历史.md，再整份换掉。"""
    f = _note_file(p, module, code)
    with _LOCK:
        head, blocks = _note_blocks(f) if f.is_file() else ([], [])
        if not 0 <= i < len(blocks) or blocks[i][0].group(4) != at:
            raise store.Refused("这条笔记变了（别处改过或删了），刷新再改")
        old = _note_entry(i, *blocks[i])
        stamp = f"{datetime.now():%Y-%m-%d %H:%M}"
        hist = f.parent / NOTE_HISTORY
        with open(hist, "a", encoding="utf-8") as out:
            if hist.stat().st_size == 0:
                out.write(f"# {code} 笔记改动留底\n\n> 笔记.md 里改之前、删之前的原样；要找回来从这里抄。\n")
            out.write(f"\n---\n{why} · {by} · {stamp}\n\n" + blocks[i][0].group(0) + "\n" + "\n".join(blocks[i][1]).rstrip("\n") + "\n")
        parts = []
        for k, (m, body) in enumerate(blocks):
            if k != i:
                parts.append(m.group(0).rstrip() + "\n" + "\n".join(body).rstrip("\n") + "\n")
            elif new is not None:
                parts.append(_note_block(old["page"], new["color"], old["by"], old["at"], f"改过（{by} {stamp[5:]}）", old["quote"], new["text"]))
        text = "\n".join(head).rstrip("\n") + "\n" + "".join("\n" + x for x in parts)
        tmp = f.with_suffix(".md.tmp")
        tmp.write_text(text, encoding="utf-8")
        with store.tx(conn):
            atomic.replace(tmp, f)
            store.log(conn, by, "改文献笔记" if new is not None else "删文献笔记", code, f"第 {old['page']} 页 {old['at']}")
    return old if new is None else notes(p, module, code)[i]


def edit_note(conn, p: Project, module: str, code: str, i: int, *, at: str, text: str, color: str, by: str = "人") -> dict:
    """阅读时改一条笔记：改你写的字、换颜色；原句不动。改过的标题行后面写「改过（谁 时间）」。"""
    text = (text or "").strip()
    if color not in COLORS:
        raise store.Refused("颜色：黄 / 绿 / 红 / 蓝 / 黑")
    cur = next((x for x in notes(p, module, code) if x["i"] == i), None)
    if cur and not text and not cur["quote"]:
        raise store.Refused("写点什么；不要了就点「删」")
    return _rewrite_notes(conn, p, module, code, i, at, why="改之前", by=by, new={"text": text, "color": color})


def delete_note(conn, p: Project, module: str, code: str, i: int, *, at: str, by: str = "人") -> dict:
    """删一条笔记（原样留进 .笔记历史.md，找得回来）。"""
    return _rewrite_notes(conn, p, module, code, i, at, why="删之前", by=by, new=None)


def add_note(conn, p: Project, module: str, code: str, *, page: int, quote: str = "", text: str = "", color: str = "黄",
             by: str = "人") -> dict:
    """记一条进 解读/L…/文本/笔记.md。原句、你写的至少有一样。"""
    quote, text = " ".join((quote or "").split()), (text or "").strip()
    if not quote and not text:
        raise store.Refused("选一句原文，或者写点什么")
    if color not in COLORS:
        raise store.Refused("颜色：黄 / 绿 / 红 / 蓝 / 黑")
    if not isinstance(page, int) or page < 1:
        raise store.Refused("页码不对")
    f = _note_file(p, module, code)
    f.parent.mkdir(parents=True, exist_ok=True)
    head = f"# {code} 笔记\n\n> 人和 agent 的笔记，一条一段：第几页 · 颜色 · 谁 · 什么时候；`>` 开头的是原句。\n" if not f.is_file() else ""
    body = f"\n## 第 {page} 页 · {color} · {by} · {datetime.now():%Y-%m-%d %H:%M}\n" + (f"> {quote}\n" if quote else "") + (f"\n{text}\n" if text else "")
    with _LOCK, store.tx(conn):                                   # 跟「改一条」错开，免得改的时候整份换掉把这条冲没了
        with open(f, "a", encoding="utf-8") as out:
            out.write(head + body)
        store.log(conn, by, "文献笔记", code, f"第 {page} 页 {quote[:40] or text[:40]}")
    return notes(p, module, code)[-1]


# ---------------------------------------------------------------- 批注和涂鸦（文献 S2-21）：高亮 · 便签 · 笔，叠在原文上显示
# 作者 09-28：「那个pdf自带的笔记和涂鸦功能也要有」。原版 PDF 不改（文-1）：批注单独存 解读/L…/批注.json，
# 坐标用 PDF 自己的单位（第几页、左上角起、放大前的尺寸），放大缩小跟着走

MARK_FILE = "批注.json"
MARK_KINDS = ("高亮", "便签", "笔")
MARK_COLORS = COLORS[:-1]


def _mark_file(p: Project, module: str, code: str) -> Path:
    return p.materials / module / get(p, module, code)["folder"] / MARK_FILE


def _marks(f: Path) -> dict:
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d if isinstance(d.get("批注"), list) else {"批注": [], "下一个": 1}
    except (OSError, ValueError):
        return {"批注": [], "下一个": 1}


def _save_marks(f: Path, d: dict) -> None:
    """一条批注一行（坐标不拆成一堆行），人和 agent 都好读。"""
    head = {"说明": "阅读页上的批注：高亮 · 便签 · 笔。坐标是 PDF 自己的单位（左上角起、放大前），原版 PDF 不改",
            "下一个": d.get("下一个", 1)}
    rows = ",\n".join("  " + json.dumps(m, ensure_ascii=False) for m in d["批注"])
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(head, ensure_ascii=False, indent=1)[:-2] + ',\n "批注": [\n' + rows + ("\n" if rows else "") + " ]\n}\n",
                   encoding="utf-8")
    atomic.replace(tmp, f)


def marks(p: Project, module: str, code: str) -> list[dict]:
    return _marks(_mark_file(p, module, code))["批注"]


def _nums(xs, n: int, most: int, what: str) -> list[list[float]]:
    if not isinstance(xs, list) or not 1 <= len(xs) <= most:
        raise store.Refused(f"{what}不对")
    out = []
    for x in xs:
        if not isinstance(x, (list, tuple)) or len(x) != n or not all(isinstance(v, (int, float)) and -1e4 < v < 1e5 for v in x):
            raise store.Refused(f"{what}不对")
        out.append([round(float(v), 1) for v in x])
    return out


def add_mark(conn, p: Project, module: str, code: str, *, page: int, kind: str, color: str = "黄", points=None, rects=None,
             at=None, text: str = "", width: float = 1.5, by: str = "人") -> dict:
    """加一条批注。笔 = points [[x, y]…]；高亮 = rects [[x, y, 宽, 高]…]；便签 = at [x, y] + text。"""
    if kind not in MARK_KINDS:
        raise store.Refused("批注只有：高亮 / 便签 / 笔")
    if color not in MARK_COLORS:
        raise store.Refused("颜色：黄 / 绿 / 红 / 蓝 / 黑")
    if not isinstance(page, int) or page < 1:
        raise store.Refused("页码不对")
    m = {"page": page, "kind": kind, "color": color}
    if kind == "笔":
        m["points"] = _nums(points, 2, 5000, "笔画")
        if len(m["points"]) < 2:
            raise store.Refused("笔画太短")
        m["width"] = min(12.0, max(0.5, float(width or 1.5)))
    elif kind == "高亮":
        m["rects"] = _nums(rects, 4, 300, "高亮的位置")
        m["text"] = " ".join((text or "").split())[:500]
    else:
        m["at"] = _nums([at], 2, 1, "便签的位置")[0]
        m["text"] = (text or "").strip()
        if not m["text"]:
            raise store.Refused("便签要写点什么")
        m["text"] = m["text"][:2000]
    f = _mark_file(p, module, code)
    with _LOCK, store.tx(conn):
        d = _marks(f)
        used = [int(g.group(1)) for x in d["批注"] if (g := re.fullmatch(r"批-(\d+)", str(x.get("id", ""))))]
        n = max([int(d.get("下一个") or 1)] + [u + 1 for u in used])
        m = {"id": f"批-{n}", **m, "by": by, "time": f"{datetime.now():%Y-%m-%d %H:%M}"}
        d["批注"].append(m)
        d["下一个"] = n + 1
        _save_marks(f, d)
        store.log(conn, by, "文献批注", code, f"第 {page} 页 {kind} {m['id']}")
    return m


def remove_mark(conn, p: Project, module: str, code: str, mark: str, *, by: str = "人") -> dict:
    """擦掉一条批注（橡皮、撤销）。号不回收。"""
    f = _mark_file(p, module, code)
    with _LOCK, store.tx(conn):
        d = _marks(f)
        m = next((x for x in d["批注"] if x.get("id") == mark), None)
        if m is None:
            raise store.Refused(f"{code} 没有批注 {mark}")
        d["批注"].remove(m)
        _save_marks(f, d)
        store.log(conn, by, "擦掉批注", code, f"第 {m['page']} 页 {m['kind']} {mark}")
    return m


def update(conn, p: Project, module: str, code: str, fields: dict, *, by: str = "人") -> dict:
    """管文献：标签、分组（列表）、阅读状态（没读 / 在读 / 读完）写回 信息.json。"""
    x = get(p, module, code)
    d = p.materials / module / x["folder"]
    info = _info(d)
    for k in ("标签", "分组"):
        if k in fields and fields[k] is not None:
            v = fields[k]
            v = re.split(r"[、,，;；\s]+", v) if isinstance(v, str) else v
            info[k] = [" ".join(str(t).split()) for t in v if str(t).strip()]
    if fields.get("阅读状态") is not None:
        if fields["阅读状态"] not in STATES:
            raise store.Refused("阅读状态：没读 / 在读 / 读完")
        info["阅读状态"] = fields["阅读状态"]
    with store.tx(conn):
        _write_info(d, info)
        store.log(conn, by, "改文献信息", code, " · ".join(f"{k}={info.get(k)}" for k in ("标签", "分组", "阅读状态")))
    return get(p, module, code)
