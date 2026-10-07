"""一站式自动推进：agent 自己开工、自己领活，不用人点（正本见 自动化/协议.md）。

作者 2026-09-30：「自动化协议宽松一点，不要老是让人去确认，只有有需求，蓝图，戒律，验收标准，等等可以一站式自动推进进程，
人可以慢慢看日志或者成果」；选了「agent 自己从蓝图挑」。
- 能自己做的件 = 还没做完、不是「以后」、不在等人（等工具 / 等你 / 待你验收）、**写了怎么验**（验收标准）的；
  你想先做哪个，在蓝图里排先后（按蓝图的顺序挑）
- 没有在跑的开工单：agent 挑蓝图里第一个有这种件的目标，自己开一张（档 2）、自己开工；灯有红的开不了，照红灯补
- 有在跑的：几个 agent 都在这一张里各领各的件（claims：同一件、同一条道只给一个人）；这张被别人占满了，
  先帮蓝图里别的、不撞道的件（不算在这张单里），不闲着——作者要的是几个 agent 一起干「速度就更快了」
- 在跑的那张里没有能做的了（也没人在做）：放下它，接着开下一个目标的——一站式往下推
- 人在网页上叫停过：不自己开新单，等人点「交给 agent」或在对话里让开工（resume）
- 先报到才领得到活；有档案的照档案挑：只给「管哪些」里的、跳过「不碰」的（agents.py，作者 09-30：「得给agent注册」）
- **只自己挑定稿了的**：目标文件、模块蓝图头上写着「规划：定稿 · 日期 · 作者原话」的，里面的件 agent 才自己挑；没定稿的，人点名照样能做
  （作者 10-01：「需求蓝图等等东西这个是最重要的，要先和人一起规划，这个完毕之后才是全自动」）
"""
from __future__ import annotations

import time

from datetime import datetime

import agents
import blueprint
import claims
import readiness
import store
import workorders
from project import Project

BATCH = 8                                          # 自己开的单一次最多圈几件
WAITING = ("以后", "等", "待你验收", "待验收")   # 这几种不自己挑：以后再说、卡在人那边（等你、等工具），或卡在别的件后面


def _open(x: dict, g: dict | None = None, bp: dict | None = None) -> bool:
    """这件 agent 能自己做：写了怎么验、没做完、不在等。状态写「等 S2-3」的卡在那件后面：那件做完了才能领（S1-8 S2-35），不用人改状态。"""
    if not x["how"].strip() or x["status"] == "ok":
        return False
    t = x["text"].strip()
    dep = blueprint.waits_on(g["code"], t) if g else ""
    if dep:
        return bp is not None and blueprint.is_done(bp, dep)
    return not t.startswith(WAITING)


def ready_items(p: Project, bp: dict | None = None) -> list[tuple[dict, dict]]:
    """蓝图里能自己做的件（按蓝图顺序：总蓝图 S1-1… 在前，模块蓝图在后）。只算规划定稿了的目标、模块。"""
    bp = bp or blueprint.pyramid(p)
    return [(g, x) for g in bp["goals"] + bp.get("modules", []) if g.get("final") for x in g["subs"] if _open(x, g, bp)]


def plan_status(p: Project) -> list[dict]:
    """离全自动还差什么：每个目标、每个模块一行——有几条需求（几条没对上任务）、还剩几件（几件没写怎么验）、
    有没有模块戒律、定没定稿。规划的时候一眼看出下一块该补谁。"""
    import governance_paths as gp
    import project as proj
    import requirements
    bp = blueprint.pyramid(p)
    qs = requirements.catalog(p, bp)

    def left(g):
        return [x for x in g["subs"] if x["status"] != "ok" and not x["text"].startswith("以后")]

    groups = {}
    for b in blueprint.big_problems(p):                 # 每个目标、模块挂在哪个大问题底下（S0「两个大问题」表）
        for t in b["to"]:
            groups.setdefault(t, b["big"])
    issues = {}
    for x in blueprint.lint(p):
        issues.setdefault(x["code"], []).append(x["text"])

    def row(g, kind, name, needs, rules):
        live = left(g) if g else []
        return {"code": name, "name": g["name"] if g else name, "kind": kind, "needs": len(needs),
                "group": groups.get(name, "" if kind == "目标" else "模块"), "lint": issues.get(name, []),
                "needs_loose": sum(not q["tasks"] for q in needs), "items": len(g["subs"]) if g else 0, "left": len(live),
                "done": sum(x["status"] == "ok" for x in g["subs"]) if g else 0,
                "no_how": sum(not x["how"].strip() for x in live), "rules": rules, "final": (g or {}).get("final", ""),
                "file": (g or {}).get("file", "")}

    def done(r):
        r["missing"] = why_not_final(r)
        return r
    out = [done(row(g, "目标", g["code"], [q for q in qs if g["code"] in q["goals"]], None)) for g in bp["goals"]]
    mods = {g["code"]: g for g in bp.get("modules", [])}
    names = list(dict.fromkeys([m.name if hasattr(m, "name") else str(m) for m in proj.module_dirs(p)] + list(mods)))
    for m in names:
        if m.startswith("_"):
            continue
        out.append(done(row(mods.get(m), "模块", m, [q for q in qs if q["scope"] == m], gp.resolve(p, f"资料/{m}/戒律.md").is_file())))
    return out


