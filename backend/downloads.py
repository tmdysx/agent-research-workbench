"""下载清单：agent 找到的论文列成清单（它没有下载权限也行），人点链接直达去下，下好的变绿。

作者 2026-09-27：「很多agent没有下载权限需要手动下载……我是想要一个下载页面有链接和勾选就行，就是下载好的就是绿色，
有链接直达就行了？你看看如果还有更好的方案也行」。
- 一个模块一张：资料/<模块>/下载清单.md，一篇一行，编号 下-1、下-2…（号不回收）；下好的放 资料/<模块>/原文/
- 灯现算：文件在、开头是 %PDF = 绿；在但不是 PDF = 红；还没下 = 灰
- 省事一：有 DOI 的去 OpenAlex（免费、不用注册）查合法的免费版直链，有就能「直接下」——后台下，走电脑的网络设置
- 省事二：点了链接，盯着系统「下载」文件夹 10 分钟，出现新的 PDF 就复制一份进来（原件不动）；学校权限只在人的浏览器里
- 规矩（文献戒律 文-9）：只从合法的地方下，不绕付费墙；只收 PDF、最大 200 MB、只 http / https
- 样子照作者的 V3 那份（09-28：「下载清单可以参考一下这个格式」）：每篇带作者 · 年 · 期刊（OpenAlex 一起查回来，agent 也能直接写）、
  按出版社分组（DOI 前缀认），每组一句去哪下；每篇写「存成」什么名字——按这个名字放进 原文/ 也认得是哪一行
"""
from __future__ import annotations

import json
import atomic
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import capture
import project as proj
import store
from project import Project

FILE = "下载清单.md"
DIR = "原文"                                   # 原版文件都在 原文/（作者：「所以原版文件一个文件夹」）
MAX = 200 * 1024 * 1024
WATCH = 600                                    # 点了链接后盯「下载」文件夹多久（秒）
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-console"
_ROW = re.compile(r"^\|\s*(下-(\d+))\s*\|")
_DOI = re.compile(r"(10\.\d{4,9}/[^\s|]+)")
HEAD = """# 下载清单

> 要下的论文一篇一行，编号 下-n，号不回收。agent 找到了就排进来（它不用自己下）；你点链接直达去下，下好的放 `原文/`，网页上变绿。
> 只从合法的地方下（出版社、arXiv、开放获取），不绕付费墙（文献戒律 文-9）。

| | 标题 | 链接 | DOI | 免费直链 | 为什么要 | 谁加的 | 放在 | 作者 | 年 | 期刊 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|
"""
_OLD_HEAD = ("| | 标题 | 链接 | DOI | 免费直链 | 为什么要 | 谁加的 | 放在 |\n|---|---|---|---|---|---|---|---|\n")
COLS = ("code", "title", "url", "doi", "oa", "why", "by", "at", "authors", "year", "venue", "note")
N = len(COLS)
# 按出版社分组（DOI 前缀，或网址里的字），每组一句去哪下；认不出的归「其它」
PUBLISHERS = (
    (("10.1016/",), "Elsevier · ScienceDirect", "学校图书馆 → ScienceDirect；标了开放获取的点「打开 DOI」就能下"),
    (("10.1007/", "10.1038/", "10.1186/"), "Springer · Nature · BMC", "学校图书馆 → SpringerLink；BMC、Nature Communications 这些本来开放，点进去就能下"),
    (("10.1109/",), "IEEE", "学校图书馆 → IEEE Xplore"),
    (("10.1145/",), "ACM", "学校图书馆 → ACM Digital Library；或在统一检索里搜题名"),
    (("10.1002/", "10.1111/"), "Wiley", "学校图书馆 → Wiley Online Library"),
    (("10.1080/",), "Taylor & Francis", "学校图书馆 → Taylor & Francis Online"),
    (("10.1093/",), "Oxford · OUP", "统一检索里搜题名，或从 Web of Science 点全文链接过去"),
    (("10.1017/",), "Cambridge", "学校图书馆 → Cambridge Core"),
    (("10.1177/",), "SAGE", "学校图书馆 → SAGE Journals"),
    (("10.1021/",), "ACS", "学校图书馆 → ACS Publications"),
    (("10.1126/",), "Science · AAAS", "学校图书馆 → Science"),
    (("10.1073/",), "PNAS", "多数半年后开放；新的走学校图书馆"),
    (("10.48550/", "arxiv.org"), "arXiv", "本来开放：点「直接下」"),
    (("10.1101/", "biorxiv.org", "medrxiv.org"), "bioRxiv · medRxiv", "本来开放：点进去就能下"),
    (("10.3390/", "10.1371/", "10.3389/", "10.7554/", "jmlr.org"), "开放获取（MDPI · PLOS · Frontiers · eLife · JMLR）", "本来开放：点进去就能下"),
)
OTHER = ("其它 · 没有 DOI", "按题名到统一检索里搜；书和软件手册看备注")
_META: dict[str, dict] = {}                     # OpenAlex 顺手查回来的作者、年、期刊（按 DOI）
_LOCK = threading.Lock()
JOBS: dict[tuple[str, str, str], dict] = {}     # (项目根, 模块, 编号) → {"state": 下载中 / 找免费版 / 等你下 / 失败, "msg"}
_WATCH: dict[tuple[str, str], threading.Event] = {}


