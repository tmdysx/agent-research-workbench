"""模块需求：这个模块要有什么功能、要什么效果——决定往哪施工。一个模块一份 资料/<模块>/需求.md。

作者 2026-09-27：「我觉得除了蓝图和戒律还有需求，因为我们要在这个模块上达到什么样的功能和效果，这决定了施工的方向」。
- 一条线：想法 → 需求 → 蓝图（要做的几件）→ 施工（开工单）→ 交付 → 人对着需求验收
- 需求表 `| 需-1 | 要什么功能 | 要什么效果 | 来自 |`；**只有作者能改**（从想法里点过来的也算作者点的）
- 需求不写状态：从本模块蓝图里「为了」写着它的那几件现算——都做完 = 达到；有在做的 = 在做；一件都没有 = 还没有要做的件
- 模块蓝图（资料/<模块>/蓝图.md）照需求写要做的几件，见 blueprint.py
"""
from __future__ import annotations

import atomic
import os
import hashlib
import re
from datetime import datetime
from pathlib import Path

import blueprint
import governance_paths as gp
import project as proj
from project import Project

FILE = "需求.md"
_ROW = re.compile(r"^\|\s*(需-(\d+))\s*\|")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_S1 = re.compile(r"S\d+-\d+")
STATE = {"ok": "达到", "todo": "在做", "warn": "做了一部分", "bad": "还没做", "none": "还没有要做的件"}

NEED_TEMPLATE = """# {m} · 需求

> 这个模块要有什么功能、要什么效果——决定往哪施工。只有作者能改；不写状态，从本模块蓝图里为它做的几件现算。

**（一句话：这个模块要装成什么样）**

为了：（总蓝图里的哪几件，写 S1 编号，比如 S1-1、S1-4）

原话：
- （你的原话，带日期）

| | 要什么功能 | 要什么效果（打开能看见什么） | 来自 |
|---|---|---|---|
"""

PLAN_TEMPLATE = """# {m} · 蓝图

> 照本模块需求要做的几件。每件写为了哪条需求、怎么验；agent 可以提（状态写「没做」），作者点头。状态只在最后一格。

怎么算装好：需求里每一条都达到。

| | 做什么 | 为了 | 怎么验 | 状态 |
|---|---|---|---|---|
"""


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _flat(s) -> str:
    return " ".join(str(s or "").replace("|", "／").split())


def path(p: Project, module: str) -> Path:
    return gp.resolve(p, f"资料/{module}/{FILE}")


def read(p: Project, module: str) -> dict | None:
    """需求.md → {module, file, one_line, for: [S1…], reqs: [{code, func, effect, source}]}；没有这份就是 None。"""
    f = path(p, module)
    if not f.is_file():
        return None
    try:
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    lines = text.splitlines()
    bold = next((m.group(1) for line in lines if not line.startswith(">") and (m := _BOLD.search(line))), "")   # 引用块里的「草稿」不算
    why = next((line.split("：", 1)[1] for line in lines if line.startswith("为了：")), "")
    col, reqs = {}, []
    for line in lines:
        m = _ROW.match(line)
        if not m:
            if line.lstrip().startswith("|"):
                head = _cells(line)
                if any("功能" in h for h in head):
                    col = {k: next((i for i, h in enumerate(head) if k in h), None) for k in ("功能", "效果", "来自", "关联目标", "承接模块")}
            continue
        c = _cells(line)
        get = lambda k, i: c[col[k]] if col.get(k) is not None and col[k] < len(c) else (c[i] if i < len(c) else "")
        row = {"code": m.group(1), "n": int(m.group(2)), "func": get("功能", 1), "effect": get("效果", 2), "source": get("来自", 3)}
        for key, header in (("goal_refs", "关联目标"), ("module_refs", "承接模块")):
            if col.get(header) is not None:
                row[key] = get(header, 99)
        reqs.append(row)
    return {"module": module, "file": gp.relative(p, f), "one_line": bold.rstrip("。"),
            "for": _S1.findall(why), "reqs": reqs}


def modules(p: Project) -> list[str]:
    """有治理记录的实际模块；需求来源不是虚构的新模块。"""
    from governance import module_catalog, normalize_module
    available = {x['key'] for x in module_catalog(p)}
    found = set(gp.records(p, '需求')) | set(gp.records(p, '任务'))
    for q in catalog(p):
        found.update(normalize_module(p, x) for x in q['modules'])
    return sorted((found & available) - set(proj.TOOL_NAMES))


