"""查乱（S1-8 S2-61；需-29）：项目里哪些重复、哪些过时（能归档）、哪些没人用、哪些太长、计划有没有重号。只读，现算。

作者 10-03：「ai编程很多信息是重复杂乱的，随着业务和功能的发展会越来越乱」。界面上叫「查乱」。
- 重复：正本（需求、戒律、目标、协议、使用说明、AGENTS.md、CLAUDE.md、DESIGN.md、README、技能）里意思差不多的段落，成对列出。
  做法是很老的公开办法：把一段字切成一小片一小片（连着的三个字一片），两段共有的片越多越像（Jaccard 相似度）；
  先用「哪些段落有这一片」的倒排表挑出有可能像的对子，再算，不用两两全比。作者的原话（「」里的）不算——
  原话照规矩到处引用，是故意的
- 过时：现在能收进归档的（archive.candidates）
- 没人用：代码地图算的，别的文件都没用到、不是入口、不是测试的程序文件（给人判断，不自动动）
- 太长：正本超过设置里的长度
- 重号：同一个目标下两份计划同一个 P 号
人的笔记不看（笔记/ 下只有机器日志算记录，也不比重复）。做法是自己写的；参考过的项目见使用说明「参考过的项目」。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import store
from project import Project

SAVED = "自动化/清理/查乱.json"
_QUOTE = re.compile(r"「[^」]*」")
_MARK = re.compile(r"[\s|*#>`_\-\[\]()（）:：,，.。;；、!！?？\"'“”‘’/\\=+~^<>]+")


def canon_files(p: Project) -> list[Path]:
    """正本：规矩、需求、目标、说明、技能这些反复要读的。"""
    r = p.root
    out = [r / n for n in ("AGENTS.md", "CLAUDE.md", "DESIGN.md", "README.md", "使用说明.md") if (r / n).is_file()]
    out += [r / "自动化" / "协议.md"] if (r / "自动化" / "协议.md").is_file() else []
    for d in ("治理/需求", "治理/戒律", "治理/目标"):
        if (r / d).is_dir():
            out += sorted((r / d).rglob("*.md"))
    if (r / "技能库").is_dir():
        out += sorted((r / "技能库").glob("*/SKILL.md"))
    return [f for f in out if "内置" not in f.relative_to(r).parts]


def paragraphs(text: str) -> list[tuple[int, str]]:
    """切段：空行隔开的一段；列表的一项、表格的一行各算一段；标题不算。→ [(第几行, 原文)]"""
    out, buf, start = [], [], 0

    def flush():
        if buf:
            out.append((start, " ".join(buf).strip()))
        buf.clear()
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or set(s) <= set("|-: "):
            flush()
            continue
        if s.startswith(("|", "- ", "* ")) or re.match(r"\d+\.\s", s):
            flush()
            out.append((i, s))
            continue
        if not buf:
            start = i
        buf.append(s)
    flush()
    return out


def _norm(s: str) -> str:
    return _MARK.sub("", _QUOTE.sub("", s)).lower()


def _shingles(s: str, k: int = 3) -> set[str]:
    return {s[i:i + k] for i in range(max(len(s) - k + 1, 0))}


def duplicates(p: Project, *, threshold: float = 0.6, min_len: int = 40, limit: int = 60) -> list[dict]:
    """意思差不多的段落，成对：[{a: {file, line, text}, b: {…}, same: 0.83}]，最像的在前。"""
    paras = []
    for f in canon_files(p):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(p.root).as_posix()
        for line, raw in paragraphs(text):
            n = _norm(raw)
            if len(n) >= min_len:
                paras.append({"file": rel, "line": line, "text": raw, "sh": _shingles(n)})
    df: dict[str, list[int]] = {}
    for i, x in enumerate(paras):
        for s in x["sh"]:
            df.setdefault(s, []).append(i)
    common = max(30, len(paras) // 20)                     # 太常见的片（几乎哪段都有）不拿来挑对子
    hits: dict[tuple[int, int], int] = {}
    for ids in df.values():
        if len(ids) > common:
            continue
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                hits[(ids[a], ids[b])] = hits.get((ids[a], ids[b]), 0) + 1
    out = []
    for (a, b), shared in hits.items():
        x, y = paras[a], paras[b]
        small = min(len(x["sh"]), len(y["sh"]))
        if shared < small * threshold * 0.8:              # 共有的片太少：不可能到门槛
            continue
        same = len(x["sh"] & y["sh"]) / len(x["sh"] | y["sh"])
        if same >= threshold:
            out.append({"a": {k: x[k] for k in ("file", "line", "text")}, "b": {k: y[k] for k in ("file", "line", "text")},
                        "same": round(same, 2)})
    out.sort(key=lambda d: -d["same"])
    for d in out:
        for k in ("a", "b"):
            d[k]["text"] = d[k]["text"][:240]
    return out[:limit]


def too_long(conn, p: Project) -> list[dict]:
    import knobs
    cap = knobs.get(conn, "long_kb") * 1024
    out = []
    for f in canon_files(p):
        n = f.stat().st_size
        if n > cap:
            out.append({"file": f.relative_to(p.root).as_posix(), "size": n})
    return sorted(out, key=lambda x: -x["size"])


def unused_code(p: Project) -> list[dict]:
    """别的文件都没用到、不是入口、不是测试的程序文件（代码地图那套算法）。"""
    import codemap
    try:
        rows = codemap.listing(p, "源代码")["files"]
    except Exception:
        return []
    return [{"file": r["rel"], "lines": r["lines"], "at": r.get("at") or datetime.fromtimestamp(r["mtime"]).strftime("%Y-%m-%d")}
            for r in rows if r["lang"] in ("py", "js") and not r.get("fan_in") and not r.get("entry") and not r.get("is_test")]


def plan_numbers(p: Project) -> list[dict]:
    """同一个目标下两份计划同一个 P 号。"""
    import governance_paths as gp
    seen: dict[tuple[str, str], list[str]] = {}
    for rel, f in gp.plan_files(p).items():
        m = re.match(r"(P\d+)\b", f.name)
        if m:
            seen.setdefault((str(Path(rel).parent), m.group(1)), []).append(f.relative_to(p.root).as_posix())
    return [{"goal": g, "code": c, "files": fs} for (g, c), fs in sorted(seen.items()) if len(fs) > 1]


def report(conn, p: Project, *, save: bool = True) -> dict:
    """查一遍乱。save：存进 自动化/清理/查乱.json（网页、agent 下回直接读）。"""
    import archive
    import time
    t0 = time.time()
    cands = archive.candidates(conn, p)
    kinds: dict = {}
    for c in cands:
        k = kinds.setdefault(c["kind"], {"count": 0, "size": 0})
        k["count"] += 1
        k["size"] += c["size"]
    d = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "dup": duplicates(p), "stale": cands, "stale_kinds": kinds,
         "unused": unused_code(p), "long": too_long(conn, p), "numbers": plan_numbers(p), "archive": archive.summary(p)}
    d["counts"] = {"dup": len(d["dup"]), "stale": len(cands), "unused": len(d["unused"]), "long": len(d["long"]), "numbers": len(d["numbers"])}
    d["took"] = round(time.time() - t0, 2)
    if save:
        f = p.root / SAVED
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, f)
    return d


def last(p: Project) -> dict | None:
    try:
        return json.loads((p.root / SAVED).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def timed(conn, p: Project, now: datetime | None = None) -> dict | None:
    """设置里「多久查一次乱」到点了：查一遍、记一条日志；开了「自动归档」就顺手收。后台每分钟问一次。"""
    import knobs
    every = knobs.get(conn, "tidy_every_days")
    if not every:
        return None
    now = now or datetime.now()
    prev = last(p)
    if prev:
        try:
            if (now - datetime.strptime(prev["at"], "%Y-%m-%d %H:%M")).total_seconds() < every * 86400:
                return None
        except (KeyError, ValueError):
            pass
    d = report(conn, p)
    import journal
    c = d["counts"]
    journal.add(conn, p, f"查乱：重复 {c['dup']} 对 · 能归档 {c['stale']} 份 · 没人用的程序 {c['unused']} 个 · 太长的正本 {c['long']} 份"
                + (f" · 计划重号 {c['numbers']} 处" if c["numbers"] else ""), kind="查乱", by="程序")
    if knobs.get(conn, "archive_auto") and d["stale"]:
        import archive
        archive.put_away(conn, p, None, by="程序")
    return d