def why_not_final(row: dict) -> list[str]:
    """定稿前先查：还缺什么，空 = 能定稿（蓝图 S2-3；作者 10-01：「需求蓝图等等东西这个是最重要的，要先和人一起规划，这个完毕之后才是全自动」）。
    缺需求、需求没对上任务、任务没写怎么验、没有模块戒律、格式不对——有一样就不能定稿。"""
    out = []
    if not row["file"] or not row["items"]:
        out.append("还没有任务")
    if not row["needs"]:
        out.append("还没有需求")
    if row["needs_loose"]:
        out.append(f"{row['needs_loose']} 条需求没对上任务")
    if row["no_how"]:
        out.append(f"{row['no_how']} 件没写怎么验")
    if row["rules"] is False:
        out.append("还没有模块戒律")
    out += [f"格式：{x}" for x in row["lint"]]
    return out


def set_final(p: Project, code: str, on: bool, words: str = "", day: str = "") -> dict:
    """定稿 / 取消定稿：在目标文件、模块任务文件头上写上或去掉「规划：定稿 · 日期 · 原话」那一行。
    只有人按（网页上；MCP 没有这个口子）。定稿前先查，缺东西就拒，写清缺什么。"""
    import datetime

    import atomic
    import governance_paths as gp
    r = next((x for x in plan_status(p) if x["code"] == code), None)
    if r is None:
        raise store.Refused(f"找不到 {code}")
    if on and r["missing"]:
        raise store.Refused(f"{code} 还不能定稿，还缺：" + "；".join(r["missing"]))
    if not r["file"]:
        raise store.Refused(f"{code} 还没有任务文件")
    f = gp.resolve(p, r["file"])
    raw = f.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    lines = [x for x in raw.replace("\r\n", "\n").split("\n") if not x.startswith("规划：")]
    line = ""
    if on:
        said = " ".join((words or "定稿").split())[:200]
        line = f"规划：定稿 · {day or datetime.date.today().isoformat()} · 作者：「{said}」"
        at = next((i for i, x in enumerate(lines) if x.startswith(("怎么算做到：", "怎么算装好："))), None)
        if at is None:                                   # 没有「怎么算做到」：放在一句话后面，空一行
            b = next((i for i, x in enumerate(lines) if not x.startswith(">") and blueprint._BOLD.search(x)), 0)
            lines[b + 1:b + 1] = ["", line]
        else:
            lines.insert(at, line)
    text = "\n".join(lines)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    atomic.replace(tmp, f)
    return {"code": code, "final": line.split("：", 1)[1] if line else "", "file": r["file"]}


def auto_target(p: Project, prof: dict | None = None) -> list[str]:
    """挑蓝图里第一个有能做的件的目标，圈它那几件。给了档案：只挑它「管哪些」里的、跳过「不碰」的。"""
    import deliveries
    latest = deliveries.latest_by_task(p)
    items = [(g, x) for g, x in ready_items(p) if _can_work(p, prof, g, x, latest)]
    if not items:
        return []
    first = items[0][0]["code"]
    return [f"{g['code']} {x['code']}" for g, x in items if g["code"] == first][:BATCH]


