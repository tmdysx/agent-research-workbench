"""交付单：agent 做完一件（一个 S2），写一张交付单交给人验收，编号 J1、J2…（号不回收）。

作者 2026-09-27：「按照我的蓝图戒律需求，自动调用或者寻找工具，然后完成和实现任务，交付成果」。
- 放在项目的 `自动化/交付/J3 S1-10 S2-2.md`：做了什么 · 怎么验的（每条检查和结果）· 东西在哪 · 存档几号 · 日志几圈 · 用的计划 ·
  照哪张开工单做的（K几，那张单的页面上就列它）
- **默认通过**（作者 2026-09-30：「验收一律默认通过」）：agent 交付时每条检查都过了，交付单直接「验收通过」、蓝图那件改
  「做完（J3 默认通过）」；有没过的检查才停在「待你验收（J3）」等人看。agent 不交付（不写怎么验、没验过）照样不算做完
- 人随时能打回（通过了的也能）：写一句为什么 → 回到「在做」，这句话记进日志，agent 下一圈读到照改
- 人在网页上点「验收通过」、或在对话里说「验收」，照旧记成人验收的（跟默认通过分得开）
- 验收关（S1-8 S2-39，样图 R3）：有岗位写着「验收」的 agent（不是交的那个）时，检查全过的先停在「等验收」、蓝图那件「待验收（J…）」，
  验收的 agent 复跑检查后 review 过（做完）或打回（回到在做，原来干活的先拿回去）；同一件被验收打回三次，第四次交上来就等人验。没有验收的 agent 照旧默认通过
- 项目显式配置 `自动化/交付策略.json` 为 checks-pass 时，以上旧验收路由改为检查全过直接通过，失败直接打回返工；施工准入和人的打回仍保留。
"""
from __future__ import annotations

import atomic
import json
import os
import re
from datetime import datetime
from pathlib import Path

import blueprint
import journal
import store
from project import Project
from skills import frontmatter

DIR = Path("自动化") / "交付"
STATES = ("待你验收", "等验收", "验收通过", "打回")
MAX_ROUNDS = 3                                        # 同一件被验收的 agent 打回三次：再交上来就交给人
AGENT_NO = "验收没过"                                  # 验收的 agent 打回时写的字（跟人打回分得开）
DEFAULT_PASS = True                                   # 作者 09-30：「验收一律默认通过」；要改回「等人验」把它改成 False
DEFAULT_BY = "默认通过（作者 09-30：「验收一律默认通过」）"
POLICY = Path("自动化") / "交付策略.json"            # 10-07 统一内置：从 自动化/内置/ 搬出来
CHECKS_PASS_BY = "自动验收（交付策略 checks-pass）"
_J = re.compile(r"J(\d+)")


def _dir(p: Project) -> Path:
    return p.root / DIR


def _checks_pass_policy(p: Project) -> bool:
    """只有项目显式配置才启用；缺失兼容旧流程，坏配置和链接不降级放行。"""
    import builtin
    try:
        f = builtin.path(p.root, POLICY.as_posix(), exists=False)
        if not f.exists():
            return False
        config = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise store.Refused(f"交付策略配置不可用：{e}") from e
    if (not isinstance(config, dict) or set(config) != {"version", "mode"}
            or type(config.get("version")) is not int or config["version"] != 1
            or config.get("mode") != "checks-pass"):
        raise store.Refused('交付策略配置必须是 {"version": 1, "mode": "checks-pass"}')
    return True


def _flat(s) -> str:
    return " ".join(str(s or "").split())


def _self_checks(body: str) -> list[dict]:
    """只读交付时的固定检查段；后来的独立复跑、意见和记账不能替换原自查。"""
    match = re.search(r"(?m)^## 怎么验的\s*$", body)
    if not match:
        return []
    section = re.split(r"(?m)^## ", body[match.end():], maxsplit=1)[0]
    out = []
    for line in section.splitlines():
        result = re.fullmatch(r"- (过了|没过) · (.+)", line.strip())
        if result:
            name, _, detail = result[2].partition("：")
            out.append({"name": name, "ok": result[1] == "过了", "detail": detail})
    return out


