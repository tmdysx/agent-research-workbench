"""读蓝图：资料/蓝图/ 里的目标金字塔（S0 终极目标 → S1-1… → 每份里的 S2），给总览、搜索和 agent 的全貌用。只读。

作者 2026-09-25：「像金字塔一样，有一个终极目标……是由上而下的一种蓝图」。
- 状态只在最底层（S2 那张表的最后一格）写；S1 的状态从它底下的 S2 现算，不手写（戒律 蓝-2）
- 09-22 那份 蓝图.json 已退休，留底在 资料/蓝图/旧蓝图（09-22）.json，不再读
- 坏一份不该让整页打不开：读不了、格式不对的，记进 problems，别的照常
- 自动化要的（作者 2026-09-27：「每一步资料手动准备好，然后再发动机器」）：S2 表可以多一列「怎么验」
  （`| | 做什么 | 怎么验 | 状态 |`，旧的三列表照样读）；S1 文件里一行「动到的模块：文献、论文」
- 状态由 agent 改（mark_goal、deliver）或人在网页上验收时改：只改那一格，别的一个字不动
- 分两层（作者 2026-09-27：「总蓝图是总蓝图，蓝图和戒律也是分层级的，现在是模块蓝图」）：
  总蓝图 = 资料/蓝图/ 的 S0、S1；模块蓝图 = 每个模块自己的 资料/<模块>/蓝图.md（照本模块需求要做的几件，
  表多一列「为了」写为了哪条需求：`| | 做什么 | 为了 | 怎么验 | 状态 |`）。模块蓝图的编号就是模块名：「文献」「文献 S2-3」
"""
from __future__ import annotations

import atomic
import os
import re
from pathlib import Path

from project import Project
import governance_paths as gp

STATUSES = ("ok", "warn", "todo", "bad")            # 做完 · 部分 · 在做 · 没做（以后、等着的也算没开始）
DIR = "蓝图"
MODULE_FILE = "蓝图.md"                                # 模块蓝图：资料/<模块>/蓝图.md

_FILE = re.compile(r"^(S\d+(?:-\d+)*)\s+(.+)\.md$")     # 「S1-3 说得准.md」
_ROW = re.compile(r"^\|\s*(S\d+(?:-\d+)+)\b[^|]*\|")    # 「| S2-1 | … | 做完 |」「| S1-1 看得懂 | … |」
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_REQ = re.compile(r"需-\d+")
_REF = re.compile(r"(?:([^、,，;；|\s:]+)(?:::|\s+))?(需-\d+)")   # 「项目 需-3」「项目::需-3」「%E9%A1%B9%E7%9B%AE::需-3」都认
STATES = ("做完", "在做", "等工具", "等你", "等", "部分", "大部分", "能用", "待你验收", "待验收", "没做", "没开始", "以后", "草稿")
# 「等 S2-3」「等 S1-8 S2-25」「等 工具 S2-5」：卡在那一件后面（S1-8 S2-35；作者 10-01 批的计划「等谁」，照三省六部、Paperclip 的「被谁卡着」）
_WAIT = re.compile(r"^等\s*(?:(S\d+-\d+|[^\s：:（(，,。、]+?)\s+)?(S2-\d+)(?!\d)")


def _need_refs(why: str) -> list[str]:
    """「为了」那一格里带来源的需求：统一写成 来源（网址编码）::需-3，跟 requirements.key 一样。"""
    from urllib.parse import quote, unquote
    return [quote(unquote(scope), safe="") + "::" + code for scope, code in _REF.findall(why or "") if scope]


def status_of(text: str) -> str:
    """S2 那一格写的字 → 四种状态。写「做完」开头的才算做完。"""
    t = text.strip()
    if t.startswith("做完"):
        return "ok"
    if t.startswith(("在做", "等工具", "等你")):              # 等工具、等你：在做，卡在人那边
        return "todo"
    if t.startswith(("部分", "大部分", "能用", "待你验收", "待验收")):   # agent 做完了但还没人验：算「不够」，不算做完（通-7）
        return "warn"
    return "bad"