def start_work(conn, p: Project, agent: str, target: list[str] | None = None, name: str = "",
               resume: bool = False) -> dict:
    """有在跑的开工单就加入它；没有就自己开一张、自己开工。→ {wo, joined}。开不了抛 store.Refused（写清缺什么）。
    resume：人叫停过、又在对话里让你开工时才带上。没报到的开不了（agents.require）。"""
    prof = agents.require(p, agent)
    wo = workorders.running(p)
    if wo:
        return {"wo": wo, "joined": True}
    stop = workorders.paused(conn)
    if stop and not resume:
        raise store.Refused(f"人叫停了（{stop}）：不自己开新单。等人在「自动化」页点「交给 agent」，"
                            "或人在对话里让你开工（那时 start_work 带 resume=true）")
    if not _lock(conn, agent):                         # 别的 agent 正在开：等它开好，加入它那张
        for _ in range(40):
            time.sleep(0.25)
            wo = workorders.running(p)
            if wo:
                return {"wo": wo, "joined": True}
        raise store.Refused("别的 agent 正在开新单，过一会儿再领")
    try:
        wo = workorders.running(p)                     # 拿到锁再看一眼：可能刚有人开好了
        if wo:
            return {"wo": wo, "joined": True}
        target = [t for t in (target or []) if t.strip()] or auto_target(p, prof)
        if not target:
            raise store.Refused("蓝图里没有你能自己做的件（看你档案上的「管哪些」「不碰」）：要做的件得写上「怎么验」（S2 表里「怎么验」那一列），"
                                "没写的先写（任务的怎么验 agent 可以写；需求、S0、S1、戒律是方向，只有人改）")
        goal = readiness.split_target(target[0])[0]
        same = next((w for w in workorders.list_all(p) if w["stored"] == "备料" and w["name"].startswith("自动开工")
                     and sorted(w["target"]) == sorted(target)), None)   # 上回自己开了、没开成工的那张：接着用，不再多开一张
        wo = same or workorders.create(conn, p, name or f"自动开工 · {goal}", target, by=agent)
        if not same:
            workorders.update(conn, p, wo["code"], {"level": 2}, by=agent)
        try:
            wo = workorders.start(conn, p, wo["code"], by=agent)
        except store.Refused:
            why = readiness.why_red(readiness.panel(conn, p, workorders.get(p, wo["code"])))
            raise store.Refused(f"蓝图里有活，但 {wo['code']} 开不了工——{why or '目标里没有要做的了'}。"
                                "写着「要人写 / 要人改」的、要改戒律正文或 S1 的，只有人能补：用 ask_human 告诉人，别自己改；"
                                "能补的（写怎么验、补材料）补上再调一次。再调不会多开一张单")
        if stop:
            workorders.resume(conn, by=agent)
        return {"wo": wo, "joined": False}
    finally:
        _unlock(conn, agent)


OPENING = "opening_order"                              # 谁正在开新单：「名字|时间」；60 秒没放就算放了（开单那几步只要一两秒）


def _lock(conn, agent: str) -> bool:
    """开新单的锁：两个 agent 同时发现没在跑的单，只让一个开，另一个等着加入（不然会开出两张、第二张开不了工）。"""
    with store.tx(conn):
        who, _, at = (store._meta(conn, OPENING) or "").partition("|")
        if who and who != agent and time.time() - float(at or 0) < 60:
            return False
        store._set_meta(conn, OPENING, f"{agent}|{time.time()}")
    return True


def _unlock(conn, agent: str) -> None:
    with store.tx(conn):
        if (store._meta(conn, OPENING) or "").partition("|")[0] == agent:
            store._set_meta(conn, OPENING, "")


