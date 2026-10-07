"""摘要和「项目现在的样子」（S1-8 S2-62；需-29）：最近几条留原文，更早的每月一段摘要，再往上一份总的；
另外一份 `自动化/现在的样子.md`，agent 开工先读它，不用翻全部日志。

作者 10-03：「要有冬藏压缩重铸的功能，相当于上下文压缩了」。界面上叫「摘要」。
- 程序管：什么时候该写（due）、给写的人备好材料（packet）、收稿写进去（write）；字是 agent 写的
- 三种稿：
  - 月摘要 `自动化/摘要/<年-月>.md`：那个月过完了、还没有（或那个月又多了记录）——那个月的日志、交付、交接、计划
  - 总摘要 `自动化/摘要/总的.md`：有月摘要比它新
  - 现在的样子 `自动化/现在的样子.md`：没有、或比设置的天数旧而且这之后有新交付 / 新日志——总摘要 + 最近几条原文 + 没做完的件 + 各人最新交接
- 谁写：设置里「摘要谁来写」——有「规划」岗位的员工（next_task 给它一件「写摘要」，同一份只给一个人）· G1；
  选了员工但没有能写的，也等 G1
- 稿头写：谁写的、什么时候、依据哪些（几条日志、哪几张交付单……）；写进去之前不改别的文件
做法是自己写的；参考过的项目见使用说明「参考过的项目」。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import store
from project import Project

DIR = "自动化/摘要"
NOW = "自动化/现在的样子.md"
TOTAL = "自动化/摘要/总的.md"
JOB = "写摘要"                                       # claims 里 goal=写摘要、sub=稿的名字
NOW_HEADS = ("## 要做成什么", "## 现在在做什么", "## 做到哪了", "## 定下来的做法")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _head(f: Path) -> dict:
    """稿头（第一段的 > 那几行）：写的人、时间、依据。"""
    out = {}
    try:
        for line in f.read_text(encoding="utf-8").splitlines()[:8]:
            m = re.match(r">\s*(谁写的|什么时候|依据)[：:]\s*(.*)", line)
            if m:
                out[m.group(1)] = m.group(2).strip()
    except OSError:
        pass
    return out


def _month_sources(p: Project, month: str) -> dict:
    import agents
    import deliveries
    import journal
    logs = [e for e in journal.read(p) if e["at"].startswith(month)]
    js = [j for j in deliveries.list_all(p) if j["at"].startswith(month)]
    hs = [h for h in agents.handovers(p) if h["date"].startswith(month)]
    return {"logs": logs, "deliveries": js, "handovers": hs}


def _sig(src: dict) -> str:
    return f"日志 {len(src['logs'])} 条 · 交付 {len(src['deliveries'])} 张 · 交接 {len(src['handovers'])} 张"


def due(conn, p: Project, now: datetime | None = None) -> list[dict]:
    """现在该写哪几份：[{kind, key, out, why}]。"""
    import journal
    import knobs
    now = now or datetime.now()
    this = now.strftime("%Y-%m")
    out = []
    months = sorted({e["at"][:7] for e in journal.read(p)})
    for m in months:
        if m >= this:
            continue
        f = p.root / DIR / f"{m}.md"
        src = _month_sources(p, m)
        if not f.is_file():
            out.append({"kind": "月摘要", "key": m, "out": f"{DIR}/{m}.md", "why": f"{m} 过完了，还没有摘要（{_sig(src)}）"})
        elif _head(f).get("依据") != _sig(src):
            out.append({"kind": "月摘要", "key": m, "out": f"{DIR}/{m}.md", "why": f"{m} 后来又多了记录（现在 {_sig(src)}）"})
    total = p.root / TOTAL
    month_files = sorted((p.root / DIR).glob("????-??.md")) if (p.root / DIR).is_dir() else []
    if month_files and (not total.is_file() or max(f.stat().st_mtime for f in month_files) > total.stat().st_mtime):
        out.append({"kind": "总摘要", "key": "总的", "out": TOTAL, "why": "有月摘要比总的新" if total.is_file() else "还没有总的"})
    nf = p.root / NOW
    days = knobs.get(conn, "now_days")
    if not nf.is_file():
        out.append({"kind": "现在的样子", "key": "现在的样子", "out": NOW, "why": "还没有"})
    else:
        at = _head(nf).get("什么时候", "")
        try:
            old = now - datetime.strptime(at, "%Y-%m-%d %H:%M") >= timedelta(days=days)
        except ValueError:
            old = True
        newer = [e for e in journal.read(p)[-300:] if e["at"] > at and e["kind"] not in ("写摘要", "查乱")]
        if old and newer:
            out.append({"kind": "现在的样子", "key": "现在的样子", "out": NOW, "why": f"{at} 写的，之后日志又多了 {len(newer)} 条"})
    return out


def packet(conn, p: Project, kind: str, key: str) -> dict:
    """给写的人备的材料（只读）：要写什么、照什么格式、依据哪些。字数有上限，太多的只给开头。"""
    import agents
    import blueprint
    import deliveries
    import journal
    import knobs
    keep = knobs.get(conn, "keep_recent")
    if kind == "月摘要":
        src = _month_sources(p, key)
        return {"kind": kind, "key": key, "out": f"{DIR}/{key}.md", "basis": _sig(src),
                "ask": f"把 {key} 这个月发生的事写成一页摘要：做成了什么（按目标分）、定下了什么、换了什么做法、打回过什么、还挂着什么。"
                       "每句后面写出处（志-n、J-n、H-n）；不编、不评价人；500～1500 字",
                "logs": [f"{e['id']} · {e['at']} · {e['by']} · {e['kind']}：{e['body'][:160]}" for e in src["logs"]][:600],
                "deliveries": [f"{j['code']} · {j['goal']} {j['sub']} · {j['state']} · {j['what'][:100]}" for j in src["deliveries"]],
                "handovers": [f"{h['code']} · {h['date']} · {h['who']}" for h in src["handovers"]]}
    if kind == "总摘要":
        months = sorted((p.root / DIR).glob("????-??.md"))
        return {"kind": kind, "key": key, "out": TOTAL, "basis": "月摘要 " + "、".join(f.stem for f in months),
                "ask": "把下面几份月摘要合成一份总的：这个项目从开始到现在做成了什么、定下的做法、走过的弯路；每句写出处（哪个月的摘要）；800～2000 字",
                "months": {f.stem: f.read_text(encoding="utf-8")[:12000] for f in months}}
    # 现在的样子
    bp = blueprint.pyramid(p)
    open_items = [f"{g['code']} {x['code']} · {x['text'][:20]} · {x['what'][:90]}" for g in bp["goals"] for x in g["subs"] if x["status"] != "ok"]
    latest = {}
    for h in agents.handovers(p):
        latest.setdefault(h["who"], h)
    recent = journal.read(p)[-keep:]
    total = p.root / TOTAL
    pend = [f"{j['code']} · {j['goal']} {j['sub']} · {j['state']}" for j in deliveries.list_all(p) if j["state"] in ("待你验收", "等验收")]
    return {"kind": "现在的样子", "key": key, "out": NOW, "basis": f"总摘要 + 最近 {len(recent)} 条日志 + 没做完的 {len(open_items)} 件 + 交接 {len(latest)} 份",
            "ask": "写一份「项目现在的样子」，新来的 agent 先读它就能接着干。四节，标题照写："
                   + "、".join(NOW_HEADS) + "。要做成什么：一两句（照 S0 和目标）；现在在做什么：谁在做哪几件；做到哪了：做完的大块、挂着的、卡着的；"
                   "定下来的做法：现在照什么规矩、什么流程干活（只写现在有效的）。每句写出处；不超过 2500 字",
            "total": total.read_text(encoding="utf-8")[:12000] if total.is_file() else "",
            "recent": [f"{e['id']} · {e['at']} · {e['by']} · {e['kind']}：{e['body'][:200]}" for e in recent],
            "open_items": open_items[:120], "pending": pend[:40],
            "handovers": [f"{h['code']} · {h['date']} · {h['who']} · {h.get('path', '')}" for h in latest.values()]}


def write(conn, p: Project, kind: str, key: str, text: str, *, by: str) -> dict:
    """收稿：检查格式、写进去（加稿头）、记日志、放掉「写摘要」的认领。"""
    import claims
    import journal
    text = (text or "").strip()
    if len(text) < 80:
        raise store.Refused("摘要太短了：照材料里的要求写")
    if kind == "现在的样子":
        miss = [h for h in NOW_HEADS if h not in text]
        if miss:
            raise store.Refused("现在的样子要有这几节标题：" + "、".join(miss))
        out, basis = NOW, packet(conn, p, kind, key)["basis"]
    elif kind == "月摘要":
        if not re.fullmatch(r"\d{4}-\d{2}", key):
            raise store.Refused("月摘要的 key 写年-月，比如 2026-09")
        out, basis = f"{DIR}/{key}.md", _sig(_month_sources(p, key))
    elif kind == "总摘要":
        out, basis = TOTAL, packet(conn, p, kind, key)["basis"]
    else:
        raise store.Refused("摘要只有三种：月摘要 · 总摘要 · 现在的样子")
    title = {"现在的样子": "# 项目现在的样子", "总摘要": "# 总摘要", "月摘要": f"# {key} 摘要"}[kind]
    body = re.sub(r"^#\s+[^\n]*\n", "", text, count=1) if text.startswith("# ") else text
    full = f"{title}\n\n> 谁写的：{by}\n> 什么时候：{_now()}\n> 依据：{basis}\n\n{body.strip()}\n"
    f = p.root / out
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(full, encoding="utf-8")
    os.replace(tmp, f)
    claims.release(conn, JOB, key, note=f"{kind} 写好了")
    journal.add(conn, p, f"写了{kind}「{key}」：{out}（依据 {basis}）", kind="写摘要", by=by)
    return {"kind": kind, "key": key, "out": out, "basis": basis, "size": len(full.encode("utf-8"))}


def job(conn, p: Project, agent: str) -> dict | None:
    """给「规划」岗位的员工（或 G1）一份该写的摘要，替它领下（同一份只给一个人）。"""
    import agents
    import claims
    import knobs
    a = agents.find(p, agent)
    if not a:
        return None
    by_g1 = knobs.get(conn, "digest_by") == "G1"
    is_g1 = a["code"] == "G1"
    if by_g1 and not is_g1:
        return None
    if not by_g1 and "规划" not in agents.jobs(a):
        return None
    for d in due(conn, p):
        try:
            claims.claim(conn, JOB, d["key"], agent, [f"{JOB} {d['key']}"], d["kind"])
        except store.Refused:
            continue
        return d | {"packet": packet(conn, p, d["kind"], d["key"])}
    return None


def listing(p: Project) -> list[dict]:
    """有哪些摘要：现在的样子、总的、每个月。"""
    out, rels = [], [NOW, TOTAL]
    if (p.root / DIR).is_dir():
        rels += sorted((f"{DIR}/{x.name}" for x in (p.root / DIR).glob("????-??.md")), reverse=True)
    for rel in rels:
        f = p.root / rel
        if f.is_file():
            h = _head(f)
            out.append({"path": rel, "title": f.stem, "by": h.get("谁写的", ""), "at": h.get("什么时候", ""), "basis": h.get("依据", ""), "size": f.stat().st_size})
    return out


def now_text(p: Project, limit: int = 6000) -> tuple[str, dict]:
    """「现在的样子」全文（给 get_overview 放最前面）。"""
    f = p.root / NOW
    if not f.is_file():
        return "", {}
    t = f.read_text(encoding="utf-8")
    return (t[:limit] + ("\n……（太长，后面没放，读全文：自动化/现在的样子.md）" if len(t) > limit else "")), _head(f)
