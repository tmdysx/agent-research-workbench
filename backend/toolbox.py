"""工具页分四块：总览 · 开源项目 · 技术栈 · 外部工具和插件（工具 S2-1、S2-2）。

作者 10-01：「我觉得工具这个模块也要分几个小模块，一个是开源项目，一个是技术栈，一个是外部工具和插件」。
- 外部工具和插件这一块里三组：外部工具（工具库/ 的 T 卡）· 插件（插件/）· Agent 程序（这台电脑装了哪家 agent、最近哪家连上来过）
- Agent 程序：程序在不在（PATH、本机设置、常见位置）、会话记录在不在（本机设置 → 各家的环境变量 → 默认位置），
  最近一次来干活的是谁（库里 agent 的最后一条动静）；只读，不启动 agent（项-2 核心不启动 agent）
"""
from __future__ import annotations

import os
from pathlib import Path

from project import CODE_DIR, Project

CATALOG = CODE_DIR / "工具库" / "智能体.md"

# 名字 · 程序名 · 认人的关键字（agent 名字里带这个就算这家）
AGENT_PROGRAMS = (("Claude Code", "claude", ("claude",)), ("Codex", "codex", ("codex",)))


def agent_programs(conn, p: Project) -> list[dict]:
    """这台电脑上各家 agent：装没装、会话记录在哪、最近哪个连上来过。"""
    import agents
    import sessions
    import tools
    src = sessions.sources()
    seen = conn.execute("SELECT actor, MAX(at) FROM event WHERE actor LIKE 'agent:%' GROUP BY actor").fetchall()
    out = []
    for name, exe, keys in AGENT_PROGRAMS:
        path = tools.find_exe(exe)
        d = src.get(name)
        found = bool(d and d.is_dir())
        hits = sorted((at or "", a) for a, at in seen if any(k in a.lower() for k in keys))
        last = hits[-1] if hits else None
        out.append({"name": name, "exe": path or "", "sessions": str(d) if d else "", "sessions_found": found,
                    "installed": bool(path) or found, "last_at": last[0] if last else "",
                    "last_agent": agents.short(last[1]) if last else "",
                    "agents": sorted({agents.short(a) for _, a in hits})})
    return out


def catalog(p: Project | None = None, f: Path | None = None) -> list[dict]:
    """市面上的智能体（工具 S2-13；作者 10-01：「你把市面上所有中国和美国的智能体都加上」）：照 工具库/智能体.md 读，
    一组一张表；每个查一下这台电脑装没装（命令在不在、Windows 位置在不在），只看不跑。"""
    import tools
    f = f or CATALOG
    if not f.is_file():
        return []
    out, cur, head = [], None, []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            cur = {"group": line[3:].strip(), "items": []}
            out.append(cur)
            head = []
            continue
        if cur is None or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        if cells and cells[0] == "名字":
            head = cells
            continue
        if not head or not cells[0]:
            continue
        x = dict(zip(head, cells + [""] * (len(head) - len(cells))))
        cmd, win = x.get("命令", ""), x.get("Windows 位置", "")
        found = tools.find_exe(cmd) if cmd else None
        place = os.path.expandvars(win) if win else ""
        if not found and place and Path(place).exists():
            found = place
        cur["items"].append({"name": x.get("名字", ""), "vendor": x.get("哪家", ""), "kind": x.get("什么样", ""), "mcp": x.get("接本应用", ""),
                             "cmd": cmd, "win": win, "url": x.get("官网", ""), "installed": bool(found), "where": found or ""})
    return [g for g in out if g["items"]]


def mcp_config(p: Project) -> dict:
    """给别家 agent 的接入配置：本应用的 MCP（research-console），写完整路径，哪家照抄都能用。"""
    import sys
    return {"mcpServers": {"research-console": {"command": sys.executable,
                                                  "args": [str(CODE_DIR / "backend" / "mcp_server.py"), "--project", str(p.root)]}}}