def _flat(s) -> str:
    return " ".join(str(s or "").replace("|", "／").split())


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def path(p: Project, module: str) -> Path:
    return p.materials / module / FILE


def _key(p: Project, module: str, code: str) -> tuple[str, str, str]:
    return (str(p.root), module, code)


def is_pdf(f: Path) -> bool:
    try:
        with open(f, "rb") as h:
            return h.read(5).startswith(b"%PDF")
    except OSError:
        return False


def normal_doi(s: str) -> str:
    m = _DOI.search(urllib.parse.unquote(s or ""))
    return m.group(1).rstrip(".,;)") if m else ""


def direct_of(x: dict) -> str:
    """能直接下的地址：查到的免费直链 > 链接本身就是 PDF > arXiv 的摘要页换成 PDF。"""
    if x.get("oa"):
        return x["oa"]
    u = x.get("url", "")
    if re.search(r"\.pdf($|\?)", u, re.I):
        return u
    m = re.match(r"^https?://arxiv\.org/(abs|pdf)/([^\s?#]+?)(\.pdf)?$", u)
    if m:
        return f"https://arxiv.org/pdf/{m.group(2)}"
    return ""


def publisher(x: dict) -> tuple[str, str]:
    """→ (分组, 去哪下)。"""
    doi, url = (x.get("doi") or "").lower(), (x.get("url") or "").lower()
    for keys, name, how in PUBLISHERS:
        if any(doi.startswith(k) if k.startswith("10.") else k in url for k in keys):
            return name, how
    return OTHER


def save_as(x: dict) -> str:
    """建议存成的文件名：放进 原文/ 就认得是这一行（入库时改成 L 号）。"""
    return f"{x['code']} {_safe(x['title'])}.pdf"


def list_all(p: Project, module: str) -> list[dict]:
    f = path(p, module)
    if not f.is_file():
        return []
    out = []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        c = _cells(line) + [""] * N
        x = dict(zip(COLS, c[:N]))
        x["n"] = int(m.group(2))
        x["direct"] = direct_of(x)
        x["group"], x["howto"] = publisher(x)
        x["save_as"] = save_as(x)
        where = p.root / x["at"] if x["at"] else None
        if where and where.is_file():
            x["lamp"], x["state"] = ("ok", "下好了") if is_pdf(where) else ("bad", "不是 PDF")
        else:
            x["lamp"], x["state"] = "", ("文件不见了" if x["at"] else "还没下")
        job = JOBS.get(_key(p, module, x["code"]))
        if job and x["lamp"] != "ok":
            x["state"], x["msg"] = job["state"], job.get("msg", "")
            if job["state"] == "失败":
                x["lamp"] = "bad"
        out.append(x)
    return out


def get(p: Project, module: str, code: str) -> dict:
    x = next((i for i in list_all(p, module) if i["code"] == code), None)
    if x is None:
        raise store.Refused(f"下载清单里没有 {code}")
    return x


def _write(f: Path, text: str) -> None:
    text = text.replace(_OLD_HEAD, HEAD[HEAD.index("| | 标题"):])        # 旧的 8 格表头换成新的（多了 作者 · 年 · 期刊 · 备注）
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    atomic.replace(tmp, f)