def _parse(f: Path) -> dict | None:
    text = f.read_text(encoding="utf-8", errors="replace")
    fm = frontmatter(text)
    m = _J.fullmatch(fm.get("编号", ""))
    if not m:
        return None
    body = text[text.find("\n---", 3) + 4:].lstrip() if text.startswith("---") else text
    checks = _self_checks(body)
    passed = None if not checks else all(c['ok'] for c in checks)
    if fm.get('自查全过') == '否':
        passed = False
    elif fm.get('自查全过') == '是' and passed is None:
        passed = True
    return {"code": fm["编号"], "n": int(m.group(1)), "goal": fm.get("目标", ""), "sub": fm.get("小目标", ""),
            "what": fm.get("做什么", ""), "state": fm.get("状态", ""), "at": fm.get("时间", ""), "by": fm.get("谁", ""),
            "checkpoint": fm.get("存档", ""), "run": fm.get("日志", ""), "plan": fm.get("计划", ""),
            "workorder": fm.get("开工单", ""), "for": [x for x in fm.get("为了", "").split("、") if x],
            "file": f.name, "body": body, "self_checks": checks, "self_checks_passed": passed}


def list_all(p: Project) -> list[dict]:
    """全部交付单：等你验收的在最上，其余新的在前。"""
    d = _dir(p)
    out = [x for f in d.glob("J*.md") if (x := _parse(f))] if d.is_dir() else []
    out.sort(key=lambda x: (x["state"] != "待你验收", -x["n"]))
    return out


def latest_by_task(p: Project) -> dict[tuple[str, str], dict]:
    """接续按交付编号选最新版；网页的待验收置顶顺序不代表时间先后。"""
    out = {}
    for j in sorted(list_all(p), key=lambda x: x['n'], reverse=True):
        out.setdefault((j['goal'], j['sub']), j)
    return out


def get(p: Project, code: str) -> dict:
    j = next((x for x in list_all(p) if x["code"] == code), None)
    if j is None:
        raise store.Refused(f"没有交付单 {code}")
    return j


def pending(p: Project) -> int:
    return sum(1 for x in list_all(p) if x["state"] == "待你验收")


def acceptors(p: Project, by: str) -> list[dict]:
    """能验这一张的 agent：岗位里有「验收」、不是交的那个（不验自己干的）。"""
    import agents
    me = agents.short(by)
    return [a for a in agents.list_all(p) if "验收" in a["roles"] and a["name"] != me and not a.get('paused')]


def rounds(p: Project, goal: str, sub: str) -> int:
    """这件被验收的 agent 打回过几次（人打回的不算）。"""
    return sum(1 for j in list_all(p) if j["goal"] == goal and j["sub"] == sub and j["state"] == "打回" and AGENT_NO in j["body"])


def _managed_author(p: Project, by: str) -> bool:
    import agents
    prof = agents.find(p, by) or {}
    return bool(prof.get('auto') or prof.get('plan_required'))


def self_checks_failed(j: dict) -> bool:
    checks = j.get('self_checks') or _self_checks(j.get('body', ''))
    return j.get('self_checks_passed') is False or any(not c['ok'] for c in checks)


def independent_pending(p: Project, j: dict) -> bool:
    """已等验收的照旧；自动员工的失败单可独立复查、打回，三次后交人。"""
    failed = self_checks_failed(j)
    import workflow_graph
    flow_managed = workflow_graph.requires_plan(p, j['goal'], j['sub'])
    if flow_managed and rounds(p, j['goal'], j['sub']) >= MAX_ROUNDS:
        return False
    if j['state'] not in ('等验收', '待你验收'):
        return False
    if j['state'] == '待你验收' and not (flow_managed or failed and _managed_author(p, j['by'])):
        return False
    if failed and _managed_author(p, j['by']):
        latest = latest_by_task(p).get((j['goal'], j['sub']))
        if latest and latest['code'] != j['code']:
            return False
    if failed and rounds(p, j['goal'], j['sub']) >= MAX_ROUNDS:
        return False
    return True


def last_note(j: dict) -> str:
    """交付单「你的意见」里最后一行：谁验的、怎么说的。"""
    lines = [x[2:] for x in j["body"].split("## 你的意见", 1)[-1].splitlines() if x.startswith("- ")] if "## 你的意见" in j["body"] else []
    return lines[-1] if lines else ""


