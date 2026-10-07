"""开工单上「用到的」每一样一盏灯：全绿（或只剩黄）人才能交给 agent。程序现算，不用 agent。

作者 2026-09-27：「自动化的要求有点高，必须每一个模块都得准备好都是绿色的……每一步资料手动准备好」。
- 灯：ok 绿（好了）· warn 黄（能转，建议补）· bad 红（要补，交不出去）
- 按一张开工单算（workorders）：目标里那几件 S2 写没写怎么验、单上列的戒律 / 模块 / 工具 / 材料 / 存档在不在、通没通……
- 每条检查写清查了什么、缺什么，带一个「去补」的地方（网页地址），人手动补好，灯自己变绿
- 09-27 一条线 想法 → 需求 → 蓝图 → 戒律（作者：「我们现在这个自动化是模块装修的自动化」）：目标可以是一个模块
  （「文献」整个、「文献 需-2」为这条需求做的几件、「文献 S2-3」一件），多两行灯：想法（这个模块还有没定去向的）、
  需求（写了没有、每条有没有效果、有没有要做的件）；戒律四层自动算：通用 · 项目 · 模块 · 这张单的「不许」
"""
from __future__ import annotations

import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import blueprint
import governance_paths as gp
import project as proj
import snapshot
import tools
from project import Project

ORDER = ("ideas", "reqs", "blueprint", "rules", "modules", "tools", "materials", "plans", "saves", "agent")
NAMES = {"ideas": ("想法", "Ideas"), "reqs": ("需求", "Needs"), "blueprint": ("蓝图", "Blueprint"), "rules": ("戒律", "Rules"), "modules": ("模块", "Modules"),
         "tools": ("工具", "Tools"), "materials": ("材料", "Materials"), "plans": ("计划", "Plans"),
         "saves": ("存档", "Snapshots"), "agent": ("Agent", "Agent")}
_RANK = {"ok": 0, "warn": 1, "bad": 2}
_S2 = re.compile(r"S2-(\d+)")
_S2_RANGE = re.compile(r"S2-(\d+)\s*[~～—–-]\s*S2-(\d+)")
_TGT = re.compile(r"^(.+?)(?:\s+((?:S2|需)-\d+))?$")


def _mod_href(name: str, file: str = "") -> str:
    return "#/m/" + name + (f"?f={file}" if file else "")


def split_target(s: str) -> tuple[str, str]:
    """「S1-10」→ (S1-10, "")；「文献 S2-3」→ (文献, S2-3)；「文献 需-2」→ (文献, 需-2)。"""
    m = _TGT.match(" ".join((s or "").split()))
    return (m.group(1), m.group(2) or "") if m else ("", "")


def scope_items(bp: dict, scope: list[str], p=None) -> tuple[list[tuple[dict, dict]], list[str]]:
    """开工单的目标 → [(目标, 一件)…]，外加找不到的。整个目标、一条需求：只算没做完、不是「以后」的；点名的一件照算。"""
    out, unknown, seen = [], [], set()

    def put(g, x):
        if (g["code"], x["code"]) not in seen:
            seen.add((g["code"], x["code"]))
            out.append((g, x))
    live = lambda x: x["status"] != "ok" and not x["text"].startswith("以后")
    for s in scope:
        code, sub = split_target(s)
        g = blueprint.find(bp, code)
        if p is not None and sub.startswith('需-'):
            import requirements
            q = next((q for q in requirements.catalog(p, bp) if q['scope'] == code and q['code'] == sub), None)
            if q:
                for t in q['tasks']:
                    owner = blueprint.find(bp, t['goal'])
                    item = next(s for s in owner['subs'] if s['code'] == t['code'])
                    if live(item):
                        put(owner, item)
                continue
        if g is None:
            unknown.append(s)
            continue
        if not sub:
            for x in g["subs"]:
                if live(x):
                    put(g, x)
        elif sub.startswith("需-"):
            for x in g["subs"]:
                if sub in x.get("for", []) and live(x):
                    put(g, x)
        else:
            x = next((x for x in g["subs"] if x["code"] == sub), None)
            if x is None:
                unknown.append(s)
            else:
                put(g, x)
    return out, unknown


def target_goals(bp: dict, scope: list[str]) -> list[dict]:
    """目标里点到的每个目标（S1 或模块），不管底下还有没有没做完的。"""
    out = []
    for s in scope:
        g = blueprint.find(bp, split_target(s)[0])
        if g and g not in out:
            out.append(g)
    return out