def view(p: Project, module: str, bp: dict | None = None) -> dict:
    """需求 + 模块蓝图，每条需求达到没有、哪几件在为它做；蓝图里没写「为了」的几件单列。"""
    bp = bp or blueprint.pyramid(p)
    if gp.active(p):
        return shared_view(p, module, bp)
    r = read(p, module)
    g = blueprint.find(bp, module)
    subs = g["subs"] if g else []
    reqs = []
    for q in (r["reqs"] if r else []):
        items = [s for s in subs if q["code"] in s["for"]]
        st = blueprint.rollup([s["status"] for s in items]) if items else "none"
        reqs.append(q | {"items": [s["code"] for s in items], "status": st, "state": STATE[st]})
    codes = {q["code"] for q in reqs}
    return {"module": module, "need": r, "plan": g, "reqs": reqs,
            "loose": [s["code"] for s in subs if not s["for"]],                     # 没写为了哪条需求的
            "unknown": sorted({c for s in subs for c in s["for"] if c not in codes}),   # 写了、需求里却没有的
            "met": sum(1 for q in reqs if q["status"] == "ok"), "total": len(reqs),
            "done": g["done"] if g else 0, "items": g["total"] if g else 0,
            "has_need": r is not None, "has_plan": g is not None}


def _write(f: Path, text: str) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    atomic.replace(tmp, f)


def skeleton(p: Project, module: str) -> list[str]:
    """给一个模块建空的 需求.md、蓝图.md（已有的不动）。返回建了哪些。"""
    d = proj.module_dir(p, module)
    if d is None:
        raise ValueError(f"没有「{module}」这个模块")
    made = []
    for name, tpl in ((FILE, NEED_TEMPLATE), (blueprint.MODULE_FILE, PLAN_TEMPLATE)):
        f = gp.resolve(p, f"资料/{module}/{name}", write=True)
        if not f.exists():
            _write(f, tpl.format(m=module))
            made.append(gp.relative(p, f))
    return made


def add(p: Project, module: str, func: str, effect: str, source: str = "") -> str:
    """加一条需求（接在表的最后）；返回编号 需-n（号不回收：比表里最大的大一）。"""
    if proj.module_dir(p, module) is None:
        raise ValueError(f"没有「{module}」这个模块")
    if not _flat(func) or not _flat(effect):
        raise ValueError("需求要写清要什么功能、要什么效果")
    f = path(p, module)
    if not f.is_file():
        skeleton(p, module)
        f = path(p, module)
    text = f.read_text(encoding="utf-8")
    r = read(p, module)
    code = f"需-{max([q['n'] for q in r['reqs']], default=0) + 1}"
    row = f"| {code} | {_flat(func)} | {_flat(effect)} | {_flat(source)} |"
    lines = text.rstrip("\n").split("\n")
    last = max((i for i, line in enumerate(lines) if _ROW.match(line) or line.strip().startswith("|---")), default=None)
    if last is None:
        lines += ["", "| | 要什么功能 | 要什么效果（打开能看见什么） | 来自 |", "|---|---|---|---|", row]
    else:
        lines.insert(last + 1, row)
    _write(f, "\n".join(lines) + "\n")
    return code


def supplement(p: Project, module: str, code: str, text: str, source: str = "") -> str:
    """往已有的一条需求里补一句（补在「效果」那格后面），来源也记上。"""
    f = path(p, module)
    if not f.is_file():
        raise ValueError(f"「{module}」还没有需求")
    if not _flat(text):
        raise ValueError("要写补什么")
    lines = f.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        m = _ROW.match(line)
        if m and m.group(1) == code:
            c = _cells(line)
            while len(c) < 4:
                c.append("")
            c[2] = (c[2] + "；" if c[2] else "") + f"补：{_flat(text)}"
            if source:
                c[3] = "、".join(x for x in (c[3], _flat(source)) if x)
            lines[i] = "| " + " | ".join(c) + " |"
            _write(f, "\n".join(lines))
            return code
    raise ValueError(f"「{module}」的需求里没有 {code}")


def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def key(scope, code):
    from urllib.parse import quote
    return quote(scope, safe='') + '::' + code


def task_refs(g, s):
    refs = s.get('need_refs', s.get('for', []))
    return [r if '::' in r else key(g['code'], r) for r in refs]


def _refs(raw):
    if re.search(r'我猜|猜的|待确认|待你确认|等你定|比如|例如', raw):
        return []
    return [v.strip() for v in re.split(r'[、,，;；]', raw) if v.strip() and v.strip() not in ('未分配', '未关联', '无', '—')]


