"""Codex 员工自动接续：发现工作、认领、开网页终端，状态用普通文件保存。

施工、施工计划审核、交付验收均走 dispatch.next_task 的同一权限与暂停关卡。
只启动档案明确开启自动运行的 Codex；没有工作或仅在待审时不会反复开空窗口。
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import agents
import atomic
import claims
import dispatch
import plugins
import store
import workorders
from project import Project

KEY, MAX_KEY, LAST = "auto_launch", "auto_launch_max", "auto_launch_at:"
TERM = "网页终端"
COOLDOWN = 600                                   # 秒：同一个 agent 自动开过以后，这么久内不再自动开
DEFAULT_MAX = 3
RUNNER_DIR = Path("自动化") / "运行状态"
RUNNER_STATUSES = ("running", "waiting", "idle", "stopped", "limit", "failed", "ready")
BLOCK_RESTART = {"stopped", "limit", "failed"}
RUN_ACTIONS = {"execute", "submit_plan", "review_plan", "review_delivery", "review_draft", "draft", "pick_fruit", "write_digest", "write_rewrite", "review_rewrite"}


def settings(conn) -> dict:
    import knobs
    mx = store._meta(conn, MAX_KEY)
    return {"on": store._meta(conn, KEY) == "1", "max": int(mx) if (mx or "").isdigit() else DEFAULT_MAX, "level": knobs.get(conn, "level")}


def cooldown(conn) -> int:
    """同一个员工自动开过以后多久内不再开（秒）：照设置（S1-8 S2-57），默认 10 分钟。"""
    try:
        import knobs
        return int(knobs.get(conn, "cooldown_min")) * 60
    except Exception:
        return COOLDOWN


def set_settings(conn, *, on: bool | None = None, max_: int | None = None) -> dict:
    with store.tx(conn):
        if on is not None:
            store._set_meta(conn, KEY, "1" if on else "0")
    if max_ is not None:                                  # 跟设置里的「同时最多几个」是同一个数（S1-8 S2-57）
        if not 1 <= max_ <= 12:
            raise store.Refused("同时最多开几个：1～12")
        import knobs
        lv = knobs.get(conn, "level")
        patch = {"max_agents": max_} | ({"level": 2} if lv == 1 and max_ > 1 else {})
        knobs.set_many(conn, patch, by="同时最多几个")    # 一条线只开一个：多开就是档位 2
    return settings(conn)


def _state_file(p: Project, key: str) -> tuple[dict, Path]:
    a = agents.get(p, key)
    return a, p.root / RUNNER_DIR / (a["code"] + ".json")


def runner_state(p: Project, key: str) -> dict:
    """只读状态。未运行过也是 ready；损坏记录不能自动当成首次运行。"""
    a, f = _state_file(p, key)
    base = {"code": a["code"], "name": a["name"], "status": "ready", "action": "idle", "reason": "",
            "current": "", "last_result": "", "cycles": 0, "rounds": 0, "blocked": [], "failure_counts": {},
            "updated": "", "history": []}
    if not f.is_file():
        return base
    try:
        raw = json.loads(f.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict) or raw.get("status") not in RUNNER_STATUSES:
            raise ValueError("运行状态不完整")
        return base | raw | {"code": a["code"], "name": a["name"]}
    except (OSError, ValueError, UnicodeDecodeError):
        return base | {"status": "failed", "reason": "运行状态读不了；检查后明确恢复再运行"}


@contextmanager
def _file_lock(p: Project, name: str):
    """多个 MCP 进程和网页后台共用短锁；锁在索引缓存，正本不依赖它。"""
    d = p.index_dir / "运行锁"
    d.mkdir(parents=True, exist_ok=True)
    with (d / (name + ".lock")).open("a+b") as stream:
        if not stream.seek(0, os.SEEK_END):
            stream.write(b"\x00")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            lock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            unlock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            lock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            unlock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        for _ in range(100):
            try:
                lock()
                break
            except OSError:
                time.sleep(0.01)
        else:
            raise store.Refused("运行状态正在更新，请稍后再试")
        try:
            yield
        finally:
            stream.seek(0)
            unlock()


def write_runner_state(p: Project, key: str, status: str | None = None, **updates) -> dict:
    """合并状态，不抹掉其他进程记录的次数、失败和上一轮结果。供 MCP 使用。"""
    a, f = _state_file(p, key)
    if status is not None and status not in RUNNER_STATUSES:
        raise store.Refused("运行状态应是 running/waiting/idle/stopped/limit/failed/ready")
    with _file_lock(p, a["code"]):
        state = runner_state(p, a["code"])
        old_status = state["status"]
        values = {k: v for k, v in updates.items() if k not in ("code", "name", "updated", "history")}
        if "rounds" in values and "cycles" not in values:
            values["cycles"] = values["rounds"]
        elif "cycles" in values and "rounds" not in values:
            values["rounds"] = values["cycles"]
        state.update(values)
        if status is not None:
            state["status"] = status
        state["updated"] = datetime.now().isoformat(timespec="seconds")
        if state["status"] != old_status:
            state["history"].append({"at": state["updated"], "from": old_status, "to": state["status"],
                                     "reason": state.get("reason", ""), "by": updates.get("by", "自动开工")})
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_bytes((json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        atomic.replace(tmp, f)
        return state


def resume_runner(p: Project, key: str, by: str = "人", reason: str = "") -> dict:
    """人的授权恢复一次运行预算；历史、实际结果保留，圈数和失败限制清零。"""
    return write_runner_state(p, key, "ready", action="idle", reason=reason or "已明确恢复",
                              cycles=0, rounds=0, blocked=[], failure_counts={}, stop_requested=False, resumed_at=time.time(), by=by)


def resumable_state(state: dict, *, explicit_resume: bool = False) -> bool:
    """终态照旧恢复；空闲时留下的失败限制只能由明确的恢复请求解除。"""
    return state.get("status") in BLOCK_RESTART or bool(
        explicit_resume and state.get("status") == "idle" and state.get("blocked"))


def _automatic(a: dict) -> bool:
    return bool(a.get("auto")) and not a.get("paused") and "codex" in (a.get("program") or "").lower()


def _job(got: dict) -> str:
    task = got.get("task")
    if task:
        return f"{task['goal']} {task['sub']}"
    plan = got.get("construction_plan")
    if plan:
        return f"施工计划 {plan['code']}"
    review = got.get("review")
    if review:
        return "验收 " + review["code"]
    draft = got.get("draft")
    if draft:
        return "审核 " + draft["code"]
    fruit = got.get("fruit")
    if fruit:
        return "挑果实 " + fruit["code"] + " " + fruit.get("item", "")
    if got.get("digest"):
        return "写摘要 " + got["digest"]["key"]
    if got.get("rewrite"):
        return "写重写单 " + got["rewrite"]["rel"]
    if got.get("rewrite_review"):
        return "审重写单 " + got["rewrite_review"]["code"]
    plan = got.get("plan")
    if plan:
        return "规划 " + str((plan.get("row") or {}).get("code") or (plan.get("draft") or {}).get("code") or "")
    return got.get("reason") or got.get("action", "")


def window_metadata(conn, p: Project, a: dict, got: dict | None = None) -> dict:
    """开窗时的明确关联；不从标题、命令或旧运行文字猜员工与任务，也不领新活。"""
    records = []
    if got is not None:
        records = [got.get(key) or {} for key in ("task", "construction_plan", "review", "draft")]
    else:
        # 人工开窗只承接已认领的记录，多个不同任务不能任选一个冒充当前任务。
        for held in (r for r in claims.active(conn) if agents.short(r["agent"]) == a["name"]):
            if re.fullmatch(r"S2-\d+", held.get("sub", "")):
                records.append(held)
            elif held.get("goal") == "验收":
                import deliveries
                try:
                    records.append(deliveries.get(p, held["sub"]))
                except store.Refused:
                    pass
            else:
                import construction_plans as cp
                if held.get("goal") == cp.REVIEW:
                    try:
                        records.append(cp.get(p, held["sub"]))
                    except store.Refused:
                        pass
    keys = {str(r["goal"]) + " " + str(r["sub"]) for r in records
            if r.get("goal") and re.fullmatch(r"S2-\d+", str(r.get("sub", "")))}
    return {"agent_code": a["code"], "task_key": next(iter(keys)) if len(keys) == 1 else "",
            "project_root": str(p.root.resolve())}


def missing_roles(conn, p: Project) -> list[str]:
    """只看真实待办和明确档案范围，报告哪类工作没有可自动运行的员工。"""
    import construction_plans as cp
    import deliveries
    import drafts
    import blueprint
    staff = [a for a in agents.list_all(p) if _automatic(a)]
    out = []
    bp = blueprint.pyramid(p)

    def capable(role, author="", g=None, x=None):
        return any(role in agents.jobs(a) and a["name"] != agents.short(author)
                   and (g is None or agents.allows(a, g, x)) for a in staff)

    for plan in cp.listing(p):
        if plan["state"] != cp.WAIT:
            continue
        g = blueprint.find(bp, plan["goal"])
        x = next((x for x in (g or {}).get("subs", []) if x["code"] == plan["sub"]), None)
        if not g or not x:
            out.append(f"{plan['code']} 对应的任务已不可用，需确认去向")
            continue
        if not capable("审核", plan["by"], g, x):
            out.append(f"{plan['code']} 缺少独立审核员工")
    for j in deliveries.list_all(p):
        if not deliveries.independent_pending(p, j):
            continue
        g = blueprint.find(bp, j["goal"])
        x = next((x for x in (g or {}).get("subs", []) if x["code"] == j["sub"]), None)
        if not g or not x:
            out.append(f"{j['code']} 对应的任务已不可用，需确认去向")
        elif not capable("验收", j["by"], g, x):
            out.append(f"{j['code']} 缺少独立验收员工")
    for d in drafts.listing(p):
        if d["state"] == drafts.WAIT and drafts.stage(p, d) in ("等审", "没人审") and not capable("审核", d["by"]):
            out.append(f"{d['code']} 缺少独立审核员工")
    held = {(c["goal"], c["sub"]) for c in claims.active(conn)}
    for g, x in dispatch.ready_items(p):
        if (g["code"], x["code"]) not in held and not capable("干活", g=g, x=x):
            crafts = "、".join(agents.task_crafts(x))
            out.append(f"{g['code']} {x['code']} 缺少{crafts + '工种的' if crafts else ''}施工员工或负责范围不匹配")
    return list(dict.fromkeys(out))


def status(conn, p: Project) -> dict:
    return settings(conn) | {"paused": workorders.paused(conn), "runners": [runner_state(p, a["code"]) for a in agents.list_all(p)],
                             "missing_roles": missing_roles(conn, p)}


def _call(p: Project, method: str, path: str, body: dict | None = None):
    st = plugins.page_status(p, TERM)
    if not st.get("running"):
        raise RuntimeError("网页终端没在跑")
    url = f"http://127.0.0.1:{st['port']}{path}{'&' if '?' in path else '?'}t={st['url'].split('t=', 1)[1]}"
    req = urllib.request.Request(url, method=method, data=json.dumps(body or {}, ensure_ascii=False).encode("utf-8") if method == "POST" else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def windows(p: Project, *, require_known: bool = False) -> list[dict]:
    """读取窗口；恢复预算时必须确认查询成功，不能把断连当成没有活窗口。"""
    if require_known and not plugins._state_file(p, TERM).exists():
        return []  # 没有登记的服务地址；恢复入口仍另查运行器 PID。
    try:
        items = _call(p, "GET", "/api/terms")["items"]
        if require_known and (not isinstance(items, list) or any(
            not isinstance(w, dict) or not isinstance(w.get("title"), str)
            or not isinstance(w.get("alive"), bool) for w in items
        )):
            raise RuntimeError("网页终端窗口状态不完整")
        return items
    except Exception:
        if require_known:
            raise
        return []


def tick(conn, p: Project, now: float | None = None, call=None) -> list[str]:
    """冷启动也找工作；暂停、额度限制和活窗口先检查，避免多领和空跑。"""
    st = settings(conn)
    if not st["on"] or workorders.paused(conn):
        return []
    try:
        with _file_lock(p, "自动开工"):
            return _tick(conn, p, st, time.time() if now is None else now, call)
    except store.Refused:
        return []


def _tick(conn, p, st, now, call):
    staff = [a for a in agents.list_all(p) if _automatic(a)]
    if not staff:
        return []
    if call is None:
        if not plugins.page_status(p, TERM).get("running"):
            try:
                plugins.open_page(conn, p, TERM)    # 网页终端没在跑：先打开（要已经启用、检查过）
            except (KeyError, RuntimeError, store.Refused):
                return []
        call = lambda m, path, body=None: _call(p, m, path, body)
    try:
        wins = call("GET", "/api/terms")["items"]
    except Exception:
        return []
    alive = {m[1] for w in wins if w.get("alive") and (m := re.match(r"^(?:枝-\d+ · )?(G\d+)(?:\s|$)", w.get("title", "")))}   # 在世界树枝上开着的也算
    running = sum(bool(w.get("alive") and re.match(r"^(?:枝-\d+ · )?G\d+(?:\s|$)", w.get("title", ""))) for w in wins)
    started = []
    import branching                                       # 档位 3、4：先排枝（长枝、派人、结果实、挑），再给主干上的人开窗口
    try:
        got = branching.tick(conn, p, running=running, alive=alive, call=call, now=now)
    except Exception as exc:
        got = []
        with store.tx(conn):
            store.log(conn, "自动开工", "排枝出错", "", str(exc)[:300])
    running += len(got)
    started += got
    for a in staff:
        if workorders.paused(conn):
            break
        title = f"{a['code']} {a['name']}"
        if a["code"] in alive:
            continue
        state = runner_state(p, a["code"])
        if state["status"] in BLOCK_RESTART or state.get("stop_requested"):
            continue
        last = float(store._meta(conn, LAST + a["code"]) or 0)
        if now - last < cooldown(conn) and last > float(state.get("resumed_at") or 0):
            continue
        if running >= st["max"]:
            break
        try:
            actor = agents.actor(a["name"])
            before = {(r["goal"], r["sub"]) for r in claims.of(conn, actor)}
            got = dispatch.next_task(conn, p, agents.actor(a["name"]))
            action = got.get("action", "idle")
            current = _job(got)
            if action not in RUN_ACTIONS:
                write_runner_state(p, a["code"], "stopped" if action == "stopped" else "waiting" if action == "waiting" else "idle",
                                   action=action, current=current, reason=got.get("reason", ""))
                continue
            l = agents.launcher(p, a["code"])
            if workorders.paused(conn):
                dispatch.recheck_action(conn, p, actor, got, before)
                break
            # 与流程停用共用短锁；核验到发出启动请求期间不能插入停用。
            with _file_lock(p, "工作流图"):
                got = dispatch.recheck_action(conn, p, actor, got, before)
                if got.get("action") not in RUN_ACTIONS:
                    write_runner_state(p, a["code"], "waiting", action=got.get("action"),
                                       current=current, reason=got.get("reason", ""))
                    continue
                write_runner_state(p, a["code"], "running", action=action, current=current, reason=got.get("reason", ""))
                call("POST", "/api/terms", {"title": l["title"], "cmd": l["cmd"]} | window_metadata(conn, p, a, got))
        except Exception as exc:
            write_runner_state(p, a["code"], "failed", reason=f"开工失败：{exc}", last_result="未启动员工")
            with store.tx(conn):
                store.log(conn, "自动开工", "开工失败", a["code"], str(exc))
            continue
        with store.tx(conn):
            store._set_meta(conn, LAST + a["code"], str(now))
            store.log(conn, "自动开工", "自动开了窗口", a["code"], f"{title}：{current}（{action}）")
        running += 1
        alive.add(a["code"])
        started.append(f"{title}：{current}")
    return started


def recent(conn, n: int = 8) -> list[dict]:
    """最近自动开的几次（网页上写着）。"""
    return [{"at": r["at"][5:16].replace("T", " "), "who": r["target"], "what": r["detail"]}
            for r in conn.execute("SELECT at, target, detail FROM event WHERE action = '自动开了窗口' ORDER BY id DESC LIMIT ?", (n,))]
