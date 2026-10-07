"""模块页用：左边的目录、右边的预览。只读，一个字节都不改。

路径两种写法：
- 「a/b.md」         模块自己文件夹里的
- 「@/backend/x.py」 挂进来的链接（从项目根算）
不管哪种，解析完必须还在这个模块能看的范围里——「../」越界一律拒。
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

import office
import governance_paths as gp
from project import SKIP_DIRS, Project, module_dir, read_links

MAX_ENTRIES = 3000
LAYER_PAGES = ("蓝图", "戒律")                  # 这两页能看各模块自己的 需求.md、蓝图.md、戒律.md（不用挂链接）
LAYER_FILES = ("需求.md", "蓝图.md", "戒律.md")
MAX_TEXT = 200 * 1024

TEXT_EXT = {
    ".md", ".txt", ".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".json", ".jsonl", ".csv", ".tsv",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".bat", ".cmd", ".ps1", ".sh", ".css",
    ".tex", ".bib", ".log", ".xml", ".sql", ".r", ".jl", ".m", ".c", ".h", ".cpp", ".hpp",
    ".java", ".go", ".rs", ".rst", ".gitignore", ".env", ".ipynb",
}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico"}
HTML_EXT = {".html", ".htm"}


class Denied(Exception):
    """路径不对：越界、不存在、不是文件。消息给人看。"""


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def resolve(p: Project, module: str, rel: str) -> Path:
    """把网页给的路径变成真路径，并确认它在这个模块能看的范围里。"""
    d = module_dir(p, module)
    if not d:
        raise Denied(f"没有「{module}」这个模块")
    rel = (rel or "").replace("\\", "/")
    if rel.startswith("@/"):
        root = p.root.resolve()
        target = (root / rel[2:]).resolve()
        links, _ = read_links(p, module)
        allowed = [(root / l).resolve() for l in links]
        if module in LAYER_PAGES:                         # 蓝图页、戒律页左栏「模块」那段：各模块的 需求 / 蓝图 / 戒律
            mats = p.materials.resolve()
            allowed += [target] if (target.parent.parent == mats and target.name in LAYER_FILES) else []
        if rel.startswith('@/治理/'):
            if module in LAYER_PAGES or target in [gp.resolve(p, f'资料/{module}/{n}') for n in LAYER_FILES]:
                allowed.append(target)
        if not any(target == a or target.is_relative_to(a) for a in allowed):
            raise Denied("这个文件不在本模块挂的链接里")
    else:
        base = d.resolve()
        target = (base / rel).resolve()
        if not target.is_relative_to(base):
            raise Denied("路径越界了：只能看这个模块文件夹里面的东西")
    target = gp.resolve(p, target.relative_to(p.root.resolve()).as_posix())
    if any(part.startswith(".") and part not in (".", "..") for part in target.relative_to(p.root.resolve()).parts[:-1]):
        raise Denied("隐藏文件夹里的东西不给看")
    if not target.is_file():
        raise Denied("找不到这个文件")
    return target


def _node(path: Path, rel: str, name: str, budget: list[int], link: bool = False) -> dict | None:
    if budget[0] <= 0:
        return None
    budget[0] -= 1
    try:
        st = path.stat()
    except OSError:
        return None
    if path.is_dir():
        kids = []
        try:
            entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
        except OSError:
            entries = []
        for e in entries:
            if e.name.startswith(".") or e.name in SKIP_DIRS:
                continue
            if e.is_symlink():
                continue
            k = _node(Path(e.path), f"{rel}/{e.name}" if rel else e.name, e.name, budget)
            if k:
                kids.append(k)
        return {"name": name, "path": rel, "dir": True, "link": link, "mtime": _iso(st.st_mtime), "children": kids}
    return {"name": name, "path": rel, "dir": False, "link": link, "size": st.st_size, "mtime": _iso(st.st_mtime),
            "kind": kind_of(path)}


def tree(p: Project, module: str) -> dict:
    """模块的目录树：自己文件夹里的 + 挂进来的链接（标 link）。最多 3000 条。"""
    d = module_dir(p, module)
    if not d:
        raise Denied(f"没有「{module}」这个模块")
    budget = [MAX_ENTRIES]
    own = _node(d, "", module, budget)
    items = own["children"] if own else []
    if gp.active(p):
        candidates = [(f.name, f) for f in gp.goal_files(p)] if module == '蓝图' else []
        if module == '戒律':
            candidates += [(f.name, f) for f in gp.rule_files(p)]
        candidates += [(name, gp.resolve(p, f'资料/{module}/{name}')) for name in LAYER_FILES]
        names = {n['name'] for n in items}
        for name, f in candidates:
            if f.is_file() and name not in names:
                n = _node(f, name, name, budget)
                if n:
                    items.append(n)
                    names.add(name)
    links, problems = read_links(p, module)
    for l in links:
        n = _node(gp.resolve(p, l), "@/" + l, l, budget, link=True)
        if n:
            items.append(n)
    return {"module": module, "items": items, "truncated": budget[0] <= 0, "problems": problems}


def kind_of(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in HTML_EXT:
        return "html"
    if ext in IMAGE_EXT:
        return "image"
    if ext == ".pdf":
        return "pdf"
    if office.kind(path):                           # 视频、音频、Word、Excel、PPT（S1-10 网页都能看）
        return office.kind(path)
    if ext in TEXT_EXT or path.name.lower() in {"readme", "license", "makefile", "dockerfile"}:
        return "text"
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return "binary"
    return "binary" if b"\0" in head else "text"


def preview(p: Project, module: str, rel: str) -> dict:
    return preview_path(resolve(p, module, rel), rel)


def preview_path(target: Path, rel: str) -> dict:
    """一个已经确认能看的文件：文字直接给内容（最多 200 KB），别的给种类。模块页、全站检索、存档里的旧文件共用。"""
    st = target.stat()
    out = {"path": rel, "name": target.name, "size": st.st_size, "mtime": _iso(st.st_mtime), "kind": kind_of(target)}
    if out["kind"] == "text":
        with open(target, "rb") as f:
            raw = f.read(MAX_TEXT + 1)
        out["truncated"] = len(raw) > MAX_TEXT
        out["text"], out["encoding"] = _decode(raw[:MAX_TEXT], out["truncated"])
    elif out["kind"] == "pptx":                      # 核心只列每页的字和图；照原样翻要装「PPT 预览」插件
        if target.suffix.lower() == ".ppt":
            out["error"] = "老格式的 .ppt 核心列不出字：用「PPT 预览」插件照原样看，或者用本机软件打开"
        else:
            try:
                out["pptx"] = office.pptx_outline(target)
            except Exception as e:
                out["error"] = f"这份 PPT 读不出来：{type(e).__name__}"
    elif target.suffix.lower() == ".zip":            # 压缩包（S1-10 S2-11）：不解开，给名字、许可证、能不能借；里面的文件用 /api/zip 看
        import zipfile
        if zipfile.is_zipfile(target):
            import repos
            try:
                out["kind"], out["zip"] = "zip", repos.inspect(target)
            except (zipfile.BadZipFile, OSError) as e:
                out["error"] = f"这个压缩包读不出来：{type(e).__name__}"
    elif out["kind"] in ("video", "audio"):
        out["playable"] = target.suffix.lower() in {".mp4", ".webm", ".ogv", ".m4v", ".mov", ".mp3", ".wav", ".m4a", ".ogg",
                                                     ".oga", ".flac", ".aac", ".opus"}   # 别的（avi、mkv…）浏览器多半放不了
    return out


def _decode(raw: bytes, truncated: bool) -> tuple[str, str]:
    # 截断处可能正好切在一个汉字中间，所以截断时允许去掉末尾 1~3 个字节再试
    cuts = range(4) if truncated else (0,)
    for enc in ("utf-8", "gb18030"):                 # 中文 Windows 上老文件常是 GBK
        for cut in cuts:
            try:
                return raw[:len(raw) - cut].decode(enc), enc
            except UnicodeDecodeError:
                continue
    return raw.decode("utf-8", errors="replace"), "utf-8（有乱码）"


# ---------------------------------------------------------------- 全项目（像 VS Code 左边那一栏）

# 这些文件夹不列：版本库、工具自己的库、缓存
PROJ_SKIP = {".git", "索引", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}


def _proj_skip(name: str) -> bool:
    return name in PROJ_SKIP or name.endswith((".pyc", ".tmp"))


def proj_resolve(p: Project, rel: str) -> Path:
    """全项目预览用：路径必须在项目里面，不许进 .git / 索引 这些。"""
    root = p.root.resolve()
    target = (root / (rel or "").replace("\\", "/")).resolve()
    if not target.is_relative_to(root) or target == root:
        raise Denied("路径越界了：只能看项目里面的东西")
    if any(_proj_skip(part) for part in target.relative_to(root).parts):
        raise Denied("这个文件夹不给看（版本库、工具自己的库、缓存）")
    target = gp.resolve(p, target.relative_to(root).as_posix())
    if not target.is_file():
        raise Denied("找不到这个文件")
    return target


def _pnode(path: Path, rel: str, budget: list[int]) -> dict | None:
    if budget[0] <= 0:
        return None
    budget[0] -= 1
    try:
        st = path.stat()
    except OSError:
        return None
    if path.is_dir():
        kids = []
        try:
            entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
        except OSError:
            entries = []
        for e in entries:
            if _proj_skip(e.name) or e.is_symlink():
                continue
            k = _pnode(Path(e.path), f"{rel}/{e.name}" if rel else e.name, budget)
            if k:
                kids.append(k)
        return {"name": path.name, "path": rel, "dir": True, "mtime": _iso(st.st_mtime), "children": kids}
    return {"name": path.name, "path": rel, "dir": False, "size": st.st_size, "mtime": _iso(st.st_mtime), "kind": kind_of(path)}


def proj_tree(p: Project) -> dict:
    """整个项目的目录树（最多 5000 条）。"""
    budget = [5000]
    root = _pnode(p.root, "", budget)
    return {"name": p.root.name, "items": root["children"] if root else [], "truncated": budget[0] <= 0}


PLANS = "计划"          # 项目根 计划/：每次做的计划一份一个文件（作者 2026-09-25：「每一次做计划都能把计划落入计划模块里」）


def _natural(name: str) -> list:
    """按人的习惯排：3-2 在 3-10 前面。"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def _plan_order(f: Path) -> tuple:
    """一个目标里的顺序：0 总览 → P 计划 → R 设计参考 → 其余（原文等），各自按编号。"""
    n = f.name
    rank = 0 if n[:1].isdigit() else 1 if n.startswith("P") else 2 if n.startswith("R") else 3
    return rank, _natural(n)