def catalog(p, bp=None):
    bp = bp or blueprint.pyramid(p)
    gs = bp['goals'] + bp.get('modules', [])
    out = []
    for scope, f in sorted(gp.records(p, '需求').items()):
        r = read(p, scope)
        if not r:
            continue
        text = f.read_text(encoding='utf-8')
        why = next((l.split('：', 1)[1] for l in text.splitlines() if l.startswith('为了：')), '')
        mods = next((l.split('：', 1)[1] for l in text.splitlines() if l.startswith('承接模块：')), None)
        for q in r['reqs']:
            ident = key(scope, q['code'])
            tasks = [dict(s, goal=g['code'], file=g['file'], key=g['code'] + '::' + s['code']) for g in gs for s in g['subs'] if ident in task_refs(g, s)]
            goals_raw = q.get('goal_refs', why)
            goals = re.findall(r'\bS1-\d+\b', goals_raw) if _refs(goals_raw) else []
            modules = _refs(q['module_refs']) if 'module_refs' in q else (_refs(mods) if mods is not None else ([] if scope == '项目' else [scope]))
            st = blueprint.rollup([s['status'] for s in tasks]) if tasks else 'none'
            pending = any(s['text'].startswith(('待你验收', '待验收')) for s in tasks)
            out.append(q | {'key': ident, 'revision': hashlib.sha256(f.read_bytes()).hexdigest(), 'scope': scope, 'file': r['file'], 'goals': list(dict.fromkeys(goals)), 'modules': modules,
                            'relation_note': goals_raw if goals_raw and not _refs(goals_raw) else '',
                            'tasks': tasks, 'items': [s['key'] for s in tasks], 'status': st, 'state': '待你验收' if pending else STATE[st]})
    return out


def shared_view(p, module, bp=None):
    bp = bp or blueprint.pyramid(p)
    reqs = [q for q in catalog(p, bp) if module in q['modules'] or (proj.module_dir(p, module) is None and q['scope'] == module)]
    g = blueprint.find(bp, module)
    tasks = [s for q in reqs for s in q['tasks']]
    codes = {q['key'] for q in catalog(p, bp)}
    subs = g['subs'] if g else []
    return {'module': module, 'need': read(p, module), 'plan': g, 'reqs': reqs,
            'loose': [s['code'] for s in subs if not s['for']],
            'unknown': sorted({r for s in subs for r in task_refs(g, s) if r not in codes}),
            'met': sum(q['status'] == 'ok' for q in reqs), 'total': len(reqs),
            'done': g['done'] if g else len({s['key'] for s in tasks if s['status'] == 'ok'}),
            'items': g['total'] if g else len({s['key'] for s in tasks}),
            'has_need': bool(reqs) or read(p, module) is not None, 'has_plan': g is not None or bool(tasks)}


def add_shared(p, func, effect, source='', goals=None, modules=None):
    """项目需求先于模块；关联列显式留空就表示尚未分配。"""
    if not _flat(func) or not _flat(effect):
        raise ValueError('需求要写清问题或功能、要达到的效果')
    f = p.root / gp.ROOT / '需求' / '项目.md'
    if not f.exists():
        _write(f, '# 项目需求\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n')
    r = read(p, '项目')
    code = '需-' + str(max([q['n'] for q in r['reqs']], default=0) + 1)
    text = f.read_text(encoding='utf-8').rstrip() + '\n'
    _write(f, text + '| ' + ' | '.join([code, _flat(func), _flat(effect), _flat(source), '、'.join(goals or []), '、'.join(modules or [])]) + ' |\n')
    return code


def assign(p, ident, goals, modules, *, conn=None, revision=None):
    """人设置既有需求的关联，保持原需求文字、编号和来源。"""
    q = next((q for q in catalog(p) if q['key'] == ident), None)
    if q is None:
        raise ValueError('找不到这条需求')
    f = gp.resolve(p, q['file'])
    lines = f.read_text(encoding='utf-8').splitlines()
    header = next((i for i, l in enumerate(lines) if l.startswith('|') and '功能' in l and '效果' in l), None)
    if header is None:
        raise ValueError('需求表缺少表头')
    cols = _cells(lines[header])
    old_count = len(cols)
    for c in ('关联目标', '承接模块'):
        if c not in cols:
            cols.append(c)
    lines[header] = '| ' + ' | '.join(cols) + ' |'
    for i in range(header + 1, len(lines)):
        if not lines[i].strip().startswith('|'):
            continue
        cells = _cells(lines[i])
        if all(re.fullmatch(r':?-+:?', c) for c in cells):
            lines[i] = '|' + '|'.join(['---'] * len(cols)) + '|'
            continue
        row = next((x for x in catalog(p) if x['scope'] == q['scope'] and x['code'] == cells[0]), None)
        if row is None:
            continue
        cells += [''] * (len(cols) - len(cells))
        for c, field, values in (('关联目标', 'goals', goals), ('承接模块', 'modules', modules)):
            idx = cols.index(c)
            if cells[0] == q['code']:
                cells[idx] = '、'.join(values)
            elif idx >= old_count:
                cells[idx] = '、'.join(row[field])
        lines[i] = '| ' + ' | '.join(cells) + ' |'
    result_text = '\n'.join(lines) + '\n'
    if conn is not None:
        import governance
        current = governance.read_document(p, gp.relative(p, f))
        governance.save_document(conn, p, gp.relative(p, f), result_text, revision if revision is not None else current['revision'], by='人', reason='设置需求关联')
    else:
        _write(f, result_text)
    return next(q for q in catalog(p) if q['key'] == ident)