def review_job(conn, p: Project, agent: str) -> dict | None:
    """接续本人已领的验收，再解除自动员工的等待；其余交付仍先交先验。"""
    import deliveries
    prof = agents.require(p, agent)
    if "验收" not in agents.jobs(prof) or prof.get("paused") or workorders.paused(conn):
        return None
    me = prof["name"]
    who = agents.actor(me)
    held = {r["sub"] for r in claims.of(conn, who) if r["goal"] == "验收"}
    authors = {a["name"]: a for a in agents.list_all(p)}

    def priority(j):
        author = authors.get(agents.short(j["by"]), {})
        group = 0 if j["code"] in held else 1 if author.get("auto") and not author.get("paused") else 2
        return group, j["n"]

    bp = blueprint.pyramid(p)
    for j in sorted((x for x in deliveries.list_all(p) if deliveries.independent_pending(p, x)), key=priority):
        if agents.short(j["by"]) == me:
            continue
        g = blueprint.find(bp, j['goal'])
        x = next((s for s in (g or {}).get('subs', []) if s['code'] == j['sub']), None)
        if not g or not x or not agents.allows(prof, g, x) or _blocked(p, prof, f"review_delivery:{j['code']}"):
            continue
        import workflow_graph
        if workflow_graph.action_reason(p, "review_delivery", g["code"], x["code"], agent):
            continue
        try:
            claims.claim(conn, "验收", j["code"], who, ["验收 " + j["code"]], f"验收 {j['goal']} {j['sub']}")
        except store.Refused:
            continue
        return j
    return None


def draft_job(conn, p: Project, agent: str) -> dict | None:
    """审核的 agent 下一张要审的草稿：等审的、不是自己写的、没人在审的，先写的先审；领走（道「审核 草-3」）。"""
    import drafts
    me = agents.short(agent)
    prof = agents.require(p, agent)
    for d in sorted(drafts.listing(p), key=lambda x: int(x["code"][2:])):
        if agents.short(d["by"]) == me or drafts.stage(p, d) != "等审":
            continue
        if _blocked(p, prof, f"review_draft:{d['code']}"):
            continue
        try:
            claims.claim(conn, "审核", d["code"], agent, ["审核 " + d["code"]], f"审核 {d['code']}")
        except store.Refused:
            continue
        return d
    return None


def plan_job(conn, p: Project, agent: str) -> dict | None:
    """规划的 agent 下一件：先改自己被打回的草稿；再挑一块还没定稿、还缺东西的目标 / 模块（领走「规划 S1-2」，同一块一个人）。"""
    import drafts
    me = agents.short(agent)
    prof = agents.require(p, agent)
    for d in drafts.listing(p):
        if agents.short(d["by"]) == me and drafts.stage(p, d) == "打回":
            return {"kind": "改草稿", "draft": d}
    for r in plan_status(p):
        if r["final"] or not r["missing"]:
            continue
        if prof.get('scope') and not any(r['code'] == t or r['code'].startswith(t + ' ') for t in prof['scope']):
            continue
        if r['code'] in prof.get('avoid', []):
            continue
        try:
            claims.claim(conn, "规划", r["code"], agent, ["规划 " + r["code"]], f"规划 {r['code']}")
        except store.Refused:
            continue
        return {"kind": "规划", "row": r}
    return None


def _sent_back(p: Project) -> dict:
    """被验收的 agent 打回、还没再交的件 →（原来干的人, 打回时的交付单）。两小时内留给原来那个人改。"""
    import deliveries
    out = {}
    for k, j in deliveries.latest_by_task(p).items():       # 接续按编号；网页将待你验收置顶，不能拿它判断最新版
        out[k] = j if j["state"] == "打回" and deliveries.AGENT_NO in j["body"] else None
    return {k: v for k, v in out.items() if v}


def _fresh(at: str) -> bool:
    try:
        return (datetime.now() - datetime.strptime(at, "%Y-%m-%d %H:%M")).total_seconds() < claims.TTL
    except ValueError:
        return False