def _set(p: Project, module: str, code: str, **kw) -> None:
    """改一行里的几格（免费直链、放在……）。"""
    with _LOCK:
        f = path(p, module)
        lines = f.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            m = _ROW.match(line)
            if m and m.group(1) == code:
                c = (_cells(line) + [""] * N)[:N]
                for k, v in kw.items():
                    c[COLS.index(k)] = _flat(v)
                lines[i] = "| " + " | ".join(c) + " |"
                _write(f, "\n".join(lines))
                return
    raise store.Refused(f"下载清单里没有 {code}")


def _log(p: Project, action: str, code: str, detail: str = "", by: str = "程序") -> None:
    """后台线程里记一笔：网页马上知道清单变了。"""
    try:
        conn = store.connect(p.db_path)
        try:
            with store.tx(conn):
                store.log(conn, by, action, code, detail[:60])
        finally:
            conn.close()
    except Exception:
        pass


def add(conn, p: Project, module: str, *, title: str, url: str = "", doi: str = "", why: str = "", by: str = "人",
        authors: str = "", year: str = "", venue: str = "", note: str = "") -> dict:
    """排进清单一篇。至少给链接或 DOI；只给 DOI 就用 doi.org 那一页当链接。作者 · 年 · 期刊知道就写，不知道 OpenAlex 会补。"""
    if proj.module_dir(p, module) is None:
        raise store.Refused(f"没有「{module}」这个模块")
    url, doi = (url or "").strip(), normal_doi(doi) or normal_doi(url)
    if url and not re.match(r"^https?://", url, re.I):
        if not doi:
            raise store.Refused("链接要以 http:// 或 https:// 开头（或者给 DOI）")
        url = ""
    if not url and not doi:
        raise store.Refused("给一个链接或 DOI")
    url = url or f"https://doi.org/{doi}"
    title = _flat(title) or doi or url
    with _LOCK:
        f = path(p, module)
        body = f.read_text(encoding="utf-8") if f.is_file() else HEAD
        have = list_all(p, module)
        dup = next((x for x in have if (doi and x["doi"] == doi) or x["url"] == url), None)
        if dup:
            return dup
        n = int(store._meta(conn, f"download_seq:{module}") or 0)
        n = max([n] + [x["n"] for x in have]) + 1
        with store.tx(conn):
            store._set_meta(conn, f"download_seq:{module}", str(n))
            code = f"下-{n}"
            row = (f"| {code} | {title} | {_flat(url)} | {doi} |  | {_flat(why)} | {_flat(by)} |  | "
                   f"{_flat(authors)} | {_flat(year)} | {_flat(venue)} | {_flat(note)} |")
            _write(f, body.rstrip("\n") + "\n" + row + "\n")
            store.log(conn, by, "排进下载清单", code, title[:60])
    x = get(p, module, code)
    if (doi or arxiv_id(x)) and (not x["direct"] or not (x["authors"] and x["year"] and x["venue"])):
        threading.Thread(target=find_free, args=(p, module, code), daemon=True).start()
    return x


def offline() -> bool:
    """测试时不上网（conftest 里设 RC_OFFLINE=1），查 OpenAlex、arXiv 的都直接当没查到。"""
    return os.environ.get("RC_OFFLINE") == "1"


def arxiv_id(x: dict) -> str:
    """arXiv 上的论文：从链接（arxiv.org/abs/…、/pdf/…）或 DOI（10.48550/arXiv.…）里认出编号。"""
    for s in (x.get("url") or "", x.get("doi") or ""):
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?$", s, re.I) or re.search(r"^10\.48550/arxiv\.([\w.\-/]+)$", s, re.I)
        if m:
            return m.group(1)
    return ""