def rollup(kids: list[str]) -> str:
    """S1 的状态从底下的 S2 算：全做完才算做完；有在做的算在做；做了一部分算不够；一个没动算没开始。"""
    if not kids:
        return "bad"
    if all(k == "ok" for k in kids):
        return "ok"
    if "todo" in kids:
        return "todo"
    if any(k in ("ok", "warn") for k in kids):
        return "warn"
    return "bad"


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _read(f: Path, problems: list[str]) -> str | None:
    try:
        return f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:          # Windows 上编辑器存盘那一瞬间可能锁着：这次跳过，下次再读
        problems.append(f"资料/{DIR}/{f.name} 暂时读不了：{e}")
        return None


def _subs(lines: list[str]) -> list[dict]:
    """S2 表：按表头认列（做什么 · 为了 · 怎么验 · 状态），没表头的旧表按位置读（三列 / 四列）。"""
    subs, col = [], {}
    for line in lines:
        if line.lstrip().startswith("|") and not _ROW.match(line):
            head = _cells(line)
            if "做什么" in head:                              # 表头：记下每列在哪
                col = {k: next((i for i, h in enumerate(head) if k in h), None) for k in ("做什么", "为了", "怎么验")}
            continue
        m = _ROW.match(line)
        c = _cells(line) if m else []
        if len(c) < 3:
            continue
        get = lambda k, d: c[col[k]] if col.get(k) is not None and col[k] < len(c) - 1 else d
        what = get("做什么", c[1])
        how = get("怎么验", c[2] if len(c) >= 4 and not col else "")
        why = get("为了", "")
        refs = _need_refs(why)
        subs.append({"code": m.group(1), "what": what, "how": how, "for": _REQ.findall(why), **({"need_refs": refs} if refs else {}),
                     "text": c[-1], "status": status_of(c[-1])})
    return subs


def _goal(f: Path, code: str, name: str, text: str, file: str = "", kind: str = "S1") -> dict:
    lines = text.splitlines()
    bold = next((m.group(1) for line in lines if not line.startswith(">") and (m := _BOLD.search(line))), "")   # 引用块里的「草稿」不算
    done_when = next((line.split("：", 1)[1].strip() for line in lines if line.startswith(("怎么算做到：", "怎么算装好："))), "")
    mods = next((line.split("：", 1)[1] for line in lines if line.startswith("动到的模块：")), "")
    mods = re.sub(r"[（(][^）)]*[）)]", "", mods)       # 「所有模块（插件在文件上加按钮）」：括号里是说明
    final = next((line.split("：", 1)[1].strip() for line in lines if line.startswith("规划：")), "")   # 「规划：定稿 · 日期 · 作者原话」
    subs = _subs(lines)
    st = [s["status"] for s in subs]
    return {"code": code, "name": name, "one_line": bold.rstrip("。"), "done_when": done_when,
            "modules": [x for x in re.split(r"[、,，\s]+", mods.strip().rstrip("。")) if x] if kind == "S1" else [code],
            "file": file or f"资料/{DIR}/{f.name}", "kind": kind, "status": rollup(st), "final": final if final.startswith("定稿") else "",
            "done": st.count("ok"), "total": len(st), "subs": subs}


def module_goals(p: Project, problems: list[str] | None = None) -> list[dict]:
    """每个模块自己的蓝图（资料/<模块>/蓝图.md）；编号就是模块名。"""
    import project as proj
    out = []
    for name, f in sorted(gp.records(p, "任务").items()):
        if not f.is_file() or (name == DIR and not gp.relative(p, f).startswith("治理/")):   # 旧的 资料/蓝图/ 里放的是总蓝图，不是「蓝图」模块自己的任务
            continue
        text = _read(f, problems if problems is not None else [])
        if text is None:
            continue
        g = _goal(f, name, name, text, file=gp.relative(p, f), kind="module")
        req = gp.resolve(p, f"资料/{name}/需求.md")               # 一句话：优先用需求里那句「装成什么样」
        if req.is_file():
            try:
                b = next((m for line in req.read_text(encoding="utf-8").splitlines()
                          if not line.startswith(">") and (m := _BOLD.search(line))), None)
                if b:
                    g["one_line"] = b.group(1).rstrip("。")
            except (OSError, UnicodeDecodeError):
                pass
        out.append(g)
    return out