_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_CODE = re.compile(r"(P\d+|R\d+|原文|\d+)")
_OLD = re.compile(r"^(P\d+|R\d+)\s+(.+?)(?:（(\d{2})-(\d{2})）)?$")    # 09-29 以前的旧名：P3 开工单（09-27）


def plan_meta(stem: str, mtime: float) -> tuple[str, str, str]:
    """文件名 →（编号, 日期, 标题）。起名是「P3 · 2026-09-27 · 开工单」（作者 2026-09-29：「计划里……没有时间编码」）；
    旧名、没写日期的也认，日期取不到就用修改时间那天。「0 总览」这类没日期的编号是 0。"""
    parts = stem.split(" · ")
    date = next((x for x in parts if _DATE.fullmatch(x)), "")
    code = parts[0] if len(parts) > 1 and _CODE.fullmatch(parts[0]) else ""
    rest = [x for i, x in enumerate(parts) if x != date and not (i == 0 and code)]
    title = " · ".join(rest) or stem
    if not date and not code:
        m = _OLD.match(stem)
        if m:
            code, title = m.group(1), m.group(2)
            if m.group(3):
                date = f"{datetime.fromtimestamp(mtime).year}-{m.group(3)}-{m.group(4)}"
        elif stem[:1].isdigit() and " " in stem:
            code, title = stem.split(" ", 1)
    if not date and code != "0" and not code.isdigit():
        date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    return code, date, title


