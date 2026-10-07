"""把人的明确派活保存在普通文件里，等待、退出和重启后核对原授权再接着做。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import agents
import atomic
import construction_plans as cp
import governance
import store

DIR = Path("自动化") / "任务接续"


def _path(p, a):
    if not re.fullmatch(r"G\d+", a["code"]):
        raise store.Refused("员工编号不合法")
    return p.root / DIR / (a["code"] + ".json")


def listing(p, a):
    f = _path(p, a)
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("employee") != a["code"] or not isinstance(data.get("items"), list):
            raise ValueError("格式不完整")
        items = data["items"]
        for r in items:
            if not isinstance(r, dict) or any(not isinstance(r.get(k), str) or not r[k] for k in
                                            ("goal", "sub", "name", "by", "authorization_path", "authorization_revision", "task_signature")):
                raise ValueError("派活来源不完整")
        return items
    except (OSError, ValueError, UnicodeError) as e:
        raise store.Refused(f"{a['code']} 的任务接续记录读不了：{e}") from e


def source_reason(p, a, record):
    """来源必须是当时的人的派活授权；不把员工自己交的施工计划当成授权。"""
    if record.get('revoked'):
        return '这份派活已撤销，需要人的新授权重新派活'
    try:
        source = governance.read_document(p, record["authorization_path"])
    except (OSError, ValueError, store.Refused) as e:
        return "派活授权读不了：" + str(e)
    if source["revision"] != record["authorization_revision"]:
        return "人的派活授权已变更，需要按新授权重新派活"
    text = source["text"]
    owners = re.search(r"^> 授权操作者：(.+)$", text, re.M)
    targets = re.search(r"^> 授权对象：(.+)$", text, re.M)
    if (not source["save_path"].startswith("治理/计划/") or "授权：作者本次" not in text
            or not owners or agents.short(record["by"]) not in agents._split(owners.group(1))
            or not targets or a["code"] not in agents._split(targets.group(1))):
        return "派活来源没有匹配人的操作者及员工授权"
    if record["name"] != a["name"]:
        return "派活员工身份已变更，需要重新派活"
    return ""


def record(p, a, goal, sub, *, by, authorization_path, authorization_revision, reason):
    """仅由已获配置授权的派活入口调用，保存成功认领的来源。"""
    import autolaunch
    g, x = cp._task(p, goal, sub)
    entry = {"goal": goal, "sub": sub, "name": a["name"], "by": by,
             "authorization_path": authorization_path, "authorization_revision": authorization_revision,
             "task_signature": cp._signature(p, g, x), "reason": reason,
             "at": datetime.now().isoformat(timespec="seconds")}
    problem = source_reason(p, a, entry)
    if problem:
        raise store.Refused(problem)
    with autolaunch._file_lock(p, "任务接续"):
        items = listing(p, a)
        old = next((r for r in items if (r['goal'], r['sub']) == (goal, sub)), None)
        if old:
            entry['history'] = list(old.get('history') or []) + [{k: v for k, v in old.items() if k != 'history'}]
        items = [r for r in items if (r["goal"], r["sub"]) != (goal, sub)] + [entry]
        f = _path(p, a)
        f.parent.mkdir(parents=True, exist_ok=True)
        temp = f.with_suffix(".json.tmp")
        temp.write_text(json.dumps({"employee": a["code"], "items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        atomic.replace(temp, f)
    return entry


def revoke(p, a, *, by, authorization_path, authorization_revision, reason):
    """撤销指定员工已有的派活接续，保留原授权及撤销来源，不改其他员工。"""
    import autolaunch
    event = {'by': by, 'authorization_path': authorization_path,
             'authorization_revision': authorization_revision, 'reason': reason,
             'at': datetime.now().isoformat(timespec='seconds')}
    why = source_reason(p, a, event | {'name': a['name']})
    if why:
        raise store.Refused(why)
    with autolaunch._file_lock(p, '任务接续'):
        items = listing(p, a)
        changed = []
        for row in items:
            if not row.get('revoked'):
                row['revoked'] = dict(event)
                changed.append({'goal': row['goal'], 'sub': row['sub'], 'revoked': dict(event)})
        if changed:
            f = _path(p, a)
            temp = f.with_suffix('.json.tmp')
            temp.write_text(json.dumps({'employee': a['code'], 'items': items}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            atomic.replace(temp, f)
    return changed


def held_reason(p, a, g, x):
    """新派活记录即使仍有认领也要核对；旧认领没有记录时保持兼容。"""
    record = next((r for r in listing(p, a) if (r['goal'], r['sub']) == (g['code'], x['code'])), None)
    if not record:
        return ''
    why = source_reason(p, a, record)
    if not why and cp._signature(p, g, x) != record['task_signature']:
        why = '目标、需求或任务已变更，需要按新范围重新派活'
    return why


def candidates(p, a, bp):
    """恢复前核对来源、任务方向和完成状态；岗位、暂停及互斥仍由派发器检查。"""
    import blueprint
    import deliveries
    latest = deliveries.latest_by_task(p)
    valid, problems = [], []
    for r in listing(p, a):
        g = blueprint.find(bp, r["goal"])
        x = next((s for s in (g or {}).get("subs", []) if s["code"] == r["sub"]), None)
        if not x or x["status"] == "ok":
            continue
        j = latest.get((r["goal"], r["sub"]))
        if j and (j["state"] in ("等验收", "验收通过") or deliveries.independent_pending(p, j)):
            continue
        why = source_reason(p, a, r)
        if not why and cp._signature(p, g, x) != r["task_signature"]:
            why = "目标、需求或任务已变更，需要按新范围重新派活"
        if why:
            problems.append(f"{r['goal']} {r['sub']}：{why}")
        else:
            valid.append((g, x, r))
    return valid, problems
