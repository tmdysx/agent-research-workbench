"""蓝图怎么看：大问题卡、卡在哪、每件最后一次变动（蓝图 S2-1、S2-5、S2-6）。

作者 10-01：「蓝图定稿」——蓝图要一眼看到全局（每个大问题定稿几块、做完几件）、看得出卡在哪、
能按时间排（「蓝图和任何的目录都有有两中排序方式，一种是结构，一种是时间，这个很重要，方便查验」）。
- 大问题卡跟自动化总览「离全自动还差什么」用同一份 dispatch.plan_status，数一定对得上
- 卡在哪：没做完的件（不算「以后」）按「为了」哪条需求分组，压得最多的排最上；没写「为了」的单独一组
- 时间：每件那一行最后一次改动的时间和人，取本机 git（git blame）；还没记进 git 的用文件的修改时间；没有 git 也照样能看
"""
from __future__ import annotations

import re
import subprocess
import threading
from datetime import datetime

import blueprint
from project import Project

_ROWCODE = re.compile(r"^\|\s*(S\d+-\d+)\s*\|")
_J = re.compile(r"\bJ\d+\b")
_CACHE: dict[str, tuple[tuple, dict]] = {}
_LOCK = threading.Lock()


def big_cards(p: Project, rows: list[dict] | None = None) -> list[dict]:
    """S0「两个大问题」表里每个大问题一张卡：底下几块、定稿几块、做完几件 / 一共几件。"""
    import dispatch
    rows = rows if rows is not None else dispatch.plan_status(p)
    order = list(dict.fromkeys(b["big"] for b in blueprint.big_problems(p)))
    out = []
    for big in order:
        xs = [r for r in rows if r["group"] == big]
        out.append({"big": big, "members": [{"code": r["code"], "name": r["name"], "kind": r["kind"], "final": bool(r["final"])} for r in xs],
                    "blocks": len(xs), "final": sum(bool(r["final"]) for r in xs),
                    "items": sum(r["items"] for r in xs), "done": sum(r["done"] for r in xs)})
    rest = [r for r in rows if r["kind"] == "模块" and r["group"] == "模块" and r["items"]]   # 有任务、S0 表里没写的模块
    if rest:
        out.append({"big": "没挂在大问题下的模块", "members": [{"code": r["code"], "name": r["name"], "kind": r["kind"], "final": bool(r["final"])} for r in rest],
                    "blocks": len(rest), "final": sum(bool(r["final"]) for r in rest),
                    "items": sum(r["items"] for r in rest), "done": sum(r["done"] for r in rest)})
    return out


def _open(s: dict) -> bool:
    return s["status"] != "ok" and not s["text"].startswith("以后")


def stuck(p: Project, bp: dict | None = None) -> list[dict]:
    """卡在哪：每条需求底下还压着几件没做完的，多的排前面；没写「为了」的件放最后一组。"""
    import requirements
    bp = bp or blueprint.pyramid(p)
    out, seen = [], set()
    for q in requirements.catalog(p, bp):
        left = [t for t in q["tasks"] if _open(t)]
        seen |= {t["key"] for t in q["tasks"]}
        if left:
            out.append({"key": q["key"], "scope": q["scope"], "code": q["code"], "func": q.get("func", ""),
                        "left": [{"goal": t["goal"], "code": t["code"], "what": t["what"], "text": t["text"]} for t in left]})
    out.sort(key=lambda x: -len(x["left"]))
    loose = [{"goal": g["code"], "code": s["code"], "what": s["what"], "text": s["text"]}
             for g in bp["goals"] + bp.get("modules", []) for s in g["subs"] if _open(s) and f"{g['code']}::{s['code']}" not in seen]
    if loose:
        out.append({"key": "", "scope": "", "code": "", "func": "没写「为了」哪条需求", "left": loose})
    return out


def _blame(p: Project, f) -> dict:
    """一份文件里每个 S2 那一行最后一次改动：{S2-3: (时间 ISO, 谁)}。git 里没有的行用文件修改时间、谁写空。"""
    import vcs
    rel = f.resolve().relative_to(p.root.resolve()).as_posix()
    st = f.stat()
    head = ""
    try:
        head = (p.root / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = p.root / ".git" / head[5:]
            head = ref.read_text(encoding="utf-8").strip() if ref.is_file() else head
    except OSError:
        pass
    key = (st.st_mtime_ns, st.st_size, head)
    with _LOCK:
        hit = _CACHE.get(rel)
        if hit and hit[0] == key:
            return hit[1]
    mtime = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
    lines = f.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    out: dict = {}
    got: list[tuple[str, str]] = []
    if vcs.enabled(p):
        try:
            code, text = vcs._run(p, "blame", "--line-porcelain", "--", rel, timeout=20)
        except (OSError, subprocess.SubprocessError):
            code, text = 1, ""
        if code == 0:
            author, at = "", 0
            for line in text.split("\n"):
                if line.startswith("author "):
                    author = line[7:].strip()
                elif line.startswith("author-time "):
                    at = int(line[12:].strip() or 0)
                elif line.startswith("\t"):
                    got.append((author, datetime.fromtimestamp(at).isoformat(timespec="seconds") if at else mtime))
    for i, line in enumerate(lines):
        m = _ROWCODE.match(line)
        if not m:
            continue
        who, at = got[i] if i < len(got) else ("", mtime)           # git blame 一行对一行
        if who == "Not Committed Yet":
            who, at = "", mtime
        out[m.group(1)] = (at, who)
    with _LOCK:
        _CACHE[rel] = (key, out)
    return out


def timeline(p: Project, bp: dict | None = None) -> list[dict]:
    """蓝图正文按时间排：每件那一行最后一次变动（交付了、改了状态、新加的），最新的在前。"""
    import governance_paths as gp
    bp = bp or blueprint.pyramid(p)
    out = []
    for g in bp["goals"] + bp.get("modules", []):
        f = gp.resolve(p, g["file"])
        if not f.is_file():
            continue
        times = _blame(p, f)
        for s in g["subs"]:
            at, who = times.get(s["code"], ("", ""))
            j = _J.search(s["text"])
            out.append({"at": at, "who": who, "goal": g["code"], "kind": g.get("kind", "S1"), "code": s["code"], "what": s["what"],
                        "text": s["text"], "status": s["status"], "j": j.group(0) if j else ""})
    out.sort(key=lambda x: x["at"], reverse=True)
    return out