def _plan_file(f: Path, rel: str, *, by_heading: bool, goal: str = "") -> dict | None:
    try:
        st = f.stat()
        code, date, title = plan_meta(f.stem, st.st_mtime)
        if by_heading:                                   # Claude Code 起的文件名是随机英文，标题取第一行「# 」
            with open(f, encoding="utf-8", errors="replace") as fh:
                for _, line in zip(range(40), fh):
                    if line.startswith("# "):
                        title = line[2:].strip() or title
                        break
    except OSError:                                      # 正被别的程序占着，下次再列
        return None
    return {"name": f.name, "path": rel, "title": title, "code": code, "date": date, "goal": goal, "kind": "html" if f.suffix == ".html" else "md",
            "size": st.st_size, "mtime": _iso(st.st_mtime), "_t": st.st_mtime}


def plans(p: Project) -> list[dict]:
    """计划/ 按蓝图的目标分：做事的顺序是「以蓝图的目标为导向，按计划，守戒律」（作者 2026-09-25）。
    - 文件夹 = 一个目标（S0 总体、S1-3 说得准 …），按编号排；里面 P1 P2 … 是计划、R1 R2 … 是设计参考，
      起名「P3 · 2026-09-27 · 开工单」；每份带 code · date · goal，网页按时间一条线排（作者 2026-09-29 选的）
    - 直接放在 计划/ 下的 .md = 还没挂到目标下的「待归位」（Claude Code 自动存进来的就是这样），新的在前，标题取第一行「# 」"""
    loose, grouped = [], {}
    for rel, f in gp.plan_files(p, html=True).items():          # 样图（.html）也列，点了照全站预览看（S1-1 S2-20）
        parts = rel.split('/')
        if len(parts) > 2 or any(x.startswith(('.', '_')) for x in parts):
            continue
        goal = parts[0] if len(parts) == 2 else '待归位'
        item = _plan_file(f, gp.relative(p, f), by_heading=len(parts)==1 and f.suffix == '.md', goal=goal)
        if not item:
            continue
        if len(parts) == 1:
            loose.append(item)
        else:
            grouped.setdefault(goal, []).append(item)
    goals = []
    for name, kids in grouped.items():
        kids.sort(key=lambda x: _natural(x['path']))
        t = max(k['_t'] for k in kids)
        goals.append({'name':name, 'path':str(Path(kids[0]['path']).parent).replace('\\','/'), 'title':name,
                      'dir':True, 'mtime':_iso(t), '_t':t, 'children':kids})
    loose.sort(key=lambda x: -x['_t'])
    goals.sort(key=lambda x: _natural(x['name']))
    import archive                                              # 收进归档的计划：最后一组「已归档」（S1-8 S2-61）
    old = []
    for under in ('计划', '治理/计划'):
        for f in archive.archived_files(p, under, '*.md'):
            item = _plan_file(f, f.relative_to(p.root).as_posix(), by_heading=False, goal='已归档')
            if item:
                old.append(item)
    if old:
        old.sort(key=lambda x: -x['_t'])
        goals.append({'name': '已归档', 'path': archive.DIR, 'title': '已归档', 'dir': True, 'mtime': _iso(max(k['_t'] for k in old)),
                      '_t': max(k['_t'] for k in old), 'children': old})
    out = loose + goals
    for x in out:
        del x['_t']
        for k in x.get('children', []):
            del k['_t']
    return out