def _next(conn, p: Project) -> str:
    n = int(store._meta(conn, "delivery_seq") or 0)
    n = max([n] + [x["n"] for x in list_all(p)]) + 1
    store._set_meta(conn, "delivery_seq", str(n))
    return f"J{n}"


def _set(f: Path, state: str, note: str) -> None:
    text = f.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^状态: .*$", f"状态: {state}", text, count=1)
    if "\n## 你的意见\n" not in text:
        text = text.rstrip("\n") + "\n\n## 你的意见\n"
    f.write_text(text.rstrip("\n") + f"\n- {datetime.now():%Y-%m-%d %H:%M} · {note}\n", encoding="utf-8")


def deliver(conn, p: Project, *, goal: str, sub: str, did: str, checks: list[dict] | None = None,
            files: list[str] | None = None, checkpoint: str = "", run: str = "", plan: str = "", by: str = "agent") -> dict:
    """agent 交一件；显式 checks-pass 策略自动验收或返工，未配置保留原验收路由。"""
    bp = blueprint.pyramid(p)
    g = blueprint.find(bp, goal)                            # 总蓝图的 S1，或模块蓝图（「文献」）
    s = next((x for x in g["subs"] if x["code"] == sub), None) if g else None
    if s is None:
        raise store.Refused(f"蓝图里没有 {goal} {sub}")
    if not _flat(did):
        raise store.Refused("要写清做了什么")
    checks = checks or []
    if not checks:
        raise store.Refused("要写清怎么验的（checks：每条 {name, ok, detail}）——没验过的不算交付")
    _checks_pass_policy(p)                                # 配置无效时，写交付单和编号之前拒绝
    import construction_plans as cp
    approved = cp.require_approved(p, goal, sub, by, files=files or [])
    import workflow_graph
    flow_managed = workflow_graph.requires_plan(p, goal, sub)
    import agents, claims, workorders
    prof = agents.find(p,by)
    if prof and (prof.get('auto') or prof.get('plan_required') or flow_managed):
        if s['status'] == 'ok' or any(j['goal']==goal and j['sub']==sub and independent_pending(p,j) for j in list_all(p)):
            raise store.Refused('本件已完成或已有交付待独立验收，不能重复交付')
    if prof and (prof.get('plan_required') or flow_managed):
        if workorders.paused(conn) or prof.get('paused'):
            raise store.Refused('项目或员工已暂停，恢复后再交付')
        if '干活' not in agents.jobs(prof) or not agents.allows(prof,g,s):
            raise store.Refused('当前岗位、工种或范围不允许施工交付')
        if not any(r['goal']==goal and r['sub']==sub for r in claims.of(conn,agents.actor(prof['name']))):
            raise store.Refused('必须先认领本件，才能交施工结果')
    if approved:
        if plan and plan != approved['formal_path']:
            raise store.Refused('交付引用的计划不是当前审核通过的施工计划')
        plan = approved['formal_path']
    missing = [x for x in (files or []) if not __import__("governance_paths").resolve(p, x).exists()]
    if missing:
        raise store.Refused(f"这些东西找不到：{'、'.join(missing)}（从项目根写，比如 资料/文献/L1 …/笔记.md）")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    import workorders                                      # 交的时候在跑的那张开工单（开工单也要读交付单，用到再引）
    wo = workorders.running(p)
    if wo:
        import readiness
        # 对话中的独立施工不能串到另一张正在跑的单上；归属只看明确目标范围。
        matching = any(code == goal and (not part or part == sub or part in s.get("for", []))
                       for code, part in map(readiness.split_target, wo["target"]))
        if not matching:
            wo = None
    with store.tx(conn):
        # 停用与交付共享写事务：不能用事务前的准入结果落新记录。
        cp.require_approved(p, goal, sub, by, files=files or [])
        if flow_managed and workorders.paused(conn):
            raise store.Refused('项目已暂停，恢复后再交付')
        auto_accept = _checks_pass_policy(p)
        if auto_accept and (not isinstance(checks, list) or any(not isinstance(c, dict) for c in checks)):
            raise store.Refused("每条检查必须填写 {name, ok, detail}，只有 ok 为 true 才算通过")
        passed = [c.get("ok") is True if auto_accept else bool(c.get("ok")) for c in checks]
        code = _next(conn, p)
        ok = all(passed)
        lines = [f"- {'过了' if good else '没过'} · {_flat(c.get('name'))}" + (f"：{_flat(c.get('detail'))}" if c.get("detail") else "")
                 for c, good in zip(checks, passed)]
        text = (f"---\n编号: {code}\n目标: {goal}\n小目标: {sub}\n做什么: {_flat(s['what'])}\n状态: 待你验收\n自查全过: {'是' if ok else '否'}\n"
                f"时间: {now}\n谁: {by}\n存档: {_flat(checkpoint)}\n日志: {_flat(run)}\n计划: {_flat(plan)}\n"
                f"开工单: {wo['code'] if wo else ''}\n为了: {'、'.join(s.get('for') or [])}\n---\n"
                f"# {code} · {goal} {sub} {_flat(s['what'])}\n\n"
                f"> {'检查全过' if ok else '有没过的检查，看下面'} · 怎么验（蓝图里写的）：{s['how'] or '（蓝图里没写，看计划）'}"
                + (f" · 为了 {goal} {'、'.join(s['for'])}（验收时对着这几条需求看效果）" if s.get("for") else "") + "\n\n"
                f"## 做了什么\n\n{did.strip()}\n\n## 怎么验的\n\n" + "\n".join(lines) + "\n\n"
                f"## 东西在哪\n\n" + ("\n".join(f"- {x}" for x in files) if files else "- （没列）") + "\n")
        d = _dir(p)
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{code} {goal} {sub}.md"
        tmp = f.with_suffix(".md.tmp")
        tmp.write_text(text, encoding="utf-8")
        atomic.replace(tmp, f)
        try:
            blueprint.set_status(p, goal, sub, f"待你验收（{code}）")
        except ValueError as e:                             # 蓝图那一格改不上：刚写的交付单收回，不留一张空单（10-01 J31 就这样留下过）
            f.unlink(missing_ok=True)
            raise store.Refused(str(e))
        store.log(conn, by, "交付", code, f"{goal} {sub}")
    if auto_accept:
        if ok:
            with store.tx(conn):
                _set(f, "验收通过", f"{CHECKS_PASS_BY}；检查全过，不满意随时打回")
                blueprint.set_status(p, goal, sub, f"做完（{code} 自动验收）")
                store.log(conn, CHECKS_PASS_BY, "验收通过", code, f"{goal} {sub}")
            journal.add(conn, p, f"自动验收通过 {code}：{goal} {sub} {_flat(s['what'])}", by=by, kind="验收")
        else:
            reject(conn, p, code, "自查未全部通过，请修复后实际复验再交付", by=CHECKS_PASS_BY)
        _book(conn, p, f, g, goal, sub, code, _flat(s["what"]), files or [], by)
        return get(p, code)
    managed_author = _managed_author(p, by) or flow_managed
    gate = [a for a in acceptors(p,by) if __import__('agents').allows(a,g,s)] if ok or managed_author else []
    if flow_managed:
        gate = [a for a in gate if not workflow_graph.action_reason(p, "review_delivery", goal, sub, a['name'])]
    tired = bool(gate) and rounds(p, goal, sub) >= MAX_ROUNDS
    import agents
    rookie = (agents.find(p, by) or {}).get("level") == "见习"   # 见习交的每件都要验（S1-8 S2-41）：没有验收的 agent 就等人
    if gate and not tired and (ok or independent_pending(p, get(p, code))):
        with store.tx(conn):
            result = '检查全过，等验收的 agent 复跑' if ok else '自查有失败，等独立员工复查并打回；修复后须重新交付'
            _set(f, "等验收", f"{result}（{'、'.join(a['code'] + ' ' + a['name'] for a in gate)}）")
            blueprint.set_status(p, goal, sub, f"待验收（{code}）")
            store.log(conn, by, "等验收", code, f"{goal} {sub}")
    elif tired:                                            # 验收打回三次了：交给人
        with store.tx(conn):
            _set(f, "待你验收", f"验收的 agent 打回过 {MAX_ROUNDS} 次了，这次交给你看")
    elif (rookie or managed_author) and ok:
        with store.tx(conn):
            _set(f, "待你验收", ("见习交的要验收" if rookie else "本次交付需要独立验收") + "：现在没有符合岗位的验收员工，等你看")
    elif DEFAULT_PASS and ok:
        with store.tx(conn):
            _set(f, "验收通过", f"{DEFAULT_BY}；不满意随时打回")
            blueprint.set_status(p, goal, sub, f"做完（{code} 默认通过）")
            store.log(conn, "默认通过", "验收通过", code, f"{goal} {sub}")
        journal.add(conn, p, f"默认通过 {code}：{goal} {sub} {_flat(s['what'])}", by=by, kind="验收")
    _book(conn, p, f, g, goal, sub, code, _flat(s["what"]), files or [], by)
    return get(p, code)


