"""扫描走到哪扫到哪（S1-8 S2-43）。

作者 10-02：「我想有的不常用的文件夹，不需要实时渲染，我的想法是像我玩游戏一样，走到哪里就扫描到哪里，这样才是最好的，最节约计算资源的你觉得呢？」
「这样我是不是就不用设置扫描文件数量上限了？」——不用：花的资源只跟正在看、正在干的那一片有关。

- 项目分成一片一片：资料/ 下每个模块一片 · 治理 · 自动化 · 核心（backend/、模板.html、界面脚本、启动器）· 其余顶层文件夹各一片 · 根目录的散文件
- 热的（马上扫、马上给监管比、网页跟着变）：网页正在看的那一片 · agent 领着的活占的模块（拿着核心锁就算核心）·
  一直盯着的（治理、自动化、笔记、核心）· 自定义「一直盯着」的文件夹 · 结构变化（资料/ 下多了少了一个模块、根目录多了少了东西）
- 冷的：系统通知照收，只记一笔「这片有变动，几次」；走进去（网页换到那页、agent 领了那里的活）先扫这一片；兜底每 N 分钟把有账的冷片扫掉
- 不看：自定义的文件夹，通知、兜底都不理
- 自定义存在 自动化/扫描规则.md（一张表：文件夹 · 怎么扫 · 备注；外加一行「兜底：每 30 分钟……」），跟项目走，agent 也看得懂
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import files
from project import Project

CORE_FILES = ("模板.html", "界面英文.js", "治理界面.js", "代码地图.js", "启动.bat", "新项目.bat")
CORE = "核心"
ROOT_AREA = "根目录"
ALWAYS = ("治理", "自动化", "笔记", CORE)              # 一直盯着（自带）：小、又是监管最要紧的（改方向、人的笔记只增、没拿锁改核心）
MODES = ("一直盯着", "走到才扫", "不看")
SWEEPS = (10, 30, 60)
RULES_FILE = "自动化/扫描规则.md"
BUILTIN = [                                            # 设置页灰着列出来的自带规矩
    {"path": ".git、索引、缓存（__pycache__、node_modules……）", "mode": "不看", "why": "版本库、库、缓存，跟你的东西无关"},
    {"path": "存档、回收站", "mode": "只看最上一层", "why": "里面是整份的副本"},
    {"path": ".claude/worktrees", "mode": "不看", "why": "agent 的临时工作区"},
    {"path": "治理、自动化、笔记、核心程序", "mode": "一直盯着", "why": "小，又是监管最要紧的（改方向、人的笔记只增、没拿锁改核心）"},
]
VIEW_AREAS = {"plans": ["治理"], "tools": ["工具库"], "skills": ["技能库"], "notes": ["笔记"], "saves": ["存档"], "trash": ["回收站"],
              "auto": ["自动化", "治理"], "commands": ["快捷指令"], "inbox": ["资料/_外部资料入口"], "qa": ["治理"], "guide": [ROOT_AREA]}

# 后台在跑才有（按项目分开）：on · stats 每个模块的文件数、大小（扫完那一片留下的，不用每次重拉都从头数）·
# dirty 冷片的账 {片: 几次} · hot 正在盯着的 {片: 为什么} · busy 正在扫的大片 · next_sweep 下回兜底（time.time()）
_STATE: dict[str, dict] = {}


def state(p: Project) -> dict:
    return _STATE.setdefault(str(p.root), {"on": False, "stats": {}, "dirty": {}, "hot": {}, "busy": [], "next_sweep": 0.0})


# ---------------------------------------------------------------- 分片

def area_of(p: Project, rel: str) -> str:
    """从项目根算的路径 → 哪一片。"""
    parts = rel.replace("\\", "/").strip("/").split("/")
    if parts[0] == "backend" or (len(parts) == 1 and parts[0] in CORE_FILES):
        return CORE
    if len(parts) == 1:
        return ROOT_AREA
    if parts[0] == p.materials.name:
        return f"{parts[0]}/{parts[1]}" if len(parts) > 2 else parts[0]
    return parts[0]


def structural(p: Project, rel: str) -> bool:
    """结构变了（资料/ 下多了少了一个模块、根目录多了少了东西）：不管冷热马上看，第二栏要跟上。"""
    parts = rel.replace("\\", "/").strip("/").split("/")
    return len(parts) == 1 or (len(parts) == 2 and parts[0] == p.materials.name)


def focus_areas(p: Project, view: str, module: str) -> set[str]:
    """网页在看哪一页 → 哪几片热（模块页是那个模块和它挂进来的链接落在的地方；计划页是治理……）。"""
    import project as proj
    if view == "mod" and module:
        out = {f"{p.materials.name}/{module}"}
        try:
            out |= {area_of(p, os.path.relpath(t, p.root)) for t in proj._targets(p, module)[1:]}
        except (OSError, ValueError):
            pass
        return out
    return set(VIEW_AREAS.get(view, ()))


def agent_areas(conn, p: Project) -> dict[str, str]:
    """agent 在干的：它领着的活占的模块、拿着核心锁就算核心。→ {片: 谁}。"""
    import claims
    out = {}
    for r in claims.active(conn):
        who = r["agent"].replace("agent:", "")
        if r["goal"] == claims.CORE:
            out[CORE] = who
            continue
        for lane in r["lanes"]:
            if (p.materials / lane).is_dir():
                out[f"资料/{lane}"] = who
    return out


# ---------------------------------------------------------------- 自定义规则（自动化/扫描规则.md）

def _rules_path(p: Project) -> Path:
    return p.root / RULES_FILE


def _norm(path: str) -> str:
    return "/".join(x for x in str(path).replace("\\", "/").split("/") if x and x != ".")


def read_rules(p: Project) -> dict:
    """{sweep: 分钟, rules: [{path, mode, note}]}；没有这份文件就是默认（兜底 30 分钟、没有自定义）。"""
    out = {"sweep": 30, "rules": []}
    try:
        text = _rules_path(p).read_text(encoding="utf-8")
    except OSError:
        return out
    m = re.search(r"兜底：每\s*(\d+)\s*分钟", text)
    if m and int(m.group(1)) in SWEEPS:
        out["sweep"] = int(m.group(1))
    for line in text.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(c) >= 2 and c[1] in MODES and _norm(c[0]):
            out["rules"].append({"path": _norm(c[0]), "mode": c[1], "note": c[2] if len(c) > 2 else ""})
    return out


def write_rules(p: Project, sweep: int, rules: list[dict]) -> dict:
    """网页「设置 → 扫描」存的：写回 自动化/扫描规则.md。"""
    if sweep not in SWEEPS:
        raise ValueError(f"兜底只能是 {' / '.join(map(str, SWEEPS))} 分钟")
    clean, seen = [], set()
    for r in rules:
        path, mode = _norm(r.get("path", "")), r.get("mode", "")
        if not path:
            continue
        if mode not in MODES:
            raise ValueError(f"「{path}」的怎么扫只能是 {' / '.join(MODES)}")
        if ".." in path.split("/"):
            raise ValueError(f"「{path}」跑到项目外面去了")
        if path in seen:
            raise ValueError(f"「{path}」写了两遍")
        seen.add(path)
        clean.append({"path": path, "mode": mode, "note": " ".join(str(r.get("note", "")).replace("|", "／").split())})
    rows = "".join(f"| {r['path']} | {r['mode']} | {r['note']} |\n" for r in clean)
    text = ("# 扫描规则\n\n"
            "> 后台怎么盯项目里的文件变化（S1-8 S2-43）：走到哪扫到哪——你在看的、agent 在干的地方实时盯，别处有变动先记一笔，走进去再扫。\n"
            "> 下面是自定义的：一行一个文件夹（从项目根写），怎么扫只能是 一直盯着 / 走到才扫 / 不看；写了的文件夹连它下面全部都照这条，写得越细的越算数。"
            "网页「设置 → 扫描」改的就是这份。\n\n"
            f"兜底：每 {sweep} 分钟把记了有变动的冷地方扫一遍\n\n"
            "| 文件夹 | 怎么扫 | 备注 |\n|---|---|---|\n" + rows)
    f = _rules_path(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, f)
    return read_rules(p)


def migrate(conn, p: Project) -> None:
    """以前在「模块」表里设过的扫描方式（库里的 scan_modes）搬成规则，一次。"""
    import store
    old = store.scan_modes(conn)
    if not old or _rules_path(p).exists():
        return
    rules = [{"path": f"{p.materials.name}/{k}", "mode": "不看" if v == "只看最上一层" else "走到才扫", "note": f"原来设的「{v}」"}
             for k, v in old.items()]
    write_rules(p, 30, rules)


def rule_for(rules: list[dict], rel: str) -> dict | None:
    """这个路径照哪条规则：写得越细（路径越长）的越算数。"""
    rel = _norm(rel)
    hits = [r for r in rules if rel == r["path"] or rel.startswith(r["path"] + "/")]
    return max(hits, key=lambda r: len(r["path"])) if hits else None


def builtin_skip(p: Project, rel: str) -> bool:
    """自带的「不看」：.git、索引、缓存、.claude/worktrees、存档和回收站里面。"""
    parts = _norm(rel).split("/")
    if any(files._proj_skip(x) for x in parts):
        return True
    if parts[0] in files.SHALLOW and len(parts) > 2:
        return True
    return parts[0] == ".claude" and len(parts) > 1 and parts[1] == "worktrees"


def classify(p: Project, rel: str, rules: list[dict], hot: set[str]) -> str:
    """系统通知来的一个路径：skip（不理）· hot（马上扫）· cold（记账）。"""
    if builtin_skip(p, rel):
        return "skip"
    r = rule_for(rules, rel)
    if r and r["mode"] == "不看":
        return "skip"
    if (r and r["mode"] == "一直盯着") or structural(p, rel) or area_of(p, rel) in hot:
        return "hot"
    return "cold"


# ---------------------------------------------------------------- 设置页那棵勾选的树（S1-8 S2-44）

def how(p: Project, rules: list[dict], rel: str, is_dir: bool = False) -> dict:
    """这个文件夹 / 文件现在怎么扫、照的哪条：{mode, why, own（规则就写在它身上）, locked（自带的，勾不了）}。
    跟 classify 一个口径：不看 > 一直盯着（你设的）> 治理、自动化、笔记、核心自带一直盯着 > 走到才扫。"""
    rel = _norm(rel)
    parts = rel.split("/")
    if builtin_skip(p, rel):
        return {"mode": "不看", "why": "自带", "own": False, "locked": True}
    if parts[0] in files.SHALLOW:
        return {"mode": "只看最上一层", "why": "自带：里面是整份的副本", "own": False, "locked": True}
    r = rule_for(rules, rel)
    own = bool(r) and r["path"] == rel
    whose = ("你设的" + (f"：{r['note']}" if r["note"] else "") if own else f"跟着 {r['path']}") if r else ""
    if r and r["mode"] in ("不看", "一直盯着"):
        return {"mode": r["mode"], "why": whose, "own": own, "locked": False}
    if area_of(p, rel + "/_" if is_dir else rel) in ALWAYS:          # 文件夹按里面的东西算（「治理」这一格本身属于根目录那片）
        return {"mode": "一直盯着", "why": "自带" + ("（盖过你设的走到才扫）" if r else ""), "own": own, "locked": False}
    return {"mode": "走到才扫", "why": whose or "默认", "own": own, "locked": False}


def children(p: Project, rel: str, rules: list[dict], limit: int = 500) -> dict:
    """一个文件夹下面一层：文件夹在前、文件在后，每个带怎么扫。库、缓存这些不列；存档、回收站里面不往下展开。"""
    rel = _norm(rel)
    if ".." in rel.split("/"):
        raise ValueError("跑到项目外面去了")
    d = p.root / rel if rel else p.root
    if not d.is_dir():
        raise ValueError(f"「{rel}」不是文件夹")
    out = []
    try:
        entries = sorted(os.scandir(d), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError:
        entries = []
    for e in entries:
        path = f"{rel}/{e.name}" if rel else e.name
        if files._proj_skip(e.name) or e.is_symlink() or builtin_skip(p, path):
            continue
        is_dir = e.is_dir()
        h = how(p, rules, path, is_dir)
        out.append({"name": e.name, "path": path, "dir": is_dir, "open": is_dir and not h["locked"], **h})
        if len(out) >= limit:
            break
    return {"path": rel, "items": out, "more": len(out) >= limit}


def set_paths(p: Project, paths: list[str], mode: str, note: str = "") -> dict:
    """勾上的几个一起设成某种扫法；mode 空 = 去掉它们身上的自定义。存回 自动化/扫描规则.md。"""
    if mode and mode not in MODES:
        raise ValueError(f"怎么扫只能是 {' / '.join(MODES)}")
    cur = read_rules(p)
    keep = {r["path"]: r for r in cur["rules"]}
    for raw in paths:
        path = _norm(raw)
        if not path or ".." in path.split("/"):
            raise ValueError(f"「{raw}」不对")
        if builtin_skip(p, path) or path.split("/")[0] in files.SHALLOW:
            raise ValueError(f"「{path}」是自带的规矩，改不了")
        if mode:
            keep[path] = {"path": path, "mode": mode, "note": note or keep.get(path, {}).get("note", "")}
        else:
            keep.pop(path, None)
    return write_rules(p, cur["sweep"], sorted(keep.values(), key=lambda r: r["path"]))


# ---------------------------------------------------------------- 扫一片

def area_roots(p: Project, area: str) -> list[tuple[Path, bool]]:
    """这一片在硬盘上是哪几处：(路径, 往里钻不钻)。"""
    if area == CORE:
        return [(p.root / "backend", True)] + [(p.root / f, False) for f in CORE_FILES]
    if area == ROOT_AREA:
        return [(p.root, False)]
    if area == p.materials.name:                       # 资料/ 这一层：有哪些模块文件夹、散放的文件；模块里面各是各的片
        return [(p.materials, False)]
    return [(p.root / area, area not in files.SHALLOW)]


def walk_area(p: Project, area: str, rules: list[dict]) -> dict:
    """扫一片：{从项目根算的路径: (大小, 修改时间)}；文件夹也记一笔（「路径/」: (0, 0)），只认名字。"""
    out: dict = {}
    root = str(p.root)

    def add(path: str, st, is_dir: bool) -> None:
        rel = os.path.relpath(path, root).replace("\\", "/")
        out[rel + "/" if is_dir else rel] = (0, 0) if is_dir else (st.st_size, st.st_mtime_ns)

    def walk(d: str, deep: bool) -> None:
        try:
            entries = list(os.scandir(d))
        except OSError:
            return
        for e in entries:
            if files._proj_skip(e.name) or e.is_symlink():
                continue
            rel = os.path.relpath(e.path, root).replace("\\", "/")
            if builtin_skip(p, rel):
                continue
            r = rule_for(rules, rel)
            if r and r["mode"] == "不看":
                continue
            try:
                is_dir = e.is_dir()
                st = e.stat()
            except OSError:                               # 正被别的程序占着，下一回再看
                continue
            if area == ROOT_AREA and e.name in CORE_FILES + ("backend",):
                continue                                  # 根目录这一片：散文件和顶层文件夹的名字；核心程序是另一片
            add(e.path, st, is_dir)
            if is_dir and deep:
                walk(e.path, True)
    for path, deep in area_roots(p, area):
        if path.is_dir():
            walk(str(path), deep)
        elif path.is_file() and area != ROOT_AREA:
            try:
                add(str(path), path.stat(), False)
            except OSError:
                pass
    return out


def all_areas(p: Project) -> list[str]:
    """项目里现在有的每一片（启动时全盘走一遍用）。"""
    out = {CORE, ROOT_AREA}
    try:
        for e in os.scandir(p.root):
            if not e.is_dir() or files._proj_skip(e.name) or e.name == "backend":
                continue
            if e.name == p.materials.name:
                out.add(e.name)
                for m in os.scandir(e.path):
                    if m.is_dir() and not files._proj_skip(m.name):
                        out.add(f"{e.name}/{m.name}")
            elif not builtin_skip(p, e.name):
                out.add(e.name)
    except OSError:
        pass
    return sorted(out)


def part(snap: dict, p: Project, area: str) -> dict:
    """整份快照里属于这一片的那些。"""
    return {k: v for k, v in snap.items() if area_of(p, k.rstrip("/")) == area}


def files_only(snap: dict) -> dict:
    """给监管看的：只要文件（文件夹那几笔不要）。"""
    return {k: v for k, v in snap.items() if not k.endswith("/")}


# ---------------------------------------------------------------- 模块的数：扫完那一片留下的

def module_stats(p: Project, name: str) -> dict:
    """第二栏、设置页要的每个模块文件数、大小。后台在跑：用扫完留下的（没有才数一遍；冷的模块有变动先不重数，走进去再说）；
    没在跑（agent 那边的进程、没开后台）：现数。"""
    import project as proj
    st = state(p)
    if not st["on"]:
        return proj.module_stats(p, name)
    s = st["stats"].get(name)
    if s is None:
        s = st["stats"][name] = proj.module_stats(p, name)
    return s


def forget_stats(p: Project, areas: set[str] | None = None) -> None:
    """这几片扫出变化了：用到它们的模块数（自己那片、挂进来的链接落在这几片）作废，下回现数。None：全作废（网页那边写了东西）。"""
    import project as proj
    stats = state(p)["stats"]
    if areas is None:
        stats.clear()
        return
    for name in list(stats):
        mine = {f"{p.materials.name}/{name}"}
        try:
            mine |= {area_of(p, os.path.relpath(t, p.root)) for t in proj._targets(p, name)[1:]}
        except (OSError, ValueError):
            pass
        if mine & areas:
            stats.pop(name, None)


def dirty_of(p: Project, name: str) -> int:
    """这个模块记了几次有变动、还没扫。"""
    return state(p)["dirty"].get(f"{p.materials.name}/{name}", 0)


def visible(p: Project, rules: list[dict], rel: str) -> bool:
    """这个路径在不在看的范围里（自带的不看、自定义的不看都排掉）。"""
    if builtin_skip(p, rel):
        return False
    r = rule_for(rules, rel)
    return not (r and r["mode"] == "不看")


def rule_areas(p: Project, path: str) -> list[str]:
    """一条规则的文件夹碰到哪几片（写的是 资料 就是所有模块；写的是 资料/实验/输出 就是实验那片）。"""
    out = [a for a in all_areas(p) if a == path or a.startswith(path + "/") or path.startswith(a + "/")]
    return out or [area_of(p, path)]


def hot_areas(conn, p: Project, focus: list[tuple[str, str]], rules: list[dict] | None = None) -> dict[str, str]:
    """正在盯着的片 → 为什么（你在看 · 谁在干 · 一直盯着 · 你设的一直盯着）。"""
    why: dict[str, list[str]] = {}
    for view, module in focus:
        for a in focus_areas(p, view, module):
            why.setdefault(a, []).append("你在看")
    for a, who in agent_areas(conn, p).items():
        why.setdefault(a, []).append(f"{who} 在干" if a != CORE else f"{who} 拿着核心锁")
    for a in ALWAYS:
        why.setdefault(a, []).append("一直盯着")
    for r in rules or ():
        if r["mode"] == "一直盯着":
            for a in rule_areas(p, r["path"]):
                why.setdefault(a, []).append(f"你设的一直盯着（{r['path']}）")
    return {a: " · ".join(dict.fromkeys(w)) for a, w in why.items()}
