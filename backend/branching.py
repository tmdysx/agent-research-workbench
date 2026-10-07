"""排枝（S1-8 S2-58；需-28）：档位 3「分枝并行」、档位 4「优中选优」时，全自动开工每分钟在主干上转一圈——

作者 10-03：「高档位就是，同时开多个agent，多个节点多个分支一起做项目，然后优中选优」。
- 开新的：蓝图里能做、没人领、该开枝的件（设置「哪些件开枝」），长枝（档 4 一件 K 根，从同一档长），
  挑能做这件的员工（尽量不同模型）派上去、在网页终端开窗口；主干上替这件记一个「世界树:比-n」的认领，主干的人就不去碰它
- 结果实：枝上那件交付了、检查全过（打回以后要新交的）→ 枝里自动结果实（交付单的做什么当 demo 说明，检查照抄）
- 挑：一件一张比较单（自动化/世界树/比较/比-n.json）。几根都结了（或第一颗果子之后等够设置的小时数）→「等挑」：
  检查没全过的先筛掉；照设置谁来挑——验收的员工（next_task 给它一件「挑果实」）· G1 · 你（网页上点）· 按检查自动挑
  （没有能挑的员工时也按检查挑）；挑好了照设置直接合或等你点；没挑中的砍掉；都不行就全打回，接着长
- 枝上窗口关了、员工没停：再给它开一个
受设置管着：同时最多几个 agent、最多几根活着的枝、空间上限（worldtree.grow 里查）、自动开过多久不再开。
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import agents
import claims
import store
import worldtree
from project import Project

DIR = "自动化/世界树/比较"
OWNER = "世界树:"                          # 主干上替枝记的认领：世界树:比-3
PICK = "挑果实"                            # 挑的人领的：claims 里 goal=挑果实、sub=比-3
OPEN = ("长着", "等挑", "等你点合")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _dir(p: Project) -> Path:
    return p.root / DIR


def groups(p: Project) -> list[dict]:
    """全部比较单，新的在前。"""
    out = []
    for f in _dir(p).glob("比-*.json") if _dir(p).is_dir() else []:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda g: -int(g["code"].split("-")[1]))


def group(p: Project, code: str) -> dict:
    g = next((x for x in groups(p) if x["code"] == code), None)
    if g is None:
        raise store.Refused(f"没有比较单 {code}")
    return g


def _save(p: Project, g: dict) -> None:
    f = _dir(p) / f"{g['code']}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def _new_code(p: Project) -> str:
    return f"比-{1 + max([0] + [int(g['code'].split('-')[1]) for g in groups(p)])}"


def _knob(conn, p: Project, name: str):
    import knobs
    return knobs.get(conn, name) if conn is not None else knobs.peek(p, name)


def scoped(conn, x: dict, p: Project | None = None) -> bool:
    """这件该不该开枝：设置「哪些件开枝」——全部 · 只有动到核心的（任务写了〔程序〕〔网页〕的算）。"""
    if _knob(conn, p, "branch_scope") == "全部":
        return True
    return bool({"程序", "网页"} & set(agents.task_crafts(x)))


def on_branches(conn, p: Project, x: dict) -> str:
    """主干上这件归不归枝做：档位 3、4，这里是主干，这件该开枝 → 写一句为什么（dispatch 不让主干的人领）。conn 可以是 None。"""
    try:
        if _knob(conn, p, "level") < 3 or worldtree.is_branch(p) or not scoped(conn, x, p):
            return ""
    except Exception:
        return ""
    return "档位 3、4：这件在世界树的枝上做（设置 → 自动化）"


# ---------------------------------------------------------------- 结果实

def _fruit_if_done(conn, p: Project, b: dict) -> bool:
    """枝上那件交付了、检查全过（打回以后要新交的）→ 枝里结果实。→ 结了没有。"""
    import deliveries
    if b.get("state") != "长着" or not b.get("item") or not b.get("exists"):
        return False
    goal, _, sub = b["item"].partition(" ")
    bp = Project(Path(b["path"]))
    j = deliveries.latest_by_task(bp).get((goal, sub))
    if not j or j["state"] == "打回" or not j.get("self_checks_passed"):
        return False
    last_reject = max([r.get("at", "") for r in b.get("rejected") or []] or [""])
    if last_reject and j["at"] <= last_reject:
        return False                                   # 打回以前交的那张不算，等新交的
    bc = store.connect(bp.db_path)
    try:
        worldtree.bear_fruit(bc, bp, demo=f"{j['code']} · {j['what']}"[:300], checks=j.get("self_checks") or [], by=j.get("by") or "自动排枝")
    finally:
        bc.close()
    store.log(conn, "自动开工", "枝上结果实", b["code"], f"{b['item']} · {j['code']}")
    return True


# ---------------------------------------------------------------- 挑

def _candidates(p: Project, g: dict) -> list[dict]:
    out = []
    for b in worldtree.list_branches(p):
        if b["code"] not in g["branches"] or b["state"] != "结果了":
            continue
        cs = b.get("checks") or []
        try:
            ch = worldtree.changes(p, b["code"])["counts"]
            changed = ch["take"] + ch["both"] + ch["delete"]
        except Exception:
            changed = None
        out.append({"branch": b["code"], "name": b["name"], "agent": (b.get("agents") or [""])[0], "demo": b.get("demo", ""),
                    "checks": len(cs), "checks_ok": bool(cs) and all(c.get("ok") for c in cs), "changed": changed,
                    "fruit_at": b.get("fruit_at", ""), "port": b.get("port")})
    return out


def _reviewers(p: Project, g: dict) -> list[dict]:
    """能挑这张的员工：自动运行的、岗位有验收的、没在这几根枝上干活的（不挑自己做的）。"""
    import autolaunch
    workers = set(g.get("agents") or [])
    return [a for a in agents.list_all(p) if autolaunch._automatic(a) and "验收" in agents.jobs(a) and a["code"] not in workers]


def auto_pick(conn, p: Project, g: dict, why: str = "按检查自动挑") -> dict:
    """按检查挑：检查全过的里面，检查条数多的、改动少的、先结的。一个都没全过：全打回接着长。"""
    ok = [c for c in g["candidates"] if c["checks_ok"]]
    if not ok:
        return pick(conn, p, g["code"], "", f"{why}：没有检查全过的果实，打回接着做", by="自动开工")
    best = sorted(ok, key=lambda c: (-c["checks"], c["changed"] if c["changed"] is not None else 1e9, c["fruit_at"]))[0]
    return pick(conn, p, g["code"], best["branch"],
                f"{why}：{best['branch']} 检查 {best['checks']} 条全过、改了 {best['changed']} 个文件" + (f"（{len(ok)} 根里挑的）" if len(ok) > 1 else ""),
                by="自动开工")


def pick(conn, p: Project, code: str, branch: str, why: str, *, by: str) -> dict:
    """挑一根合回（branch 空 = 都不行，全打回接着长）。设置「挑完怎么合」是等你点、挑的又不是人：先记下挑了哪根，等人点「合」。"""
    import knobs
    g = group(p, code)
    why = " ".join((why or "").split())
    if not why:
        raise store.Refused("写一句为什么挑这根（或为什么都不行）")
    if g["state"] not in ("等挑", "等你点合"):
        raise store.Refused(f"{code} 现在是「{g['state']}」，不用挑")
    human = by == "人" or by.startswith("人")
    if g["state"] == "等你点合" and not human:
        raise store.Refused(f"{code} 已经挑好了，等人点合")
    if not branch:                                      # 都不行：每根打回，接着长
        for c in g["candidates"]:
            try:
                worldtree.reject(conn, p, c["branch"], by=by, why=why)
            except store.Refused:
                pass
        g.setdefault("history", []).append({"at": _now(), "by": by, "act": "都打回", "why": why})
        g.update(state="长着", candidates=[], first_fruit="")
        _done_pick(conn, code)
        _save(p, g)
        store.log(conn, by, "比较单都打回", code, why[:200])
        return g
    if branch not in [c["branch"] for c in g["candidates"]]:
        raise store.Refused(f"{branch} 不在 {code} 的候选里（只有结了果的能挑）")
    if knobs.get(conn, "after_pick") == "等你点" and not human:
        g.update(state="等你点合", pick=branch, why=why, by=by, picked_at=_now())
        g.setdefault("history", []).append({"at": _now(), "by": by, "act": f"挑了 {branch}，等人点合", "why": why})
        _save(p, g)
        _done_pick(conn, code)
        store.log(conn, by, "挑了果实", code, f"{branch}（等人点合）：{why}"[:200])
        return g
    r = worldtree.merge(conn, p, branch, by=by)
    for b in g["branches"]:                              # 没挑中的：砍掉（进 .回收，能拿回来）
        if b == branch:
            continue
        try:
            worldtree.cut(conn, p, b, by=by, why=f"{code} 挑了 {branch}")
        except store.Refused:
            pass
    g.update(state="合了", pick=branch, why=why, by=by, picked_at=_now(), merged=r)
    g.setdefault("history", []).append({"at": _now(), "by": by, "act": f"合了 {branch}", "why": why})
    _save(p, g)
    _done_pick(conn, code)
    claims.release(conn, g["goal"], g["sub"], note=f"{code} 合了 {branch}")   # 主干上替枝记的认领放掉
    store.log(conn, by, "比较单合了", code, f"{branch}：{why}"[:200])
    return g


def _done_pick(conn, code: str) -> None:
    claims.release(conn, PICK, code)


def pick_job(conn, p: Project, agent: str) -> dict | None:
    """给验收的员工（或 G1）一张等挑的比较单，替它领下（同一张只给一个人）。"""
    import knobs
    picker = knobs.get(conn, "picker")
    a = agents.find(p, agent)
    if not a:
        return None
    g1 = agents.find(p, "G1")
    for g in sorted((x for x in groups(p) if x["state"] == "等挑"), key=lambda x: x["code"]):
        if picker == "G1" and not (g1 and g1["code"] == a["code"]):
            continue
        if picker == "验收的员工" and ("验收" not in agents.jobs(a) or a["code"] in (g.get("agents") or [])):
            continue
        if picker in ("你", "按检查自动挑"):
            continue
        try:
            claims.claim(conn, PICK, g["code"], agent, [f"{PICK} {g['code']}"], g["item"])
        except store.Refused:
            continue
        return g | {"how": "看每根枝的果实：demo 说明、检查、branch_changes 看改动（能的话进枝的文件夹跑一遍测试）；"
                            "挑一根最好的，调用 pick_fruit(code, branch, why) 合回；都不行就 pick_fruit(code, '', why) 打回，写清哪里不对"}
    return None


# ---------------------------------------------------------------- 每分钟一圈

def _refresh(conn, p: Project, g: dict, now: float) -> None:
    """一张比较单：结果实、到点了就进「等挑」、照设置挑。"""
    import knobs
    bs = {b["code"]: b for b in worldtree.list_branches(p) if b["code"] in g["branches"]}
    for b in bs.values():
        if _fruit_if_done(conn, p, b):
            bs[b["code"]] = worldtree.get(p, b["code"])
    claims.beat(conn, OWNER + g["code"])                  # 主干上替枝记的认领续上
    if g["state"] != "长着":
        return
    fruited = [b for b in bs.values() if b["state"] == "结果了"]
    growing = [b for b in bs.values() if b["state"] == "长着"]
    if fruited and not g.get("first_fruit"):
        g["first_fruit"] = _now()
        _save(p, g)
    if not fruited:
        if not growing:                                   # 枝都没了（人砍了、合了）：这张结束
            g.update(state="没有能合的", why="枝都不在了")
            _save(p, g)
            claims.release(conn, g["goal"], g["sub"], note=f"{g['code']} 的枝都不在了")
        return
    waited = (now - datetime.strptime(g["first_fruit"], "%Y-%m-%d %H:%M").timestamp()) / 3600
    if growing and waited < knobs.get(conn, "compare_wait_h"):
        return                                            # 还有在长的、没等够：再等等
    g.update(state="等挑", candidates=_candidates(p, g), ready_at=_now())
    _save(p, g)
    store.log(conn, "自动开工", "比较单等挑", g["code"], f"{g['item']} · {len(g['candidates'])} 颗果实")
    picker = knobs.get(conn, "picker")
    if picker == "按检查自动挑" or (picker == "验收的员工" and not _reviewers(p, g)):
        auto_pick(conn, p, g, "按检查自动挑" if picker == "按检查自动挑" else "没有能挑的验收员工，按检查自动挑")


def tick(conn, p: Project, *, running: int, alive: set, call, now: float | None = None) -> list[str]:
    """档位 3、4 的一圈：先照看已有的比较单，再在能开的范围里给新的件长枝、派人。→ 这圈开了谁。running：现在开着几个员工窗口。"""
    import autolaunch
    import dispatch
    import knobs
    now = time.time() if now is None else now
    level = knobs.get(conn, "level")
    if level < 3 or worldtree.is_branch(p):
        return []
    started = []
    for g in groups(p):
        if g["state"] in OPEN:
            try:
                _refresh(conn, p, g, now)
            except (store.Refused, OSError, ValueError) as e:
                store.log(conn, "自动开工", "照看比较单出错", g["code"], str(e)[:200])
    most = knobs.get(conn, "max_agents")
    # 枝上窗口关了、员工没停：再开一个
    for b in worldtree.live(p):
        if running >= most:
            break
        if b["state"] != "长着" or not b.get("item") or not b.get("agents"):
            continue
        key = b["agents"][0]
        if key in alive:
            continue
        st = autolaunch.runner_state(Project(Path(b["path"])), key)
        if st.get("status") in autolaunch.BLOCK_RESTART:
            continue
        last = float(store._meta(conn, autolaunch.LAST + key) or 0)
        if now - last < autolaunch.cooldown(conn):
            continue
        goal, _, sub = b["item"].partition(" ")
        try:
            worldtree.assign(conn, p, b["code"], key, goal, sub, by="自动开工", open_window=True, call=call, plan_free=True)
        except Exception as e:
            store.log(conn, "自动开工", "枝上开窗口失败", b["code"], str(e)[:200])
            continue
        with store.tx(conn):
            store._set_meta(conn, autolaunch.LAST + key, str(now))
        running += 1
        alive.add(key)
        started.append(f"{b['code']} · {key}：接着做 {b['item']}")
    # 开新的
    k = knobs.get(conn, "per_item") if level == 4 else 1
    staff = [a for a in agents.list_all(p) if autolaunch._automatic(a) and "干活" in agents.jobs(a)]
    held = {(r["goal"], r["sub"]) for r in claims.active(conn)}
    busy_items = {g["item"] for g in groups(p) if g["state"] in OPEN}
    import deliveries
    latest = deliveries.latest_by_task(p)
    for g0, x in dispatch.ready_items(p):
        if running >= most:
            break
        item = f"{g0['code']} {x['code']}"
        if (g0["code"], x["code"]) in held or item in busy_items or not scoped(conn, x):
            continue
        can = [a for a in staff if dispatch._work_reason(p, a, g0, x, latest) in ("", on_branches(conn, p, x))]
        if not can:
            continue
        free = [a for a in can if a["code"] not in alive
                and now - float(store._meta(conn, autolaunch.LAST + a["code"]) or 0) >= autolaunch.cooldown(conn)
                and autolaunch.runner_state(p, a["code"]).get("status") not in autolaunch.BLOCK_RESTART]
        want = min(k, len(can), most - running)
        if want < min(k, len(can)) or len(free) < want or want < 1:
            continue                                      # 人不够：这一件先不开，等有空的（不拿一根顶几根）
        by_model: dict[str, list] = {}                   # 尽量不同模型：按模型分堆，轮着各挑一个
        for a in free:
            by_model.setdefault(agents._model(a), []).append(a)
        team = []
        while len(team) < want:
            for m in list(by_model):
                if by_model[m] and len(team) < want:
                    team.append(by_model[m].pop(0))
        code = _new_code(p)
        try:
            claims.claim(conn, g0["code"], x["code"], OWNER + code, claims.lanes_of(g0, x), x["what"])
        except store.Refused:
            continue                                      # 道上有人：换下一件
        g = {"code": code, "item": item, "goal": g0["code"], "sub": x["code"], "what": x["what"], "level": level, "k": want,
             "branches": [], "agents": [a["code"] for a in team], "state": "长着", "at": _now(), "first_fruit": "",
             "candidates": [], "pick": "", "why": "", "by": "", "history": []}
        base = "现在"
        try:
            for a in team:
                b = worldtree.grow(conn, p, name=f"{x['code']} {a['code']}", by="自动开工", why=f"{item} {x['what']}"[:200],
                                   base=base, for_=item, item=item, group=code)
                base = b["base"]                          # 同一件的几根从同一档长
                g["branches"].append(b["code"])
                _save(p, g)
                worldtree.assign(conn, p, b["code"], a["code"], g0["code"], x["code"], by="自动开工", open_window=True, call=call, plan_free=True)
                with store.tx(conn):
                    store._set_meta(conn, autolaunch.LAST + a["code"], str(now))
                running += 1
                alive.add(a["code"])
                started.append(f"{b['code']} · {a['code']} {a['name']}：{item}")
        except store.Refused as e:                        # 枝太多、地方不够：停下，下一圈再看
            store.log(conn, "自动开工", "没长枝", item, str(e)[:200])
            if not g["branches"]:
                claims.release(conn, g0["code"], x["code"], note=str(e)[:100])
                break
            g["k"] = len(g["branches"])
            _save(p, g)
            break
        store.log(conn, "自动开工", "开了比较单", code, f"{item} · {len(team)} 根枝：{'、'.join(g['branches'])}")
        busy_items.add(item)
    return started
