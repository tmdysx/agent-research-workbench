"""蓝图全景：从已有文件和记录读取目标、模块的明确关联与状态，网页和 MCP 共用。"""
from __future__ import annotations

import re

import blueprint
import deliveries
import files
import requirements
import workorders
from project import Project, FIXED_NAMES, GOVERNANCE_NAMES

_TENTATIVE = re.compile(r"我猜|猜的|等你定|待确认|待你确认|比如|例如")

# 通用层是应用已有的操作入口，不是某个项目的资料目录。稳定 key 防止与同名 DIY 模块串线。
COMMON = (
    ("search", "全站检索", "Search", "#/search"),
    ("notes", "笔记本", "Notebook", "#/notes"),
    ("inbox", "外部资料入口", "Intake", "#/inbox"),
    ("plans", "计划", "Plans", "#/plans"),
    ("qa", "问答", "Q&A", "#/qa"),
    ("auto", "自动化", "Automation", "#/auto"),
    ("saves", "存档", "Snapshots", "#/saves"),
    ("skills", "技能库", "Skills", "#/skills"),
    ("tools", "工具库", "Tools", "#/tools"),
    ("commands", "快捷指令", "Commands", "#/commands"),
    ("settings", "设置", "Settings", "#/settings"),
    ("guide", "使用说明", "Guide", "#/guide"),
    ("trash", "回收站", "Cleanup", "#/trash"),
)
# 内置模块自己的需求、任务文件名（治理/需求/工具.md、治理/任务/工具.md）：装修过的内置模块挂上它们（工具 S2-1）
COMMON_FILES = {"tools": "工具", "guide": "使用说明"}   # 使用说明 10-02 起草了需求、任务（等作者定稿）
LAYERS = (("common", "通用操作层", "General operations"),
          ("shared", "项目交集层", "Project governance"),
          ("business", "DIY 业务层", "DIY workloads"))