def _next_task(conn, p: Project, agent: str) -> dict:
    """给这个 agent 下一件并领走。→ {wo, task, reason, done}；task 为 None 时 reason 写清为什么（都有人在做 / 做完了）；
    done 是这一趟放下的单（在跑的那张没有能做的了，放下、接着开下一个目标的）。
    分工（S1-8 S2-39）：岗位有验收的先拿验收活（{review: 交付单}）；岗位里没有干活的不领件；被验收打回的件先还给原来干的。"""
    prof = agents.require(p, agent)
    jobs = agents.jobs(prof)
    if "验收" in jobs:                                     # 档位 3、4：先挑果实（S1-8 S2-58）
        import branching
        fj = branching.pick_job(conn, p, agent)
        if fj:
            return {"wo": None, "joined": False, "task": None, "fruit": fj, "reason": "", "done": []}
    if "验收" in jobs:
        j = review_job(conn, p, agent)
        if j:
            return {"wo": None, "joined": False, "task": None, "review": j, "reason": "", "done": []}
    if "审核" in jobs:                                     # 清理：审别人出的重写单（S1-8 S2-63；作者 10-03「重铸由agent来做」）
        import rewrite
        rv = rewrite.review_job(conn, p, agent)
        if rv:
            return {"wo": None, "joined": False, "task": None, "rewrite_review": rv, "reason": "", "done": []}
    if "审核" in jobs:                                     # S1-8 S2-40：审核的先审草稿
        d = draft_job(conn, p, agent)
        if d:
            return {"wo": None, "joined": False, "task": None, "draft": d, "reason": "", "done": []}
    if "规划" in jobs:
        pj = plan_job(conn, p, agent)
        if pj:
            return {"wo": None, "joined": False, "task": None, "plan": pj, "reason": "", "done": []}
    if "规划" in jobs or agents.short(agent) == "claude-code":   # 清理：写摘要、写重写单（S1-8 S2-62、S2-63）——规划的活排在前面，这些是闲时做的
        import digest
        import rewrite
        dj = digest.job(conn, p, agent)
        if dj:
            return {"wo": None, "joined": False, "task": None, "digest": dj, "reason": "", "done": []}
        rj = rewrite.job(conn, p, agent)
        if rj:
            return {"wo": None, "joined": False, "task": None, "rewrite": rj, "reason": "", "done": []}
    if "干活" not in jobs:
        none = [y for x, y in (("验收", "等验收的交付单"), ("审核", "等审的草稿"), ("规划", "缺东西的目标或模块")) if x in jobs]
        return {"wo": None, "joined": False, "task": None, "done": [],
                "reason": f"你的岗位是 {'、'.join(jobs)}，不领干活的件" + (f"；现在没有{'、'.join(none)}" if none else "")}
    back = _sent_back(p)
    me = agents.short(agent)
    bp0 = blueprint.pyramid(p)
    import employee_assignments
    import deliveries
    latest = deliveries.latest_by_task(p)
    for (goal, sub), j in back.items():                    # 自己交的被打回了：先拿回来改
        g = blueprint.find(bp0, goal)
        x = next((s for s in (g or {}).get("subs", []) if s["code"] == sub), None)
        if x is None or agents.short(j["by"]) != me or not _open(x, g, bp0) or not _can_work(p, prof, g, x, latest):
            continue
        if employee_assignments.held_reason(p, prof, g, x):
            continue
        try:
            claims.claim(conn, goal, sub, agent, claims.lanes_of(g, x), x["what"])
        except store.Refused:
            continue
        import deliveries
        return {"wo": workorders.running(p) or {"code": "", "name": "不在开工单里"}, "joined": True, "task": _task(g, x, claims.lanes_of(g, x)),
                "reason": f"你交的 {j['code']} 验收没过，先改它：{deliveries.last_note(j)}", "done": []}
    # 点名领着的任务不要求先有K：开单只负责自动挑新活，不能吞掉既有授权。
    own_wo = workorders.running(p) or {"code": "", "name": "不在开工单里"}
    assignment_problems = []
    for r in claims.of(conn, agent):
        g = blueprint.find(bp0, r["goal"]) if r["goal"] != claims.CORE else None
        x = next((s for s in (g or {}).get("subs", []) if s["code"] == r["sub"]), None)
        if x is not None and x['status'] != 'ok':
            why = _work_reason(p, prof, g, x, latest)
            if why:
                claims.release(conn, r['goal'], r['sub'], agent, note=why)
                assignment_problems.append(f"{r['goal']} {r['sub']}：{why}")
                continue
            if not _open(x, g, bp0):
                dependency = blueprint.waits_on(g['code'], x['text'])
                # 上面已核对来源和签名；有持久派活才能安全放道，前置完成后按原来源领回。
                if dependency and not blueprint.is_done(bp0, dependency) and any(
                    (row['goal'], row['sub']) == (g['code'], x['code'])
                    for row in employee_assignments.listing(p, prof)
                ):
                    claims.release(conn, r['goal'], r['sub'], agent, note=f'等待 {dependency}，保留派活来源并释放施工道')
                assignment_problems.append(f"{r['goal']} {r['sub']}：任务当前不可施工（{x['text']}）")
                continue
            return {"wo": own_wo, "joined": bool(own_wo['code']), "task": _task(g, x, claims.lanes_of(g, x)),
                    "reason": "你领着的，接着做", "done": []}
        if g and x and not _can_work(p, prof, g, x, latest):
            claims.release(conn, r['goal'], r['sub'], agent, note='岗位、工种或范围已变化，不再占原施工任务')
        elif r['goal'] not in (claims.CORE, '审核', '验收', '施工审核', '规划') and (not x or x['status'] == 'ok'):
            claims.release(conn, r['goal'], r['sub'], agent, note='原施工任务已完成或不可用')
    assigned, recorded_problems = employee_assignments.candidates(p, prof, bp0)
    assignment_problems.extend(recorded_problems)
    for g, x, record in assigned:
        if not _open(x, g, bp0) or not _can_work(p, prof, g, x, latest):
            continue
        try:
            claims.claim(conn, g['code'], x['code'], agent, claims.lanes_of(g, x), x['what'])
        except store.Refused as e:
            assignment_problems.append(str(e))
            continue
        return {"wo": own_wo, "joined": bool(own_wo['code']), "task": _task(g, x, claims.lanes_of(g, x)),
                "reason": "按人的明确派活记录接续：" + record['authorization_path'], "done": []}
    done = []
    for _ in range(3):
        try:
            got = start_work(conn, p, agent)
        except store.Refused as e:
            if assignment_problems:
                raise store.Refused(str(e) + "；派活未恢复：" + "；".join(assignment_problems[:3])) from e
            raise
        wo = got["wo"]
        bp = blueprint.pyramid(p)
        items, _ = readiness.scope_items(bp, wo["target"], p)
        for r in claims.of(conn, agent):                   # 自己领着没交的（单里的、单外帮忙的）：接着做它
            g = blueprint.find(bp, r["goal"]) if r["goal"] != claims.CORE else None
            x = next((x for x in (g or {}).get("subs", []) if x["code"] == r["sub"]), None)
            if x is not None and _open(x, g, bp) and _can_work(p, prof, g, x, latest):
                return {"wo": wo, "joined": got["joined"], "task": _task(g, x, claims.lanes_of(g, x)),
                        "reason": "你领着的，接着做", "done": done}
        busy, blocked = [], []
        for g, x in items:
            if not _open(x, g, bp):                        # 点名的件做完了、在等人、卡在别的件后面：跳过
                continue
            j = back.get((g["code"], x["code"]))
            if j and agents.short(j["by"]) != me and _fresh(j["at"]):   # 验收打回的：两小时内留给原来干的那个改
                continue
            if not _can_work(p, prof, g, x, latest):      # 不归它管，或授权/交付不允许继续施工。
                blocked.append(f"{g['code']} {x['code']}：{_work_reason(p, prof, g, x, latest)}")
                continue
            try:
                claims.claim(conn, g["code"], x["code"], agent, claims.lanes_of(g, x), x["what"])
            except store.Refused as e:
                busy.append(str(e))
                continue
            return {"wo": wo, "joined": got["joined"], "task": _task(g, x, claims.lanes_of(g, x)), "reason": "", "done": done}
        others = [r for r in claims.active(conn) if r["goal"] != claims.CORE
                  and any((r["goal"], r["sub"]) == (g["code"], x["code"]) for g, x in items)]
        if busy or others or blocked:
            why = ("；".join(busy[:3]) or "、".join(f"{r['agent']} 在做 {r['goal']} {r['sub']}" for r in others[:3])
                   or f"剩下的 {'、'.join(blocked[:3])} 不归你管（档案 {prof['code']}）")
            extra = _elsewhere(conn, p, agent, {(g["code"], x["code"]) for g, x in items}, prof, latest)
            if extra:                                      # 单里被别人占满了 / 不归它管：先做蓝图里别的、归它管、不撞道的件，不闲着
                g, x = extra
                return {"wo": wo, "joined": got["joined"], "task": _task(g, x, claims.lanes_of(g, x)) | {"outside": True},
                        "reason": f"{wo['code']} 里没有给你的（{why}）：先做蓝图里别的这件，不算在 {wo['code']} 里", "done": done}
            return {"wo": wo, "joined": got["joined"], "task": None, "reason": f"{wo['code']} 里没有给你的：" + why, "done": done}
        workorders.finish(conn, p, wo["code"], by=agent)   # 这张没有能做的了：放下，接着开下一个目标的
        done.append(wo["code"])
        if not auto_target(p, prof):
            break
    return {"wo": wo, "joined": False, "task": None, "done": done,
            "reason": f"{'、'.join(done)} 里没有能做的了（都做完了，或在等人、没写怎么验）；蓝图里也没有别的你能自己做的件"}


