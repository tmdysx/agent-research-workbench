"""想法：人随口说的，一个口进来，每个都有去向。一张表 资料/想法/想法.md，编号 想-1、想-2…（号不回收）。

作者 2026-09-27：「我觉得蓝图戒律和想法，也就是把想法变成需求模块也要优化」。
一条线：想法（随口说的）→ 需求（功能 + 效果）→ 蓝图（要做的几件）→ 施工 → 交付 → 验收。
- 怎么进来：随堂笔记里点「是想法」· 想法页上直接记 · agent 在对话里听到的用 MCP add_idea 记（写原话、从哪来）
- 怎么变成需求：照「外部资料入口」那套——agent 给 1~3 个去向候选（suggest_requirement），每个带一句理由；人点一个：
  - 模块需求：新的一条，或补进已有的一条 → 直接写进那个模块的 需求.md（写上「来自 想-n」）
  - 模块戒律：新的一条 → 写进那个模块的 戒律.md
  - 总的那层（S0、S1、通用 / 项目戒律）：只标去向、放进问答请人亲自改——那两层是方向，不自动写
  - 放一放 / 不要：人点的，标上，留着不删
- 候选存在库里（跟外部资料入口一样）；想法和去向在文件里，人和 agent 都能直接看
"""
from __future__ import annotations

import json
import atomic
import os
import re
from datetime import datetime
from pathlib import Path

import project as proj
import requirements
import store
from project import Project

MODULE = "想法"
FILE = "想法.md"
WHOLE = "整个项目"
_ROW = re.compile(r"^\|\s*(想-(\d+))\s*\|")
TOPS = ("S0", "S1", "通用戒律", "项目戒律")          # 总的那层：只标去向，人亲自改
HEAD = """# 想法

> 你随口说的都记在这：一个想法一行，编号 想-n，号不回收。agent 给去向候选，你在网页「想法」里点一个；
> 变成需求、戒律的，那边写着「来自 想-n」。放一放、不要的也留着，不删。

| | 时间 | 想法 | 从哪来 | 关于 | 去向 |
|---|---|---|---|---|---|
"""


def _flat(s) -> str:
    return " ".join(str(s or "").replace("|", "／").split())


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _file(p: Project) -> Path:
    return p.materials / MODULE / FILE


def _write(f: Path, text: str) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    atomic.replace(tmp, f)


def state_of(dest: str) -> str:
    """去向 → 左栏的分组。"""
    d = dest.strip()
    if not d:
        return "待整理"
    for k in ("变成需求", "补进需求"):
        if d.startswith(k):
            return "变成了需求"
    if d.startswith("变成戒律"):
        return "变成了戒律"
    if d.startswith("等你改总的"):
        return "等你改总的"
    if d.startswith("放一放"):
        return "放一放"
    if d.startswith("不要"):
        return "不要"
    return "待整理"


GROUPS = ("待整理", "等你改总的", "变成了需求", "变成了戒律", "放一放", "不要")


def list_all(p: Project) -> list[dict]:
    f = _file(p)
    if not f.is_file():
        return []
    out = []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        c = _cells(line) + [""] * 6
        out.append({"code": m.group(1), "n": int(m.group(2)), "at": c[1], "text": c[2], "source": c[3],
                    "about": c[4] or WHOLE, "dest": c[5], "state": state_of(c[5])})
    return out


def get(p: Project, code: str) -> dict:
    x = next((i for i in list_all(p) if i["code"] == code), None)
    if x is None:
        raise store.Refused(f"没有想法 {code}")
    return x


def _about(p: Project, about: str) -> str:
    about = _flat(about) or WHOLE
    if about in (WHOLE, "整个", "总的", "项目"):
        return WHOLE
    if proj.module_dir(p, about) is None:
        raise store.Refused(f"没有「{about}」这个模块（关于写模块名，或「{WHOLE}」）")
    return about


def add(conn, p: Project, text: str, *, source: str = "自己写", about: str = WHOLE, by: str = "人") -> dict:
    text = _flat(text)
    if not text:
        raise store.Refused("想法是空的")
    about = _about(p, about)
    f = _file(p)
    with store.tx(conn):
        n = int(store._meta(conn, "idea_seq") or 0)
        n = max([n] + [x["n"] for x in list_all(p)]) + 1
        store._set_meta(conn, "idea_seq", str(n))
        code = f"想-{n}"
        body = f.read_text(encoding="utf-8") if f.is_file() else HEAD
        row = f"| {code} | {datetime.now():%Y-%m-%d %H:%M} | {text} | {_flat(source)} | {about} |  |"
        _write(f, body.rstrip("\n") + "\n" + row + "\n")
        store.log(conn, by, "记想法", code, text[:60])
    return get(p, code)


