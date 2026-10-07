"""自动化看板（S1-8 S2-28～S2-31）：任务看板四列、一件的详情（为什么那条链）、总览四张图的数。

作者 10-01：「我感觉我那个自动化看板太乱了，我想向他这个项目学习一下看板设计和框架」「我觉得看板和图表都得优化一下」；
10-02「就这样做」（照 Paperclip 改的样图 治理/计划/S1-8 转得起来/R2）。
- 全是现算的：蓝图里的件、认领、交付单、监管记录；不另存一份
- 四列：能做（没做完、没人领、不在等）· 在做（有人领着，或状态写在做）· 等着（等工具 / 等你 / 待你验收 / 等别的件）· 做完；「以后」的单放一边
- 为什么那条链：S0 一句话 → 哪个大问题 → 目标 / 模块的一句话和「怎么算做到」→ 为了的需求原文 → 这件
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import blueprint
import claims
from project import Project

WAITS = ("等工具", "等你", "待你验收", "待验收", "等 ", "等S", "等")
COLS = ("能做", "在做", "等着", "等验收", "做完")


def _need_index(p: Project, bp: dict) -> dict:
    """需求编号 → 原文：「项目::需-3」「文献::需-2」两种 key。"""
    import requirements
    out = {}
    for q in requirements.catalog(p, bp):
        out[q["key"]] = {"scope": q["scope"], "code": q["code"], "func": q.get("func", ""), "effect": q.get("effect", "")}
    return out


def _needs_of(g: dict, x: dict, idx: dict) -> list[dict]:
    from urllib.parse import quote
    keys = list(x.get("need_refs") or [])
    keys += [quote(g["code"], safe="") + "::" + c for c in x.get("for", [])]
    seen, out = set(), []
    for k in keys:
        q = idx.get(k)
        if q and k not in seen:
            seen.add(k)
            out.append(q)
    return out


def items(conn, p: Project, bp: dict | None = None) -> list[dict]:
    """蓝图里每一件一张卡：在哪一列、谁领着、领了多久、为了哪几条需求、哪张交付单。"""
    import deliveries
    import dispatch
    import agents
    import construction_plans
    plans = construction_plans.listing(p)
    roster = agents.list_all(p)
    bp = bp or blueprint.pyramid(p)
    rows = {r["code"]: r for r in dispatch.plan_status(p)}
    held = {(r["goal"], r["sub"]): r for r in claims.active(conn) if r["goal"] != claims.CORE}
    blocking = {}                                         # 谁卡在谁后面：「S1-8 S2-25」→ [等它的那几件]
    for g in bp["goals"] + bp.get("modules", []):
        for x in g["subs"]:
            dep = blueprint.waits_on(g["code"], x["text"]) if x["status"] != "ok" else ""
            if dep:
                blocking.setdefault(dep, []).append(f"{g['code']} {x['code']}")
    js = {}
    for j in deliveries.list_all(p):                      # 新的在前：每件留最新那张
        js.setdefault((j["goal"], j["sub"]), j)
    idx = _need_index(p, bp)
    out = []
    for g in bp["goals"] + bp.get("modules", []):
        r = rows.get(g["code"], {})
        for x in g["subs"]:
            t, c, j = x["text"], held.get((g["code"], x["code"])), js.get((g["code"], x["code"]))
            dep = blueprint.waits_on(g["code"], t)
            if x["status"] == "ok":
                col = "做完"
            elif t.startswith("以后"):
                col = "以后"
            elif c or t.startswith("在做"):
                col = "在做"
            elif t.startswith(("待验收", "待你验收")):         # 交了、等验收的 agent 或你验（S1-8 S2-39）
                col = "等验收"
            elif dep:                                     # 卡在别的件后面：那件做完了就回到「能做」
                col = "能做" if blueprint.is_done(bp, dep) else "等着"
            elif t.startswith(WAITS):
                col = "等着"
            else:
                col = "能做"
            out.append({"key": f"{g['code']} {x['code']}", "goal": g["code"], "goal_name": g["name"], "kind": g.get("kind", "S1"), "code": x["code"],
                        "what": x["what"], "how": x["how"], "text": t, "col": col, "group": r.get("group") or ("模块" if g.get("kind") == "module" else ""),
                        "final": bool(g.get("final")), "needs": [f"{q['scope']} {q['code']}" if q["scope"] != g["code"] else q["code"] for q in _needs_of(g, x, idx)],
                        "who": c["agent"].replace("agent:", "") if c else "", "since": c["since"] if c else "", "idle": c["idle"] if c else 0,
                        "j": j["code"] if j else "", "j_state": j["state"] if j else "", "j_at": j["at"] if j else "",
                        "j_by": (j["by"] or "").replace("agent:", "") if j else "", "file": g["file"],
                        "wait_on": dep, "blocking": blocking.get(f"{g['code']} {x['code']}", [])})
            card = out[-1]
            ps = [z for z in plans if z['goal'] == g['code'] and z['sub'] == x['code']]
            if c:
                ps = [z for z in ps if z['by'] == agents.actor(c['agent'])]
            selected = max(ps, key=lambda z: (z.get('updated', ''), int(z['code'][2:])), default=None)
            if selected:
                valid = bool(construction_plans.approved(p, g['code'], x['code'], selected['by']))
                selected = dict(selected, valid=valid,
                                display_state='失效' if selected['state'] == construction_plans.OK and not valid else selected['state'],
                                approved_files=selected['files'] if valid else [])
            card['execution_plan'] = selected
            card['eligible'] = [{'code': a['code'], 'name': a['name'], 'allowed': '干活' in agents.jobs(a) and not agents.allows_reason(a,g,x),
                                 'reason': agents.allows_reason(a,g,x) or ('' if '干活' in agents.jobs(a) else '岗位不承担施工')} for a in roster]
    return out


def _rules(p: Project, g: dict) -> list[dict]:
    """这件守哪几份戒律：通用 · 项目（每件都守）· 它所在模块的（S1 就是它动到的模块）。"""
    import governance_paths as gp
    out = []
    for layer, pre in (("通用", "1 "), ("项目", "2 ")):
        f = next((f for f in gp.rule_files(p) if f.name.startswith(pre)), None)
        if f:
            out.append({"layer": layer, "file": gp.relative(p, f)})
    for m in [g["code"]] if g.get("kind") == "module" else list(g.get("modules") or []):
        f = gp.module_rule(p, m)
        if f.is_file():
            out.append({"layer": "模块 " + m, "file": gp.relative(p, f)})
    return out


def _orders(p: Project, goal: str, sub: str, needs: list[str]) -> list[dict]:
    """哪几张开工单的目标里有这件：写了整个目标 / 模块、写了这件、或写了它为了的那条需求。"""
    import workorders
    out = []
    for wo in workorders.list_all(p):
        for t in wo["target"]:
            head, _, rest = t.partition(" ")
            if head == goal and (not rest or rest == sub or rest in needs):
                out.append({"code": wo["code"], "name": wo["name"]})
                break
    return out


def _drafted(p: Project, goal: str, sub: str) -> dict | None:
    """这件是从草稿区收进来的：谁起草、什么时候、审核最后怎么说（S1-8 S2-40）。"""
    import drafts
    for d in drafts.listing(p):
        if d["state"] == drafts.TAKEN and d["where"] == goal and d["result"].endswith(f"编号 {sub}"):
            last = next((r for r in reversed(d.get("reviews") or []) if r["act"] in (drafts.OK, drafts.NO)), None)
            return {"code": d["code"], "by": d["by"].replace("agent:", ""), "at": d["at"],
                    "review": f"{last['by']} {last['act']}：{last['why']}" if last else ""}
    return None


def _note(p: Project, code: str) -> str:
    import deliveries
    if not code:
        return ""
    try:
        return deliveries.last_note(deliveries.get(p, code))
    except Exception:                                      # 交付单读不了：详情照样出
        return ""


def why(p: Project, goal: str, sub: str, bp: dict | None = None) -> dict | None:
    """为什么做这件：S0 → 大问题 → 目标 / 模块（一句话、怎么算做到、定没定稿）→ 为了的需求原文 → 怎么验 → 守哪几份戒律。
    网页「一件的详情」和 MCP 交活（next_task、claim_task）用同一份（S1-8 S2-34）。"""
    import dispatch
    bp = bp or blueprint.pyramid(p)
    g = blueprint.find(bp, goal)
    x = next((s for s in g["subs"] if s["code"] == sub), None) if g else None
    if x is None:
        return None
    row = next((r for r in dispatch.plan_status(p) if r["code"] == g["code"]), {})
    return {"s0": (bp["s0"] or {}).get("one_line", ""), "group": row.get("group") or ("模块" if g.get("kind") == "module" else ""),
            "goal": g["code"], "goal_name": g["name"], "kind": g.get("kind", "S1"), "goal_line": g.get("one_line", ""),
            "done_when": g.get("done_when", ""), "goal_final": g.get("final", ""), "what": x["what"], "how": x["how"],
            "needs_full": _needs_of(g, x, _need_index(p, bp)), "rules": _rules(p, g)}


def goal_text(p: Project, goal: str) -> str:
    """一块目标 / 模块的方向：S0 一句话 · 大问题 · 这块的一句话和怎么算做到 · 它的需求原文（审核草稿、规划时对着看）。"""
    import dispatch
    import requirements
    bp = blueprint.pyramid(p)
    g = blueprint.find(bp, goal)
    if g is None:
        return ""
    row = next((r for r in dispatch.plan_status(p) if r["code"] == g["code"]), {})
    mod = g.get("kind") == "module"
    name = g["name"].replace(g["code"], "").strip()
    out = ["## 这块的方向（审、写都对着它）", f"- 总的（S0）：{(bp['s0'] or {}).get('one_line', '')}"]
    if row.get("group") and not mod:
        out.append(f"- 大问题：{row['group']}")
    out.append(f"- {'模块' if mod else '目标'} {g['code']}{' ' + name if name else ''}：{g.get('one_line', '')}")
    if g.get("done_when"):
        out.append(f"  - 怎么算做到：{g['done_when']}")
    qs = [q for q in requirements.catalog(p, bp) if (q["scope"] == g["code"]) or (g["code"] in (q.get("goals") or []))]
    out += [f"- 需求 {q['scope']} {q['code']}：{q.get('func', '')}——{q.get('effect', '')}" for q in qs[:12]]
    return "\n".join(out)


def why_text(p: Project, goal: str, sub: str) -> str:
    """交给 agent 的那一段：做的时候对着它，别跑偏（照 Paperclip「目标链跟着活走」、三省六部「规划带着旨意」）。"""
    w = why(p, goal, sub)
    if not w:
        return ""
    name = w["goal_name"].replace(w["goal"], "").strip()
    mod = w["kind"] == "module"
    out = ["## 为什么做这件（做的时候对着它，别跑偏）", f"- 总的（S0）：{w['s0'] or '（S0 没写一句话）'}"]
    if w["group"] and not mod:
        out.append(f"- 大问题：{w['group']}")
    out.append(f"- {'模块' if mod else '目标'} {w['goal']}{' ' + name if name else ''}：{w['goal_line'] or '（没写一句话）'}"
               + ("（规划定稿了）" if w["goal_final"] else "（规划还没定稿）"))
    if w["done_when"]:
        out.append(f"  - 怎么算做到：{w['done_when']}")
    for q in w["needs_full"]:
        out.append(f"- 为了 {q['scope']} {q['code']}：{q['func']}" + (f"——{q['effect']}" if q["effect"] else ""))
    if not w["needs_full"]:
        out.append("- 为了：这件没写为了哪条需求（做之前先问人，或用 propose_draft 起草）")
    out.append(f"- 怎么验：{w['how'] or '（没写：先写进计划，交付时照它验）'}")
    if w["rules"]:
        out.append("- 守的戒律：" + " · ".join(f"{r['layer']} `{r['file']}`" for r in w["rules"]))
    return "\n".join(out)


def detail(conn, p: Project, goal: str, sub: str) -> dict | None:
    """一件的详情：卡上那些 + 为什么那条链（S0 → 大问题 → 目标 / 模块 → 需求原文）+ 来龙去脉。"""
    import agents
    bp = blueprint.pyramid(p)
    w = why(p, goal, sub, bp)
    if w is None:
        return None
    card = next(i for i in items(conn, p, bp) if i["goal"] == goal and i["code"] == sub)
    out = dict(card)
    out.update({k: v for k, v in w.items() if k not in ("group",)})
    out.update(orders=_orders(p, goal, sub, [q["code"] for q in w["needs_full"]]), timeline=agents.timeline(conn, p, goal, sub),
               wait_done=bool(card["wait_on"]) and blueprint.is_done(bp, card["wait_on"]),
               j_note=_note(p, card["j"]), drafted=_drafted(p, goal, sub))
    return out


def daily(conn, p: Project, days: int = 14, cards: list[dict] | None = None) -> dict:
    """总览四张图的数（最近 days 天）：每天交付（通过 / 打回）· 每天做完的件（按大问题）· 累计做完 · 监管发现和关了。"""
    import deliveries
    import supervise
    today = date.today()
    ds = [(today - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
    cards = cards if cards is not None else items(conn, p)
    groups = {c["goal"]: c["group"] or "模块" for c in cards}
    passed, rejected, by_group = {d: 0 for d in ds}, {d: 0 for d in ds}, {}
    done_after = 0
    for j in deliveries.list_all(p):
        d = (j["at"] or "")[:10]
        ok = j["state"] in ("验收通过",)
        if ok and d > ds[-1]:
            done_after += 1
        if d not in passed:
            continue
        if ok:
            passed[d] += 1
            g = groups.get(j["goal"], "模块")
            by_group.setdefault(g, {k: 0 for k in ds})[d] += 1
        elif j["state"] == "打回":
            rejected[d] += 1
    done_now = sum(1 for c in cards if c["col"] == "做完")
    cum, later = [], done_after
    for d in reversed(ds):                                # 往回倒：那天结束时做完了几件 = 现在的 − 那天以后通过的
        cum.append(done_now - later)
        later += passed[d]
    cum.reverse()
    found, closed = {d: 0 for d in ds}, {d: 0 for d in ds}
    supervise._ensure(conn)
    for r in conn.execute("SELECT state, first_at, last_at FROM finding").fetchall():
        a, b = (r["first_at"] or "")[:10], (r["last_at"] or "")[:10]
        if a in found:
            found[a] += 1
        if r["state"] != supervise.OPEN and b in closed:
            closed[b] += 1
    return {"days": ds, "passed": [passed[d] for d in ds], "rejected": [rejected[d] for d in ds],
            "by_group": {g: [v[d] for d in ds] for g, v in by_group.items()}, "cumulative": cum, "total": len([c for c in cards if c["col"] != "以后"]),
            "found": [found[d] for d in ds], "closed": [closed[d] for d in ds]}


def snapshot(conn, p: Project) -> dict:
    cards = items(conn, p)
    week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    counts = {k: sum(1 for c in cards if c["col"] == k) for k in COLS + ("以后",)}
    counts["做完这周"] = sum(1 for c in cards if c["col"] == "做完" and c["j_at"][:10] >= week)
    return {"items": cards, "counts": counts, "daily": daily(conn, p, cards=cards)}
