"""把真实任务、批准计划、戒律和所选技能组合成网页与 MCP 共用的只读工作包。"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import agents
import blueprint
import board
import claims
import construction_plans
import deliveries
import drafts  # 旧看板的纯读依赖在服务初始化导入，避免首个请求生成缓存。
import governance_paths as gp
import knobs
import requirements
import skills
import store
import vcs
import workorders
from project import Project
from record_refs import Changed, ReadPath, Snapshot, normalize, relative_source, resolve

_EVENT_SQL = ("SELECT at, actor, action, target, detail FROM event WHERE (target = ? AND action IN ('领了', '放手'))"
              " OR (detail = ? AND action IN ('交付', '验收通过', '打回')) ORDER BY at, id")
_SELECTS = {"SELECT * FROM claim ORDER BY since", "SELECT value FROM meta WHERE key = ?", _EVENT_SQL}
_UNCERTAIN = re.compile(r"待确认|待你确认|等你定|我猜|猜的|比如|例如|未关联|未分配")


class _IndexConnection(sqlite3.Connection):
    """附带当前索引观察的连接，防止 immutable 期间出现新 WAL 被忽略。"""


@contextmanager
def open_read_connection(p):
    """入口专用只读索引连接；不存在就返回 None，不创建目录、库或表。"""
    snap = Snapshot(p)
    try:
        rel = Path(p.db_path).absolute().relative_to(snap.root).as_posix()
    except ValueError as exc:
        raise ValueError("工作包索引必须属于当前项目") from exc
    path = snap.path(rel)
    connection = None
    if path.is_file():
        database = snap.read(rel, include_text=False)
        wal = snap.read(rel + "-wal", include_text=False)
        shared = snap.observe_identity(rel + "-shm")
        live_wal = wal["state"] == "ok" and wal["bytes"] > 0
        # SQLite 的 mode=ro 在已关闭的 WAL 库上仍会创建空 WAL/SHM。
        # 已落盘且没有活 WAL 时用 immutable；若后来出现 WAL，快照核对会拒绝该包。
        ordinary = database["state"] == "ok" and wal["state"] in {"ok", "missing"} and shared["state"] in {"ok", "missing"}
        if ordinary and (not live_wal or shared["state"] == "ok"):
            options = "?mode=ro" + ("" if live_wal else "&immutable=1")
            connection = sqlite3.connect("file:" + quote(path.as_posix(), safe="/:") + options,
                                         uri=True, timeout=5, isolation_level=None, check_same_thread=False,
                                         factory=_IndexConnection)
            connection.row_factory = sqlite3.Row
            connection.index_snapshot = snap
    try:
        yield connection
    finally:
        if connection is not None:
            connection.close()


class _Cursor:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def __iter__(self):
        return iter(self.rows)

    def fetchall(self):
        return list(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None


class ReadOnlyConnection:
    """只放行旧看板的三个已知 SELECT；不把幂等建表发给真实连接。"""

    def __init__(self, conn):
        self.conn = conn
        self.unavailable = set()
        self.reads = {}

    def execute(self, statement, parameters=()):
        if statement.strip() == claims._TABLE.strip():
            return _Cursor()
        if statement not in _SELECTS:
            raise ValueError("只读工作包拒绝数据库动作：" + statement.split(None, 1)[0])
        key = (statement, tuple(parameters))
        try:
            rows = list(self.conn.execute(statement, parameters)) if self.conn is not None else []
            if self.conn is None:
                self.unavailable.add("索引连接不可用")
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            self.unavailable.add(str(exc))
            rows = []
        self.reads.setdefault(key, self._fingerprint(rows))
        return _Cursor(rows)

    @staticmethod
    def _fingerprint(rows):
        values = [dict(r) if hasattr(r, "keys") else list(r) for r in rows]
        return hashlib.sha256(json.dumps(values, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    def validate(self):
        issues = []
        for (statement, parameters), previous in list(self.reads.items()):
            if self._fingerprint(self.execute(statement, parameters).fetchall()) != previous:
                issues.append("项目索引在读取期间变化")
        if getattr(self.conn, "index_snapshot", None) is not None:
            issues.extend(self.conn.index_snapshot.validate())
        return issues

    def sources(self):
        out = []
        for (statement, parameters), revision in self.reads.items():
            query = hashlib.sha256(json.dumps([statement, parameters], ensure_ascii=False).encode()).hexdigest()
            out.append({"source": "sqlite:" + query, "state": "index_unavailable" if self.unavailable else "ok",
                        "revision": revision, "bytes": 0})
        if getattr(self.conn, "index_snapshot", None) is not None:
            out.extend(dict(row, source="index:" + row["source"]) for row in self.conn.index_snapshot.report()["sources"])
        return out


def _observe(snap, *, selected_skills):
    # 旧解析器会宽列这些治理目录；先检查真实路径，禁止经联接读取根外正文。
    for root in ("治理", "计划", "自动化/agent", "自动化/施工计划", "自动化/开工单", "自动化/交付"):
        for rel, kind in snap.walk(root):
            if kind == "file" and Path(rel).suffix.lower() in {".md", ".json"}:
                snap.read(rel, include_text=False)
    for name in snap.children("资料"):
        directory = "资料/" + name
        f = snap.path(directory)
        if not f.is_dir():
            continue
        snap.children(directory)
        for file in ("需求.md", "蓝图.md", "戒律.md"):
            snap.read(directory + "/" + file, include_text=False)
        if name in {"蓝图", "戒律"}:
            for child in snap.children(directory):
                rel = directory + "/" + child
                if child.endswith(".md") and snap.path(rel).is_file():
                    snap.read(rel, include_text=False)
    if selected_skills:
        for rel, kind in snap.walk("技能库"):
            if kind == "file":
                snap.read(rel, include_text=False)
        for module in snap.children("资料"):
            f = snap.path("资料/" + module)
            if f.is_dir():
                for rel, kind in snap.walk("资料/" + module + "/技能"):
                    if kind == "file":
                        snap.read(rel, include_text=False)


def _document(p, snap, kind, scope, source, code="", revision="", *, include_text=True):
    result = resolve(p, {"kind": kind, "scope": scope, "source": source, "code": code,
                         "revision": revision}, snapshot=snap, include_text=include_text)
    return {"ref": result["ref"], "document": result["document"], "reference_state": result["state"],
            "original_source": result.get("original_source", source),
            "resolved_source": result.get("resolved_source", source), "aliases": result.get("aliases", []),
            "conflicts": result.get("conflicts", []), "unverified_sources": result.get("unverified_sources", [])}


@skills._reading
def _skill_source_data(p, sid, language, snap):
    """复用技能目录验证，仅返回当前项目包数据，明确不探测本机或安装副本。"""
    row = skills._resolve(skills._records(p)[1], sid)
    if row is None:
        raise KeyError(sid)
    if row["id"] != sid:
        raise ValueError("请使用唯一完整技能编号：" + row["id"])
    normalized = "en" if language.startswith("en") else "zh-CN"
    choices = ["en", "en-US", "en-GB"] if normalized == "en" else ["zh-CN", "zh"]
    selected = next((choice for choice in choices if choice in row["languages"]), "zh-CN")
    fallback = ("en" if selected.startswith("en") else "zh-CN") != normalized
    source = row["languages"].get(selected) if row["kind"] == "skill" else row.get("info_path")
    document = snap.read(source) if source else None
    directory = row.get("_dir")
    out = {key: value for key, value in row.items() if not key.startswith("_")}
    out.update(files=len(skills._tree(directory)) if directory and directory.is_dir() else 0,
               package_revision=skills._digest(directory) if directory and directory.is_dir() else None,
               text=document["text"] if document else "", revision=document["revision"] if document else None,
               path=source, requested_language=language, language=selected if row["kind"] == "skill" else None,
               fallback=row["kind"] == "skill" and fallback,
               language_fallback="未提供请求语言，显示已有中文正本" if row["kind"] == "skill" and fallback else "",
               installation_status_checked=False, installation_status="not_checked")
    skills._verify_read(skills._READ.get())
    return out


def _complete(record):
    return record.get("reference_state") == "ok" and bool((record.get("document") or {}).get("complete"))


def _task_need_text(document, sub):
    columns = {}
    for line in document.get("text", "").splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
        if cells and "做什么" in cells:
            columns = {cell: i for i, cell in enumerate(cells)}
        if cells and cells[0] == sub:
            return cells[columns["为了"]] if "为了" in columns and columns["为了"] < len(cells) else ""
    return ""


def _rules(p, snap, g, gaps):
    out = []
    for layer, files in [("接手", ["AGENTS.md"]),
                         ("通用", [gp.relative(p, f) for f in gp.rule_files(p) if f.name.startswith("1 ")]),
                         ("项目", [gp.relative(p, f) for f in gp.rule_files(p) if f.name.startswith("2 ")])]:
        if not files:
            out.append({"layer": layer, "title": layer + "戒律", "ref": None,
                        "document": None, "missing": True, "reference_state": "missing"})
            gaps.append("缺少" + layer + "戒律")
        for source in files:
            record = dict(_document(p, snap, "rule", layer, source), layer=layer, title=Path(source).stem)
            record["missing"] = not _complete(record)
            if record["missing"]:
                gaps.append("戒律不能完整读取：" + source)
            out.append(record)
    modules = [g["code"]] if g.get("kind") == "module" else g.get("modules", [])
    for module in modules:
        source = f"资料/{gp.file_name(module)}/戒律.md"
        record = dict(_document(p, snap, "rule", module, source), layer="模块", title=module + " · 戒律")
        record["missing"] = not _complete(record)
        if record["missing"]:
            gaps.append("缺少或无法读取模块戒律：" + module)
        out.append(record)
    return out


def _empty(p, goal, sub):
    root = Path(p.root).absolute().as_posix()
    return {"schema": 1, "read_only": True,
            "project": {"root": root, "name": Path(p.root).name,
                        "identity": hashlib.sha256(root.casefold().encode()).hexdigest(),
                        "identity_scope": "current_local_root"},
            "task": None, "ref": None, "requirements": [], "goals": [], "execution_plans": [],
            "selected_plan": None, "allowed_files": [], "rules": [], "skills": [], "context_files": [],
            "workorders": [], "deliveries": [], "timeline": [],
            "views": {"structure": [], "time": [], "business": []},
            "readiness": {"state": "incomplete", "plan_valid": False, "context_complete": False,
                          "gaps": [], "warnings": [], "execution_authorized": False},
            "request": {"goal": goal, "sub": sub}, "snapshot": {}, "prompt": ""}


def _assemble(conn, p, snap, goal, sub, plan_code, skill_ids, lang):
    out = _empty(p, goal, sub)
    gaps, warnings = out["readiness"]["gaps"], out["readiness"]["warnings"]
    _observe(snap, selected_skills=bool(skill_ids))
    bp = blueprint.pyramid(p)
    groups = [g for g in bp["goals"] + bp.get("modules", []) if g["code"] == goal]
    if len(groups) != 1:
        gaps.append("任务所属目标不唯一" if groups else "找不到任务所属目标：" + goal)
        return out
    g = groups[0]
    tasks = [x for x in g["subs"] if x["code"] == sub]
    if len(tasks) != 1:
        gaps.append("任务编号在该来源内不唯一" if tasks else "找不到完整任务：" + goal + " " + sub)
        return out
    x = tasks[0]
    task_doc = _document(p, snap, "task", goal, g["file"], sub)
    if not _complete(task_doc):
        gaps.append("任务来源有冲突或无法完整读取：" + g["file"])
    detail = board.detail(conn, p, goal, sub)
    out["task"] = dict(detail or {}, **task_doc)
    out["ref"] = task_doc["ref"]
    out["timeline"] = [dict(r, kind="saved_event", time_known=bool(r.get("at"))) for r in (detail or {}).get("timeline", [])]
    warnings.append("时间记录仅含项目已保存记录；本包未读取本机 Git")
    warnings.append("戒律和技能显示当前正文版本；施工计划签名未覆盖全部上下文正文")
    out["task"]["timeline_source"] = "saved_project_records"
    goal_sources = [bp["s0"]] if bp.get("s0") else []
    if not bp.get("s0"):
        gaps.append("缺少 S0 目标正本")
    goal_sources.append(g)
    for row in goal_sources:
        record = dict(row, **_document(p, snap, "goal", row["code"], row["file"], row["code"]))
        out["goals"].append(record)
        if not _complete(record):
            gaps.append("目标正本不能完整读取：" + row["file"])
    raw_needs = _task_need_text(task_doc["document"] or {}, sub)
    refs = requirements.task_refs(g, x) if not _UNCERTAIN.search(raw_needs) else []
    out["task"]["requirement_relation_text"] = raw_needs
    if not refs:
        gaps.append("需求关联待确认" if _UNCERTAIN.search(raw_needs) else "该任务未明确关联需求")
    catalog = requirements.catalog(p, bp)
    available_modules = set(snap.children("资料"))
    for key in refs:
        candidates = [q for q in catalog if q["key"] == key]
        if len(candidates) != 1:
            out["requirements"].append({"key": key, "reference_state": "ambiguous" if candidates else "missing",
                                        "candidates": candidates, "ref": None, "document": None})
            gaps.append("需求来源不唯一或缺失：" + key)
            continue
        q = candidates[0]
        record = dict(q, **_document(p, snap, "requirement", q["scope"], q["file"], q["code"], q["revision"]))
        record["missing_modules"] = [m for m in q.get("modules", []) if m not in available_modules and not m.startswith("common:")]
        out["requirements"].append(record)
        if not _complete(record):
            gaps.append("需求原文不能完整读取：" + key)
        if record["missing_modules"]:
            gaps.append("需求承接模块已不存在：" + "、".join(record["missing_modules"]))
    # board 的旧 needs_full 会丢来源且接受待确认；替换成刚核对过的明确记录。
    out["task"]["needs_full"] = out["requirements"]
    matches = [r for r in construction_plans.listing(p) if r["goal"] == goal and r["sub"] == sub]
    for row in matches:
        record = dict(row, **_document(p, snap, "execution_plan", goal + " " + sub, row["file"], row["code"], row["revision"]))
        record["context_signature_scope"] = "existing_plan_signature_only"
        record["formal_document"] = None
        record["valid"], record["invalid_reason"] = False, "尚未通过当前有效审核"
        if row.get("formal_path"):
            formal = _document(p, snap, "formal_plan", goal, row["formal_path"],
                               (re.match(r"P\d+", Path(row["formal_path"]).name) or [""])[0], row.get("formal_revision", ""))
            record["formal_document"] = formal
        approved = construction_plans.approved(p, goal, sub, row["by"])
        author = agents.find(p, row["by"])
        valid = bool(author and author["code"] == row["employee"] and approved
                     and all(approved.get(k) == row.get(k) for k in ("code", "revision", "by")))
        if valid and _complete(record) and _complete(record["formal_document"] or {}):
            # 既有审批只检查 resolve 后的边界；读取关再拒绝实际链接与联接。
            for source in row["files"]:
                snap.path(relative_source(source, directory=True))
            record["valid"], record["invalid_reason"] = True, ""
        elif approved and approved.get("code") != row["code"]:
            record["invalid_reason"] = "该作者另一张计划的批准不能用于这张计划"
        elif row.get("state") == construction_plans.OK:
            record["invalid_reason"] = "正式计划、任务范围、施工正文或员工权限已变化，需重新核验批准"
        record["approved_files"] = list(row["files"]) if record["valid"] else []
        record["display_state"] = row["state"] if record["valid"] or row["state"] != construction_plans.OK else "失效"
        out["execution_plans"].append(record)
        for history in row.get("history", []):
            out["timeline"].append({"kind": "execution_plan", "at": history.get("at", ""),
                                    "time_known": bool(history.get("at")), "who": history.get("by", ""),
                                    "what": history.get("act", ""), "detail": row["code"], "ref": record["ref"]})
    selected = next((r for r in out["execution_plans"] if r["code"] == plan_code), None) if plan_code else (
        out["execution_plans"][0] if len(out["execution_plans"]) == 1 else None)
    if selected and selected["valid"]:
        out["selected_plan"] = selected
        out["allowed_files"] = list(selected["files"])
    else:
        if plan_code:
            gaps.append("所选施工计划不存在或已失效：" + plan_code)
        elif len(out["execution_plans"]) > 1:
            gaps.append("有多份施工计划，请明确选择计划编号")
        else:
            gaps.append("没有当前有效批准的施工计划")
    out["task"]["execution_plan"] = out["selected_plan"]
    out["rules"] = _rules(p, snap, g, gaps)
    for sid in skill_ids:
        try:
            entry = _skill_source_data(p, sid, lang, snap)
            if entry["id"] != sid:
                raise ValueError("请使用唯一完整技能编号：" + entry["id"])
            record = dict(entry, document=None, ref=None, reference_state="external_reference")
            if entry.get("path"):
                record.update(_document(p, snap, "skill", entry.get("business") or entry.get("module") or "project",
                                        entry["path"], sid, entry.get("revision") or ""))
                if not _complete(record):
                    gaps.append("技能正文不能完整读取：" + sid)
                record["text"] = (record.get("document") or {}).get("text", "")
            else:
                warnings.append("技能只有外部参考，未加载正文：" + sid)
            record["executed"] = False
            record["execution_state"] = "未运行"
            if entry.get("issues") or entry.get("blocked"):
                gaps.append("技能配套或版本存在缺项：" + sid)
            out["skills"].append(record)
        except (KeyError, OSError, ValueError) as exc:
            out["skills"].append({"id": sid, "ref": None, "document": None, "reference_state": "missing",
                                  "executed": False, "execution_state": "未运行", "error": str(exc)})
            gaps.append("所选技能无法读取：" + sid + "（" + str(exc) + "）")
    for source in out["allowed_files"]:
        rel = relative_source(source, directory=True)
        record = _document(p, snap, "source_file", "current_project", rel, include_text=False)
        record.update(approved_path=source, content_loaded=False, origin="current_project")
        if record["document"]["state"] == "missing":
            record["planned_new"] = True
        elif record["document"]["state"] == "oversize":
            warnings.append("源码超出有界指纹读取上限：" + source)
        out["context_files"].append(record)
    orders = workorders.list_all(p)
    for wo in orders:
        # 完整目标/任务或来源限定需求关联；禁止裸需号串到另一来源。
        linked = any(target in {goal, goal + " " + sub, *refs, *[goal + " " + ref for ref in refs]}
                     for target in wo.get("target", []))
        if not linked:
            continue
        source = "自动化/开工单/" + wo["file"]
        row = dict(wo, **_document(p, snap, "workorder", goal + " " + sub, source, wo["code"]))
        out["workorders"].append(row)
        out["timeline"].append({"kind": "workorder", "at": wo.get("started", ""), "time_known": bool(wo.get("started")),
                                "what": "开工单开始", "detail": wo["code"], "ref": row["ref"]})
    out["task"]["orders"] = [{"code": r["code"], "name": r["name"]} for r in out["workorders"]]
    drafted = out["task"].get("drafted")
    if drafted:
        row = dict(drafted, **_document(p, snap, "draft", goal + " " + sub, "治理/草稿/" + drafted["code"] + ".md", drafted["code"]))
        out["task"]["drafted"] = row
        out["timeline"].append({"kind": "draft", "at": drafted.get("at", ""), "time_known": bool(drafted.get("at")),
                                "who": drafted.get("by", ""), "what": "任务草稿记录", "detail": drafted["code"], "ref": row["ref"]})
    for j in deliveries.list_all(p):
        if (j["goal"], j["sub"]) != (goal, sub):
            continue
        source = "自动化/交付/" + j["file"]
        row = dict(j, **_document(p, snap, "delivery", goal + " " + sub, source, j["code"]))
        out["deliveries"].append(row)
        out["timeline"].append({"kind": "delivery", "at": j.get("at", ""), "time_known": bool(j.get("at")),
                                "who": j["by"], "what": j["state"], "detail": j["code"], "ref": row["ref"]})
    for row in out["execution_plans"]:
        formal = row.get("formal_document")
        if formal:
            date = re.search(r" · (\d{4}-\d{2}-\d{2}) · ", row["formal_path"])
            out["timeline"].append({"kind": "formal_plan", "at": date[1] if date else "",
                                    "time_known": bool(date), "precision": "date" if date else "unknown",
                                    "what": "正式计划", "detail": formal["ref"]["code"], "ref": formal["ref"]})
    if conn.unavailable:
        gaps.append("索引不可用，负责人和时间记录不能确认")
        out["task"]["ownership_known"] = False
        warnings.extend(sorted(conn.unavailable))
    else:
        out["task"]["ownership_known"] = True
    gaps.extend(bp.get("problems", []))
    out["timeline"].sort(key=lambda r: (not r.get("time_known", True), r.get("at", ""), r.get("detail", "")))
    out["views"]["structure"] = [{"goal": goal, "sub": sub, "ref": out["ref"],
                                      "requirement_refs": [r.get("ref") for r in out["requirements"]]}]
    out["views"]["time"] = out["timeline"]
    out["views"]["business"] = [{"business": r.get("business", ""), "skill_id": r["id"], "ref": r.get("ref")}
                                     for r in out["skills"]]
    out["readiness"].update(plan_valid=bool(out["selected_plan"]), context_complete=not gaps,
                            state="ready_to_read" if not gaps else "incomplete")
    return out


def _prompt(out):
    goal, sub = out["request"]["goal"], out["request"]["sub"]
    lines = [f"任务工作包 Task work package · {goal} {sub}",
             "本包是只读材料，复制不等于开工；按本人员工身份、原认领、核心锁和开工流程执行。",
             "This package is read-only; copying it does not start work or grant execution permission."]
    if not out["readiness"]["plan_valid"] or not out["readiness"]["context_complete"]:
        lines += ["不准据此直接施工 / Do not execute directly from this package:", *["- " + s for s in out["readiness"]["gaps"]]]
    for row in out["goals"]:
        lines += ["", "目标原文 / Goal source: " + row["ref"]["source"], (row["document"] or {}).get("text", "")]
    task = out.get("task") or {}
    lines += ["", "任务原话 / Task: " + task.get("what", ""), "怎么验 / Acceptance: " + task.get("how", ""),
              "实际状态 / Current state: " + task.get("col", "未知 / Unknown")]
    for row in out["requirements"]:
        lines += ["", "需求 / Requirement: " + row.get("key", ""), (row.get("document") or {}).get("text", "缺失或来源不唯一")]
    plan = out["selected_plan"]
    if plan:
        lines += ["", f"已批准计划 / Approved plan: {plan['code']} · {plan['by']} · {plan['revision']}",
                  (plan.get("formal_document", {}).get("document") or {}).get("text", ""),
                  "允许修改 / Allowed files:", *["- " + f for f in out["allowed_files"]]]
    for row in out["rules"]:
        lines += ["", "适用规则 / Rule: " + row["title"], (row.get("document") or {}).get("text", "缺少正本")]
    for row in out["skills"]:
        lines += ["", "所选技能 / Selected skill: " + row["id"], "执行状态 / Execution state: 未运行 / Not run",
                  "依赖 / Dependencies: " + json.dumps(row.get("dependencies", []), ensure_ascii=False), row.get("text", "")]
    for row in out["deliveries"]:
        lines += ["", f"已有交付 / Recorded delivery: {row['code']} · {row['state']}", row["body"]]
    lines += ["", "缺项 / Gaps:", *["- " + s for s in out["readiness"]["gaps"]],
              "读取提示 / Read warnings:", *["- " + s for s in out["readiness"]["warnings"]],
              "交付必须记录实际检查；未运行、失败、待独立验收和待你验收分别照实填写。",
              "工作包指纹仅代表读取内容，不是批准或验收结果。"]
    return "\n".join(lines)


def build(conn, p, goal, sub, *, plan_code="", skill_ids=None, lang="zh"):
    """有界纯读取；正文或目录变化时整包重读一次，仍变化则不返回混合正文。"""
    if not all(isinstance(v, str) and v.strip() and not any(ord(c) < 32 for c in v) for v in (goal, sub)):
        raise ValueError("必须写完整目标和任务编号")
    if not isinstance(plan_code, str) or (plan_code and not re.fullmatch(r"施-\d+", plan_code)):
        raise ValueError("施工计划编号应写施-1这样的完整编号")
    if lang not in {"zh", "zh-CN", "en", "en-US", "en-GB"}:
        raise ValueError("语言只支持中文或英文")
    if skill_ids is None:
        skill_ids = []
    if not isinstance(skill_ids, (list, tuple)) or len(skill_ids) > 50 or any(not isinstance(s, str) or not s.strip() for s in skill_ids):
        raise ValueError("技能应是至多 50 个唯一完整编号组成的列表")
    skill_ids = list(dict.fromkeys(skill_ids))
    selection = {"goal": goal, "sub": sub, "plan_code": plan_code, "skill_ids": skill_ids, "lang": lang}
    for retry in range(2):
        snap, readonly = Snapshot(p), ReadOnlyConnection(conn)
        current = Project(ReadPath(snap.root, snapshot=snap))
        try:
            out = _assemble(readonly, current, snap, goal, sub, plan_code, skill_ids, lang)
            issues = snap.validate() + readonly.validate()
        except Changed as exc:
            out, issues = _empty(p, goal, sub), [str(exc)]
        except (OSError, ValueError, KeyError, store.Refused) as exc:
            out, issues = _empty(p, goal, sub), snap.validate()
            out["readiness"]["gaps"].append("工作包来源读取失败：" + str(exc))
        if issues and retry == 0:
            continue
        if issues:
            out = _empty(p, goal, sub)
            out["readiness"].update(state="inconsistent", gaps=list(dict.fromkeys(issues)))
        out["readiness"]["gaps"] = list(dict.fromkeys(out["readiness"]["gaps"]))
        out["readiness"]["warnings"] = list(dict.fromkeys(out["readiness"]["warnings"]))
        out["snapshot"] = snap.report(selection=selection, extra_sources=readonly.sources(), retries=retry, issues=issues)
        out["prompt"] = _prompt(out)
        return out
