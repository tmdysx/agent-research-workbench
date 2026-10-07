"""离固化还差什么（S1-6 S2-12；作者 10-02「固化通用核心什么时候固化好？」）：S1-6 S2-5 写的四条固化条件，各一盏灯，现算。

09-25 作者定过「什么时候固化作者说了算，大概第二篇论文用顺手以后」；10-02 把「用顺手」写成看得见的四条：
1. 通用层、交集层各块都有需求和任务、都定稿 —— 从「离全自动还差什么」那张表数
2. 给 agent 的接口（MCP 工具和它们的参数）、插件格式、各种卡片的格式连着两周没改 —— 算一个「指纹」，变了就从那天重新数
3. 分好岗位的 agent 跑完一篇真论文 —— 机器判断不了，作者点「跑完了」记下日期
4. 「改了核心」最近两周只有修小毛病 —— 列出最近两周改了几次核心，作者自己看；一次都没有就亮绿
都亮绿了也不自动固化：作者按（S1-6 S2-5）。
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from pathlib import Path

import store
from project import Project

HERE = Path(__file__).resolve().parent
QUIET_DAYS = 14
FORMAT_FILES = ("plugins.py", "repos.py", "tools.py", "deliveries.py", "workorders.py", "drafts.py")   # 卡片、插件、交付单、开工单、草稿的格式


def _keys(name: str) -> list[str]:
    """一种文件格式的格子：程序里读的那几个字段名（fm.get("名字") 这种）。"""
    try:
        text = (HERE / name).read_text(encoding="utf-8")
    except OSError:
        return []
    return sorted(set(re.findall(r'fm\.get\("([^"]+)"', text)))


def iface_sig() -> str:
    """接口和格式的指纹：MCP 工具名和参数 · agent 档案的格子 · 插件、开源项目卡、工具卡、交付单、开工单、草稿读的字段。只改说明文字不算。"""
    import agents
    mcp = (HERE / "mcp_server.py").read_text(encoding="utf-8")
    tools = [" ".join(t.split()) for t in re.findall(r"@mcp\.tool\(\)\s*\n\s*def (\w+\([^)]*\))", mcp)]
    parts = sorted(tools) + [w for _, w in agents.FIELDS] + [k for f in FORMAT_FILES for k in _keys(f)]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def status(conn, p: Project) -> dict:
    import dispatch
    import journal
    today = date.today()
    rows = dispatch.plan_status(p)
    fin = [r for r in rows if r["final"]]
    c1 = {"key": "final", "name": "通用层、交集层各块都有需求和任务、都定稿", "ok": bool(rows) and len(fin) == len(rows),
          "now": f"定稿 {len(fin)} / {len(rows)} 块", "more": "、".join(r["code"] for r in rows if not r["final"])[:200]}
    sig = iface_sig()
    with store.tx(conn):
        if store._meta(conn, "iface_sig") != sig:            # 接口或格式变了：从今天重新数
            store._set_meta(conn, "iface_sig", sig)
            store._set_meta(conn, "iface_since", today.isoformat())
        since = store._meta(conn, "iface_since") or today.isoformat()
    days = (today - date.fromisoformat(since)).days
    c2 = {"key": "iface", "name": f"给 agent 的接口、插件格式、各种卡片的格式连着 {QUIET_DAYS} 天没改", "ok": days >= QUIET_DAYS,
          "now": f"上次改在 {since}（{days} 天前）", "more": "只改说明文字不算；工具名、参数、卡片的格子变了才算"}
    paper = store._meta(conn, "paper_done") or ""
    c3 = {"key": "paper", "name": "分好岗位的 agent 跑完一篇真论文（第二篇）", "ok": bool(paper),
          "now": paper or "还没有：跑完了点「跑完了」", "more": "机器判断不了，你说了算", "button": True}
    cut = (today - timedelta(days=QUIET_DAYS)).isoformat()
    core = [e for e in journal.read(p) if e["kind"] == "改了核心" and e["at"][:10] >= cut]
    c4 = {"key": "core", "name": f"最近 {QUIET_DAYS} 天改核心只有修小毛病", "ok": not core,
          "now": f"最近 {QUIET_DAYS} 天改了 {len(core)} 次核心" if core else f"最近 {QUIET_DAYS} 天没改核心",
          "more": "；".join(f"{e['at'][5:16]} {' '.join(e['body'].split())[:40]}" for e in core[-3:])}
    items = [c1, c2, c3, c4]
    return {"items": items, "ready": all(c["ok"] for c in items), "green": sum(c["ok"] for c in items)}


def mark_paper(conn, done: bool, by: str = "人") -> str:
    """作者点「跑完了」（或取消）：记下日期。"""
    with store.tx(conn):
        v = f"{date.today().isoformat()} {by}点的" if done else ""
        store._set_meta(conn, "paper_done", v)
        store.log(conn, by, "固化条件", "跑完一篇真论文", "跑完了" if done else "取消")
    return v