def _set_dest(p: Project, code: str, dest: str) -> None:
    f = _file(p)
    lines = f.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        m = _ROW.match(line)
        if m and m.group(1) == code:
            c = _cells(line) + [""] * 6
            c = c[:6]
            c[5] = _flat(dest)
            lines[i] = "| " + " | ".join(c) + " |"
            _write(f, "\n".join(lines))
            return
    raise store.Refused(f"没有想法 {code}")


# ---------------------------------------------------------------- 候选（agent 写，人点）

def candidates(conn, code: str) -> list[dict]:
    try:
        return json.loads(store._meta(conn, f"idea_cand:{code}") or "[]")
    except ValueError:
        return []


def _check(p: Project, c: dict) -> dict:
    to = _flat(c.get("to"))
    reason = _flat(c.get("reason"))
    if not reason:
        raise store.Refused("每个候选要写一句理由，让人一看就能判断")
    if to == "需求" and ('modules' in c or 'goals' in c):
        goals, modules = c.get('goals', []), c.get('modules', [])
        if not isinstance(goals, list) or not isinstance(modules, list) or not all(isinstance(x, str) for x in goals + modules):
            raise store.Refused('goals 和 modules 要写列表')
        if not _flat(c.get('func')) or not _flat(c.get('effect')):
            raise store.Refused('需求要写 func 和 effect')
        import governance
        governance.validate_links(p, goals, modules)
        return {'to': to, 'goals': goals, 'modules': modules, 'func': _flat(c['func']), 'effect': _flat(c['effect']), 'reason': reason}
    if to == "需求":
        m = _flat(c.get("module"))
        if proj.module_dir(p, m) is None or m in proj.TOOL_NAMES:
            raise store.Refused(f"需求要写进一个模块（不是想法、蓝图、戒律、源代码这几个工具模块）：没有「{m}」")
        req = _flat(c.get("req"))
        if req:                                                # 补进已有的一条
            r = requirements.read(p, m)
            if not r or req not in {q["code"] for q in r["reqs"]}:
                raise store.Refused(f"「{m}」的需求里没有 {req}")
            if not _flat(c.get("add")):
                raise store.Refused("补进已有的一条：add 写补什么")
            return {"to": to, "module": m, "req": req, "add": _flat(c["add"]), "reason": reason}
        if not _flat(c.get("func")) or not _flat(c.get("effect")):
            raise store.Refused("新需求要写 func（要什么功能）和 effect（要什么效果：打开能看见什么）")
        return {"to": to, "module": m, "func": _flat(c["func"]), "effect": _flat(c["effect"]), "reason": reason}
    if to == "戒律":
        m = _flat(c.get("module"))
        if proj.module_dir(p, m) is None:
            raise store.Refused(f"没有「{m}」这个模块")
        if not _flat(c.get("rule")):
            raise store.Refused("戒律要写 rule：不许做什么（一行）")
        return {"to": to, "module": m, "rule": _flat(c["rule"]), "reason": reason}
    if to == "总的":
        what = _flat(c.get("what"))
        if what not in TOPS:
            raise store.Refused(f"总的那层 what 写 {' / '.join(TOPS)} 之一")
        if not _flat(c.get("text")):
            raise store.Refused("写清想怎么改")
        return {"to": to, "what": what, "text": _flat(c["text"]), "reason": reason}
    raise store.Refused("to 写 需求 / 戒律 / 总的（放一放、不要由人点）")


def suggest(conn, p: Project, code: str, cands: list[dict], *, by: str) -> dict:
    get(p, code)
    if not 1 <= len(cands or []) <= 3:
        raise store.Refused("候选 1~3 个，把握大的在前")
    clean = [_check(p, c) for c in cands]
    with store.tx(conn):
        store._set_meta(conn, f"idea_cand:{code}", json.dumps(clean, ensure_ascii=False))
        store.log(conn, by, "想法候选", code, f"{len(clean)} 个")
    return get(p, code) | {"candidates": clean}