def _elsewhere(conn, p: Project, agent: str, skip: set, prof: dict | None = None, latest: dict | None = None) -> tuple[dict, dict] | None:
    """在跑的单里没有给它的：蓝图里别的、归它管的件，按顺序领第一件领得到的（撞道的自然领不到）。"""
    import deliveries
    latest = deliveries.latest_by_task(p) if latest is None else latest
    for g, x in ready_items(p):
        if (g["code"], x["code"]) in skip or not _can_work(p, prof, g, x, latest):
            continue
        try:
            claims.claim(conn, g["code"], x["code"], agent, claims.lanes_of(g, x), x["what"])
        except store.Refused:
            continue
        return g, x
    return None


def _task(g: dict, x: dict, lanes: list[str]) -> dict:
    return {"goal": g["code"], "sub": x["code"], "what": x["what"], "how": x["how"], "for": x.get("for", []),
            "text": x["text"], "lanes": lanes, "file": g["file"]}


def _blocked(p, prof, key):
    import json
    try:
        state = json.loads((p.root / '自动化' / '运行状态' / (prof['code'] + '.json')).read_text(encoding='utf-8'))
        return key in state.get('blocked', [])
    except (OSError, ValueError, TypeError):
        return False


def _work_reason(p, prof, g, x, latest=None):
    """所有施工候选同守来源、失败限制和最新交付，不能从另一条派发路径绕回。"""
    import employee_assignments
    import deliveries
    why = agents.allows_reason(prof, g, x)
    if why:
        return why
    import workflow_graph
    why = workflow_graph.worker_reason(p, prof, g, x)
    if why:
        return why
    import branching
    why = branching.on_branches(None, p, x)                # 档位 3、4：该开枝的件主干上不领（S1-8 S2-58）
    if why:
        return why
    if prof:
        if any(_blocked(p, prof, f"{act}:{g['code']}:{x['code']}") for act in ('execute', 'submit_plan')):
            return '本件已到连续失败限制，需要明确恢复'
        why = employee_assignments.held_reason(p, prof, g, x)
        if why:
            return why
    latest = deliveries.latest_by_task(p) if latest is None else latest
    j = latest.get((g['code'], x['code']))
    if j and j['state'] in ('待你验收', '等验收', '验收通过'):
        return f"{j['code']} 已{j['state']}，不能重复施工"
    return ''


