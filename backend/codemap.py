"""代码地图的后台（S1-1 S2-21）：模块里每个程序文件多少行、git 里改过几次、没交的改动在哪几行；按需给一个文件的全文、搜一个词、列函数和谁用到它。

作者 10-02 发来 Rik Arends 的 3D 代码浏览器截图：「我想做的可视化是这个」；「以你的能力，不需要看他的代码，完全可以自己设计把这些功能实现」。
网页（代码地图.js）把每个文件铺成一块、块里按栏排真代码；这里只管给数：
- files：先给目录（路径、行数、大小、改动时间、改过几次、谁最后改的），全文不在这——网页看到哪块才来取哪块（text），取过的留着
- diff：没交的改动（跟上一次 git 记账比），哪个文件哪几行是加的、改的、删的
- search：一个词在哪些文件哪几行
- defs / uses：一个文件里有哪些函数和类；一个名字在别处哪几行用到
全是只读。路径一律从项目根算，出不了项目（files.proj_resolve 管）。
"""
from __future__ import annotations

import re
from pathlib import Path

import files
import outline
import vcs
from project import Project

MAX_LINES = 30000                                    # 一个文件最多给这么多行（再长的是数据不是代码）
MAX_HITS = 400
_LINES: dict[str, tuple[int, int, int]] = {}         # 路径 → (大小, 改动时间, 行数)：没变就不重数

LANGS = {".py": "py", ".js": "js", ".mjs": "js", ".ts": "js", ".tsx": "js", ".jsx": "js", ".html": "html", ".htm": "html",
         ".css": "css", ".json": "json", ".bat": "bat", ".cmd": "bat", ".ps1": "sh", ".sh": "sh", ".md": "md",
         ".toml": "conf", ".yaml": "conf", ".yml": "conf", ".ini": "conf", ".cfg": "conf", ".sql": "sql"}

