"""可编辑工作流：项目 W 普通文件、不可变启用快照和真实派活前的流程关卡。

这里只计算既有任务、计划和交付事实，不执行图中的代码、不启动员工。
旧项目没有流程配置时保留原派发；停用的任务留下守卫，避免落回旧派发重复施工。
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import atomic
import store

DIR = Path("自动化") / "工作流" / "项目"
STATE = Path("自动化") / "流程状态" / "控制.json"
TYPES = {"start", "dispatch", "review_plan", "execute", "review_delivery", "condition", "end"}
STAGES = {"dispatch", "review_plan", "execute", "review_delivery"}
ACTION_TYPES = {"submit_plan": "dispatch", "review_plan": "review_plan", "execute": "execute", "review_delivery": "review_delivery"}
FIELDS = {"plan_status": {"missing", "pending", "rejected", "approved", "invalid"},
          "delivery_status": {"missing", "pending", "rejected", "accepted"}, "task_done": {True, False}}
CODE = re.compile(r"W[1-9]\d*")
IDENT = re.compile(r"[A-Za-z0-9_-]{1,64}")
MARK = "## 流程配置\n\n```json\n"


def _now():
    return datetime.now().isoformat(timespec="microseconds")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _safe(p, rel):
    root = p.root.resolve()
    candidate = root
    for part in Path(rel).parts:
        candidate /= part
        if candidate.is_symlink() or candidate.is_junction():
            raise store.Refused("流程文件不能通过链接离开项目")
    if not candidate.resolve().is_relative_to(root):
        raise store.Refused("流程文件不能离开项目")
    return candidate


def _shape(graph):
    if not isinstance(graph, dict) or graph.get("schema", 1) != 1:
        raise store.Refused("流程图应是 schema=1 的 JSON 对象")
    nodes, edges = graph.get("nodes"), graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list) or len(nodes) > 128 or len(edges) > 256:
        raise store.Refused("流程图最多 128 个节点、256 条边")
    if any(not isinstance(n, dict) for n in nodes + edges):
        raise store.Refused("节点和边应是 JSON 对象")
    for node in nodes:
        for field in ("id", "type", "label", "task", "employee", "field", "op"):
            if field in node and (not isinstance(node[field], str) or len(node[field]) > 300):
                raise store.Refused("节点的 " + field + " 应是简短文字")
        if "value" in node and not isinstance(node["value"], (str, bool)):
            raise store.Refused("条件值只支持文字或布尔值")
    for edge in edges:
        for field in ("id", "from", "to", "when"):
            if field in edge and (not isinstance(edge[field], str) or len(edge[field]) > 128):
                raise store.Refused("边的 " + field + " 应是简短文字")
    try:
        raw = json.dumps(graph, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise store.Refused("流程图必须是普通 JSON，坐标不能是无穷或非数字") from exc
    if len(raw) > 1024 * 1024:
        raise store.Refused("流程图不能超过 1 MB")
    return copy.deepcopy(graph) | {"schema": 1}


def split_task(value):
    if not isinstance(value, str):
        return "", ""
    match = re.fullmatch(r"(.+?) (S2-\d+)", " ".join(value.split()))
    return (match[1], match[2]) if match else ("", "")


def validate(p, graph):
    """只读校验。未完工草稿可保存，启用必须通过完整校验。"""
    import agents
    import blueprint
    errors, warnings, bindings = [], [], []
    try:
        graph = _shape(graph)
    except store.Refused as exc:
        return {"ok": False, "errors": [str(exc)], "warnings": [], "bindings": []}
    nodes, edges = graph["nodes"], graph["edges"]
    ids = [n.get("id") for n in nodes]
    if not nodes:
        errors.append("至少需要开始、任务流程和结束节点")
    if not any(node.get("type") in STAGES for node in nodes):
        errors.append("至少配置一件任务的派活、审核、施工和验收流程")
    if any(not isinstance(i, str) or not IDENT.fullmatch(i) for i in ids) or len(set(str(i) for i in ids)) != len(ids):
        errors.append("节点 id 必须是不同的字母、数字、下划线或短横线")
    by_id = {n.get("id"): n for n in nodes if isinstance(n.get("id"), str)}
    starts = [n for n in nodes if n.get("type") == "start"]
    ends = [n for n in nodes if n.get("type") == "end"]
    if len(starts) != 1 or not ends:
        errors.append("需要一个开始节点和至少一个结束节点")
    adjacency, incoming = {i: [] for i in by_id}, {i: [] for i in by_id}
    edge_ids = []
    for index, edge in enumerate(edges):
        edge_id = edge.get("id", "edge-" + str(index))
        edge_ids.append(edge_id)
        source, target = edge.get("from"), edge.get("to")
        if source not in by_id or target not in by_id or source == target:
            errors.append(f"边 {edge_id} 的节点不存在或连向自身")
            continue
        when = edge.get("when", "always")
        expected = {"true", "false"} if by_id[source].get("type") == "condition" else {"always"}
        if when not in expected:
            errors.append(f"边 {edge_id} 的条件应为 {'/'.join(sorted(expected))}")
        adjacency[source].append(target)
        incoming[target].append(source)
    if any(not isinstance(i, str) or not IDENT.fullmatch(i) for i in edge_ids) or len(set(str(i) for i in edge_ids)) != len(edge_ids):
        errors.append("边 id 必须合法且不能重复")
    for node in nodes:
        kind, key = node.get("type"), node.get("id")
        if kind not in TYPES:
            errors.append(f"节点 {key} 的类型不受支持")
        if kind == "start" and incoming.get(key):
            errors.append("开始节点不能有入边")
        if kind == "end" and adjacency.get(key):
            errors.append("结束节点不能有出边")
        if kind == "condition":
            outgoing = [e.get("when") for e in edges if e.get("from") == key]
            if sorted(str(x) for x in outgoing) != ["false", "true"]:
                errors.append(f"条件 {key} 需要各一条 true、false 出边")
            field, value = node.get("field"), node.get("value")
            if field not in FIELDS or (field == "task_done" and not isinstance(value, bool)) or (field != "task_done" and not isinstance(value, str)):
                errors.append(f"条件 {key} 只支持计划状态、交付状态、任务完成的等于判断")
            elif value not in FIELDS[field]:
                errors.append(f"条件 {key} 的比较值不受支持")
            if node.get("op", "eq") != "eq":
                errors.append(f"条件 {key} 仅支持 eq，不执行表达式")
    degree = {i: len(incoming[i]) for i in by_id}
    queue, order = [i for i, n in degree.items() if n == 0], []
    while queue:
        key = queue.pop(0)
        order.append(key)
        for child in adjacency[key]:
            degree[child] -= 1
            if degree[child] == 0:
                queue.append(child)
    if len(order) != len(by_id):
        errors.append("流程首版只支持有限有向无环图；返工使用已有打回流程，不画无限循环")
    def reachable(key):
        seen, todo = set(), [key]
        while todo:
            current = todo.pop()
            if current not in seen:
                seen.add(current)
                todo.extend(adjacency.get(current, []))
        return seen
    if len(starts) == 1:
        reach = reachable(starts[0].get("id"))
        for key in by_id:
            if key not in reach:
                errors.append(f"节点 {key} 从开始不可达")
            if not any(n.get("id") in reachable(key) for n in ends):
                errors.append(f"节点 {key} 不能到达结束")
    bp = blueprint.pyramid(p)
    people = {a["code"]: a for a in agents.list_all(p)}
    targets = list(dict.fromkeys(n.get("task") for n in nodes if n.get("type") in STAGES | {"condition"}))
    for task in targets:
        goal, sub = split_task(task)
        g = blueprint.find(bp, goal) if goal else None
        x = next((s for s in (g or {}).get("subs", []) if s["code"] == sub), None)
        if not x:
            errors.append(f"任务 {task!s} 不存在；必须使用完整目标和 S2 编号")
            continue
        if x.get("status") == "ok":
            warnings.append(f"{task} 已完成，不会重复施工")
        stage_nodes = {stage: [n for n in nodes if n.get("task") == task and n.get("type") == stage] for stage in STAGES}
        if not any(stage_nodes.values()):
            bindings.append({"task": task, "goal": goal, "sub": sub, "condition_only": True,
                             "worker": "", "plan_reviewer": "", "delivery_reviewer": ""})
            continue
        if not x.get("how", "").strip():
            errors.append(f"{task} 缺验收标准")
        selected = {}
        for stage, group in stage_nodes.items():
            employee_ids = set(str(n.get("employee", "")) for n in group)
            if not group or len(employee_ids) != 1 or next(iter(employee_ids), "") not in people:
                errors.append(f"{task} 的 {stage} 需要绑定当前项目的一个真实员工")
                continue
            employee = people[next(iter(employee_ids))]
            selected[stage] = employee["code"]
            role = "审核" if stage == "review_plan" else "验收" if stage == "review_delivery" else "干活"
            if role not in agents.jobs(employee):
                errors.append(f"{employee['code']} 没有 {role} 岗位")
            # 暂停是当前运行等待，不能把仍有效的结构和职责当成损坏。
            # 实际准入与既有派发仍读取员工原本的 paused，绝不清除档案开关。
            why = agents.allows_reason(employee | {"paused": False}, g, x)
            if why:
                errors.append(f"{task} / {employee['code']}：{why}")
            if employee.get("paused"):
                warnings.append(f"{employee['code']} 已暂停，运行会等待")
        if len(selected) == len(STAGES):
            worker = selected["dispatch"]
            if worker != selected["execute"]:
                errors.append(f"{task} 派活与施工必须是同一员工；换人须按已有交接流程")
            if worker in (selected["review_plan"], selected["review_delivery"]):
                errors.append(f"{task} 不能自审或自验")
            for first, second in (("dispatch", "review_plan"), ("review_plan", "execute"), ("execute", "review_delivery")):
                if not any(b["id"] in reachable(a["id"]) for a in stage_nodes[first] for b in stage_nodes[second]):
                    errors.append(f"{task} 的 {first} 必须衔接 {second}")
            bindings.append({"task": task, "goal": goal, "sub": sub, "worker": worker,
                             "plan_reviewer": selected["review_plan"], "delivery_reviewer": selected["review_delivery"]})
    return {"ok": not errors, "errors": list(dict.fromkeys(errors)), "warnings": list(dict.fromkeys(warnings)), "bindings": bindings}


def _state(p):
    file = _safe(p, STATE)
    if not file.is_file():
        return {"schema": 1, "active": None, "guards": {}, "history": []}
    try:
        state = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("schema") != 1 or not isinstance(state.get("guards"), dict) or not isinstance(state.get("history"), list):
            raise ValueError("状态格式不完整")
        if any(not all(split_task(task)) or not isinstance(guard, dict) or not isinstance(guard.get("reason"), str)
               or not CODE.fullmatch(str(guard.get("workflow", ""))) or not isinstance(guard.get("revision"), str)
               for task, guard in state["guards"].items()):
            raise ValueError("停用守卫格式不完整")
        active = state.get("active")
        if active is not None:
            if not isinstance(active, dict) or not CODE.fullmatch(active.get("code", "")) or not isinstance(active.get("bindings"), list):
                raise ValueError("启用快照格式不完整")
            if any(not isinstance(row, dict) or any(not isinstance(row.get(k), str) for k in ("task", "goal", "sub", "worker", "plan_reviewer", "delivery_reviewer"))
                   for row in active["bindings"]):
                raise ValueError("启用快照的任务绑定格式不完整")
            payload = {k: v for k, v in active.items() if k != "snapshot_digest"}
            if _hash(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")) != active.get("snapshot_digest"):
                raise ValueError("启用快照已变更，需要人重新核对启用")
        return state
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise store.Refused("流程状态读不了，不能退回旧派发：" + str(exc)) from exc


def _find(p, code):
    if not CODE.fullmatch(code or ""):
        raise store.Refused("工作流编号应为 W1 这样的编号")
    files = [f for f in _safe(p, DIR).glob(code + " *.md") if f.is_file()]
    if len(files) != 1:
        raise store.Refused("没有该项目工作流" if not files else "工作流同号冲突，先对照处理")
    return _safe(p, files[0].relative_to(p.root.resolve()))


def read(p, code):
    file = _find(p, code)
    raw = file.read_bytes()
    text = raw.decode("utf-8-sig")
    normalized = text.replace("\r\n", "\n")
    _, mark, tail = normalized.partition(MARK)
    metadata, end, _ = tail.partition("\n```\n")
    try:
        record = json.loads(metadata)
        if not mark or not end or not isinstance(record, dict) or record.get("code") != code:
            raise ValueError("配置段不完整")
        graph = _shape(record.get("graph"))
    except (ValueError, TypeError, store.Refused) as exc:
        raise store.Refused(f"工作流 {code} 读不了：{exc}") from exc
    state = _state(p)
    active = state["active"] if (state.get("active") or {}).get("code") == code else None
    return record | {"file": file.relative_to(p.root.resolve()).as_posix(), "text": text, "graph": graph,
                     "revision": _hash(raw), "validation": validate(p, graph), "active": active}


def list_all(p):
    state = _state(p)
    items = []
    for file in sorted(_safe(p, DIR).glob("W* *.md")):
        code = file.name.split(" ", 1)[0]
        if CODE.fullmatch(code):
            items.append(read(p, code))
    items.sort(key=lambda x: int(x["code"][1:]))
    return {"items": items, "active": state["active"], "guards": state["guards"]}


def _write_json(p, rel, data):
    file = _safe(p, rel)
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_name(file.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atomic.replace(temporary, file)


def save(conn, p, code, name, graph, revision="", *, by="人"):
    import autolaunch
    import project
    graph = _shape(graph)
    try:
        name = project.check_name(name or "我的工作流")
    except ValueError as exc:
        raise store.Refused("工作流名称不合法：" + str(exc)) from exc
    with autolaunch._file_lock(p, "工作流图"), store.tx(conn):
        old = read(p, code) if code else None
        if old:
            if not revision or revision != old["revision"]:
                raise store.Refused("工作流版本已变化；重新读取后对照，不覆盖新内容")
            file = _find(p, code)
            history = _safe(p, DIR / "历史" / f"{code} {_now().replace(':', '-')} {revision[:12]}.md")
            history.parent.mkdir(parents=True, exist_ok=True)
            history.write_bytes(file.read_bytes())
            prefix, _, tail = old["text"].replace("\r\n", "\n").partition(MARK)
            _, _, suffix = tail.partition("\n```\n")
        else:
            if revision:
                raise store.Refused("新工作流不应带旧版本")
            numbers = [int(match[1]) for f in (p.root / "自动化" / "工作流").rglob("W* *.md")
                       if (match := re.match(r"W(\d+) ", f.name))]
            # 应用通用 W 可为旧项目回退，私有号不能与它碰撞。
            from project import CODE_DIR
            numbers += [int(match[1]) for f in (CODE_DIR / "自动化" / "工作流").glob("W* *.md")
                        if (match := re.match(r"W(\d+) ", f.name))]
            code = f"W{max(numbers, default=0) + 1}"
            file = _safe(p, DIR / (code + " " + name + ".md"))
            prefix, suffix = f"# {code} · {name}\n\n", ""
        record = {"code": code, "name": name, "graph": graph, "by": by, "updated": _now(),
                  "created": (old or {}).get("created", _now()), "version": int((old or {}).get("version", 0)) + 1}
        text = prefix + MARK + json.dumps(record, ensure_ascii=False, indent=2) + "\n```\n" + suffix
        file.parent.mkdir(parents=True, exist_ok=True)
        temporary = file.with_name(file.name + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        atomic.replace(temporary, file)
        store.log(conn, by, "保存工作流草稿", code, "仅保存，不启用、不启动员工")
    return read(p, code)


def control(conn, p, code, action, revision, *, by="人"):
    import autolaunch
    import construction_plans as cp
    if action not in {"enable", "stop"}:
        raise store.Refused("流程控制只有 enable 或 stop")
    with autolaunch._file_lock(p, "工作流图"), store.tx(conn):
        state = _state(p)
        active = state.get("active")
        if action == "enable":
            record = read(p, code)
            if not revision or revision != record["revision"]:
                raise store.Refused("启用版本已变化，先重新读取工作流")
            check = validate(p, record["graph"])
            if not check["ok"]:
                raise store.Refused("流程不能启用：" + "；".join(check["errors"]))
            if active and active["code"] == code and active["snapshot_revision"] == revision:
                return {"active": active, "guards": state["guards"]}
            if active:
                raise store.Refused("已有流程启用；先明确停用它，修改草稿不会替换正在执行的快照")
            bindings = check["bindings"]
            import blueprint
            pyramid = blueprint.pyramid(p)
            signatures = {}
            for row in bindings:
                goal = blueprint.find(pyramid, row["goal"])
                task = next(x for x in goal["subs"] if x["code"] == row["sub"])
                signatures[row["task"]] = cp._signature(p, goal, task)
            snapshot = {"code": code, "name": record["name"], "snapshot_revision": revision,
                        "graph": copy.deepcopy(record["graph"]), "bindings": bindings, "task_signatures": signatures,
                        "enabled_by": by, "enabled_at": _now(), "on": True, "state": "active"}
            snapshot["snapshot_digest"] = _hash(json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode("utf-8"))
            state["active"] = snapshot
            for row in bindings:
                if not row.get("condition_only"):
                    state["guards"].pop(row["task"], None)
        else:
            if not active or active["code"] != code:
                raise store.Refused("该流程没有启用；不会停止另一个流程")
            if not revision or revision != active["snapshot_revision"]:
                raise store.Refused("停用请传当前启用快照版本")
            for row in active["bindings"]:
                if row.get("condition_only"):
                    continue
                state["guards"][row["task"]] = {"workflow": code, "revision": revision, "by": by, "at": _now(),
                                                 "binding": copy.deepcopy(row),
                                                 "reason": "流程已停用；保留任务守卫，重新启用前不退回旧派发"}
            state["active"] = None
        state["history"].append({"code": code, "action": action, "revision": revision, "by": by, "at": _now()})
        _write_json(p, STATE, state)
        store.log(conn, by, "启用工作流" if action == "enable" else "停用工作流", code,
                  "仅改变流程准入；自动开工、项目暂停和员工权限保持原设置")
    return {"active": state["active"], "guards": state["guards"]}


def _facts(p, bindings, signatures=None):
    import agents
    import blueprint
    import construction_plans as cp
    import deliveries
    bp = blueprint.pyramid(p)
    plans, latest = cp.listing(p), deliveries.latest_by_task(p)
    facts = {}
    for row in bindings:
        goal, sub, task = row["goal"], row["sub"], row["task"]
        g = blueprint.find(bp, goal)
        x = next((s for s in (g or {}).get("subs", []) if s["code"] == sub), None)
        worker = agents.find(p, row["worker"]) if row["worker"] else None
        if not x or not worker and not row.get("condition_only"):
            facts[task] = {"unknown": "任务或施工员工已移除"}
            continue
        # 做完会改变目标文件状态，但不会改变施工方向签名；先读取完成事实。
        done = x.get("status") == "ok"
        if signatures and not done and cp._signature(p, g, x) != signatures.get(task):
            facts[task] = {"unknown": "任务、需求或验收范围已变化，需要重新核对启用流程"}
            continue
        task_plans = [r for r in plans if r["goal"] == goal and r["sub"] == sub]
        if row.get("condition_only"):
            plan = task_plans[0] if len(task_plans) == 1 else None
            worker = agents.find(p, plan["employee"]) if plan else None
        else:
            plan = next((r for r in task_plans if r["employee"] == worker["code"]), None)
        valid = cp.approved(p, goal, sub, agents.actor(worker["name"])) if worker else None
        plan_status = "approved" if valid else "missing" if not plan else "pending" if plan["state"] == cp.WAIT else "rejected" if plan["state"] == cp.NO else "invalid"
        if row.get("condition_only") and (len(task_plans) > 1 or plan and not worker):
            plan_status = "unknown"
        delivery = latest.get((goal, sub))
        if delivery and not row.get("condition_only") and agents.short(delivery["by"]) != worker["name"] and not done:
            facts[task] = {"unknown": "最新交付属于其他员工，不自动接管或覆盖"}
            continue
        delivery_status = ("missing" if not delivery else "accepted" if delivery["state"] == "验收通过" else
                           "rejected" if delivery["state"] == "打回" else "pending" if delivery["state"] in ("等验收", "待你验收") else "unknown")
        facts[task] = {"task_done": done, "plan_status": plan_status, "delivery_status": delivery_status,
                       "plan": plan, "delivery": delivery}
    return facts


def _evaluate(p, graph, check, signatures=None):
    """依据真实记录推导节点；没有认领、开单、日志或文件写入副作用。"""
    facts = _facts(p, check["bindings"], signatures)
    nodes = {n["id"]: n for n in graph["nodes"]}
    incoming = {i: [] for i in nodes}
    outgoing = {i: [] for i in nodes}
    edges = []
    for index, raw in enumerate(graph["edges"]):
        edge = raw | {"id": raw.get("id", "edge-" + str(index)), "when": raw.get("when", "always")}
        edges.append(edge)
        incoming[edge["to"]].append(edge)
        outgoing[edge["from"]].append(edge)
    # 条件明确分流拒绝结果；直线流程使用既有打回修订/返工闭环。
    branched = {field: {n.get("task") for n in nodes.values() if n["type"] == kind and any(
        nodes[e["to"]]["type"] == "condition" and nodes[e["to"]].get("field") == field for e in outgoing[n["id"]])}
        for field, kind in (("plan_status", "review_plan"), ("delivery_status", "review_delivery"))}
    degree = {i: len(incoming[i]) for i in nodes}
    todo = [i for i, n in degree.items() if n == 0]
    result = {}
    decisions, edge_states = [], {}
    while todo:
        key = todo.pop(0)
        node, kind = nodes[key], nodes[key]["type"]
        inputs = []
        for edge in incoming[key]:
            parent = result[edge["from"]]
            if parent["status"] == "skipped":
                state = "skipped"
            elif parent["status"] != "complete":
                state = "waiting"
            elif nodes[edge["from"]]["type"] == "condition":
                state = "active" if (parent.get("decision") is True) == (edge["when"] == "true") else "skipped"
            else:
                state = "active"
            inputs.append(state)
            edge_states[edge["id"]] = state
        status, reason, decision = "waiting", "等待前一步", None
        if "waiting" in inputs:
            reason = next((result[e["from"]]["reason"] for e in incoming[key]
                           if result[e["from"]]["status"] != "complete" and result[e["from"]]["status"] != "skipped"), reason)
        if kind == "start":
            status, reason = "complete", "开始"
        elif inputs and all(s == "skipped" for s in inputs):
            status, reason = "skipped", "未选择此分支"
        elif inputs and "waiting" not in inputs and "active" in inputs:
            fact = facts.get(node.get("task"), {})
            if kind == "end":
                status, reason = "complete", "此分支结束"
            elif fact.get("unknown"):
                reason = fact["unknown"]
            elif kind == "condition":
                field = node["field"]
                actual = fact.get(field)
                if actual is None or actual == "unknown":
                    reason = "条件记录未知，等待核对"
                else:
                    decision = actual == node["value"]
                    status, reason = "complete", "条件成立" if decision else "条件不成立"
                    decisions.append({"node": key, "task": node["task"], "field": field, "actual": actual,
                                      "value": node["value"], "result": decision})
            elif fact.get("task_done"):
                status, reason = "complete", "任务真实记录已完成，不重复执行"
            elif kind == "dispatch":
                current = fact.get("plan_status")
                retry = current == "rejected" and node["task"] not in branched["plan_status"]
                status = "ready" if current in ("missing", "invalid") or retry else "complete"
                reason = "提交或修订施工计划" if status == "ready" else "已有施工计划"
            elif kind == "review_plan":
                current = fact.get("plan_status")
                status = "ready" if current == "pending" else "complete" if current == "approved" or current == "rejected" and node["task"] in branched["plan_status"] else "waiting"
                reason = "独立审核施工计划" if status == "ready" else "计划审核已有结果" if status == "complete" else "等待有效施工计划"
            elif kind == "execute":
                delivery = fact.get("delivery_status")
                retry = delivery == "rejected" and node["task"] not in branched["delivery_status"]
                if delivery in ("pending", "accepted") or delivery == "rejected" and not retry:
                    status, reason = "complete", "已有交付记录"
                elif fact.get("plan_status") == "approved":
                    status, reason = "ready", "按当前有效批准施工" if not retry else "交付打回，按原有效计划返工"
                else:
                    reason = "计划未有效批准，不能施工"
            elif kind == "review_delivery":
                current = fact.get("delivery_status")
                status = "ready" if current == "pending" else "complete" if current == "accepted" or current == "rejected" and node["task"] in branched["delivery_status"] else "waiting"
                reason = "独立验收交付" if status == "ready" else "交付验收已有结果" if status == "complete" else "等待施工交付"
        result[key] = node | {"status": status, "reason": reason, "decision": decision}
        if status == "ready":
            import agents
            employee = agents.find(p, node.get("employee", ""))
            if employee and employee.get("paused"):
                result[key].update(status="waiting", reason="指定员工已暂停，等待人恢复")
        for edge in outgoing[key]:
            degree[edge["to"]] -= 1
            if degree[edge["to"]] == 0:
                todo.append(edge["to"])
    return {"ok": True, "nodes": list(result.values()), "edges": [e | {"status": edge_states.get(e["id"], "waiting")} for e in edges],
            "decisions": decisions, "waiting": [n for n in result.values() if n["status"] == "waiting"], "read_only": True}


def dry_run(conn, p, graph):
    check = validate(p, graph)
    if not check["ok"]:
        return {"ok": False, "nodes": [], "edges": [], "decisions": [], "waiting": [], "read_only": True, "validation": check}
    try:
        result = _evaluate(p, _shape(graph), check)
        import workorders
        stopped = workorders.paused(conn)
        if stopped:
            for node in result["nodes"]:
                if node["status"] == "ready":
                    node.update(status="waiting", reason="项目已叫停：" + stopped)
            result["waiting"] = [n for n in result["nodes"] if n["status"] == "waiting"]
        return result | {"validation": check, "project_paused": stopped}
    except (OSError, ValueError, store.Refused) as exc:
        return {"ok": False, "nodes": [], "edges": [], "decisions": [], "waiting": [{"reason": "真实记录读不了：" + str(exc)}], "read_only": True, "validation": check}


def _bound(p, goal, sub):
    state = _state(p)
    task = goal + " " + sub
    active = state.get("active")
    row = next((b for b in (active or {}).get("bindings", []) if b.get("task") == task and not b.get("condition_only")), None)
    return state, active if row else None, row, state["guards"].get(task)


def requires_plan(p, goal, sub):
    _, active, _, guard = _bound(p, goal, sub)
    return bool(active or guard)


def employee_bindings(p, agent):
    """核心准入也查明确员工绑定，不能靠尚未领活绕过流程审核。"""
    import agents
    employee = agents.require(p, agent)
    state = _state(p)
    rows = [b for b in (state.get("active") or {}).get("bindings", []) if not b.get("condition_only")]
    for task, guard in state["guards"].items():
        binding = guard.get("binding")
        if (not isinstance(binding, dict) or binding.get("task") != task
                or any(not isinstance(binding.get(k), str) or not binding.get(k)
                       for k in ("goal", "sub", "worker", "plan_reviewer", "delivery_reviewer"))
                or (binding.get("goal"), binding.get("sub")) != split_task(task)):
            # 旧停止守卫没有员工快照，不能用可变草稿猜其人员后放行核心。
            raise store.Refused("旧流程停止记录缺员工绑定；请人重新核对启用后再拿核心锁")
        rows.append(binding)
    return [b for b in rows if employee["code"] in
            (b.get("worker"), b.get("plan_reviewer"), b.get("delivery_reviewer"))]


def action_reason(p, action, goal, sub, agent):
    """准入发生在认领及实际记录写入之前；返回空文字才允许。"""
    import agents
    try:
        _, active, row, guard = _bound(p, goal, sub)
        if not active:
            return (guard or {}).get("reason", "")
        employee = agents.find(p, agent)
        if not employee:
            return "流程绑定的员工身份未确认"
        stage = ACTION_TYPES.get(action)
        expected = row["plan_reviewer"] if action == "review_plan" else row["delivery_reviewer"] if action == "review_delivery" else row["worker"]
        if stage is None or employee["code"] != expected:
            return f"流程 {active['code']} 的 {action} 已指定 {expected}"
        if employee.get("paused"):
            return "流程员工已暂停"
        check = validate(p, active["graph"])
        if not check["ok"]:
            return "启用流程的任务或员工配置已不适用：" + "；".join(check["errors"][:3])
        evaluated = _evaluate(p, active["graph"], check, active["task_signatures"])
        candidates = [n for n in evaluated["nodes"] if n.get("task") == row["task"] and n["type"] == stage]
        if any(n["status"] == "ready" for n in candidates):
            return ""
        reason = next((n["reason"] for n in candidates if n["status"] == "waiting"), None)
        return f"流程 {active['code']} 当前不允许 {action}：" + (reason or "该动作未激活或已经有真实结果")
    except (OSError, ValueError, store.Refused) as exc:
        return "流程准入无法确认：" + str(exc)


def worker_reason(p, prof, g, x):
    import agents
    import construction_plans as cp
    if not requires_plan(p, g["code"], x["code"]):
        return ""
    action = "execute" if cp.approved(p, g["code"], x["code"], agents.actor(prof["name"])) else "submit_plan"
    return action_reason(p, action, g["code"], x["code"], prof["name"])


def metadata(p, goal, sub, action="", agent=""):
    _, active, row, guard = _bound(p, goal, sub)
    if guard and not active:
        return {"code": guard["workflow"], "revision": guard["revision"], "stopped": True, "reason": guard["reason"]}
    if not active:
        return None
    stage = ACTION_TYPES.get(action)
    return {"code": active["code"], "revision": active["snapshot_revision"], "task": row["task"],
            "nodes": [n["id"] for n in active["graph"]["nodes"] if n.get("task") == row["task"] and (not stage or n["type"] == stage)]}