def _can_work(p, prof, g, x, latest=None):
    return not _work_reason(p, prof, g, x, latest)


def recheck_action(conn, p: Project, agent: str, got: dict, before=()) -> dict:
    """认领后和启动前复核；准入失效只撤回这次新增认领。"""
    import workflow_graph
    target = got.get("task") or got.get("construction_plan") or got.get("review") or {}
    action = got.get("action", "")
    runnable = action in workflow_graph.ACTION_TYPES
    actionable = action not in ("", "idle", "waiting", "stopped")
    reason = workorders.paused(conn) if actionable else ""
    if actionable and agents.require(p, agent).get("paused"):
        reason = reason or "员工已暂停"
    if target.get("goal") and target.get("sub"):
        try:
            flow = workflow_graph.metadata(p, target["goal"], target["sub"], action, agent)
            previous = got.get("workflow")
            if previous and (not flow or previous.get("revision") != flow.get("revision")):
                reason = reason or "流程版本已变化，重新领取当前动作"
            got["workflow"] = flow
            if flow and flow.get("stopped"):
                reason = reason or flow["reason"]
            elif runnable:
                reason = reason or workflow_graph.action_reason(p, action, target["goal"], target["sub"], agent)
        except store.Refused as exc:
            reason = reason or str(exc)
    if reason:
        old = set(before)
        for row in claims.of(conn, agent):
            if (row["goal"], row["sub"]) not in old:
                claims.release(conn, row["goal"], row["sub"], agent, "准入复核未通过：" + reason)
        return got | {"action": "waiting", "task": None, "construction_plan": None,
                      "review": None, "reason": reason}
    return got