def waits_on(goal: str, text: str) -> str:
    """这件卡在哪一件后面：「等 S2-3」→「<本目标> S2-3」，「等 S1-8 S2-25」→「S1-8 S2-25」；等你、等工具这种 → 空。"""
    m = _WAIT.match((text or "").strip())
    return f"{m.group(1) or goal} {m.group(2)}" if m else ""


def is_done(bp: dict, key: str) -> bool:
    """「S1-8 S2-25」「工具 S2-5」那一件做完了没（找不到也算没做完）。"""
    goal, _, sub = key.rpartition(" ")
    g = find(bp, goal)
    x = next((s for s in g["subs"] if s["code"] == sub), None) if g else None
    return bool(x) and x["status"] == "ok"


def find(bp: dict, code: str) -> dict | None:
    """按编号找目标：总蓝图的 S1，或模块蓝图（模块名）。"""
    return next((g for g in bp["goals"] + bp.get("modules", []) if g["code"] == code), None)


def pyramid(p: Project) -> dict:
    """{s0, goals[], counts, problems}。goals 是 S1 那一层（按编号排），每个带底下的 S2（subs）；counts 数的是 S2。"""
    d = p.materials / DIR
    out = {"s0": None, "goals": [], "modules": [], "counts": {s: 0 for s in STATUSES}, "problems": []}
    if not gp.goal_files(p):
        out["modules"] = module_goals(p, out["problems"])
        return out
    files = []
    for f in gp.goal_files(p):
        m = _FILE.match(f.name) if f.is_file() else None
        if m:
            files.append((m.group(1), m.group(2), f))
    files.sort(key=lambda x: [int(n) for n in re.findall(r"\d+", x[0])])
    listed: list[str] = []
    for code, name, f in files:
        text = _read(f, out["problems"])
        if text is None:
            continue
        if code == "S0":
            bold = _BOLD.search(text)
            listed = [m.group(1) for line in text.splitlines() if (m := _ROW.match(line))]
            out["s0"] = {"code": "S0", "name": name, "one_line": bold.group(1).rstrip("。") if bold else "",
                         "file": gp.relative(p, f)}
        elif code.count("-") == 1:                      # S1-x；更深的层单独成文件的，以后再说
            g = _goal(f, code, name, text, file=gp.relative(p, f))
            out["goals"].append(g)
            for s in g["subs"]:
                out["counts"][s["status"]] += 1
    out["modules"] = module_goals(p, out["problems"])
    have = [g["code"] for g in out["goals"]]
    if have and out["s0"] is None:
        out["problems"].append(f"资料/{DIR}/ 里有 S1，没有 S0 终极目标")
    if listed:                                           # S0 那张表跟 S1 的文件对一下账
        out["problems"] += [f"S0 里列了 {c}，资料/{DIR}/ 里找不到它那一份" for c in listed if c not in have]
        out["problems"] += [f"{c} 有文件，S0 的表里没列它" for c in have if c not in listed]
    return out