SHALLOW = {"存档", "回收站"}                         # 里面是整份的副本：只看最上一层（哪档、哪件、清单），不往里钻


def proj_signature(p: Project, snap: dict | None = None, top_only: set | None = None) -> str:
    """整个项目的指纹：任何地方加、删、改文件，指纹就变，网页跟着重拉（作者 2026-09-25：「我都要实时的要活的东西」）。
    不设条数上限——项目大、扫一遍慢，后台就自己放慢扫的间隔（见 main.watch），不拖垮电脑。
    版本库、工具自己的库、缓存不看；存档/ 回收站/ 只看最上一层。
    给了 snap：同一遍里顺便记下每个文件「从项目根算的路径 → (大小, 修改时间)」，监管拿两遍比一比（作者 10-01：「能自动化监管的活的网页端」）。
    top_only：设成「只看最上一层」的模块（S1-8 S2-42）——资料/<它>/ 只看第一层，不往里钻。"""
    h = hashlib.sha1()

    def walk(d: str, deep: bool, light: bool = False) -> None:
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            return
        for e in entries:
            if _proj_skip(e.name) or e.is_symlink():
                continue
            try:
                st = e.stat()
                is_dir = e.is_dir()
            except OSError:                              # 正被别的程序占着（比如 Word 开着），下一轮再看
                continue
            if light and is_dir:                         # 只看最上一层：第一层的文件夹只认名字（Windows 上文件夹时间慢半拍才变）
                h.update(f"{e.path}|dir\n".encode("utf-8", "surrogatepass"))
            else:
                h.update(f"{e.path}|{st.st_size}|{st.st_mtime_ns}\n".encode("utf-8", "surrogatepass"))
            if snap is not None and not is_dir:
                snap[os.path.relpath(e.path, root).replace("\\", "/")] = (st.st_size, st.st_mtime_ns)
            if is_dir and deep:
                top = d == mats and e.name in (top_only or ())
                walk(e.path, not ((d == root and e.name in SHALLOW) or top), light=top)

    root, mats = str(p.root), str(p.materials)
    walk(root, True)
    return h.hexdigest()


def proj_preview(p: Project, rel: str) -> dict:
    return preview_path(proj_resolve(p, rel), rel)


def _proj_files(p: Project):
    stack = [p.root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    if _proj_skip(e.name) or e.is_symlink():
                        continue
                    if e.is_dir():
                        stack.append(Path(e.path))
                    elif e.is_file():
                        yield Path(e.path)
        except OSError:
            continue


def proj_search(p: Project, q: str, limit: int = 200) -> tuple[list[dict], bool]:
    """全站检索：整个项目的文件名 + 文字文件内容（≤1 MB）。按第一层文件夹分组给网页。"""
    ql, root = q.lower(), p.root
    hits: list[dict] = []
    for f in sorted(_proj_files(p)):
        rel = f.relative_to(root).as_posix()
        lines = []
        try:
            if kind_of(f) == "text" and f.stat().st_size <= 1024 * 1024:
                text, _ = _decode(f.read_bytes(), False)
                for i, line in enumerate(text.splitlines(), 1):
                    k = line.lower().find(ql)
                    if k >= 0:
                        lines.append({"line": i, "text": line[max(0, k - 40): k + len(q) + 60].strip()})
                        if len(lines) >= 3:
                            break
        except OSError:
            continue
        if lines or ql in f.name.lower():
            top = rel.split("/")[0] if "/" in rel else "（项目根）"
            hits.append({"top": top, "path": rel, "name": f.name, "lines": lines})
            if len(hits) >= limit:
                return hits, True
    return hits, False