def rule_stack(p: Project, wo: dict) -> list[dict]:
    """一张单要守的戒律，从上到下四层：通用 · 项目（每张都守，去不掉）· 模块（单上的模块自己的，自动带上）· 另加的 · 这张单的「不许」。"""
    out = []
    d = p.materials / "戒律"
    for layer, pre in (("通用", "1 "), ("项目", "2 ")):
        f = next((f for f in gp.rule_files(p) if f.name.startswith(pre)), None)
        out.append({"layer": layer, "file": gp.relative(p, f) if f else "AGENTS.md", "fixed": True,
                    "exists": bool(f) or (p.root / "AGENTS.md").is_file()})
    auto = {x["file"] for x in out} | {"AGENTS.md"}
    for m in wo.get("modules") or []:
        rel = gp.relative(p, gp.module_rule(p, m))
        auto.add(rel)
        out.append({"layer": "模块", "module": m, "file": rel, "auto": True, "exists": gp.resolve(p, rel).is_file()})
    for x in wo.get("rules") or []:
        if x not in auto:
            out.append({"layer": "另加", "file": x, "exists": gp.resolve(p, x).is_file()})
    no = ((wo.get("notes") or {}).get("不许") or "").strip()
    if no:
        out.append({"layer": "这张单", "text": no, "exists": True})
    return out


def _covered_by_plans(p: Project) -> set[tuple[str, str]]:
    """计划/ 里每份 P 开头那几行写了为了哪几件 S2（「S1-2 · P2 · 目标：S1-2 记得住（S2-9 ~ S2-12）」）。"""
    out: set[tuple[str, str]] = set()
    mods = set(proj.module_dirs(p))
    for rel, f in gp.plan_files(p).items():
        parts = rel.split('/')
        if len(parts) != 2 or not f.name.startswith('P'):
            continue
        m = re.match(r'(S\d+-\d+)\b', parts[0])
        if not m and parts[0].split(' ')[0] in mods:
            m = re.match(r'(\S+)', parts[0])
        if not m:
            continue
        try:
            head = '\n'.join(f.read_text(encoding='utf-8', errors='replace').splitlines()[:6])
        except OSError:
            continue
        nums = {int(x) for x in _S2.findall(head)}
        for a, b in _S2_RANGE.findall(head):
            nums |= set(range(int(a), int(b) + 1))
        out |= {(m.group(1), f'S2-{n}') for n in nums}
    return out


def _last_agent(conn) -> str | None:
    r = conn.execute("SELECT MAX(at) FROM event WHERE actor LIKE 'agent%'").fetchone()
    return r[0] if r else None


def _claude_cli() -> str | None:
    hit = shutil.which("claude")
    if hit:
        return hit
    npm = Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"
    return str(npm) if npm.is_file() else None


def _device(key: str, checks: list[dict], ok_text: str) -> dict:
    lamp = max((c["lamp"] for c in checks), key=lambda x: _RANK[x], default="ok")
    bad = [c["text"] for c in checks if c["lamp"] != "ok"]
    return {"key": key, "name": NAMES[key][0], "en": NAMES[key][1], "lamp": lamp,
            "summary": ok_text if lamp == "ok" else "；".join(bad[:2]) + ("……" if len(bad) > 2 else ""),
            "checks": checks}


STOP = re.compile(r"必停|只在[^。\n]{0,8}停|通-15")         # AGENTS.md 里写了在哪几件事上停
ALL_MODULES = ("所有模块", "全部模块")


def why_red(pnl: dict) -> str:
    """红灯的原因，一句话一条：哪盏灯 · 缺什么（给 agent 和人看，不用翻代码）。"""
    return "；".join(f"{d['name']}：" + "、".join(c["text"] for c in d["checks"] if c["lamp"] == "bad")
                     for d in pnl["devices"] if d["lamp"] == "bad")


def _c(lamp: str, text: str, go: str = "") -> dict:
    return {"lamp": lamp, "text": text, "go": go}


def _path_href(x: str) -> str:
    x = x.replace("\\", "/")
    if x == "AGENTS.md":
        return "#/m/戒律"
    if x.startswith("治理/"):
        return "#/m/蓝图?f=" + quote("@/" + x, safe="")
    parts = x.split("/")
    if parts[0] == "资料" and len(parts) >= 2:
        return _mod_href(parts[1], "/".join(parts[2:]))
    return "#/plans" if parts[0] == "计划" else ""


def _req_href(m: str) -> str:
    return "#/m/" + m + "?f=" + quote("#需求:" + m, safe="")