def _book(conn, p: Project, f: Path, g: dict, goal: str, sub: str, code: str, what: str, files: list[str], by: str) -> None:
    """交完：放手（这件、核心锁），在本机 git 记一次（只记这个 agent 该管的路径）。记不上不挡交付，交付单里写一句。"""
    import claims
    import vcs
    paths = [f"{DIR.as_posix()}/{f.name}", g["file"], *files, *vcs.RECORD_PATHS]
    paths += [f"资料/{m}" for m in claims.lanes_of(g) if (p.materials / m).is_dir()]
    if claims.holds_core(conn, by):
        paths += vcs.CORE_PATHS
    try:
        h = vcs.commit(p, paths, agent=by, message=f"{code} · {goal} {sub} · {what}"[:200])
        note = f"本机 git：{h}（作者 {by}）" if h else ""
    except (RuntimeError, OSError) as e:
        note = f"本机 git 没记上：{e}"
    if note:
        with open(f, "a", encoding="utf-8") as w:
            w.write(f"\n## 记账\n\n- {note}\n")
    claims.release(conn, goal, sub, by, note="交付 " + code)
    claims.release(conn, claims.CORE, "", by, note="交付 " + code)


def accept(conn, p: Project, code: str, *, by: str = "人") -> dict:
    j = get(p, code)
    if j["state"] not in ("待你验收", "等验收"):          # 等验收的人也能直接点过
        raise store.Refused(f"{code} 已经是「{j['state']}」了")
    with store.tx(conn):
        _set(_dir(p) / j["file"], "验收通过", f"{by} 验收通过")
        blueprint.set_status(p, j["goal"], j["sub"], f"做完（{code} 验收）")
        store.log(conn, by, "验收通过", code, f"{j['goal']} {j['sub']}")
    journal.add(conn, p, f"验收通过 {code}：{j['goal']} {j['sub']} {j['what']}", by=by, kind="验收")
    return get(p, code)