def next_task(conn, p: Project, agent: str) -> dict:
    """统一入口：暂停优先；施工计划审核、既有分工、施工计划关共用同一动作。"""
    import construction_plans as cp
    a = agents.require(p, agent)
    before = {(r["goal"], r["sub"]) for r in claims.of(conn, agent)}
    stopped = workorders.paused(conn) or ("员工已暂停" if a.get("paused") else "")
    if stopped:
        if not a.get('auto') and not a.get('plan_required') and not a.get('paused'):
            raise store.Refused('人叫停了：' + stopped)
        return {"action": "stopped", "task": None, "wo": None, "done": [], "reason": stopped}
    if a.get('plan_required') and '干活' in agents.jobs(a):
        import deliveries
        pending = next((j for j in deliveries.latest_by_task(p).values()
                        if deliveries.independent_pending(p, j) and agents.short(j['by']) == a['name']), None)
        if pending:
            import workflow_graph
            return {'action':'waiting','task':None,'wo':None,'done':[], 'review':pending, 'reason':f"{pending['code']} 等独立验收；通过后继续下一件",
                    'workflow': workflow_graph.metadata(p, pending['goal'], pending['sub'])}
    if "审核" in agents.jobs(a):
        plan = cp.next_review(conn, p, agent)
        if plan:
            if _blocked(p, a, f"review_plan:{plan['code']}"):
                claims.release(conn, cp.REVIEW, plan['code'], agent, '本轮失败上限，先跳过')
            else:
                import workflow_graph
                return recheck_action(conn, p, agent,
                    {"action": "review_plan", "construction_plan": plan, "task": None, "wo": None, "done": [], "reason": "施工计划待审",
                     "workflow": workflow_graph.metadata(p, plan['goal'], plan['sub'], "review_plan", agent)}, before)
    try:
        got = _next_task(conn, p, agent)
    except store.Refused as e:
        if not a.get('auto') and not a.get('plan_required'):
            raise
        return {"action": "idle", "task": None, "wo": None, "done": [], "reason": str(e)}
    task = got.get("task")
    import workflow_graph
    if task and (a.get("plan_required") or workflow_graph.requires_plan(p, task["goal"], task["sub"])):
        plans = [x for x in cp.listing(p) if x["goal"] == task["goal"] and x["sub"] == task["sub"] and agents.short(x["agent"]) == a["name"]]
        plan = plans[0] if plans else None
        got["construction_plan"] = plan
        if plan and cp.approved(p, task['goal'], task['sub'], agent):
            got["action"] = "execute"
            import vcs
            core_files = any(any(f.rstrip('/') == k or f.startswith(k + '/') for k in vcs.CORE_PATHS + ['插件']) for f in plan['files'])
            owner = next((r for r in claims.active(conn) if r['goal']==claims.CORE and agents.short(r['agent']) != a['name']),None)
            if core_files and owner:
                got['action'],got['reason']='waiting',f"核心锁由 {owner['agent']} 持有；放手后再施工"
        elif plan and plan["state"] == "待审":
            got["action"], got["reason"] = "waiting", "计划待审；退出本轮，审核后自动接续"
        else:
            got["action"] = "submit_plan"
    else:
        got["action"] = ("execute" if task else "pick_fruit" if got.get("fruit") else "write_digest" if got.get("digest")
                         else "write_rewrite" if got.get("rewrite") else "review_rewrite" if got.get("rewrite_review")
                         else "review_delivery" if got.get("review")
                         else "review_draft" if got.get("draft") else "draft" if got.get("plan") else "idle")
    if '干活' in agents.jobs(a):
        import employee_assignments
        _, problems = employee_assignments.candidates(p, a, blueprint.pyramid(p))
        if problems:
            got['reason'] = '；'.join(filter(None, [got.get('reason'), '派活未恢复：' + '；'.join(problems[:3])]))
    target = task or got.get("construction_plan") or got.get("review") or {}
    if target.get("goal") and target.get("sub"):
        got["workflow"] = workflow_graph.metadata(p, target["goal"], target["sub"], got.get("action", ""), agent)
    return recheck_action(conn, p, agent, got, before)