def panel(conn, p: Project, wo: dict, *, all_plans: list[dict] | None = None) -> dict:
    """wo：一张开工单（workorders 读出来的）。没列的东西按目标提醒（S1 的「动到的模块」、S2 里提到的工具）。"""
    import ideas
    import requirements
    bp = blueprint.pyramid(p)
    target = wo.get("target") or []
    items, unknown = scope_items(bp, target, p)
    goals = []
    for g, _ in items:
        if g not in goals:
            goals.append(g)
    mgoals = [g for g in target_goals(bp, target) if g.get("kind") == "module"]
    mnames = [split_target(x)[0] for x in target]
    mods_t = [m for m in mnames if not re.match(r"S\d", m) and (proj.module_dir(p, m) or m in {x["key"] for x in __import__("governance").module_catalog(p)})]   # 目标里点名的模块
    dev = {}

    # 想法：这个模块还有没定去向的（黄）——交给 agent 前看一眼，别漏了你想要的
    c = []
    for m in mods_t:
        n = len(ideas.pending(p, about=m))
        if n:
            c.append(_c("warn", f"「{m}」还有 {n} 个想法没定去向（交给 agent 前看一眼）", "#/m/想法"))
    dev["ideas"] = _device("ideas", c, "、".join(mods_t) + " 没有待整理的想法" if mods_t else "目标不是模块，不看")

    # 需求：写了没有、每条有没有「要什么效果」、有没有在为它做的件；蓝图里每件写没写「为了」
    c = []
    for m in mods_t:
        v = requirements.view(p, m, bp)
        href = _req_href(m)
        if not v["has_need"]:
            c.append(_c("bad", f"「{m}」还没写需求（资料/{m}/需求.md）", href))
            continue
        c += [_c("bad", f"{m} {q['code']} 没写要什么效果", href) for q in v["reqs"] if not q["effect"]]
        empty = [q["code"] for q in v["reqs"] if q["status"] == "none"]
        if empty:
            c.append(_c("warn", f"{m} {'、'.join(empty)} 还没有要做的件", href))
        if v["loose"]:
            c.append(_c("warn", f"{m} 蓝图里 {'、'.join(v['loose'][:4])}{'……' if len(v['loose']) > 4 else ''} 没写为了哪条需求", href))
        if v["unknown"]:
            c.append(_c("warn", f"{m} 蓝图里写了为了 {'、'.join(v['unknown'])}，需求里没有", href))
        if not v["reqs"]:
            c.append(_c("bad", f"「{m}」的需求表是空的", href))
    selected_reqs = [q for q in requirements.catalog(p, bp) if f"{q['scope']} {q['code']}" in target or any(q['key'] in requirements.task_refs(g, x) for g, x in items)]
    for q in selected_reqs:
        if not q['effect']:
            c.append(_c('bad', q['scope'] + ' ' + q['code'] + ' 缺验收标准', '#/m/蓝图'))
        if not q['tasks']:
            c.append(_c('bad', q['scope'] + ' ' + q['code'] + ' 尚无承接任务', '#/m/蓝图'))
    nreq = sum(requirements.view(p, m, bp)["total"] for m in mods_t) if mods_t else 0
    dev["reqs"] = _device("reqs", c, f"{nreq} 条需求，都有要做的件" if mods_t else "总蓝图的目标：需求就是 S1 本身")

    # 蓝图：选了目标、蓝图里找得到；S0 在；这次的 S1 写了怎么算做到；这次的每件 S2 写了怎么验
    c = [_c("ok", "S0 终极目标在", _mod_href("蓝图")) if bp["s0"] else _c("bad", "还没有 S0 终极目标", _mod_href("蓝图"))]
    if not target:
        c.append(_c("bad", "还没选目标（蓝图里的 S1，或几件 S2）", ""))
    for u in unknown:
        m = split_target(u)[0]
        if proj.module_dir(p, m) and not gp.resolve(p, f"资料/{m}/{blueprint.MODULE_FILE}").is_file():
            c.append(_c("bad", f"「{m}」还没写蓝图（资料/{m}/蓝图.md）", _req_href(m)))
        else:
            c.append(_c("bad", f"蓝图里找不到：{u}", _mod_href("蓝图")))
    for g in goals + [g for g in mgoals if g not in goals]:
        fname = g["file"].split("/")[-1]
        gh = _req_href(g["code"]) if g.get("kind") == "module" else _mod_href("蓝图", fname)
        word = "怎么算装好" if g.get("kind") == "module" else "怎么算做到"
        c.append(_c("ok", f"{g['code']} 写了{word}", gh) if g["done_when"]
                 else _c("warn", f"{g['code']} 没写「{word}：」（每件的怎么验写了就能开工，09-30 放宽）", gh))
        miss = [x["code"] for gg, x in items if gg is g and not x["how"]]
        if miss:
            c.append(_c("bad", f"{g['code']} 的 {'、'.join(miss)} 没写怎么验", gh))
    if target and not items and not unknown:
        c.append(_c("warn", "目标里的都做完了，没有要做的", ""))
    dev["blueprint"] = _device("blueprint", c, f"{len(items)} 件都写了怎么验" if items else "S0 在")

    # 模块：单上列的都在；S1 写了「动到的模块」、单上漏了的提醒
    listed = wo.get("modules") or []
    c = []
    for g in goals:
        if not g["modules"] and g.get("kind") != "module":
            c.append(_c("warn", f"{g['code']} 没写「动到的模块：」", _mod_href("蓝图", g["file"].split("/")[-1])))
        miss = [m for m in g["modules"] if m not in listed]
        if miss:
            c.append(_c("warn", f"{g['code']} 写了动到「{'、'.join(miss)}」，单上没列", ""))
    for raw in listed:
        m = re.sub(r"[（(].*$", "", raw).strip()          # 「所有模块（插件在文件上加按钮）」：括号里是说明，不是名字
        if m in ALL_MODULES:
            c.append(_c("ok", f"动到{m}", ""))
            continue
        c.append(_c("ok", f"「{m}」在", _mod_href(m)) if (proj.module_dir(p, m) or m in {x["key"] for x in __import__("governance").module_catalog(p)})
                 else _c("bad", f"没有「{m}」这个模块（资料/{m}/）", "#/settings"))
    dev["modules"] = _device("modules", c, "、".join(listed) + " 都在" if listed else "这次不动模块")

    # 戒律：AGENTS.md 和「在哪几件事上停」那条在（「必停」或 09-30 放宽后的「只在两类事上停」、通-15）；单上列的戒律文件都在；要动的模块有自己的戒律
    agents = p.root / "AGENTS.md"
    text = agents.read_text(encoding="utf-8", errors="replace") if agents.is_file() else ""
    c = [_c("ok", "AGENTS.md 在，写了在哪几件事上停", "#/m/戒律") if STOP.search(text)
         else _c("bad", "AGENTS.md 不在" if not text else "AGENTS.md 里没写在哪几件事上停（通-15）：这条要人写", "#/m/戒律")]
    stack = rule_stack(p, wo)
    for r in stack:
        if r["layer"] in ("通用", "项目") and not r["exists"]:
            c.append(_c("warn", f"没有{r['layer']}戒律（资料/戒律/）", "#/m/戒律"))
        elif r["layer"] == "模块" and not r["exists"]:
            c.append(_c("warn", f"「{r['module']}」模块没有自己的戒律（资料/{r['module']}/戒律.md）", _mod_href(r["module"])))
        elif r["layer"] == "另加" and not r["exists"]:
            c.append(_c("bad", f"找不到 {r['file']}", _path_href(r["file"])))
    words = [r["layer"] if r["layer"] != "模块" else r["module"] for r in stack if r["exists"] and r["layer"] != "这张单"]
    dev["rules"] = _device("rules", c, " · ".join(words))

    # 工具：单上列的、技术栈、这次写到的都要通；「待你装」的要装
    tool_lib = p.root / "工具库"
    cards = tools.list_tools(tool_lib)
    have = {t["code"] for t in cards}
    mention = " ".join(f"{g['one_line']} {x['what']} {x['how']}" for g, x in items) + " " + " ".join(
        f"{q['func']} {q['effect']}" for m in mods_t for q in (requirements.read(p, m) or {"reqs": []})["reqs"])
    named = set(re.findall(r"T\d+", mention)) | set(wo.get("tools") or [])

    def used(t: dict) -> bool:
        return t["code"] in named or bool(t["name"] and t["name"] in mention)
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = dict(zip([t["code"] for t in cards], ex.map(lambda t: tools.check_cached(t["code"], lib=tool_lib), cards)))
    c = [_c("bad", f"工具库里没有 {x} 这张卡", "#/tools") for x in (wo.get("tools") or []) if x not in have]
    for t in cards:
        r = res[t["code"]]
        if t["state"] == "待你装":                      # 这次要用的：红；这次不用的：黄，不挡着
            c.append(_c("warn", f"{t['code']} {t['name']} 待你装（agent 可以自己装：只从官方来源，装了记日志；09-30 放宽）", "#/tools?t=" + t["code"]))
        elif t.get("manual") and not t["check"]:
            c.append(_c("bad" if used(t) or t["kind"] == "技术栈" else "warn",
                        f"{t['code']} {t['name']} 未检查（尚未配置检查）", "#/tools?t=" + t["code"]))
        elif r.get("ok") is False:
            c.append(_c("bad" if used(t) or t["kind"] == "技术栈" else "warn",
                        f"{t['code']} {t['name']} 没接通：{r.get('msg', '')}", "#/tools?t=" + t["code"]))
        elif r.get("ok") is not True and t["check"]:
            c.append(_c("bad" if used(t) or t["kind"] == "技术栈" else "warn",
                        f"{t['code']} {t['name']} 未检查：{r.get('msg', '')}", "#/tools?t=" + t["code"]))
    good = sum(1 for t in cards if t["state"] != "待你装" and not (t.get("manual") and not t["check"])
               and (res[t["code"]].get("ok") is True or (not t["check"] and res[t["code"]].get("ok") is None)))
    dev["tools"] = _device("tools", c, f"{good}/{len(cards)} 接通")

    # 材料：单上列的文件都在
    mats = wo.get("materials") or []
    c = [_c("bad", f"找不到 {m}", _path_href(m)) for m in mats if not gp.resolve(p, m).exists()]
    dev["materials"] = _device("materials", c, f"{len(mats)} 样都在" if mats else "没列材料")

    # 计划：每件都有计划（没有也能转：agent 先写，档 1 你点头）
    have_p = _covered_by_plans(p)
    miss = [f"{g['code']} {x['code']}" for g, x in items if (g["code"], x["code"]) not in have_p]
    c = [_c("warn", f"{len(miss)} 件还没有计划（{'、'.join(miss[:4])}{'……' if len(miss) > 4 else ''}）：agent 先写"
            + ("，你点头" if wo.get("level", 1) == 1 else ""), "#/plans")] if miss else []
    dev["plans"] = _device("plans", c, f"{len(items)} 件都有计划" if items else "没有要做的")

    # 存档：单上写了哪档就查那档定没定性；没写就要有一档定性过的（出事回得去）
    saves = snapshot.list_saves(p)
    by_code = {m["code"]: m for m in saves}
    listed_s = wo.get("saves") or []
    c = []
    for code in listed_s:
        m = by_code.get(code)
        if m is None:
            c.append(_c("bad", f"没有存档 {code}", "#/saves"))
        elif not m.get("settled"):
            c.append(_c("warn", f"{code}「{m['name']}」没定性（开工前 agent 自己存一档全量；09-30 放宽）", "#/saves?c=" + code))
    settled = [m for m in saves if m.get("settled")]
    if not listed_s and not settled:
        c.append(_c("warn", "还没有定性过的存档（开工前 agent 自己存一档全量；09-30 放宽）", "#/saves"))
    ok_s = next((by_code[x] for x in listed_s if x in by_code), None) or (settled[0] if settled else None)
    dev["saves"] = _device("saves", c, f"{ok_s['code']}「{ok_s['name']}」已定性" if ok_s else "")

    # Agent：装了、连上过
    last = _last_agent(conn)
    cli = _claude_cli()
    mcp = p.root / ".mcp.json"
    if not mcp.is_file() or "research-console" not in mcp.read_text(encoding="utf-8", errors="replace"):
        c = [_c("bad", "项目里没有 .mcp.json（写着 research-console）：agent 连不上这个工具", "")]
    elif last:
        c = []
    elif cli:
        c = [_c("warn", "Claude Code 装了，还没连上过（第一次跑会连）", "")]
    else:
        c = [_c("bad", "没找到 Claude Code（或别的 agent）：先装一个", "")]
    dev["agent"] = _device("agent", c, f"上次连上 {last.replace('T', ' ')[5:16]}" if last else "")

    # Supplied records belong to this request, including an intentionally empty list.
    if all_plans is None:
        all_plans = __import__("governance").plan_records(p)
    devices = [dev[k] for k in ORDER]
    red = [d["name"] for d in devices if d["lamp"] == "bad"]
    return {"devices": devices, "ready": not red, "red": red,
            "green": sum(1 for d in devices if d["lamp"] == "ok"), "total": len(devices),
            "items": [{"goal": g["code"], "code": x["code"], "what": x["what"], "how": x["how"], "text": x["text"],
                       "for": x.get("for", []), "status": x["status"]} for g, x in items],
            "rules": stack, "requirements": selected_reqs, "plans": [x for x in all_plans if set(x["goals"]) & {g["code"] for g, t in items} or set(x["modules"]) & set(wo.get("modules", []))]}