def accept_by_word(conn, p: Project, code: str, said: str, *, agent: str) -> dict:
    """人在对话里说了「验收」「可以」：agent 照原话记（作者 09-28：「不用去自动化页交付，我让你执行就可以执行了」）。"""
    import workflow_graph
    delivery = get(p, code)
    if _managed_author(p, agent) or _managed_author(p, delivery['by']) or workflow_graph.requires_plan(p, delivery['goal'], delivery['sub']):
        raise store.Refused('自动化员工及其交付不能用口头验收绕过独立实查；请由其他验收员工通过 review_delivery 提交实际检查，原失败须打回修复重交；人仍可在网页直接验收')
    said = " ".join((said or "").split())
    if not said:
        raise store.Refused("要写上人的原话（他在对话里怎么说的）")
    return accept(conn, p, code, by=f"人（对话里说的：「{said[:60]}」，{agent} 记的）")


def _review_context(conn, p: Project, code: str, by: str, ok: bool, checks: list[dict]) -> tuple[dict, dict]:
    """只核对现状；写入事务内再读一次，不能沿用等锁前的员工或交付状态。"""
    import agents
    import claims
    a = agents.require(p, by)
    if "验收" not in a["roles"]:
        raise store.Refused(f"{a['code']} {a['name']} 的岗位里没有「验收」：要验，请人在档案上加")
    j = get(p, code)
    if not independent_pending(p, j):
        raise store.Refused(f"{code} 是「{j['state']}」，不用验")
    if agents.short(j["by"]) == a["name"]:
        raise store.Refused("不验自己干的")
    import workorders
    if workorders.paused(conn) or a.get('paused'):
        raise store.Refused('项目或验收员工已暂停')
    g = blueprint.find(blueprint.pyramid(p), j['goal'])
    x = next((s for s in (g or {}).get('subs',[]) if s['code'] == j['sub']), None)
    if not g or not x or not agents.allows(a,g,x):
        raise store.Refused('不在你的验收范围或工种不匹配')
    import workflow_graph
    flow_reason = workflow_graph.action_reason(p, "review_delivery", j['goal'], j['sub'], by)
    if flow_reason:
        raise store.Refused(flow_reason)
    managed = bool(a.get('auto') or a.get('plan_required') or _managed_author(p, j['by']) or workflow_graph.requires_plan(p,j['goal'],j['sub']))
    if ok and self_checks_failed(j):
        raise store.Refused('原交付自查有失败，不能验收通过；请打回修复后重新交付，再独立复验')
    if ok and managed and not checks:
        raise store.Refused('独立验收通过必须提交实际复跑检查')
    if ok and not all(bool(x.get('ok')) for x in checks):
        raise store.Refused('复跑有失败，不能验收通过')
    me = agents.actor(a['name'])
    held = next((r for r in claims.active(conn) if r['goal'] == '验收' and r['sub'] == code), None)
    if held and held['agent'] != me:
        raise store.Refused(f"{code} 正在由其他员工 {held['agent']} 验收，不能代替它提交结果")
    if managed and held is None:
        raise store.Refused('自动化独立验收必须先认领本张交付，再提交复跑结果')
    return a, j


