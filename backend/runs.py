"""自动化：工作流（W）和它每次运行的日志。

- 工作流 = 做熟了、会反复用的一串步骤。卡片在应用根目录 `自动化/工作流/W<号> <名字>.md`，号不回收
- 每跑一次是一「次」：W1-3（W1 第 3 次）；里面一圈一圈往下记：W1-3.1、W1-3.2…
- 日志在 `自动化/日志/<工作流>/W1-3.md`，跟人的笔记分开（作者 2026-09-25：「自动化要有自己的专属自动化日志」）
- 这个工具不转圈、不调模型：转圈的是 agent（Claude Code 的 /loop），它每走一圈调一次 report_run，这里只记和给人看
- 照开工单转（workorders）：人在网页上把一张开工单「交给 agent」它才在跑；没有在跑的单，agent 报不了「在跑」。
  每一次记下是照哪张单跑的（日志开头写「开工单 K1」）
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import store
from project import CODE_DIR, Project
from skills import frontmatter

WORKFLOWS = CODE_DIR / "自动化" / "工作流"
LOGS = Path("自动化") / "日志"
STATUS = ("在跑", "停了等你", "跑完待验收", "失败停了")
LEVELS = {0: "手动：不自己转，你复制指令给 agent", 1: "半自动：自己转，但新写的计划、每件的验收都等你点头",
          2: "自动：计划和做都自己来，只在必停时停"}
_W = re.compile(r"W(\d+)")
_RUN = re.compile(r"(W\d+)-(\d+)")
_HEAD = re.compile(r"^## (W\d+-\d+\.(\d+)) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?)\s*$")
_WO = re.compile(r"开工单 (K\d+)")


# ---------------------------------------------------------------- 工作流卡片

def list_workflows(lib: Path | None = None, *, project: Project | None = None) -> list[dict]:
    # 旧调用可继续传库路径。回退只读取应用顶层 W，不借用作者的私有图。
    local = project.root / "自动化" / "工作流" if project else None
    lib = lib or (local if local and any(local.glob("*.md")) else WORKFLOWS)
    out = []
    if not lib.is_dir():
        return out
    for f in lib.glob("*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        code = fm.get("编号") or f.stem.split(" ")[0]
        m = _W.fullmatch(code)
        if not m:
            continue
        body = text[text.find("\n---", 3) + 4:].lstrip() if text.startswith("---") else text
        out.append({"code": code, "n": int(m.group(1)), "name": fm.get("名字", f.stem), "one_line": fm.get("一句话", ""),
                    "start": fm.get("启动", ""), "file": f.name, "folder": f.stem, "body": body})
    out.sort(key=lambda w: w["n"])
    for w in out:
        del w["n"]
    if project:
        import workflow_graph
        for card in workflow_graph.list_all(project)["items"]:
            out.append({"code": card["code"], "name": card["name"], "one_line": "项目可编辑流程",
                        "start": "按启用快照及既有自动化开关执行", "file": card["file"],
                        "folder": card["code"] + " " + card["name"], "body": card["text"],
                        "graph": card["graph"], "revision": card["revision"], "project": True, "active": card["active"]})
    return out


# ---------------------------------------------------------------- 设置：档位、每次最多几圈

def settings(conn) -> dict:
    level = int(store._meta(conn, "auto_level") or 1)
    import knobs
    rounds = int(knobs.get(conn, "rounds"))                # 设置里「每个员工一次最多几圈」（S1-8 S2-57），默认 12
    return {"level": level, "level_text": LEVELS[level], "rounds": rounds}


def set_settings(conn, level: int, rounds: int) -> dict:
    if level not in LEVELS:
        raise store.Refused("档位只有 0、1、2")
    if not 1 <= rounds <= 50:
        raise store.Refused("每次最多几圈：1 到 50")
    with store.tx(conn):
        store._set_meta(conn, "auto_level", str(level))
        store._set_meta(conn, "auto_rounds", str(rounds))
    return settings(conn)


# ---------------------------------------------------------------- 运行日志

def _parse(f: Path) -> list[dict]:
    return _read(f)[0]


def _read(f: Path) -> tuple[list[dict], str]:
    """一次运行的文件 → (每一圈, 照哪张开工单跑的)。"""
    rounds, cur, wo = [], None, ""
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if not rounds and line.startswith(">") and (w := _WO.search(line)):
            wo = w.group(1)
        m = _HEAD.match(line)
        if m:
            cur = {"code": m.group(1), "n": int(m.group(2)), "at": m.group(3), "status": m.group(4), "fields": {}}
            rounds.append(cur)
        elif cur is not None and line.startswith("- ") and "：" in line:
            k, v = line[2:].split("：", 1)
            cur["fields"][k] = v
    return rounds, wo


def list_runs(p: Project, limit: int = 30) -> list[dict]:
    """最近的运行，新的在前。每次：编号、哪条工作流、状态（最后一圈的）、走了几圈、每一圈。"""
    d = p.root / LOGS
    out = []
    if not d.is_dir():
        return out
    for f in d.rglob("W*-*.md"):
        m = _RUN.fullmatch(f.stem)
        rounds, wo = _read(f) if m else ([], "")
        if not rounds:
            continue
        last = rounds[-1]
        out.append({"code": f.stem, "workflow": m.group(1), "folder": f.parent.name, "status": last["status"],
                    "rounds": rounds, "started": rounds[0]["at"], "updated": last["at"],
                    "goal": last["fields"].get("在做", ""), "workorder": wo, "_t": f.stat().st_mtime})
    out.sort(key=lambda r: -r["_t"])
    for r in out:
        del r["_t"]
    return out[:limit]


def _one_line(s: str) -> str:
    return " / ".join(x.strip() for x in (s or "").strip().splitlines() if x.strip())


def report(conn, p: Project, workflow: str, *, by: str, run: str = "", goal: str = "", did: str = "",
           result: str = "", status: str = "在跑", next_step: str = "") -> dict:
    """agent 走完一圈报一次。run 空着 = 开始新的一次。返回这一圈的编号，如 W1-3.2。"""
    if status not in STATUS:
        raise store.Refused(f"状态只能是：{' / '.join(STATUS)}")
    import workorders                                      # 开工单要读 runs 的档位；这里用到再引，免得互相引
    wo = workorders.running(p)
    if status == "在跑" and wo is None:
        raise store.Refused("没有在跑的开工单：别转了。人要在网页「自动化」页把一张开工单的灯补绿、点「交给 agent」你才能转；"
                            "要报这一次停下，status 用「停了等你」")
    w = next((x for x in list_workflows(project=p) if x["code"] == workflow), None)
    if w is None:
        raise store.Refused(f"没有工作流 {workflow}（卡片在 自动化/工作流/）")
    folder = p.root / LOGS / w["folder"]
    with store.tx(conn):
        folder.mkdir(parents=True, exist_ok=True)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not run:
            nums = [int(m.group(2)) for f in folder.glob(f"{workflow}-*.md") if (m := _RUN.fullmatch(f.stem))]
            run = f"{workflow}-{max(nums, default=0) + 1}"
            head = (f"# {run} · {w['name']} · 第 {run.split('-')[1]} 次\n\n"
                    f"> 开始于 {now} · {by} · " + (f"开工单 {wo['code']} {wo['name']} · 档位 {wo['level']}" if wo else "没有在跑的开工单")
                    + f"。一圈一条，编号 {run}.1、{run}.2…\n")
        elif not _RUN.fullmatch(run) or not run.startswith(workflow + "-"):
            raise store.Refused(f"run 要写成 {workflow}-3 这样（{workflow} 的第几次）")
        else:
            head = ""
        f = folder / f"{run}.md"
        if not head and not f.exists():
            raise store.Refused(f"没有 {run} 这一次；开新的一次就把 run 空着")
        n = len(_parse(f)) + 1 if f.exists() else 1
        code = f"{run}.{n}"
        fields = [("在做", goal), ("做了", did), ("结果", result), ("下一步", next_step)]
        body = "".join(f"- {k}：{_one_line(v)}\n" for k, v in fields if _one_line(v))
        with open(f, "a", encoding="utf-8") as out:
            out.write(head + f"\n## {code} · {now} · {status}\n{body}")
        store.log(conn, by, "自动化", code, status)
    return {"code": code, "run": run, "round": n, "status": status}


def latest(p: Project, workorder: str = "") -> dict | None:
    """总览顶上那一行：最近一次运行（在跑、停了等你的优先）。workorder：只看照这张开工单跑的。"""
    runs = [r for r in list_runs(p, 30) if not workorder or r["workorder"] == workorder][:5]
    if not runs:
        return None
    live = next((r for r in runs if r["status"] in ("在跑", "停了等你")), runs[0])
    r = dict(live)
    r["round"] = len(r.pop("rounds"))
    return r