def describe(c: dict) -> str:
    """候选说成一句人话（网页和 agent 都用）。"""
    if c['to'] == '需求' and 'modules' in c:
        return f"项目新需求：{c['func']}——{c['effect']}（承接：{'、'.join(c['modules']) or '未分配模块'}）"
    if c["to"] == "需求" and c.get("req"):
        return f"补进「{c['module']}」{c['req']}：{c['add']}"
    if c["to"] == "需求":
        return f"「{c['module']}」新需求：{c['func']}——{c['effect']}"
    if c["to"] == "戒律":
        return f"「{c['module']}」新戒律：{c['rule']}"
    return f"改总的 {c['what']}：{c['text']}"


# ---------------------------------------------------------------- 人点了

def _add_rule(p: Project, module: str, rule: str, source: str) -> str:
    """模块戒律加一行，编号照这份里已有的前缀（文-1 → 文-9）；没有就用模块名的头一个字。"""
    f = __import__("governance_paths").resolve(p, f"资料/{module}/戒律.md", write=True)
    if not f.is_file():
        _write(f, f"# {module} · 模块戒律\n\n> 进「{module}」模块干活先读这份。只能比通用戒律、项目戒律更严。\n\n"
                  "| | 规矩 | 从哪来 |\n|---|---|---|\n")
    text = f.read_text(encoding="utf-8")
    codes = re.findall(r"^\|\s*([^|\s\d][^|\s]*)-(\d+)\s*\|", text, re.M)
    prefix = codes[0][0] if codes else module[0]
    n = max([int(x) for pre, x in codes if pre == prefix], default=0) + 1
    code = f"{prefix}-{n}"
    lines = text.rstrip("\n").split("\n")
    last = max((i for i, line in enumerate(lines) if re.match(r"^\|\s*[^|\s\d][^|\s]*-\d+\s*\|", line)
                or line.strip().startswith("|---")), default=len(lines) - 1)
    lines.insert(last + 1, f"| {code} | {_flat(rule)} | {source} |")
    _write(f, "\n".join(lines) + "\n")
    return code


def adopt(conn, p: Project, code: str, index: int, *, by: str = "人") -> dict:
    """人点了第几个候选：写进需求 / 戒律，或放进问答请人改总的。"""
    idea = get(p, code)
    cands = candidates(conn, code)
    if not 0 <= index < len(cands):
        raise store.Refused("没有这个候选")
    c = cands[index]
    src = f"来自 {code}（{requirements.stamp()}）"
    try:
        if c['to'] == '需求' and 'modules' in c:
            req = requirements.add_shared(p, c['func'], c['effect'], source=code, goals=c['goals'], modules=c['modules'])
            dest = f'变成需求：项目 {req}'
        elif c["to"] == "需求" and c.get("req"):
            requirements.supplement(p, c["module"], c["req"], c["add"], source=code)
            dest = f"补进需求：{c['module']} {c['req']}"
        elif c["to"] == "需求":
            req = requirements.add(p, c["module"], c["func"], c["effect"], source=code)
            dest = f"变成需求：{c['module']} {req}"
        elif c["to"] == "戒律":
            rc = _add_rule(p, c["module"], c["rule"], src)
            dest = f"变成戒律：{c['module']} {rc}"
        else:
            q = store.ask_human(conn, f"{code} 想改总的 {c['what']}：{c['text']}（{c['reason']}）", by=by,
                                context=f"想法原话：{idea['text']}")
            dest = f"等你改总的：{c['what']}（问答 {q['code']}）"
    except ValueError as e:
        raise store.Refused(str(e))
    with store.tx(conn):
        _set_dest(p, code, dest)
        store._set_meta(conn, f"idea_cand:{code}", "[]")
        store.log(conn, by, "想法去向", code, dest)
    return get(p, code)


def settle(conn, p: Project, code: str, dest: str, *, by: str = "人") -> dict:
    """人点「放一放」「不要」，或「重新整理」（去向清空）。"""
    if dest not in ("放一放", "不要", ""):
        raise store.Refused("只能是 放一放 / 不要 / 重新整理")
    get(p, code)
    with store.tx(conn):
        _set_dest(p, code, dest)
        store.log(conn, by, "想法去向", code, dest or "重新整理")
    return get(p, code)


def pending(p: Project, about: str | None = None) -> list[dict]:
    """还没定去向的；about 给了就只看关于它的。"""
    return [x for x in list_all(p) if x["state"] == "待整理" and (about is None or x["about"] == about)]
