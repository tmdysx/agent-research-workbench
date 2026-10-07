"""归档（S1-8 S2-61；需-29）：旧的过程记录按月收进 `归档/年-月/`，原文原样、整份搬，带一张索引；随时能拿回来。

作者 10-03：「清理模块不光得有垃圾桶的功能，还得有重铸的功能，因为ai编程很多信息是重复杂乱的，随着业务和功能的发展会越来越乱，
所以要有冬藏压缩重铸的功能，相当于上下文压缩了」。界面上叫「归档」。
- 收哪些：机器日志（整月一个文件，那个月过完了、最后一条也够旧了才收）· 交接单（每个 agent 留最新那份）·
  施工计划（那件做完了的）· 计划（写了做完的、那件做完了的、被同一施工计划的新版取代的）。都要比设置里的天数旧
- 不碰：人的笔记、交付单（时间线和「做完在哪一档」要用）、方向文件（需求、戒律、目标）
- 整份搬、内容一个字不改（日志写着只增不改，这样也不破）；搬到 `归档/<那条记录自己的年-月>/<原来的路径>`；
  `归档/索引.json` 记从哪来、搬到哪、什么时候、谁、多大
- 搬之前存一档（自动存档，不管设置里开没开）；搬的时候监管认得是归档（不当成删东西）
- 日志、交接单、计划列表、时间线、全站检索都把归档的算进去（各自的读法里加一步）
做法是自己写的；参考过的项目见使用说明「参考过的项目」。
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import store
from project import Project

DIR = "归档"
INDEX = "索引.json"
KINDS = ("日志", "交接单", "施工计划", "计划")
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def root(p: Project) -> Path:
    return p.root / DIR


def index(p: Project) -> list[dict]:
    try:
        return json.loads((root(p) / INDEX).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _save_index(p: Project, rows: list[dict]) -> None:
    f = root(p) / INDEX
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def archived_files(p: Project, under: str, pattern: str = "*.md") -> list[Path]:
    """归档里原来在 under 下面的文件（日志、交接单、计划的读法用）：归档/<年-月>/<under>/…"""
    d = root(p)
    if not d.is_dir():
        return []
    out = []
    for month in sorted(x for x in d.iterdir() if x.is_dir() and re.fullmatch(r"\d{4}-\d{2}", x.name)):
        base = month / under
        if base.is_dir():
            out += sorted(base.rglob(pattern))
    return out


def is_archived(p: Project, rel: str) -> bool:
    """这个路径是被归档搬走的（监管用：不当成删东西）。"""
    return any(r["from"] == rel and r.get("state") == "归档" for r in index(p))


# ---------------------------------------------------------------- 哪些能收

def _old(day: str, days: int, now: datetime) -> bool:
    try:
        return datetime.strptime(day[:10], "%Y-%m-%d") <= now - timedelta(days=days)
    except ValueError:
        return False


def _mday(f: Path) -> str:
    return datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")


def _rel(p: Project, f: Path) -> str:
    return f.relative_to(p.root).as_posix()


def _plan_done(p: Project, text: str, bp: dict) -> str:
    """一份计划做完了没有：头上写了做完 / 它那件做完了 → 写一句为什么；没做完返回空。"""
    import blueprint
    head = "\n".join(text.splitlines()[:12])
    m = re.search(r"状态[：:]\s*(做完|完成|已完成)", head)
    if m:
        return "计划头上写着做完"
    m = re.search(r"目标[：:]\s*(S1-\d+)\s+(S2-\d+)", head)
    if m:
        g = blueprint.find(bp, m.group(1))
        x = next((s for s in (g or {}).get("subs", []) if s["code"] == m.group(2)), None)
        if x and x["status"] == "ok":
            return f"{m.group(1)} {m.group(2)} 做完了"
    return ""


def candidates(conn, p: Project, *, days: int | None = None, now: datetime | None = None) -> list[dict]:
    """能收进归档的：[{kind, rel, title, day, month, size, why}]，旧的在前。"""
    import blueprint
    import governance_paths as gp
    import knobs
    days = knobs.get(conn, "archive_days") if days is None else days
    now = now or datetime.now()
    out = []

    def add(kind, f, day, why, title=""):
        out.append({"kind": kind, "rel": _rel(p, f), "title": title or f.stem, "day": day, "month": day[:7],
                    "size": f.stat().st_size, "why": why})

    # 日志：整月一份，那个月过完了、最后一条也够旧了
    import journal
    this_month = now.strftime("%Y-%m")
    for f in journal._files(p):
        if f.stem >= this_month:
            continue
        es = journal.parse(f.read_text(encoding="utf-8"))
        last = max((e["at"] for e in es), default=f.stem + "-01")
        if _old(last, days, now):
            add("日志", f, last[:10], f"{f.stem} 整月 {len(es)} 条，最后一条 {last[:10]}", f"日志 {f.stem}")
    # 交接单：每个 agent 留最新那份
    hd = p.root / "自动化" / "交接"
    rows = []
    for f in (hd.glob("H*.md") if hd.is_dir() else []):
        m = re.match(r"H(\d+)", f.name)
        if not m:
            continue
        parts = [x.strip() for x in f.stem.split("·")]
        day = parts[1] if len(parts) > 1 and _DATE.fullmatch(parts[1]) else _mday(f)
        rows.append((int(m.group(1)), parts[2] if len(parts) > 2 else "", day, f))
    newest = {}
    for n, who, day, f in rows:
        if n > newest.get(who, (0,))[0]:
            newest[who] = (n, f)
    for n, who, day, f in rows:
        if newest.get(who, (0,))[0] != n and _old(day, days, now):
            add("交接单", f, day, f"{who} 后来又写了 H{newest[who][0]}")
    # 施工计划：那件做完了
    bp = blueprint.pyramid(p)
    cd = p.root / "自动化" / "施工计划"
    for f in sorted(cd.glob("施-*.md")) if cd.is_dir() else []:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r'"goal":\s*"([^"]+)".*?"sub":\s*"([^"]+)"', text, re.S)
        if not m:
            continue
        g = blueprint.find(bp, m.group(1))
        x = next((s for s in (g or {}).get("subs", []) if s["code"] == m.group(2)), None)
        if x and x["status"] == "ok" and _old(_mday(f), days, now):
            add("施工计划", f, _mday(f), f"{m.group(1)} {m.group(2)} 做完了")
    # 计划：做完的、被同一施工计划新版取代的
    plans = {}
    for rel, f in gp.plan_files(p).items():
        if not re.match(r"P\d+", f.name):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        m = _DATE.search(f.name)
        day = m.group(1) if m else _mday(f)
        sv = re.search(r"施工计划[：:]\s*(施-\d+)\s*第\s*(\d+)\s*版", "\n".join(text.splitlines()[:12]))
        plans[f] = (text, day, (sv.group(1), int(sv.group(2))) if sv else None)
    latest_ver = {}
    for f, (_, _, sv) in plans.items():
        if sv:
            latest_ver[sv[0]] = max(latest_ver.get(sv[0], 0), sv[1])
    for f, (text, day, sv) in plans.items():
        if not _old(day, days, now):
            continue
        why = f"被 {sv[0]} 第 {latest_ver[sv[0]]} 版取代" if sv and sv[1] < latest_ver[sv[0]] else _plan_done(p, text, bp)
        if why:
            add("计划", f, day, why)
    return sorted(out, key=lambda x: (x["day"], x["rel"]))


# ---------------------------------------------------------------- 收、拿回来

def put_away(conn, p: Project, rels: list[str] | None = None, *, by: str, days: int | None = None) -> dict:
    """收进归档。rels 空 = 把现在能收的都收；给了就只收这些（得在能收的里面）。先存一档。→ {moved, bytes, checkpoint}"""
    import snapshot
    cands = candidates(conn, p, days=days)
    pick = cands if rels is None else [c for c in cands if c["rel"] in set(rels)]
    if rels is not None and len(pick) != len(set(rels)):
        bad = sorted(set(rels) - {c["rel"] for c in pick})
        raise store.Refused("这些现在不能收：" + "、".join(bad[:5]))
    if not pick:
        return {"moved": [], "bytes": 0, "checkpoint": ""}
    m = snapshot.save(conn, p, name="归档前", why=f"收 {len(pick)} 份旧记录进归档之前", mode="全量", by=by, auto=True)
    rows = index(p)
    moved, size = [], 0
    for c in pick:
        src = p.root / c["rel"]
        dst = root(p) / c["month"] / c["rel"]
        if not src.is_file() or dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
        rows.append({"from": c["rel"], "to": dst.relative_to(p.root).as_posix(), "kind": c["kind"], "title": c["title"], "day": c["day"],
                     "month": c["month"], "size": c["size"], "why": c["why"], "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                     "by": by, "checkpoint": m["code"], "state": "归档"})
        moved.append(c["rel"])
        size += c["size"]
    _save_index(p, rows)
    import journal
    kinds = {}
    for c in pick:
        if c["rel"] in moved:
            kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    journal.add(conn, p, f"收了 {len(moved)} 份旧记录进 归档/（" + "、".join(f"{k} {n}" for k, n in kinds.items())
                + f"，{size // 1024} KB），归档前存了 {m['code']}；能拿回来", kind="归档", by=by)
    return {"moved": moved, "bytes": size, "checkpoint": m["code"]}


def bring_back(conn, p: Project, rels: list[str], *, by: str) -> dict:
    """拿回来：放回原处（原处已经有同名的就不放，写清）。"""
    rows = index(p)
    back, skipped = [], []
    for r in rows:
        if r["from"] not in rels or r.get("state") != "归档":
            continue
        src, dst = p.root / r["to"], p.root / r["from"]
        if dst.exists() or not src.is_file():
            skipped.append(r["from"])
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
        r.update(state="拿回来了", back_at=datetime.now().strftime("%Y-%m-%d %H:%M"), back_by=by)
        back.append(r["from"])
    _save_index(p, rows)
    if back:
        import journal
        journal.add(conn, p, f"从归档拿回来 {len(back)} 份：" + "、".join(back[:8]), kind="归档", by=by)
    return {"back": back, "skipped": skipped}


def summary(p: Project) -> dict:
    """归档里有什么：按月、按类几份、多大。"""
    rows = [r for r in index(p) if r.get("state") in ("归档", "旧版")]   # 旧版：重写单换下来的（S1-8 S2-63）
    months: dict = {}
    for r in rows:
        m = months.setdefault(r["month"], {"month": r["month"], "count": 0, "size": 0, "kinds": {}})
        m["count"] += 1
        m["size"] += r.get("size", 0)
        m["kinds"][r["kind"]] = m["kinds"].get(r["kind"], 0) + 1
    return {"count": len(rows), "size": sum(r.get("size", 0) for r in rows), "months": sorted(months.values(), key=lambda m: m["month"], reverse=True)}