def big_problems(p: Project) -> list[dict]:
    """S0 里「两个大问题」那张表 → [{big, small, to: [S1 编号或模块名]}]；大问题那格空着 = 跟上一行同一个（作者 10-01 定的两个大问题）。"""
    f = next((f for f in gp.goal_files(p) if f.name.startswith("S0 ")), None)
    text = _read(f, []) if f else None
    out, on, big = [], False, ""
    for line in (text or "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else None
        if cells and cells[0] == "大问题":
            on = True
            continue
        if not on:
            continue
        if cells is None:
            if out:
                break
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        big = cells[0] or big
        to = [x for x in re.split(r"[、,，]", cells[2] if len(cells) > 2 else "") if x.strip()]
        out.append({"big": big, "small": cells[1] if len(cells) > 1 else "",
                    "to": [re.match(r"(S\d+-\d+)", x.strip()).group(1) if re.match(r"S\d+-\d+", x.strip()) else x.strip() for x in to]})
    return out


def lint(p: Project) -> list[dict]:
    """格式检查：照 治理/格式说明.md 看，读不懂的行写清哪个文件、第几行、哪里不对。不改文件。"""
    out = []
    bp = pyramid(p)
    for g in bp["goals"] + bp.get("modules", []):
        f = gp.resolve(p, g["file"])
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        if g.get("kind") != "module" and not any(_BOLD.search(x) for x in lines if not x.startswith(">")):
            out.append({"file": g["file"], "code": g["code"], "line": 0, "text": "没有一句话（**……**）"})
        n = 0
        for i, line in enumerate(lines, 1):
            if line.startswith("|") and "做什么" in line:
                n = len(line.strip().strip("|").split("|"))
            elif _ROW.match(line) and n and line.lstrip("| ").startswith("S2-"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) != n:
                    out.append({"file": g["file"], "code": g["code"], "line": i, "text": f"第 {i} 行：{cells[0]} 有 {len(cells)} 格，表头是 {n} 格"})
                elif not cells[-1]:
                    out.append({"file": g["file"], "code": g["code"], "line": i, "text": f"第 {i} 行：{cells[0]} 没写状态"})
                elif not cells[-1].startswith(STATES):
                    out.append({"file": g["file"], "code": g["code"], "line": i, "text": f"第 {i} 行：{cells[0]} 的状态「{cells[-1][:12]}」认不出（写 没做 / 在做 / 做完 / 以后……）"})
    covered = {t for b in big_problems(p) for t in b["to"]}
    if covered:
        out += [{"file": bp["s0"]["file"] if bp["s0"] else "", "code": g["code"], "line": 0, "text": f"{g['code']} 没挂到哪个大问题（S0「两个大问题」表）"}
                for g in bp["goals"] if g["code"] not in covered]
    return out


def search(p: Project, q: str, limit: int = 30) -> list[dict]:
    """全站检索用：目标和 S2 里带这几个字的。"""
    bp, q, hits = pyramid(p), q.strip().lower(), []
    for g in bp["goals"] + bp["modules"]:
        if q in f"{g['name']} {g['one_line']} {g['done_when']}".lower():
            hits.append({"kind": "蓝图", "code": g["code"], "text": f"{g['name']}：{g['one_line']}"})
        for s in g["subs"]:
            if q in f"{s['what']} {s['text']}".lower():
                hits.append({"kind": "蓝图", "code": f"{g['code']} {s['code']}", "text": f"{s['what']}（{s['text']}）"})
    return hits[:limit]


def set_status(p: Project, goal: str, sub: str, text: str) -> str:
    """改蓝图里一件 S2 的状态（那张表最后一格）；返回原来写的。找不到抛 ValueError（消息给人看）。"""
    d = p.materials / DIR
    f = None
    if gp.goal_files(p):
        f = next((x for x in gp.goal_files(p) if x.is_file() and (m := _FILE.match(x.name)) and m.group(1) == goal), None)
    if f is None and goal and not goal.startswith("S") and gp.resolve(p, f"资料/{goal}/{MODULE_FILE}").is_file():
        f = gp.resolve(p, f"资料/{goal}/{MODULE_FILE}", write=True)                  # 模块蓝图：「文献 S2-3」
    if f is None:
        raise ValueError(f"蓝图里没有 {goal}")
    lines = f.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        m = _ROW.match(line)
        if m and m.group(1) == sub:
            c = _cells(line)
            if len(c) < 3:
                break
            old, c[-1] = c[-1], " ".join(text.replace("|", "／").split())
            lines[i] = "| " + " | ".join(c) + " |"
            tmp = f.with_suffix(".md.tmp")
            tmp.write_text("\n".join(lines), encoding="utf-8")
            atomic.replace(tmp, f)
            return old
    raise ValueError(f"{goal} 里没有 {sub}")
