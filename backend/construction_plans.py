"""施工计划审核关：普通 Markdown 正本、版本检查、独立审核和获准文件范围。

本关只约束档案开启「施工计划必审」的员工；老项目、旧交付不会因此失效。
待审记录在 自动化/施工计划/，审核通过的每一版另存为治理区的正式 P 计划。
SQLite 只用作写入互斥和事件日志；删去索引后仍能读出所有计划与审核历史。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PureWindowsPath

import agents
import atomic
import blueprint
import claims
import governance_paths as gp
import requirements
import store
import workorders
from project import Project

DIR = Path("自动化") / "施工计划"
WAIT, NO, OK = "待审", "打回", "通过"
REVIEW = "施工审核"
_CODE = re.compile(r"施-(\d+)")
_META = "## 记录\n\n```json\n"
_BODY = "\n```\n\n## 施工正文\n\n"


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _file(p: Project, code: str) -> Path:
    if not _CODE.fullmatch(code or ""):
        raise store.Refused("施工计划编号应写施-1这样的编号")
    return p.root / DIR / (code + ".md")


def _write(f: Path, record: dict) -> None:
    data = {k: v for k, v in record.items() if k not in ("file", "revision", "text", "approved_files")}
    text = f"# {record['code']} · {record['goal']} {record['sub']} · {record['name']}\n\n"
    text += _META + json.dumps(data, ensure_ascii=False, indent=2) + _BODY + record["text"].rstrip() + "\n"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    atomic.replace(tmp, f)


def _read(p: Project, f: Path) -> dict:
    try:
        raw = f.read_bytes()
        _, sep, tail = raw.decode("utf-8-sig").replace("\r\n", "\n").partition(_META)
        metadata, end, text = tail.partition(_BODY)
        record = json.loads(metadata)
        if (not sep or not end or not isinstance(record, dict) or record.get("code") != f.stem
                or record.get("state") not in (WAIT, NO, OK)
                or any(not record.get(k) for k in ("goal", "sub", "by", "employee"))
                or not isinstance(record.get("files"), list) or not isinstance(record.get("history"), list)):
            raise ValueError("记录格式不完整")
        record.update(text=text.rstrip(), file=gp.relative(p, f), revision=_digest(raw))
        record["approved_files"] = list(record.get("files", [])) if record.get("state") == OK else []
        return record
    except (OSError, UnicodeDecodeError, ValueError, TypeError) as exc:
        raise store.Refused(f"施工计划 {f.stem} 读不了：{exc}") from exc


def listing(p: Project) -> list[dict]:
    """按提交编号排列，不依赖索引数据库。损坏记录明确报错，不能当成没有。"""
    files = [f for f in (p.root / DIR).glob("施-*.md") if _CODE.fullmatch(f.stem)]
    return [_read(p, f) for f in sorted(files, key=lambda f: int(_CODE.fullmatch(f.stem)[1]))]


def get(p: Project, id: str) -> dict:
    f = _file(p, id)
    if not f.is_file():
        raise store.Refused(f"没有施工计划 {id}")
    return _read(p, f)


def _task(p: Project, goal: str, sub: str) -> tuple[dict, dict]:
    g = blueprint.find(blueprint.pyramid(p), goal)
    x = next((s for s in g["subs"] if s["code"] == sub), None) if g else None
    if x is None:
        raise store.Refused(f"蓝图里没有 {goal} {sub}")
    if not x.get("how", "").strip():
        raise store.Refused(f"{goal} {sub} 没写怎么验，先补齐再提交施工计划")
    return g, x


def _signature(p: Project, g: dict, x: dict) -> str:
    refs = requirements.task_refs(g, x)
    needs = [{k: q.get(k) for k in ("key", "func", "effect", "source", "goals", "modules")}
             for q in requirements.catalog(p) if q["key"] in refs]
    data = {"what": x["what"], "how": x["how"], "requirements": refs, "needs": needs,
            "goal": g.get("one_line", ""), "done_when": g.get("done_when", ""), "modules": g.get("modules", [])}
    return _digest(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _approval_signature(record: dict) -> str:
    """范围或正文经文件编辑器改动也必须重审，不能沿用旧版批准标记。"""
    fields = ("goal", "sub", "by", "version", "text", "files", "rules", "task_signature")
    # 旧批准仍按原字段核对；新审核把当时的审核来源一起封入签名。
    if "reviewer_model" in record:
        fields += ("reviewer", "reviewer_employee", "reviewer_model", "reviewed", "reviewed_revision", "why")
    return _digest(json.dumps({k: record.get(k) for k in fields}, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def normalize_files(p: Project, paths) -> list[str]:
    """文件精确匹配；目录必须以 / 结尾或确实是项目里的目录，不能扩大到项目根。"""
    if isinstance(paths, str):
        paths = [x.strip() for x in paths.split("、") if x.strip()]
    if not isinstance(paths, (list, tuple)):
        raise store.Refused("修改范围应写项目内文件或目录的列表")
    out = []
    root = p.root.resolve()
    for value in paths:
        if not isinstance(value, str):
            raise store.Refused("修改范围的每一项都应是路径文字")
        raw = value.strip().replace("\\", "/")
        if not raw or PureWindowsPath(raw).drive or raw.startswith("/") or any(c in raw for c in ('\x00', '*', '?', ':', '"', '<', '>', '|')):
            raise store.Refused("修改范围只允许项目内明确的相对路径")
        components = raw.rstrip("/").split("/")
        if any(part in ("", ".", "..") or part.endswith((".", " "))
               or re.match(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", part, re.I) for part in components):
            raise store.Refused("修改范围不能包含空路径或 .、..")
        f = (root / raw).resolve()
        if f == root or not f.is_relative_to(root):
            raise store.Refused("修改范围不能离开项目")
        rel = f.relative_to(root).as_posix()
        parts = rel.split("/")
        if parts[0].casefold() in {"索引", "回收站", "存档", ".git"} or (parts[0] == "笔记" and (len(parts) < 2 or parts[1] != "日志")):
            raise store.Refused("修改范围不能包括索引、回收站、存档或人的笔记")
        rel += "/" if raw.endswith("/") or f.is_dir() else ""
        if rel not in out:
            out.append(rel)
    if not out:
        raise store.Refused("施工计划必须明确至少一个允许修改的文件或目录")
    return out


def _model(prof: dict) -> str:
    if prof.get("model"):
        return str(prof["model"])
    match = re.search(r"[（(]([^）)]+)[）)]", prof.get("program", ""))
    return match[1].strip() if match else "沿用员工当前默认模型（档案未指定）"


def _revision(record: dict, revision: str) -> None:
    if not revision or record["revision"] != revision:
        raise store.Refused("施工计划版本已变化或未提供版本；先重新读取、对照后再提交")


def submit(conn, p: Project, goal: str, sub: str, agent: str, text: str, files,
           revision: str = "", rules=None) -> dict:
    """首次提交或修订同任务、同作者的计划。修订立即撤销上一版获准范围。"""
    prof = agents.require(p, agent)
    g, x = _task(p, goal, sub)
    if "干活" not in agents.jobs(prof):
        raise store.Refused("只有负责干活的员工能提交自己的施工计划")
    if not agents.allows(prof, g, x):
        raise store.Refused("这件任务不在你的负责范围内，不能提交施工计划")
    import workflow_graph
    if workflow_graph.requires_plan(p, goal, sub) and workorders.paused(conn):
        raise store.Refused("项目已叫停，流程恢复前不能提交施工计划")
    flow_reason = workflow_graph.action_reason(p, "submit_plan", goal, sub, agent)
    if flow_reason:
        raise store.Refused(flow_reason)
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 1024 * 1024:
        raise store.Refused("施工计划正文不能为空，且不超过 1 MB")
    scope = normalize_files(p, files)
    missing_rules = []
    rules_source = "提交者明确填写"
    if rules is None:
        import board
        applicable = (board.why(p, goal, sub) or {}).get("rules", [])
        rules = [r["file"] for r in applicable]
        layers = {r["layer"] for r in applicable}
        modules = [g["code"]] if g.get("kind") == "module" else list(g.get("modules") or [])
        missing_rules = [layer + "戒律记录" for layer in ["通用", "项目", *["模块 " + m for m in modules]]
                         if layer not in layers]
        rules_source = "项目现存适用戒律记录"
    if not isinstance(rules, (list, tuple)) or any(not isinstance(v, str) or not v.strip() for v in rules):
        raise store.Refused("适用规则应是非空文字组成的列表")
    who = agents.actor(prof["name"])
    with store.tx(conn):
        if workflow_graph.requires_plan(p, goal, sub) and workorders.paused(conn):
            raise store.Refused("项目已叫停，流程恢复前不能提交施工计划")
        flow_reason = workflow_graph.action_reason(p, "submit_plan", goal, sub, agent)
        if flow_reason:
            raise store.Refused(flow_reason)
        records = listing(p)
        old = next((r for r in records if r["goal"] == goal and r["sub"] == sub and r["by"] == who), None)
        if old:
            _revision(old, revision)
        elif revision:
            raise store.Refused("这是首次提交，不应带旧版本")
        code = old["code"] if old else f"施-{max([int(r['code'][2:]) for r in records], default=0) + 1}"
        refs = requirements.task_refs(g, x)
        needs = [q for q in requirements.catalog(p) if q["key"] in refs]
        history = list((old or {}).get("history", []))
        history.append({"at": _now(), "by": who, "act": "修订" if old else "提交", "version": (old or {}).get("version", 0) + 1,
                        "previous_revision": (old or {}).get("revision", ""), "previous_files": (old or {}).get("files", []),
                        "previous_formal_path": (old or {}).get("formal_path", "")})
        record = {"code": code, "goal": goal, "sub": sub, "by": who, "agent": who, "employee": prof["code"],
                  "name": prof["name"], "model": _model(prof), "at": (old or {}).get("at", _now()), "updated": _now(),
                  "state": WAIT, "version": (old or {}).get("version", 0) + 1, "text": text.strip(), "files": scope,
                  "rules": list(dict.fromkeys(v.strip() for v in rules)), "rules_source": rules_source,
                  "missing_rules": missing_rules, "modules": g.get("modules", []),
                  "requirements": needs, "requirement_refs": refs, "how": x["how"], "what": x["what"],
                  "task_signature": _signature(p, g, x), "goal_file": g["file"], "formal_path": "", "formal_revision": "", "approval_signature": "",
                  "reviewer": "", "reviewer_employee": "", "reviewer_model": "",
                  "reviewed": "", "reviewed_revision": "", "why": "", "history": history}
        _write(_file(p, code), record)
        store.log(conn, who, "修订施工计划" if old else "提交施工计划", code, f"{goal} {sub}；范围：{'、'.join(scope)}")
    # 修订使旧审核认领失效；拿着旧正文的审核员会被版本检查拒绝。
    if old:
        claims.release(conn, REVIEW, code, note="施工计划修订，重新审核")
    return get(p, code)


def _plan_target(p: Project, record: dict) -> tuple[Path, int]:
    goal = record["goal"]
    choices = [f for f in gp.plan_files(p).values() if f.parent.name == goal or f.parent.name.startswith(goal + " ")]
    old_folder = next((f.parent.name for f in choices if f.parent.parent.name == "计划"), "")
    g, _ = _task(p, goal, record["sub"])
    folder = gp.file_name(old_folder or (goal + " " + g["name"] if g.get("kind") != "module" else goal))
    n = max([int(m[1]) for f in choices if (m := re.match(r"^P(\d+)(?:\D|$)", f.name))], default=0) + 1
    title = gp.file_name(record["what"][:60].strip() or f"{goal} {record['sub']} 施工计划")
    path = gp.safe(p, f"治理/计划/{folder}/P{n} · {datetime.now():%Y-%m-%d} · {title}.md")
    return path, n


def _formal(record: dict, n: int) -> str:
    rule_text = "、".join(record["rules"])
    missing_rules = record.get("missing_rules", [])
    if missing_rules:
        rule_text += ("；" if rule_text else "") + "缺少：" + "、".join(missing_rules)
    out = [f"目标：{record['goal']} {record['sub']} · 守的戒律：{rule_text or '未填写'} · 用到的工具：见施工正文 · 动到的模块：{'、'.join(record['modules'])} · 状态：审核通过",
           "", f"# P{n} · {record['what']}", "", f"施工计划：{record['code']} 第 {record['version']} 版",
           f"作者：{record['employee']} {record['by']} · 模型：{record['model']} · 提交：{record['updated']}",
           f"审核：{record['reviewer']} · 模型：{record.get('reviewer_model') or '当时未记录'} · {record['reviewed']} · {record['why']}",
           f"审核版本：第 {record['version']} 版 · {record.get('reviewed_revision') or '当时未记录'}",
           "", "## 需求与验收", "", "需求关联：" + ("、".join(record["requirement_refs"]) or "未关联需求"),
           "怎么验：" + record["how"], "", "## 允许修改", "", *["- " + f for f in record["files"]],
           "", "## 施工正文", "", record["text"], ""]
    return "\n".join(out)


def review(conn, p: Project, id: str, agent: str, ok: bool, why: str, revision: str) -> dict:
    """独立审核。批准的正文、修改范围和蓝图验收标准一起留在正式 P 计划。"""
    prof = agents.require(p, agent)
    if prof.get("paused"):
        raise store.Refused("员工已暂停，不能继续审核施工计划")
    if "审核" not in agents.jobs(prof):
        raise store.Refused("员工岗位中没有审核，不能审核施工计划")
    if not isinstance(ok, bool):
        raise store.Refused("审核结果应是通过或打回")
    why = " ".join((why or "").split())
    if not why:
        raise store.Refused("审核必须写理由，通过或打回都要说明原因")
    who = agents.actor(prof["name"])
    with store.tx(conn):
        if workorders.paused(conn):
            raise store.Refused("人叫停了，恢复前不继续审核施工计划")
        prof = agents.require(p, who)
        if prof.get("paused") or "审核" not in agents.jobs(prof):
            raise store.Refused("员工已暂停或失去审核岗位，不能继续审核施工计划")
        record = get(p, id)
        _revision(record, revision)
        if record["by"] == who:
            raise store.Refused("不能审核自己写的施工计划")
        if record["state"] != WAIT:
            raise store.Refused(f"{id} 现在是{record['state']}，不在待审状态")
        g, x = _task(p, record["goal"], record["sub"])
        if not agents.allows(prof, g, x):
            raise store.Refused("这件任务不在你的审核范围内")
        import workflow_graph
        flow_reason = workflow_graph.action_reason(p, "review_plan", record["goal"], record["sub"], agent)
        if flow_reason:
            raise store.Refused(flow_reason)
        if _signature(p, g, x) != record["task_signature"]:
            raise store.Refused("蓝图需求、验收或模块范围已变化，请作者修订后重新审核")
        normalize_files(p, record["files"])
        held = [c for c in claims.active(conn) if c["goal"] == REVIEW and c["sub"] == id]
        if held and held[0]["agent"] != who:
            raise store.Refused("这张施工计划正在由其他员工审核")
        record.update(state=OK if ok else NO, reviewer=who, reviewer_employee=prof["code"],
                      reviewer_model=_model(prof), reviewed=_now(), reviewed_revision=revision, why=why)
        record["history"].append({"at": record["reviewed"], "by": who, "act": "通过" if ok else "打回",
                                  "reviewer_employee": prof["code"], "reviewer_model": record["reviewer_model"],
                                  "why": why, "version": record["version"], "reviewed_revision": revision})
        if ok:
            formal, n = _plan_target(p, record)
            formal.parent.mkdir(parents=True, exist_ok=True)
            raw = _formal(record, n).encode("utf-8")
            # 同号冲突不覆盖；普通文件保留上一轮正式计划。
            with formal.open("xb") as stream:
                stream.write(raw)
            record.update(formal_path=gp.relative(p, formal), formal_revision=_digest(raw), approval_signature=_approval_signature(record))
            record["history"][-1]["formal_path"] = record["formal_path"]
        _write(_file(p, id), record)
        store.log(conn, who, "通过施工计划" if ok else "打回施工计划", id, why)
    claims.release(conn, REVIEW, id, who, "审核完成")
    return get(p, id)


def approved(p: Project, goal: str, sub: str, agent: str) -> dict | None:
    """只返回当前版的有效批准；修订、正本被改或蓝图范围变动后都须重审。"""
    prof = agents.find(p, agent)
    who = agents.actor(prof["name"] if prof else agent)
    record = next((r for r in listing(p) if r["goal"] == goal and r["sub"] == sub and r["by"] == who), None)
    if not record or record["state"] != OK or not record.get("formal_path"):
        return None
    try:
        f = gp.safe(p, record["formal_path"])
        g, x = _task(p, goal, sub)
        if prof and (prof.get("paused") or "干活" not in agents.jobs(prof) or not agents.allows(prof, g, x)):
            return None
        if (_digest(f.read_bytes()) != record.get("formal_revision") or _signature(p, g, x) != record["task_signature"]
                or _approval_signature(record) != record.get("approval_signature")):
            return None
    except (OSError, ValueError, store.Refused):
        return None
    return record


def require_approved(p: Project, goal: str, sub: str, agent: str, files=None) -> dict | None:
    """交付/核心锁调用的统一关卡；未启用必审的旧员工保留旧行为。"""
    prof = agents.find(p, agent)
    record = approved(p, goal, sub, agent)
    import workflow_graph
    flow_required = workflow_graph.requires_plan(p, goal, sub)
    required = bool((prof or {}).get("plan_required", False) or flow_required)
    if not required:
        return record
    if flow_required:
        flow_reason = workflow_graph.action_reason(p, "execute", goal, sub, agent)
        if flow_reason:
            raise store.Refused(flow_reason)
    if not prof:
        raise store.Refused("流程施工必须使用已绑定的真实员工身份")
    if prof.get("paused"):
        raise store.Refused("员工已暂停，不能沿用之前批准的施工计划")
    if "干活" not in agents.jobs(prof):
        raise store.Refused("员工当前没有干活岗位，之前批准的施工计划不能继续施工")
    g, x = _task(p, goal, sub)
    if not agents.allows(prof, g, x):
        raise store.Refused("任务已不在当前工种或负责范围内，之前批准的施工计划不能继续施工")
    if record is None:
        raise store.Refused(f"{goal} {sub} 的施工计划尚未通过审核；提交/修订后交给其他审核员工")
    if files is not None:
        actual = normalize_files(p, files)
        for path in actual:
            if not any(path.casefold() == allowed.casefold() or (allowed.endswith("/") and path.casefold().startswith(allowed.casefold()))
                       for allowed in record["files"]):
                raise store.Refused(f"{path} 不在审核通过的修改范围内；修订施工计划并重新审核")
    return record


def next_review(conn, p: Project, agent: str) -> dict | None:
    """审核员工认领最早待审计划；叫停期间不认领。"""
    prof = agents.require(p, agent)
    if "审核" not in agents.jobs(prof) or prof.get("paused") or workorders.paused(conn):
        return None
    who = agents.actor(prof["name"])
    for record in listing(p):
        if record["state"] != WAIT or record["by"] == who:
            continue
        import dispatch
        if dispatch._blocked(p, prof, "review_plan:" + record["code"]):
            continue
        try:
            g, x = _task(p, record["goal"], record["sub"])
        except store.Refused:
            continue
        if not agents.allows(prof, g, x):
            continue
        import workflow_graph
        if workflow_graph.action_reason(p, "review_plan", record["goal"], record["sub"], agent):
            continue
        try:
            claims.claim(conn, REVIEW, record["code"], who, [REVIEW + " " + record["code"]],
                         f"审核施工计划 {record['goal']} {record['sub']}")
        except store.Refused:
            continue
        fresh = agents.require(p, who)
        if (workorders.paused(conn) or fresh.get("paused") or "审核" not in agents.jobs(fresh) or not agents.allows(fresh, g, x)
                or workflow_graph.action_reason(p, "review_plan", record["goal"], record["sub"], who)):
            claims.release(conn, REVIEW, record["code"], who, "准入失效，放下施工计划审核")
            return None
        return record
    return None