def review(conn, p: Project, code: str, ok: bool, notes: str, *, by: str, checks: list[dict] | None = None) -> dict:
    """验收的 agent 验一张（S1-8 S2-39）：照交付单上的检查自己复跑、看东西对不对。过 → 做完；不过 → 打回给干活的（写清哪条）。"""
    import agents
    import claims
    checks = checks or []                                  # 旧员工未传 checks 的调用继续兼容；自动化仍要求实际检查。
    a, _ = _review_context(conn, p, code, by, ok, checks)
    notes = _flat(notes)
    if not notes:
        raise store.Refused("写一句你看到了什么（过了也写，没过写清哪条、实际看到什么）")
    me = agents.actor(a["name"])
    with store.tx(conn):
        a, j = _review_context(conn, p, code, me, ok, checks)
        f = _dir(p) / j["file"]
        who = f"{a['code']} {a['name']}"
        if checks:
            with open(f, "a", encoding="utf-8") as w:
                w.write(f"\n## 验收复跑（{who}）\n\n" + "\n".join(f"- {'过了' if c.get('ok') else '没过'} · {_flat(c.get('name'))}"
                                                         + (f"：{_flat(c.get('detail'))}" if c.get("detail") else "") for c in checks) + "\n")
        if ok:
            _set(f, "验收通过", f"{who} 验收过了：{notes}")
            blueprint.set_status(p, j["goal"], j["sub"], f"做完（{code} 验收 · {a['code']}）")
            store.log(conn, me, "验收通过", code, f"{j['goal']} {j['sub']}")
        else:
            _set(f, "打回", f"{who} {AGENT_NO}：{notes}")
            blueprint.set_status(p, j["goal"], j["sub"], f"在做（{code} {AGENT_NO}：{notes[:40]}）")
            store.log(conn, me, "打回", code, f"{j['goal']} {j['sub']}")
    claims.release(conn, "验收", code, me, note=("过了" if ok else "打回"))
    journal.add(conn, p, f"{'验收通过' if ok else '验收打回'} {code}（{j['goal']} {j['sub']} {j['what']}）：{notes}", by=me, kind="验收" if ok else "打回")
    return get(p, code)


def reject(conn, p: Project, code: str, reason: str, *, by: str = "人") -> dict:
    reason = (reason or "").strip()
    if not reason:
        raise store.Refused("打回要写一句为什么，agent 照着改")
    j = get(p, code)
    if j["state"] == "打回":                               # 通过了的（包括默认通过）也能打回
        raise store.Refused(f"{code} 已经打回过了")
    with store.tx(conn):
        _set(_dir(p) / j["file"], "打回", f"{by} 打回：{_flat(reason)}")
        blueprint.set_status(p, j["goal"], j["sub"], f"在做（{code} 打回：{_flat(reason)[:40]}）")
        store.log(conn, by, "打回", code, f"{j['goal']} {j['sub']}")
    journal.add(conn, p, f"打回 {code}（{j['goal']} {j['sub']} {j['what']}）：{reason}", by=by, kind="打回")
    return get(p, code)
