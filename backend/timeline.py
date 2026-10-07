"""存档是总入口（S1-8 S2-54）：一档 = 一个时间节点；这一档跟上一档之间发生了什么、一件事出生在哪一档做完在哪一档，都现算。

作者 10-03「改良存档模块，让存档和日志蓝图想法模块融合成一个有机整体」，选了「存档是总入口」。
- 一档的「中间发生了什么」：按时间（上一档存的时候, 这一档存的时候] 圈出——
  冒出的想法（想-n）· 交付（J，带哪件、过没过）· 日志（志-n）· 拍板（A-n，答的哪条 D-n）；
  需求（需-n）和蓝图里的件（S2）没有自己的时间，就拿两档里存的 治理/ 文件比：这一档有、上一档没有的，就是这中间定下 / 加进来的；
  改了哪些文件直接拿两档的清单比（snapshot.diff）
- 最新一档之后还没存的，算一个「现在」节点
- 反过来：一个时间落在哪一档（第一档存的时候 ≥ 它的那档）；一件事出生在哪一档（第一档的 治理/ 里出现这一行）、做完在哪一档（交付单上写的那档，或交付之后的第一档）
全是读，不写任何东西。
"""
from __future__ import annotations

import re
from datetime import datetime

import deliveries
import ideas
import journal
import snapshot
import store
from project import Project

NOW = "现在"
_NEED = re.compile(r"^\|\s*(需-\d+)\s*\|\s*([^|]*)\|")
_S2 = re.compile(r"^\|\s*(S2-\d+)\s*\|\s*([^|]*)\|")
GOV = ("治理/需求/", "治理/目标/", "治理/任务/")


def _t(s: str) -> str:
    """各处的时间统一成「YYYY-MM-DD HH:MM」好比大小（ISO 的 T 换成空格、去掉秒）。"""
    s = (s or "").replace("T", " ").strip()
    return s[:16]


def nodes(p: Project) -> list[dict]:
    """全部存档按时间从早到晚，每个带上一档的号和时间；最后加一个「现在」。"""
    saves = sorted(snapshot.list_saves(p), key=lambda m: (_t(m["at"]), int(m["code"][1:])))
    out, prev = [], None
    for m in saves:
        out.append({"code": m["code"], "name": m["name"], "at": _t(m["at"]), "by": m.get("by", ""), "grade": m.get("grade", ""),
                    "settled": bool(m.get("settled")), "prev": prev["code"] if prev else "", "since": prev["at"] if prev else ""})
        prev = out[-1]
    out.append({"code": NOW, "name": "还没存的", "at": datetime.now().strftime("%Y-%m-%d %H:%M"), "by": "", "grade": "",
                "settled": False, "prev": prev["code"] if prev else "", "since": prev["at"] if prev else ""})
    return out


def _within(at: str, since: str, until: str) -> bool:
    at = _t(at)
    return bool(at) and (not since or at > since) and at <= until


def _gov_rows(p: Project, code: str) -> tuple[dict, dict]:
    """某一档（或现在）的 治理/ 里有哪些需求、哪些件：({需-n@文件: 一句}, {S2-n@文件: 一句})。"""
    needs, items = {}, {}
    if code == NOW:
        files = {f.relative_to(p.root).as_posix(): f for d in GOV for f in (p.root / d).glob("*.md")}
        read = lambda rel: files[rel].read_text(encoding="utf-8", errors="replace")
        rels = list(files)
    else:
        folder = snapshot._folder(p, code)
        manifest = snapshot._files(folder)
        rels = [r for r in manifest if r.startswith(GOV) and r.endswith(".md")]

        def read(rel):
            got = snapshot._content(p, folder, rel, manifest[rel])
            return got.read_text(encoding="utf-8", errors="replace") if got else ""
    for rel in rels:
        name = rel.rsplit("/", 1)[-1][:-3]
        for line in read(rel).splitlines():
            m = _NEED.match(line)
            if m and rel.startswith("治理/需求/"):
                needs[f"{name} {m.group(1)}"] = m.group(2).strip()
                continue
            m = _S2.match(line)
            if m and not rel.startswith("治理/需求/"):
                goal = name.split(" ", 1)[0] if rel.startswith("治理/目标/") else name
                items[f"{goal} {m.group(1)}"] = m.group(2).strip()[:120]
    return needs, items


