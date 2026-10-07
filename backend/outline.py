"""模块页的左栏：上面「总的」、下面「目录」，还有源代码页的代码地图。只读。

09-27 分两层（作者：「总蓝图是总蓝图，蓝图和戒律也是分层级的」「把想法变成需求模块也要优化」）：
- 想法：总的 = 想法表；下面按去向分组（待整理 · 等你改总的 · 变成了需求 · 变成了戒律 · 放一放 · 不要），一个想法一行
- 蓝图：总的 = S0；总蓝图 = S1-1…；模块 = 每个写了需求 / 蓝图的模块一行（需求达到几条、施工做完几件、有没有开工单在装）
- 戒律：总的 = AGENTS.md；总戒律 = 1 通用、2 项目；模块 = 每个模块自己的 戒律.md（现算，不用手动挂）
- 别的模块：总的 = 本模块需求（需求 + 蓝图现算的一页）· 本模块蓝图 · 本模块戒律；目录 = 其余文件

作者 2026-09-25：「左边上面有一个总的模块下面才是目录」「我是说蓝图和戒律这两个目录的左侧栏」。
- 蓝图：总的 = S0；目录 = S1-1…（按编号，S1-10 在 S1-9 后面），旁边写底下的 S2 做完几个
- 戒律：总的 = AGENTS.md；目录 = 1 通用、2 项目、3 模块（下面挂各模块的 戒律.md），旁边写几条
- 源代码：总的 = 代码地图（每个文件一句话，现场从文件开头那句说明读，永远跟代码对得上）；目录照旧
别的模块没有分段，左栏还是平铺的文件。
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from files import _natural
import project as proj
import governance_paths as gp
from project import Project, module_dir, read_links

_GOAL = re.compile(r"^S(\d+(?:-\d+)*)\s")                        # 「S1-3 说得准.md」
_NUM = re.compile(r"^\d+\s")                                      # 「1 通用戒律.md」
_RULE_ROW = re.compile(r"^\|\s*[^|\s\d][^|\s]*-\d+\s*\|")        # 「| 通-1 | … |」
_GOAL_ROW = re.compile(r"^\|\s*S\d+(?:-\d+)+\s*\|")              # 「| S2-1 | … | 做完 |」
READ_MAX = 256 * 1024


def _real(p: Project, module: str, node: dict) -> Path:
    path = node["path"]
    return gp.resolve(p, path[2:] if path.startswith("@/") else f"资料/{module}/{path}")


def _text(f: Path) -> str:
    try:
        with open(f, "rb") as fh:
            return fh.read(READ_MAX).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _goal_note(f: Path) -> str | None:
    """S1 那份里的 S2 表：做完几个 / 一共几个。"""
    done = total = 0
    for line in _text(f).splitlines():
        if _GOAL_ROW.match(line):
            total += 1
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            done += cells[-1].startswith("做完")
    return f"做完 {done}/{total}" if total else None


def _rule_count(f: Path) -> int:
    return sum(1 for line in _text(f).splitlines() if _RULE_ROW.match(line))


def _blueprint(p: Project, module: str, items: list[dict]) -> list[dict]:
    top, toc, rest = [{"name": "项目全景", "path": "#项目全景", "dir": False, "link": False, "virtual": True}], [], []
    for n in items:
        m = None if n["dir"] or n["link"] else _GOAL.match(n["name"])
        if m and m.group(1) == "0":
            top.append(n)
        elif m:
            toc.append(n)
        else:
            rest.append(n)
    toc.sort(key=lambda n: _natural(n["name"]))
    for n in toc:
        n["note"] = _goal_note(_real(p, module, n))
    rest, own = _own_rules(rest)
    return [{"title": "总的", "items": top + own}, {"title": "总蓝图", "items": toc},
            {"title": "模块", "items": _module_rows(p)}, {"title": "其它", "items": rest}]


REQ = "#需求:"                                                   # 「#需求:文献」：文献的需求 + 蓝图，现场算的一页


def _module_rows(p: Project) -> list[dict]:
    """蓝图页「模块」那段：每个写了需求或蓝图的模块一行；旁边写需求达到几条、施工做完几件、在装的开工单。"""
    import blueprint
    import requirements
    import workorders
    bp = blueprint.pyramid(p)
    wos = workorders.list_all(p)
    out = []
    for m in requirements.modules(p):
        v = requirements.view(p, m, bp)
        k = next((w for w in wos if m in w["modules"] and w["stored"] != "搁置"), None)
        bits = [f"需求 {v['met']}/{v['total']}" if v["has_need"] else "没写需求",
                f"施工 {v['done']}/{v['items']}" if v["has_plan"] else "没写蓝图"]
        if k:
            bits.append(f"{k['code']} {'在跑' if k['stored'] == '在跑' else '备料'}")
        display = next((x["name"] for x in __import__("governance").module_catalog(p) if x["key"] == m), m)
        out.append({"name": m, "label": display, "path": REQ + m, "dir": False, "link": False, "virtual": True,
                    "note": " · ".join(bits)})
    return out


def _own_rules(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """模块自己的 戒律.md 挑出来，放到「总的」里（跟着模块走的规矩，一进来就看得见）。"""
    own = [dict(n, label="本模块戒律") for n in items if not n["dir"] and not n["link"] and n["name"] == "戒律.md"]
    return [n for n in items if not (not n["dir"] and not n["link"] and n["name"] == "戒律.md")], own


def _rules(p: Project, module: str, items: list[dict]) -> list[dict]:
    top, toc, kids, rest = [], [], [], []
    for n in items:
        name = n["name"]
        if n["dir"]:
            rest.append(n)
        elif n["link"] and name == "AGENTS.md":
            top.append(dict(n, label="AGENTS.md", note="一行版"))
        elif name == "戒律.md" or (n["link"] and name.endswith("/戒律.md")):
            owner = module if not n["link"] else Path(name).parent.name
            kids.append(dict(n, label=f"{owner}模块", note=f"{_rule_count(_real(p, module, n))} 条"))
        elif not n["link"] and _NUM.match(name) and name.lower().endswith(".md"):
            toc.append(n)
        else:
            rest.append(n)
    toc.sort(key=lambda n: _natural(n["name"]))
    for n in toc:
        k = _rule_count(_real(p, module, n))
        n["note"] = f"{k} 条" if k else None
    # 「模块」那段现算：每个模块自己的 戒律.md（挂了链接的、没挂的都算），不用再手动维护；「3 模块戒律」只当说明
    seen = {Path(_real(p, module, n)).resolve() for n in kids}
    for m in sorted(proj.module_dirs(p)):
        f = gp.module_rule(p, m)
        if m != module and f.is_file() and f.resolve() not in seen:
            kids.append({"name": f"资料/{m}/戒律.md", "path": f"@/资料/{m}/戒律.md", "dir": False, "link": True,
                         "label": f"{m}模块", "note": f"{_rule_count(f)} 条"})
    kids.sort(key=lambda n: n["label"])
    idx = [n for n in toc if n["name"].startswith("3 ")]
    toc = [n for n in toc if not n["name"].startswith("3 ")]
    return [{"title": "总的", "items": top}, {"title": "总戒律", "items": toc}, {"title": "模块", "items": kids},
            {"title": "其它", "items": idx + rest}]


CODEMAP = "#代码地图"


def _code(p: Project, module: str, items: list[dict]) -> list[dict]:
    top = [{"name": "代码地图", "path": CODEMAP, "dir": False, "link": False, "virtual": True,
            "note": "每个文件一句话"}]
    items, own = _own_rules(items)
    return [{"title": "总的", "items": top + own}, {"title": "目录", "items": items}]


def _ideas(p: Project, module: str, items: list[dict]) -> list[dict]:
    """想法仓库与集中需求共用一个入口；下面仍按想法去向分组。"""
    import ideas
    table = [dict(n, label="想法仓库", en="Idea repository") for n in items if not n["dir"] and not n["link"] and n["name"] == ideas.FILE]
    rest = [n for n in items if not (not n["dir"] and not n["link"] and n["name"] == ideas.FILE)]
    new = {"name": "＋ 记一个想法", "label": "＋ 记一个想法", "path": IDEA + "新", "dir": False, "link": False, "virtual": True}
    needs = {"name": "需求", "label": "需求", "en": "Requirements", "path": REQ + "全部", "dir": False, "link": False, "virtual": True}
    secs = [{"title": "总的", "items": [new] + table + [needs]}]
    all_ = ideas.list_all(p)
    for g in ideas.GROUPS:
        xs = [x for x in all_ if x["state"] == g]
        if g == "待整理":                                      # 有候选的在上
            import store
            conn = store.connect(p.db_path)
            try:
                has = {x["code"] for x in xs if ideas.candidates(conn, x["code"])}
            finally:
                conn.close()
            xs.sort(key=lambda x: (x["code"] not in has, -x["n"]))
        else:
            xs.sort(key=lambda x: -x["n"])
        secs.append({"title": g, "items": [{"name": x["code"], "label": f"{x['code']} {x['text'][:24]}", "path": IDEA + x["code"],
                                            "dir": False, "link": False, "virtual": True,
                                            "note": x["about"] if g == "待整理" else x["dest"].split("：", 1)[-1]} for x in xs]})
    secs.append({"title": "其它", "items": rest})
    return secs


IDEA = "#想法:"                                                  # 「#想法:想-3」一个想法；「#想法:新」记一个


def _plain(p: Project, module: str, items: list[dict]) -> list[dict]:
    """别的模块：顶上三篇——本模块需求（现算的一页）· 本模块蓝图 · 本模块戒律；其余是目录。"""
    import downloads
    names = {"蓝图.md": "本模块蓝图", "戒律.md": "本模块戒律", "需求.md": None, downloads.FILE: None}
    rest = [n for n in items if n["dir"] or n["link"] or n["name"] not in names]
    top = []  # 需求、任务和戒律统一从蓝图阅读；旧链接仍由路径解析兼容。
    if (p.materials / module / "技能" / "SKILL.md").is_file():      # 模块专属技能（放在模块里：技能/SKILL.md）
        top.append({"name": "SKILL.md", "label": "本模块技能", "path": "技能/SKILL.md", "dir": False, "link": False})
    secs_more = []
    import library
    if library.enabled(p, module):                               # 文献库：一页（搜、筛、排序）+ 一篇一行
        xs, probs = library.entries(p, module)
        top.append({"name": "文献库", "label": "文献库", "path": LIB + module, "dir": False, "link": False, "virtual": True,
                    "note": f"{len(xs)} 篇" + (f" · {len(probs)} 处对不上" if probs else "")})
        secs_more.append({"title": "文献", "items": [{"name": x["code"], "label": f"{x['code']} {x['title'][:26]}", "path": PAPER + x["code"],
                                                     "dir": False, "link": False, "virtual": True,
                                                     "note": x["problem"] or x["info"].get("阅读状态", "")} for x in xs]})
    if any(not n["dir"] and not n["link"] and n["name"] == downloads.FILE for n in items):   # 下载清单：现场生成的一页（灯现查）
        xs = downloads.list_all(p, module)
        top.append({"name": "下载清单", "label": "下载清单", "path": DL + module, "dir": False, "link": False, "virtual": True,
                    "note": f"下好 {sum(1 for x in xs if x['lamp'] == 'ok')}/{len(xs)}"})
    return [{"title": "总的", "items": top}] + secs_more + [{"title": "目录", "items": rest}]


DL = "#下载:"
LIB = "#文献库:"                                                 # 「#文献库:文献」：搜、筛、排序的一页
PAPER = "#篇:"                                                   # 「#篇:L1」：这一篇的信息                                                    # 「#下载:文献」：文献的下载清单


SECTIONS = {"想法": _ideas, "蓝图": _blueprint, "戒律": _rules, "源代码": _code}


def sections(p: Project, module: str, items: list[dict]) -> dict:
    """给模块页左栏分段。返回 {"sections": [...], "default": 一进来打开哪篇}；不分段的模块两样都是 None。"""
    if module == "文献":
        # 两个操作入口共用原来的下载/文献库记录；目录仍保留旧文件深链。
        entries = [{"name": title, "label": title, "en": en, "path": path,
                    "dir": False, "link": False, "virtual": True}
                   for title, en, path in (("下载列表", "Downloads", DL + module),
                                           ("文献库", "Library", LIB + module))]
        return {"sections": [{"title": "工作台", "items": entries},
                             {"title": "目录", "items": items}], "default": LIB + module}
    if module in ("文献", "论文", "测试", "PPT", "宣传片"):
        import content_modules
        try:
            workspace = content_modules.workspace(p, module)
            if not workspace["config_revision"]:
                # 尚无新工作台配置的旧项目保持原有文献/下载入口和默认页。
                secs = [s for s in _plain(p, module, items) if s["items"]]
                first = next((n for s in secs for n in s["items"] if not n["dir"]), None)
                return {"sections": secs, "default": first["path"] if first else None}
            entries = [{"name": "全部", "label": "全部 All", "path": "#工作区:all", "dir": False,
                        "link": False, "virtual": True}]
            entries += [{"name": s["title"], "label": f'{s["title"]} {s["en"]}', "path": "#工作区:" + s["id"],
                         "dir": False, "link": False, "virtual": True} for s in workspace["sections"]]
            if module == "文献":
                kinds = {s["kind"]: s["files"] for s in workspace["sections"]}
                if kinds["downloads"]:
                    entries.append({"name": "下载清单", "label": "下载清单", "path": DL + module,
                                    "dir": False, "link": False, "virtual": True})
                if kinds["originals"] or kinds["reading"] or kinds["notes"]:
                    entries.append({"name": "文献库", "label": "文献库", "path": LIB + module,
                                    "dir": False, "link": False, "virtual": True})
                codes = sorted({f["reader_code"] for fs in kinds.values() for f in fs if f.get("reader_code")},
                               key=lambda c: int(c[1:]))
                entries += [{"name": c, "label": c, "path": PAPER + c, "dir": False,
                             "link": False, "virtual": True} for c in codes]
            # 目录/时间和原文件链接继续使用原 tree；旧文献阅读入口由工作台显式按钮进入。
            return {"sections": [{"title": "工作台", "items": entries}, {"title": "目录", "items": items}],
                    "default": "#工作区:all"}
        except (ValueError, OSError):
            return {"sections": [{"title": "目录", "items": items}], "default": None}
    fn = SECTIONS.get(module) or _plain
    secs = [s for s in fn(p, module, items) if s["items"]]
    first = next((n for s in secs for n in s["items"] if not n["dir"] and not n["path"].endswith(":新")), None)
    return {"sections": secs, "default": first["path"] if first else None}


# ---------------------------------------------------------------- 代码地图

CODE_EXT = {".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".htm", ".css", ".bat", ".cmd", ".ps1", ".sh",
            ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".r", ".jl", ".m", ".c", ".h", ".cpp", ".hpp",
            ".java", ".go", ".rs", ".sql", ".ipynb"}
# 没法写注释的几种常见文件，一句话写在这（跟哪个项目都一样）
KNOWN = {".mcp.json": "给 agent 接上这个工具的配置（MCP）", "package.json": "网页前端要装的包",
         "requirements.txt": "Python 要装的库", "pyproject.toml": "Python 项目的配置和要装的库"}
_DECOR = "=-*#/<>!~ \t"
_HASH = {".py", ".sh", ".ps1", ".r", ".jl", ".toml", ".yaml", ".yml", ".ini", ".cfg"}
_SLASH = {".js", ".mjs", ".ts", ".tsx", ".jsx", ".css", ".c", ".h", ".cpp", ".hpp", ".java", ".go", ".rs"}


def _first_line(text: str) -> str | None:
    """一段注释里第一句像话的（去掉 ==== 这类装饰线）。"""
    for line in text.splitlines():
        line = line.strip().strip(_DECOR).strip()
        if re.search(r"[A-Za-z一-鿿]", line) and "coding" not in line[:12]:
            return line
    return None


def says(f: Path) -> str | None:
    """这个文件开头那句「它管什么」（戒律 源-6）。找不到就是 None。"""
    if f.name in KNOWN:
        return KNOWN[f.name]
    ext, text = f.suffix.lower(), _text(f)
    if ext == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text))
        except (SyntaxError, ValueError):
            doc = None
        if doc:
            return _first_line(doc)
    if ext in (".html", ".htm"):
        m = re.search(r"<!--(.*?)-->", text, re.S)
        return _first_line(m.group(1)) if m else None
    if ext in (".bat", ".cmd"):
        for line in text.splitlines():
            m = re.match(r"\s*(?:@?rem|::)\s+(.+)", line, re.I)
            if m:
                return _first_line(m.group(1))
        return None
    if ext in _SLASH:
        m = re.search(r"/\*(.*?)\*/|//(.*)", text, re.S)
        return _first_line(m.group(1) or m.group(2)) if m else None
    if ext == ".sql":
        m = re.search(r"--(.*)", text)
        return _first_line(m.group(1)) if m else None
    if ext in _HASH:
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("#") and not s.startswith(("#!", "# -*-")):
                return _first_line(s[1:])
    return None


def codemap(p: Project, module: str, items: list[dict], limit: int = 1000) -> dict:
    """模块里（含挂进来的）每个程序文件一句话，按所在文件夹分组。"""
    groups: dict[str, list[dict]] = {}
    seen = [0]

    def walk(nodes):
        for n in sorted(nodes, key=lambda n: n["dir"]):     # 先这一层的文件，再进子文件夹：backend 在 backend/tests 前面
            if seen[0] >= limit:
                return
            if n["dir"]:
                walk(n["children"])
                continue
            f = _real(p, module, n)
            if f.suffix.lower() not in CODE_EXT and f.name not in KNOWN:
                continue
            seen[0] += 1
            try:
                where = f.resolve().parent.relative_to(p.root.resolve()).as_posix()
            except ValueError:
                continue
            groups.setdefault("" if where == "." else where, []).append(
                {"path": n["path"], "name": f.name, "says": says(f)})

    walk(items)
    return {"groups": [{"dir": d, "files": fs} for d, fs in groups.items()], "truncated": seen[0] >= limit}