_DEFS = {
    "py": [(re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)"), "函数"), (re.compile(r"^\s*class\s+([A-Za-z_]\w*)"), "类")],
    "js": [(re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)"), "函数"),
           (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)"), "函数"),
           (re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"), "类")],
}
_DEFS["html"] = _DEFS["js"]


def lang_of(name: str) -> str:
    return LANGS.get(Path(name).suffix.lower(), "text")


def _rel(p: Project, f: Path) -> str | None:
    try:
        return f.resolve().relative_to(p.root.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def _count(f: Path, st) -> int:
    key = str(f)
    hit = _LINES.get(key)
    if hit and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
        return hit[2]
    try:
        data = f.read_bytes()
    except OSError:
        return 0
    n = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    _LINES[key] = (st.st_size, st.st_mtime_ns, n)
    return n


def _code_files(p: Project, module: str) -> list[tuple[str, Path, str]]:
    """模块里（含挂进来的）每个程序文件：(网页里打开用的路径, 真文件, 从项目根算的路径)。跟「每个文件一句话」那张清单同一个口径。"""
    out, seen = [], set()

    def walk(nodes):
        for n in nodes:
            if n["dir"]:
                walk(n.get("children") or [])
                continue
            f = outline._real(p, module, n)
            if f.suffix.lower() not in outline.CODE_EXT and f.name not in outline.KNOWN:
                continue
            rel = _rel(p, f)
            if rel and rel not in seen and f.is_file():
                seen.add(rel)
                out.append((n["path"], f, rel))
    walk(files.tree(p, module)["items"])
    return out


def _history(p: Project) -> dict[str, dict]:
    """git 记账里每个文件：改过几次、最后一次谁什么时候（最近 2000 次记账）。没有 git 就是空的。"""
    if not vcs.enabled(p):
        return {}
    code, out = vcs._run(p, "-c", "core.quotepath=false", "log", "-n", "2000", "--name-only",
                         "--pretty=format:\x1e%an\x1f%ad", "--date=format:%Y-%m-%d %H:%M", timeout=60)
    if code != 0:
        return {}
    got: dict[str, dict] = {}
    for block in out.split("\x1e"):
        head, _, body = block.partition("\n")
        if "\x1f" not in head:
            continue
        who, at = head.split("\x1f", 1)
        for line in body.splitlines():
            rel = line.strip()
            if not rel:
                continue
            h = got.setdefault(rel, {"commits": 0, "who": who, "at": at})
            h["commits"] += 1
    return got


# ---------------------------------------------------------------- 重要性（S1-1 S2-24 代码重要性金字塔）
# 作者 10-03：「我想用重要性来分……就是最重要的核心代码放最上面，这样依次往下……我需要这个是通用的内置模块」。
# 重要性现算，只看代码本身，哪个项目都适用：
# - 被多少别的文件用到：Python 的 import / from（按模块名对上文件）；网页和脚本里 src=、import、require 引的文件；
#   任何文件里写出了另一个文件的全名（「代码地图.js」「mcp_server.py」这样，起码 5 个字、带扩展名）
# - 是不是入口：有 `if __name__ == "__main__"`、或叫 main.py / app.py / server.py / index.html 这类
# - 有几个测试守着：tests/ 里、test_ 开头的文件用到它几个（测试自己、文字说明排在最底下）
_PY_IMPORT = re.compile(r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+([\w*, ()]+)|import\s+([\w., ]+))", re.M)
_JS_REF = re.compile(r"""(?:\bsrc\s*=\s*|\bhref\s*=\s*|\bfrom\s+|\bimport\s*\(?\s*|\brequire\s*\(\s*|\bnew\s+Worker\s*\(\s*)["'`]([^"'`\s]+)["'`]""")
ENTRY_NAMES = {"main.py", "__main__.py", "app.py", "server.py", "manage.py", "index.html", "index.js", "main.js", "模板.html"}
_REFS: dict[str, tuple[int, int, frozenset]] = {}     # 路径 → (大小, 改动时间, 它用到的文件)：没变就不重读


def is_test(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return "/tests/" in f"/{rel}" or "/test/" in f"/{rel}" or name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".spec.js"))


def _refs_of(f: Path, st, rel: str, lang: str, by_stem: dict, by_name: dict, long_names: list) -> frozenset:
    """这个文件用到了哪些（别的）文件：从项目根算的路径。"""
    key = str(f)
    hit = _REFS.get(key)
    if hit and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
        return hit[2]
    try:
        body = f.read_bytes()[:4 * 1024 * 1024].decode("utf-8", errors="replace")
    except OSError:
        return frozenset()
    here = rel.rpartition("/")[0]
    out: set[str] = set()

    def stem(name: str):                                   # 一个模块名 → 文件（同一个文件夹里的优先）
        cands = by_stem.get(name)
        if cands:
            out.add(next((c for c in cands if c.rpartition("/")[0] == here), cands[0]))

    if lang == "py":
        for m in _PY_IMPORT.finditer(body):
            if m.group(3) is not None:
                for part in m.group(3).split(","):
                    name = part.strip().split(" as ")[0].strip()
                    if name:
                        stem(name.split(".")[-1]); stem(name.split(".")[0])
            else:
                mod = m.group(1).lstrip(".")
                if mod:
                    stem(mod.split(".")[-1])
                else:                                       # from . import a, b
                    for part in m.group(2).replace("(", "").replace(")", "").split(","):
                        stem(part.strip().split(" as ")[0].strip())
    if lang in ("js", "html"):
        for m in _JS_REF.finditer(body):
            name = m.group(1).split("?")[0].split("#")[0].rstrip("/").rsplit("/", 1)[-1]
            for c in by_name.get(name, []):
                out.add(c)
            if "." not in name:
                stem(name)
    for name in long_names:                                # 写出了另一个文件的全名
        if name in body:
            out.update(by_name[name])
    out.discard(rel)
    got = frozenset(out)
    _REFS[key] = (st.st_size, st.st_mtime_ns, got)
    return got


def importance(rows: list[dict], real: dict[str, Path]) -> None:
    """给每个文件算重要性，写回 rows：fan_in（被几个别的文件用到）、users（是哪几个，最多 12 个）、tests（几个测试用到）、entry、score。"""
    by_stem: dict[str, list[str]] = {}
    by_name: dict[str, list[str]] = {}
    for r in rows:
        if r["lang"] == "py":
            by_stem.setdefault(Path(r["name"]).stem, []).append(r["rel"])
        elif r["lang"] in ("js", "html", "css"):
            by_stem.setdefault(Path(r["name"]).stem, []).append(r["rel"])
        by_name.setdefault(r["name"], []).append(r["rel"])
    long_names = [n for n in by_name if len(n) >= 5 and "." in n.strip(".") and n not in ("__init__.py",)]
    users: dict[str, set] = {r["rel"]: set() for r in rows}
    tests: dict[str, set] = {r["rel"]: set() for r in rows}
    entry: dict[str, bool] = {}
    for r in rows:
        f = real[r["rel"]]
        try:
            st = f.stat()
        except OSError:
            continue
        for t in _refs_of(f, st, r["rel"], r["lang"], by_stem, by_name, long_names):
            if t in users:
                (tests if is_test(r["rel"]) else users)[t].add(r["rel"])
        guard = False
        if r["lang"] == "py" and r["bytes"] < 4 * 1024 * 1024:
            try:
                guard = "__name__" in f.read_text(encoding="utf-8", errors="replace") and bool(
                    re.search(r"^if\s+__name__\s*==\s*['\"]__main__['\"]", f.read_text(encoding="utf-8", errors="replace"), re.M))
            except OSError:
                pass
        entry[r["rel"]] = guard or r["name"] in ENTRY_NAMES
    for r in rows:
        rel = r["rel"]
        r["fan_in"], r["tests"], r["entry"] = len(users[rel]), len(tests[rel]), bool(entry.get(rel))
        r["users"] = sorted(users[rel])[:12]
        r["is_test"] = is_test(rel)
        if r["is_test"] or r["lang"] in ("md", "text"):
            r["score"] = round(min(r["fan_in"], 3) * 0.1, 2)              # 测试、文字说明排最底下
        else:
            r["score"] = round(r["fan_in"] * 3 + min(r["tests"], 10) + (5 if r["entry"] else 0) + 0.1 * (r["lines"] > 0) * len(str(r["lines"])), 2)


def listing(p: Project, module: str) -> dict:
    """代码地图要的目录：每个文件一行。全文不在这（网页看到哪块才取）。每个文件带上重要性（importance）。"""
    hist = _history(p)
    rows, total, real = [], 0, {}
    for path, f, rel in _code_files(p, module):
        try:
            st = f.stat()
        except OSError:
            continue
        n = _count(f, st)
        total += n
        h = hist.get(rel, {})
        rows.append({"path": path, "rel": rel, "name": f.name, "dir": rel.rpartition("/")[0], "lines": n, "bytes": st.st_size,
                     "mtime": int(st.st_mtime), "lang": lang_of(f.name), "commits": h.get("commits", 0),
                     "who": h.get("who", ""), "at": h.get("at", ""), "says": outline.says(f) or ""})
        real[rel] = f
    importance(rows, real)
    return {"files": rows, "lines": total, "git": bool(hist)}


def text(p: Project, rel: str) -> dict:
    """一个文件的全文（按行，Tab 换成 4 个空格）。"""
    f = files.proj_resolve(p, rel)
    if not f.is_file():
        raise files.Denied(f"「{rel}」不是文件")
    with open(f, "rb") as fh:
        raw = fh.read(16 * 1024 * 1024)
    lines = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    cut = len(lines) > MAX_LINES
    return {"rel": rel, "lines": [x.expandtabs(4) for x in lines[:MAX_LINES]], "cut": cut}


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def diff(p: Project) -> dict:
    """没交的改动：{从项目根算的路径: [[从第几行, 几行, 加 / 改 / 删 / 新]]}。跟上一次 git 记账比；新文件整个算「新」。"""
    if not vcs.enabled(p):
        return {"git": False, "marks": {}}
    code, out = vcs._run(p, "-c", "core.quotepath=false", "diff", "--unified=0", "--no-color", "--no-ext-diff", "HEAD", timeout=60)
    marks: dict[str, list] = {}
    cur = None
    for line in out.splitlines() if code == 0 else []:
        if line.startswith("+++ "):
            cur = line[6:].rstrip("\t") if line.startswith("+++ b/") else None     # 带空格的文件名，git 在后面加个 Tab
            continue
        m = _HUNK.match(line)
        if m and cur:
            old_n = 1 if m.group(2) is None else int(m.group(2))
            start, n = int(m.group(3)), 1 if m.group(4) is None else int(m.group(4))
            if n == 0:
                marks.setdefault(cur, []).append([max(start, 1), 1, "删"])
            else:
                marks.setdefault(cur, []).append([start, n, "加" if old_n == 0 else "改"])
    code, out = vcs._run(p, "-c", "core.quotepath=false", "ls-files", "--others", "--exclude-standard", timeout=60)
    for rel in out.splitlines() if code == 0 else []:
        rel = rel.strip()
        f = p.root / rel
        if rel and f.is_file():
            try:
                marks[rel] = [[1, max(_count(f, f.stat()), 1), "新"]]
            except OSError:
                pass
    return {"git": True, "marks": marks}


def search(p: Project, module: str, q: str) -> dict:
    """一个词（不分大小写）在哪些文件哪几行；文件名对上的也算。"""
    q = (q or "").strip()
    if not q:
        return {"q": q, "hits": [], "names": [], "more": False}
    low = q.lower()
    hits, names = [], []
    for _path, f, rel in _code_files(p, module):
        if low in f.name.lower():
            names.append(rel)
        if len(hits) >= MAX_HITS:
            continue
        try:
            body = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if low not in body.lower():
            continue
        for i, line in enumerate(body.splitlines(), 1):
            if low in line.lower():
                hits.append({"rel": rel, "line": i, "text": line.strip()[:160]})
                if len(hits) >= MAX_HITS:
                    break
    return {"q": q, "hits": hits, "names": names, "more": len(hits) >= MAX_HITS}


def defs(p: Project, rel: str) -> dict:
    """一个文件里的函数和类：名字、第几行、函数还是类。"""
    lang = lang_of(rel)
    pats = _DEFS.get(lang)
    out = []
    if pats:
        for i, line in enumerate(text(p, rel)["lines"], 1):
            for pat, kind in pats:
                m = pat.match(line)
                if m:
                    out.append({"name": m.group(1), "line": i, "kind": kind})
                    break
    return {"rel": rel, "defs": out}


def uses(p: Project, module: str, word: str, rel: str = "", line: int = 0) -> dict:
    """一个名字在模块里别的地方哪几行用到（整词对上；定义它的那一行不算）。"""
    if not re.fullmatch(r"[A-Za-z_$][\w$]*", word or ""):
        raise files.Denied("只能找一个函数名或类名")
    pat = re.compile(r"(?<![\w$])" + re.escape(word) + r"(?![\w$])")
    hits = []
    for _path, f, r in _code_files(p, module):
        try:
            body = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if word not in body:
            continue
        for i, s in enumerate(body.splitlines(), 1):
            if (r, i) == (rel, line) or not pat.search(s):
                continue
            hits.append({"rel": r, "line": i, "text": s.strip()[:160]})
            if len(hits) >= MAX_HITS:
                return {"word": word, "hits": hits, "more": True}
    return {"word": word, "hits": hits, "more": False}
