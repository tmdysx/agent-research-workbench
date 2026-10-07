"""日志：机器记的——你在网页上点的操作（装技能、存档、删模块、启用插件、拍板、验收……）和 agent 做的事（改了核心、新建模块……）。

作者 2026-09-29：「笔记分两个模块，一个是机器的日志，一个是人的笔记」；
又说：「日志和笔记放笔记模块就行，放两个文件夹不就好了？」——所以日志不单独成页，是笔记本里的另一个文件夹：
- 人自己写的（随堂笔记里记下的字、截图、录屏，还有删除请求）照旧在 `笔记/`；机器记的一律进 `笔记/日志/`，不跟人写的混
- 一个月一个文件：`笔记/日志/2026-09.md`；每条编号 志-0001（全项目一个序列，号不回收），
  带时间、谁（人 = 你在网页上点的；agent:xxx = agent 做的）、什么事、跟哪个模块有关
- 只增：网页上不给改、不给删（是发生过的事，跟存档的凭据一样）
- agent 一圈圈转的流水账在 自动化/日志/，问题在问答页；这里是一条条操作
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

import notebook
import store
from project import Project

DIR = "日志"
MAIN = notebook.MAIN
HUMAN = {"笔记", "截图", "录屏", "删除请求"}      # 人自己写的这几种留在笔记；别的都是机器记的
_HEAD = re.compile(r"^## (志-(\d+)) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?) · (.+?) · (.+?)\s*$")
_SEQ = "log_seq"


def log_dir(p: Project) -> Path:
    return notebook.note_dir(p) / DIR


def parse(text: str) -> list[dict]:
    out, cur = [], None
    for line in text.splitlines():
        m = _HEAD.match(line)
        if m:
            cur = {"id": m.group(1), "n": int(m.group(2)), "at": m.group(3), "by": m.group(4), "kind": m.group(5),
                   "scope": m.group(6), "body": []}
            out.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    for e in out:
        e["body"] = "\n".join(e["body"]).strip()
    return out


def _files(p: Project) -> list[Path]:
    d = log_dir(p)
    return sorted(d.glob("????-??.md")) if d.is_dir() else []


def _all_files(p: Project) -> list[Path]:
    """连归档里的一起（S1-8 S2-61：旧月份整份收进 归档/年-月/笔记/日志/，读的时候照样算）。同一个月两处都有时都读。"""
    import archive
    got = _files(p) + [f for f in archive.archived_files(p, "笔记/日志", "????-??.md")]
    return sorted(got, key=lambda f: (f.stem, str(f)))


def months(p: Project) -> list[dict]:
    """一个月一个文件，新的在上（收进归档的那几个月也列，标 archived）。"""
    out = []
    live = set(_files(p))
    for f in reversed(_all_files(p)):
        es = parse(f.read_text(encoding="utf-8"))
        out.append({"month": f.stem, "count": len(es), "latest": max((e["at"] for e in es), default=None), "archived": f not in live})
    return out


def read(p: Project, month: str | None = None) -> list[dict]:
    """某个月（不给就全部）的条目，按时间排、新的在后。归档里的也算。"""
    out = []
    for f in _all_files(p):
        if month is None or f.stem == month:
            out += parse(f.read_text(encoding="utf-8"))
    return sorted(out, key=lambda e: (e["at"], e["n"]))


def _head(month: str) -> str:
    return (f"# 日志 · {month}\n\n> 机器记的：网页上点的操作、agent 做的事。只增不改。"
            f"人自己写的在上一层 笔记/。\n")


def _entry(e: dict) -> str:
    return f"\n## {e['id']} · {e['at']} · {e['by']} · {e['kind']} · {e['scope']}\n{e['body']}\n"


def _next(conn, p: Project) -> int:
    """号只增不减：库里记着用到哪了；库丢了也从文件里找最大的接着来。"""
    n = int(store._meta(conn, _SEQ) or 0)
    fs = _files(p)
    if fs:
        n = max([n] + [e["n"] for e in parse(fs[-1].read_text(encoding="utf-8"))])
    store._set_meta(conn, _SEQ, str(n + 1))
    return n + 1


def _append(p: Project, month: str, text: str) -> None:
    f = log_dir(p) / f"{month}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as w:
        if f.stat().st_size == 0:
            w.write(_head(month))
        w.write(text)


def add(conn, p: Project, text: str, *, kind: str, by: str = "人", scope: str = MAIN) -> dict:
    """记一条。正文里「## 」开头的行降一级，免得被当成新的一条。"""
    body = notebook._clean(text)
    if not body:
        raise store.Refused("日志是空的")
    kind = (kind or "操作").replace(" · ", " ")[:20]
    with store.tx(conn):                              # 拿库的写锁：两个进程同时记也不会乱号
        n = _next(conn, p)
        now = datetime.now()
        e = {"id": f"志-{n:04d}", "n": n, "at": now.strftime("%Y-%m-%d %H:%M"), "by": by, "kind": kind,
             "scope": scope or MAIN, "body": body}
        _append(p, now.strftime("%Y-%m"), _entry(e))
        store.log(conn, by, kind, e["id"], body[:120])
    return e


def recent(p: Project, limit: int = 30) -> list[dict]:
    return read(p)[-limit:]


# ---------------------------------------------------------------- 分开以前记在笔记里的：搬过来（原文件先留底）

def split_from_notes(conn, p: Project, modules: list[str]) -> int:
    """笔记里机器记的条目搬进日志：只留人写的（HUMAN 那几种、记成「人」的）。
    每个要改的笔记文件先整份留底进 笔记/历史/；改动记录.md 记一行。没有要搬的就什么都不做。返回搬了几条。"""
    moved: list[tuple[str, dict]] = []
    keep: dict[str, list[dict]] = {}
    for s in notebook.scopes(p, modules):
        es = notebook.read(p, s["scope"])
        out = [e for e in es if not (e["by"] == "人" and e["kind"] in HUMAN)]
        if out:
            moved += [(s["scope"], e) for e in out]
            keep[s["scope"]] = [e for e in es if e not in out]
    if not moved:
        return 0
    stamp = datetime.now().strftime("%Y-%m-%d %H%M")
    with store.tx(conn):
        first = None
        for scope, e in sorted(moved, key=lambda x: (x[1]["at"], x[0], notebook._num(x[1]["id"]))):
            n = _next(conn, p)
            first = first or n
            body = (e["body"] + "\n\n" if e["body"] else "") + f"（原先记在笔记 {e['id']}）"
            _append(p, e["at"][:7], _entry({"id": f"志-{n:04d}", "at": e["at"], "by": e["by"], "kind": e["kind"],
                                            "scope": scope, "body": body}))
        for scope, es in keep.items():
            f = notebook._file(p, scope)
            bak = notebook._history(p, f"分出日志前 · {scope} · {stamp}.md")
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, bak)
            notebook._write(f, notebook._render(scope, es))
        notebook._append_change(p, f"\n## {datetime.now():%Y-%m-%d %H:%M} · 机器 · 笔记和日志分开\n"
                                   f"笔记里机器记的 {len(moved)} 条搬进 笔记/日志/（志-{first:04d} 起，每条写着原来的编号）；"
                                   f"只留人写的。改之前的笔记整份留底：笔记/历史/分出日志前 · …{stamp}.md\n")
        store.log(conn, "机器", "笔记和日志分开", f"{len(moved)} 条", ", ".join(keep))
    return len(moved)