def _text(p: Project, path: str) -> str:
    try:
        return __import__("governance_paths").resolve(p, path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _field(text: str, name: str) -> str:
    # 兼容计划开头的一行元数据（包括旧的 > 引用格式），不扫描正文猜关系。
    for line in text.splitlines()[:30]:
        m = re.search(r"(?:^|[·>])\s*" + re.escape(name) + r"[：:]\s*(.*)", line)
        if m:
            return re.split(r"\s*·\s*[^·：:]+[：:]", m.group(1), maxsplit=1)[0].strip()
    return ""


def _names(value: str) -> list[str]:
    value = re.sub(r"（[^）]*）|\([^)]*\)", "", value)
    return [x.strip("。` ") for x in re.split(r"[、,，·\s]+", value) if x.strip("。` ")]


def phase(s: dict) -> str:
    if s["text"].startswith(("待你验收", "待验收")):
        return "pending"
    return {"ok": "done", "todo": "doing", "warn": "partial", "bad": "todo"}[s["status"]]


def _counts(subs: list[dict]) -> dict:
    return {key: sum(phase(s) == key for s in subs) for key in ("done", "pending", "doing", "partial", "todo")}


def build(p: Project, bp: dict, modules: list[dict], pending: list[dict], save: dict | None) -> dict:
    goals = {g["code"]: dict(g, related_modules=[], counts=_counts(g["subs"])) for g in bp["goals"]}
    mods = {}
    module_blueprints = {g["code"]: g for g in bp["modules"]}
    for m in modules:
        name = m["name"]
        need = requirements.read(p, name)
        g = module_blueprints.get(name)
        # 蓝图模块自己的蓝图就是 S0/S1 文件，不要求重复造一份 蓝图.md。
        plan_files = ([bp["s0"]["file"]] if bp["s0"] else []) + [x["file"] for x in bp["goals"]] if name == "蓝图" else ([g["file"]] if g else [])
        mods[name] = dict(m, key=name, kind="project", layer="shared" if name in GOVERNANCE_NAMES else "business",
                          goals=[], need=need, blueprint=g, blueprint_files=plan_files,
                          has_need=need is not None, has_blueprint=bool(plan_files), relation_notes=[], plans=[], tasks=[])
    mods = dict(sorted(mods.items(), key=lambda kv: GOVERNANCE_NAMES.index(kv[0]) if kv[0] in GOVERNANCE_NAMES else len(GOVERNANCE_NAMES)))
    folder_names = list(mods)
    for ident, name, en, href in COMMON:
        key = "common:" + ident
        own = COMMON_FILES.get(ident)
        need = requirements.read(p, own) if own else None
        g = module_blueprints.get(own) if own else None
        mods[key] = dict(key=key, name=name, en=en, href=href, kind="common", layer="common", goals=[],
                         need=need, blueprint=g, blueprint_files=[g["file"]] if g else [], has_need=need is not None,
                         has_blueprint=bool(g), relation_notes=[], plans=[], tasks=[])
    alias = {own: "common:" + ident for ident, own in COMMON_FILES.items()}

    def module_key(name):
        if name in mods:
            return name
        # 裸名优先保留旧的目录语义；显式「通用/名字」可区分同名 DIY 模块。
        return next((m["key"] for m in mods.values() if m["kind"] == "common"
                     and name in (m["name"], "通用/" + m["name"])), name)

    def module_names(raw):
        names = _names(raw)
        expanded = []
        for name in names:
            if name == "所有模块":
                expanded += folder_names                # 不改变历史记录中「所有模块」的目录语义
            elif name == "所有通用模块":
                expanded += [m["key"] for m in mods.values() if m["kind"] == "common"]
            else:
                expanded.append(module_key(name))
        return list(dict.fromkeys(expanded))
    relations, problems = {}, []

    def connect(code, name, source, field):
        if code not in goals or name not in mods:
            problems.append(f"{source} 的{field}引用了不存在的{'目标 ' + code if code not in goals else '模块 ' + name}")
            return
        key = code, name
        relations.setdefault(key, {"goal": code, "module": name, "sources": []})["sources"].append({"file": source, "field": field})

    for code, g in goals.items():
        raw = _field(_text(p, g["file"]), "动到的模块")
        if _TENTATIVE.search(raw):
            problems.append(f"{g['file']} 的模块关联待确认：{raw}")
            continue
        for name in module_names(raw):
            connect(code, name, g["file"], "动到的模块")
    for name, m in mods.items():
        if not m["need"]:
            continue
        raw = _field(_text(p, m["need"]["file"]), "为了")
        if _TENTATIVE.search(raw):
            m["relation_notes"].append(f"目标关联待确认：{raw}")
            continue
        for code in dict.fromkeys(re.findall(r"\bS1-\d+\b", raw)):
            connect(code, name, m["need"]["file"], "为了")
    plans = []
    for group in files.plans(p):
        for item in group.get("children", [group]):
            if not re.fullmatch(r"P\d+", item["code"]):
                continue
            text = _text(p, item["path"])
            owner = item["goal"].split(" ", 1)[0]
            goal_codes = [code for code in re.findall(r"\bS1-\d+\b", _field(text, "目标")) if code in goals]
            if owner in goals:
                goal_codes.append(owner)
            raw = _field(text, "动到的模块")
            names = [] if _TENTATIVE.search(raw) else module_names(raw)
            if item["goal"] in mods:
                names.append(item["goal"])
            plan_goals = list(dict.fromkeys(goal_codes))
            plan_modules = [n for n in dict.fromkeys(names) if n in mods]
            plans.append(dict(item, goals=plan_goals, modules=plan_modules))
            # 项目的计划约定明确用「目标 · 动到的模块」连接两边，只认元数据，不认正文提及。
            for code in plan_goals:
                for name in plan_modules:
                    connect(code, name, item["path"], "目标 / 动到的模块")
    plans.sort(key=lambda x: (x["date"], x["mtime"], x["path"]), reverse=True)
    for code, name in relations:
        goals[code]["related_modules"].append(name)
        mods[name]["goals"].append(code)
    goal_order = {code: i for i, code in enumerate(goals)}
    for m in mods.values():
        m["goals"].sort(key=goal_order.__getitem__)
    for code, g in goals.items():
        g["plans"] = [x for x in plans if code in x["goals"]]
    for name, m in mods.items():
        m["plans"] = [x for x in plans if name in x["modules"]]
        m["missing"] = (["缺需求"] if not m["has_need"] else []) + (["缺蓝图"] if not m["has_blueprint"] else []) + (["未关联"] if not m["goals"] else [])
        if m["kind"] == "common":
            m["missing"] = ["未关联"] if not m["goals"] else []
        if m["need"] and not m["need"]["reqs"]:
            m["missing"].append("需求未列条目")
        if m["blueprint"] and not m["blueprint"]["subs"]:
            m["missing"].append("蓝图未列任务")
        # 本模块任务与支撑目标下的任务分开标明归属，不暗示每个 S2 都分配给这个模块。
        m["tasks"] = [dict(s, goal=name, source="模块蓝图") for s in (m["blueprint"] or {}).get("subs", [])]
        m["goal_tasks"] = [dict(s, goal=code, source="支撑目标") for code in m["goals"] for s in goals[code]["subs"]]

    import governance
    import governance_paths as gp
    reqs = governance.catalog(p, bp)
    for q in reqs:
        for name in [alias.get(x, x) for x in q['modules']]:
            if name not in mods:
                mods[name] = dict(key=name, name=name, en='', kind='unavailable', layer='business', goals=[], need=None, blueprint=None,
                                  blueprint_files=[], has_need=False, has_blueprint=False, relation_notes=[], plans=[], tasks=[], goal_tasks=[], missing=['承接模块不可用'])
            for code in q['goals']:
                if code in goals:
                    connect(code, name, q['file'], q['scope'] + ' ' + q['code'])
                    if name not in goals[code]['related_modules']:
                        goals[code]['related_modules'].append(name)
                    if code not in mods[name]['goals']:
                        mods[name]['goals'].append(code)
    for m in mods.values():
        m['requirements'] = [q for q in reqs if m['key'] in [alias.get(x, x) for x in q['modules']]]
        if m['requirements']:
            m['has_need'] = True
            m['missing'] = [x for x in m['missing'] if x not in ('缺需求', '需求未列条目')]
        if m['goals']:
            m['missing'] = [x for x in m['missing'] if x != '未关联']
        if m['kind'] == 'common' and not m['requirements']:
            m['missing'] += ['缺需求']
    for g in goals.values():
        g['requirements'] = [q for q in reqs if g['code'] in q['goals']]
    problems += gp.problems(p)
    orders = workorders.list_all(p)
    js = deliveries.list_all(p)
    return {"s0": bp["s0"], "goals": list(goals.values()), "modules": list(mods.values()),
            "layers": [{"key": key, "name": name, "en": en, "modules": [m["key"] for m in mods.values() if m["layer"] == key]}
                       for key, name, en in LAYERS],
            "relations": list(relations.values()), "problems": problems, "requirements": reqs, "unassigned": [q for q in reqs if not q["modules"]],
            "counts": _counts([s for g in bp["goals"] for s in g["subs"]]),
            "status": {"running": [dict(code=w["code"], name=w["name"], state=w["stored"], target=w["target"], modules=w["modules"]) for w in orders if w["stored"] == "在跑"],
                       "pending": pending, "deliveries": [j for j in js if j["state"] == "待你验收"], "save": save}}