def lookup_arxiv(aid: str, timeout: float = 15) -> dict:
    """arXiv 自己的接口补作者、年、标题（OpenAlex 不收 arXiv 的 DOI）。只把编号发出去。"""
    if offline():
        return {}
    req = urllib.request.Request("https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(aid),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        root = ET.fromstring(r.read())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    e = root.find("a:entry", ns)
    if e is None or "api/errors" in (e.findtext("a:id", "", ns) or ""):
        return {}
    names = [n.text.strip() for n in e.findall("a:author/a:name", ns) if n.text and n.text.strip()]
    return {"authors": "; ".join(names[:2]) + ("等" if len(names) > 2 else ""), "year": (e.findtext("a:published", "", ns) or "")[:4],
            "venue": "arXiv", "title": " ".join((e.findtext("a:title", "", ns) or "").split())}


# ---------------------------------------------------------------- 省事一：开放获取的直接下

def lookup_oa(doi: str, timeout: float = 15) -> str:
    """OpenAlex：这个 DOI 有没有合法的免费版 PDF。只把 DOI 发出去。没有就是空。"""
    if offline():
        return ""
    req = urllib.request.Request("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/"),
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:            # 走电脑的网络设置（开着代理也照样走）
        data = json.load(r)
    names = [((a.get("author") or {}).get("display_name") or "").strip() for a in data.get("authorships") or []]
    names = [n for n in names if n]
    src = ((data.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    vol = (data.get("biblio") or {}).get("volume") or ""
    _META[doi] = {"authors": "; ".join(names[:2]) + ("等" if len(names) > 2 else ""), "year": str(data.get("publication_year") or ""),
                  "venue": src + (f" · 卷 {vol}" if src and vol else ""), "title": data.get("title") or ""}
    loc = data.get("best_oa_location") or {}
    return loc.get("pdf_url") or ""


def find_free(p: Project, module: str, code: str) -> str:
    key = _key(p, module, code)
    x = get(p, module, code)
    JOBS[key] = {"state": "找免费版"}
    oa, note = "", ""
    if x["doi"]:
        try:
            oa = lookup_oa(x["doi"])
        except urllib.error.HTTPError as e:
            note = "OpenAlex 里查不到这个 DOI" if e.code == 404 else f"查免费版没查成：{e}"
        except Exception as e:
            note = f"查免费版没查成：{e}"
    meta = dict(_META.get(x["doi"]) or {}) if x["doi"] else {}
    aid = arxiv_id(x)
    if aid and not (meta.get("authors") and meta.get("year")):              # arXiv 的：去 arXiv 自己那查
        try:
            meta = {**lookup_arxiv(aid), **{k: v for k, v in meta.items() if v}}
            note = ""
        except Exception:
            pass
    JOBS.pop(key, None)
    fill = {k: meta[k] for k in ("authors", "year", "venue") if meta.get(k) and not x[k]}
    if meta.get("title") and x["title"] in (x["doi"], x["url"]):                   # 排的时候没写标题：用查回来的
        fill["title"] = meta["title"]
    if fill:
        _set(p, module, code, **fill)
    y = get(p, module, code)
    if y["at"] and (y["authors"] or y["year"] or y["venue"]):          # 已经下好入库了：文献库那篇还空着的信息也补上
        try:
            import library
            library.fill_info(p, module, y["at"], {"作者": y["authors"], "年份": y["year"], "期刊": y["venue"], "DOI": y["doi"]})
        except Exception:
            pass
    if oa:
        _set(p, module, code, oa=oa)
        _log(p, "找到免费版", code, oa)
    elif get(p, module, code)["direct"]:                                       # 本来就能直接下（arXiv、PDF 直链）：不用提示
        _log(p, "查过信息", code)
    else:
        JOBS[key] = {"state": "还没下", "msg": (f"{note}；" if note else "") + "没有合法的免费版：点链接自己下（学校账号）"}
        _log(p, "没有免费版", code)
    return oa


def _safe(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", name)
    return " ".join(name.split())[:60].rstrip(" .") or "论文"


def _target(p: Project, module: str, x: dict) -> Path:
    return p.materials / module / DIR / f"{x['code']} {_safe(x['title'])}.pdf"


def fetch(p: Project, module: str, code: str, *, by: str = "人", timeout: float = 60) -> dict:
    """后台下一篇（在调用的线程里跑）：先写临时文件，查开头是不是 %PDF、多大，再改名；不是 PDF 的不留。"""
    x = get(p, module, code)
    url = x["direct"]
    if not url:
        raise store.Refused("这一篇没有能直接下的地址：点链接自己下")
    if not re.match(r"^https?://", url, re.I):
        raise store.Refused("只下 http / https 的地址")
    key = _key(p, module, code)
    dst = _target(p, module, x)
    tmp = dst.with_name(f".{code}.下载中")
    JOBS[key] = {"state": "下载中"}
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
        n = 0
        with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as out:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                n += len(chunk)
                if n > MAX:
                    raise ValueError("超过 200 MB，不下")
                out.write(chunk)
        if not is_pdf(tmp):
            raise ValueError("下来的不是 PDF（多半是要登录的网页）：点链接自己下")
        atomic.replace(tmp, dst)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        JOBS[key] = {"state": "失败", "msg": str(e)}
        _log(p, "下载没成", code, str(e), by)
        return get(p, module, code)
    JOBS.pop(key, None)
    _set(p, module, code, at=dst.relative_to(p.root).as_posix())
    _log(p, "下载好了", code, dst.name, by)
    _to_library(p, module)
    return get(p, module, code)


def _to_library(p: Project, module: str) -> None:
    """下好的在 原文/ 里：马上入库（编 L 号、建解读文件夹），这一行的「放在」跟着改。"""
    try:
        import library
        conn = store.connect(p.db_path)
        try:
            library.scan(conn, p, module)
        finally:
            conn.close()
    except Exception:
        pass


def fetch_later(p: Project, module: str, code: str, *, by: str = "人") -> None:
    get(p, module, code)
    JOBS[_key(p, module, code)] = {"state": "下载中"}
    threading.Thread(target=fetch, args=(p, module, code), kwargs={"by": by}, daemon=True).start()


# ---------------------------------------------------------------- 省事二：你自己下的，从「下载」文件夹捡进来

def downloads_dir() -> Path:
    return capture.downloads_dir()


def watch(p: Project, module: str, code: str, *, timeout: float = WATCH, poll: float = 1.0, settle: float = 2.0) -> None:
    """点了链接：盯「下载」文件夹，出现新的 PDF（写完了）就复制一份给这一行。同一个模块同时只盯一篇（后点的算）。"""
    get(p, module, code)
    folder = downloads_dir()
    before = {f.name for f in folder.iterdir()} if folder.is_dir() else set()
    since = time.time()
    k = (str(p.root), module)
    if k in _WATCH:
        _WATCH[k].set()
    stop = threading.Event()
    _WATCH[k] = stop
    key = _key(p, module, code)
    JOBS[key] = {"state": "等你下", "msg": f"盯着「下载」文件夹（{folder}）"}

    def run() -> None:
        got = capture.wait_file(folder, before, since, stop, {".pdf"}, timeout, poll, settle)
        if _WATCH.get(k) is stop:
            _WATCH.pop(k, None)
        if got is None:
            if JOBS.get(key, {}).get("state") == "等你下":
                JOBS.pop(key, None)
            return
        try:
            take(p, module, code, got)
        except Exception as e:
            JOBS[key] = {"state": "失败", "msg": str(e)}
    threading.Thread(target=run, daemon=True).start()


def take(p: Project, module: str, code: str, src: Path, *, by: str = "人") -> dict:
    """把一个下好的 PDF 复制给这一行（从「下载」文件夹捡的、网页上选的都走这）。原件不动。"""
    x = get(p, module, code)
    if not is_pdf(src):
        raise store.Refused("这不是 PDF")
    if src.stat().st_size > MAX:
        raise store.Refused("超过 200 MB")
    dst = _target(p, module, x)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{code}.下载中")
    shutil.copyfile(src, tmp)
    atomic.replace(tmp, dst)
    JOBS.pop(_key(p, module, code), None)
    _set(p, module, code, at=dst.relative_to(p.root).as_posix())
    _log(p, "下载好了", code, f"{src.name} → {dst.name}", by)
    _to_library(p, module)
    return get(p, module, code)


def pending(p: Project) -> list[tuple[str, dict]]:
    """各模块还没下好的（给 agent 的全貌用）。"""
    out = []
    for m in proj.module_dirs(p):
        if path(p, m).is_file():
            out += [(m, x) for x in list_all(p, m) if x["lamp"] != "ok"]
    return out


def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
