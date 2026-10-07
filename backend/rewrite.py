"""重写单（S1-8 S2-63；需-29）：给正本出一张「改前 / 改后」对照，每处写来源；点「行」才换上，换之前存档，旧版标「被哪张取代」收进归档。

作者 10-03：「要有冬藏压缩重铸的功能，相当于上下文压缩了」。界面上叫「重写」。
- 正本：需求、戒律、目标（方向文件）· 协议、使用说明、AGENTS.md、CLAUDE.md、DESIGN.md、README、技能
- 作者 10-03：「我的想法是重铸由agent来做」——查乱报的太长、重复的正本自动派给「规划」岗位的员工出单；
  非方向文件的单由另一个「审核」岗位的员工独立审（next_task 给它一件「审重写单」），审过就换上；方向文件还是只有人能换（戒律：方向只有人改）
- 出单（propose）：谁都能出（agent 用 propose_rewrite；人在网页上点「让 agent 重写这份」只是派一件「写重写单」的活）；
  单子记 改-n：改哪份、改之前那份的指纹、改后全文、改了哪几处（每处：合并了哪几条 / 去掉了哪几句 / 为什么）
- 换上（accept）：正本还是出单时那份才换（中间被人改过就拒，重出一张）；换前存一档；旧版整份收进
  `归档/<年-月>/旧版/<原路径>.改-n.md`，索引写「被 改-n 取代」；方向文件（需求、戒律、目标）只有人能点，别的人和 G1 能点
- 不要（drop）：写一句为什么，单子留着
做法是自己写的（改版留旧版、标被谁取代是文档管理的老办法）；参考过的项目见使用说明「参考过的项目」。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import store
from project import Project

DIR = "自动化/重写单"
JOB = "写重写单"
DIRECTION = ("治理/需求/", "治理/戒律/", "治理/目标/")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canon(p: Project) -> list[str]:
    import tidy
    return [f.relative_to(p.root).as_posix() for f in tidy.canon_files(p)]


def is_direction(rel: str) -> bool:
    return rel.startswith(DIRECTION)


def _dir(p: Project) -> Path:
    return p.root / DIR


def listing(p: Project) -> list[dict]:
    out = []
    for f in _dir(p).glob("改-*.json") if _dir(p).is_dir() else []:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda x: -int(x["code"].split("-")[1]))


def get(p: Project, code: str) -> dict:
    x = next((s for s in listing(p) if s["code"] == code), None)
    if x is None:
        raise store.Refused(f"没有重写单 {code}")
    return x


def _save(p: Project, x: dict) -> None:
    f = _dir(p) / f"{x['code']}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(x, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def propose(conn, p: Project, rel: str, text: str, changes: list[dict], *, by: str) -> dict:
    """出一张重写单。changes：[{what: 改了什么, from: 合并 / 去掉的是哪几条（出处）, why: 为什么}]，至少一条。"""
    import claims
    rel = rel.strip().replace("\\", "/")
    if rel not in canon(p):
        raise store.Refused(f"「{rel}」不是正本（需求、戒律、目标、协议、使用说明、AGENTS.md、技能这些）")
    old = (p.root / rel).read_text(encoding="utf-8")
    text = (text or "").replace("\r\n", "\n")
    if not text.strip():
        raise store.Refused("改后全文是空的")
    if text.strip() == old.strip():
        raise store.Refused("改后跟现在一样")
    cs = [{"what": " ".join(str(c.get("what") or "").split()), "from": " ".join(str(c.get("from") or "").split()),
           "why": " ".join(str(c.get("why") or "").split())} for c in (changes or [])]
    cs = [c for c in cs if c["what"]]
    if not cs or any(not c["why"] for c in cs):
        raise store.Refused("每处改动写清改了什么、为什么（合并 / 去掉的写出处）")
    n = 1 + max([0] + [int(s["code"].split("-")[1]) for s in listing(p)])
    x = {"code": f"改-{n}", "target": rel, "direction": is_direction(rel), "base_sha": _sha(old), "text": text,
         "changes": cs, "by": by, "at": _now(), "state": "待定", "old_size": len(old.encode("utf-8")), "new_size": len(text.encode("utf-8"))}
    _save(p, x)
    asks = _asks(p)
    if asks.pop(rel, None) is not None:                     # 人要的那份出了单：这件活算交了
        _save_asks(p, asks)
    claims.release(conn, JOB, rel, note=f"出了 {x['code']}")
    store.log(conn, by, "出了重写单", x["code"], f"{rel} · {len(cs)} 处 · {x['old_size']} → {x['new_size']} 字节")
    return x


def diff(p: Project, code: str) -> dict:
    """对照：一行一行（-- 去掉的、++ 加的），还有前后多大。"""
    x = get(p, code)
    f = p.root / x["target"]
    cur = f.read_text(encoding="utf-8") if f.is_file() else ""
    lines = list(difflib.unified_diff(cur.splitlines(), x["text"].splitlines(), "现在", "改后", n=2, lineterm=""))
    return {"code": code, "target": x["target"], "stale": _sha(cur) != x["base_sha"], "lines": lines[2:][:4000],
            "old_size": len(cur.encode("utf-8")), "new_size": x["new_size"]}


def accept(conn, p: Project, code: str, *, by: str, reviewer: bool = False) -> dict:
    """换上：方向文件只有人能点；正本被改过了就拒；换前存档；旧版收进归档、标被取代。"""
    import archive
    import journal
    import snapshot
    x = get(p, code)
    if x["state"] != "待定":
        raise store.Refused(f"{code} 是「{x['state']}」")
    human = by == "人" or by.startswith("人")
    if x["direction"] and not human:
        raise store.Refused(f"{x['target']} 是方向文件（需求、戒律、目标），只有人能点换上")
    if not human and not by.endswith("claude-code") and not reviewer:
        raise store.Refused("重写单只有人、G1 和审它的员工能换上")
    f = p.root / x["target"]
    cur = f.read_text(encoding="utf-8")
    if _sha(cur) != x["base_sha"]:
        raise store.Refused(f"{x['target']} 在出单以后又被改过了：照现在的样子重出一张")
    m = snapshot.save(conn, p, name=f"重写前 {code}", why=f"{code} 换上 {x['target']} 之前", mode="全量", by=by, auto=True)
    month = datetime.now().strftime("%Y-%m")
    old_rel = f"{archive.DIR}/{month}/旧版/{x['target']}.{code}.md"
    (p.root / old_rel).parent.mkdir(parents=True, exist_ok=True)
    (p.root / old_rel).write_text(cur, encoding="utf-8")
    rows = archive.index(p)
    rows.append({"from": x["target"], "to": old_rel, "kind": "旧版", "title": f"{Path(x['target']).name}（{code} 以前）", "day": datetime.now().strftime("%Y-%m-%d"),
                 "month": month, "size": len(cur.encode("utf-8")), "why": f"被 {code} 取代", "at": _now(), "by": by, "checkpoint": m["code"],
                 "state": "旧版", "replaced_by": code})
    archive._save_index(p, rows)
    tmp = f.with_name(f.name + ".rewrite.tmp")
    tmp.write_text(x["text"], encoding="utf-8")
    os.replace(tmp, f)
    x.update(state="换上了", accepted_by=by, accepted_at=_now(), checkpoint=m["code"], old_version=old_rel)
    _save(p, x)
    journal.add(conn, p, f"{code} 换上了 {x['target']}（{x['old_size']} → {x['new_size']} 字节，{len(x['changes'])} 处）；换前存了 {m['code']}，旧版在 {old_rel}",
                kind="重写", by=by)
    return x


def drop(conn, p: Project, code: str, *, by: str, why: str) -> dict:
    x = get(p, code)
    if x["state"] != "待定":
        raise store.Refused(f"{code} 是「{x['state']}」")
    why = " ".join((why or "").split())
    if not why:
        raise store.Refused("写一句为什么不要")
    x.update(state="不要了", dropped_by=by, dropped_at=_now(), dropped_why=why)
    _save(p, x)
    store.log(conn, by, "不要重写单", code, why[:200])
    return x


def ask(conn, p: Project, rel: str, *, by: str, note: str = "") -> dict:
    """人点「让 agent 重写这份」：记一件「写重写单」的活（next_task 给规划的员工或 G1）。"""
    rel = rel.strip()
    if rel not in canon(p):
        raise store.Refused(f"「{rel}」不是正本")
    asks = _asks(p)
    asks[rel] = {"rel": rel, "by": by, "at": _now(), "note": " ".join((note or "").split())}
    _save_asks(p, asks)
    store.log(conn, by, "要重写", rel, note[:200])
    return asks[rel]


def _asks(p: Project) -> dict:
    try:
        return json.loads((_dir(p) / "要重写.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_asks(p: Project, d: dict) -> None:
    f = _dir(p) / "要重写.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def wanted(conn, p: Project) -> list[dict]:
    """该出重写单的：人点过「让 agent 重写」的；设置里开着「自动派」（默认开）时，查乱报的太长、有重复的正本。
    已经有待定单子的不算；七天内出过单（换上了 / 不要了）的也先不派，免得来回改。"""
    import knobs
    import tidy
    sheets = listing(p)
    open_targets = {x["target"] for x in sheets if x["state"] == "待定"}
    week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    recent = {x["target"] for x in sheets if x["at"] >= week}
    out = [a | {"why": "人要重写" + (f"：{a['note']}" if a.get("note") else "")} for a in _asks(p).values() if a["rel"] not in open_targets]
    if knobs.get(conn, "rewrite_auto"):
        skip = open_targets | recent | {a["rel"] for a in out}
        for x in tidy.too_long(conn, p):
            if x["file"] not in skip:
                out.append({"rel": x["file"], "why": f"太长（{x['size'] // 1024} KB）"})
                skip.add(x["file"])
        count: dict[str, int] = {}
        for d in tidy.duplicates(p):
            for k in ("a", "b"):
                count[d[k]["file"]] = count.get(d[k]["file"], 0) + 1
        for rel, n in sorted(count.items(), key=lambda kv: -kv[1]):
            if rel not in skip:
                out.append({"rel": rel, "why": f"跟别的正本有 {n} 段意思差不多"})
                skip.add(rel)
    return out


REVIEW = "审重写单"


def review_job(conn, p: Project, agent: str) -> dict | None:
    """给「审核」岗位的员工一张别人出的、非方向文件的待定重写单，替它领下（同一张只给一个人）。"""
    import agents
    import claims
    import knobs
    a = agents.find(p, agent)
    if not a or "审核" not in agents.jobs(a) or knobs.get(conn, "digest_by") == "G1":
        return None                                      # 设置成 G1 写（作者 10-03「先别搞员工了」「现阶段由你全权处理」）：单子 G1 自己换，不派员工审
    for x in sorted((s for s in listing(p) if s["state"] == "待定" and not s["direction"]), key=lambda s: s["code"]):
        if agents.short(x["by"]) == a["name"]:
            continue                                     # 不审自己出的
        try:
            claims.claim(conn, REVIEW, x["code"], agent, [f"{REVIEW} {x['code']}"], x["target"])
        except store.Refused:
            continue
        d = diff(p, x["code"])
        return {"code": x["code"], "target": x["target"], "changes": x["changes"], "by": x["by"], "stale": d["stale"],
                "diff": d["lines"][:1500], "old_size": d["old_size"], "new_size": d["new_size"],
                "how": "逐处核对：合并 / 去掉的出处是不是真的、有没有把现在还有效的规矩删掉、改后读起来对不对；"
                       "行就 review_rewrite(code, true, why) 换上，不行就 review_rewrite(code, false, why) 写清哪里不对"}
    return None


def review(conn, p: Project, code: str, ok: bool, why: str, *, by: str) -> dict:
    """审核员工审一张重写单：行就换上（换前存档、旧版进归档），不行就不要（写清为什么）。不审自己出的、不审方向文件。"""
    import agents
    import claims
    x = get(p, code)
    a = agents.find(p, by)
    if not a or "审核" not in agents.jobs(a):
        raise store.Refused("审重写单要有「审核」岗位")
    if agents.short(x["by"]) == a["name"]:
        raise store.Refused("不能审自己出的重写单")
    if x["direction"]:
        raise store.Refused(f"{x['target']} 是方向文件，只有人能换")
    why = " ".join((why or "").split())
    if not why:
        raise store.Refused("写一句审的理由")
    try:
        r = accept(conn, p, code, by=by, reviewer=True) if ok else drop(conn, p, code, by=by, why=why)
    finally:
        claims.release(conn, REVIEW, code, note="审过了")
    r["review"] = {"by": by, "ok": bool(ok), "why": why, "at": _now()}
    _save(p, r)
    return r


def job(conn, p: Project, agent: str) -> dict | None:
    """给「规划」岗位的员工（或 G1，看设置「摘要谁来写」）一件「写重写单」，替它领下。"""
    import agents
    import claims
    import knobs
    a = agents.find(p, agent)
    if not a:
        return None
    if knobs.get(conn, "digest_by") == "G1" and a["code"] != "G1":
        return None
    if knobs.get(conn, "digest_by") != "G1" and "规划" not in agents.jobs(a):
        return None
    import tidy
    for w in wanted(conn, p):
        try:
            claims.claim(conn, JOB, w["rel"], agent, [f"{JOB} {w['rel']}"], w["why"])
        except store.Refused:
            continue
        dups = [d for d in tidy.duplicates(p) if w["rel"] in (d["a"]["file"], d["b"]["file"])]
        return {"rel": w["rel"], "why": w["why"], "direction": is_direction(w["rel"]), "dups": dups[:20],
                "how": "读这份正本全文，出一张重写单（propose_rewrite）：合并重复、去掉过时的、把抄来的换成指向原处；只写现在有效的。"
                       "每处改动写 what（改了什么）、from（合并 / 去掉的是哪几条，写出处）、why（为什么）。不改别的文件，不自己换上"}
    return None