def node(conn, p: Project, code: str) -> dict:
    """这一档跟上一档之间发生了什么（code 是「现在」就是最新一档之后还没存的）。"""
    ns = nodes(p)
    n = next((x for x in ns if x["code"] == code), None)
    if n is None:
        raise store.Refused(f"没有 {code} 这一档")
    since, until = n["since"], n["at"]
    out = dict(n)
    out["ideas"] = [{"code": x["code"], "at": x["at"], "text": x["text"][:160], "state": x["state"]}
                    for x in ideas.list_all(p) if _within(x["at"], since, until)]
    out["deliveries"] = [{"code": d["code"], "goal": d["goal"], "sub": d["sub"], "what": d["what"][:120], "state": d["state"],
                          "by": d["by"], "at": d["at"]} for d in deliveries.list_all(p) if _within(d["at"], since, until)]
    out["logs"] = [{"id": e["id"], "at": e["at"], "kind": e["kind"], "by": e["by"], "text": e["body"][:160]}
                   for e in journal.read(p) if _within(e["at"], since, until)]
    out["decisions"] = [{"code": r["code"], "ref": r["ref"] or "", "at": _t(r["created_at"]), "text": (r["text"] or "")[:160]}
                        for r in conn.execute("SELECT code, ref, text, created_at FROM note WHERE kind = '决定' ORDER BY id")
                        if _within(r["created_at"], since, until)]
    try:                                                        # 需求、件：拿两档的 治理/ 比
        now_needs, now_items = _gov_rows(p, code)
        old_needs, old_items = _gov_rows(p, n["prev"]) if n["prev"] else ({}, {})
        out["needs"] = [{"key": k, "text": v} for k, v in now_needs.items() if k not in old_needs]
        out["items"] = [{"key": k, "text": v} for k, v in now_items.items() if k not in old_items]
    except (store.Refused, OSError, ValueError):
        out["needs"], out["items"] = [], []
    try:                                                        # 改了哪些文件
        if n["prev"]:
            d = snapshot.diff(p, n["prev"], "now" if code == NOW else code)
            out["files"] = {"added": d["added"][:200], "changed": [x["path"] for x in d["changed"]][:200],
                            "removed": [x["path"] for x in d["removed"]][:200],
                            "counts": [len(d["added"]), len(d["changed"]), len(d["removed"])]}
        else:
            out["files"] = {"added": [], "changed": [], "removed": [], "counts": [0, 0, 0]}
    except (store.Refused, OSError, ValueError):
        out["files"] = {"added": [], "changed": [], "removed": [], "counts": [0, 0, 0]}
    out["counts"] = {k: len(out[k]) for k in ("ideas", "needs", "items", "deliveries", "logs", "decisions")}
    return out


def summary(conn, p: Project) -> list[dict]:
    """世界树总览用：每个节点几条想法、需求、件、交付、日志、拍板（不带明细；需求和件要读文件，慢一点，只在这算一次）。"""
    out = []
    for n in nodes(p):
        try:
            x = node(conn, p, n["code"])
            out.append({k: x[k] for k in ("code", "name", "at", "by", "grade", "settled", "prev", "since", "counts")}
                       | {"files": x["files"]["counts"]})
        except store.Refused:
            continue
    return out


def where(p: Project, at: str) -> str:
    """一个时间落在哪一档：第一档存的时候 ≥ 它；都比它早就是「现在」（还没存）。"""
    at = _t(at)
    for n in nodes(p):
        if n["code"] != NOW and n["at"] >= at:
            return n["code"]
    return NOW


def life(conn, p: Project, *, goal: str = "", sub: str = "", idea: str = "", need: str = "") -> dict:
    """一件事出生在哪一档、做完在哪一档。件：goal + sub；想法：idea（想-n）；需求：need（「项目 需-3」这样）。"""
    born = done = ""
    if idea:
        x = next((i for i in ideas.list_all(p) if i["code"] == idea), None)
        if x:
            born = where(p, x["at"])
        return {"born": born, "done": ""}
    key = f"{goal} {sub}" if sub else need
    for n in nodes(p):
        try:
            needs, items = _gov_rows(p, n["code"])
        except (store.Refused, OSError, ValueError):
            continue
        if key in (items if sub else needs):
            born = n["code"]
            break
    if sub:
        js = [d for d in deliveries.list_all(p) if d["goal"] == goal and d["sub"] == sub
              and any(w in d["state"] for w in ("做完", "通过"))]
        if js:
            done = where(p, max(js, key=lambda d: d["n"])["at"])     # 交付单上的「存档」是动手前存的那档；做完落在交付之后的第一档
    return {"born": born, "done": done}
