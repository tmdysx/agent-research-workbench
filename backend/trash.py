"""回收站：项目根 `回收站/`，跟 笔记/ 计划/ 自动化/ 存档/ 并排，不在 资料/ 里、不算模块。

作者 2026-09-25：「独立建一个文件夹当缓存空间来装清理的垃圾文件」「进入文件夹的垃圾也要有编码和目录，
这样存档之后恢复的时候好恢复，存档定性了之后，删除的时候也好删除」。
- 一件（或一批）一个编号 X1、X2…（号不回收），放在 `回收站/<年-月-日 时分> X<号>/<原来的相对路径>`，原样放
- 目录 `回收站/清单.md`：每件写清原来在哪、从哪来（设置里删模块 / 复活 C3 换下来的 / agent 照删除请求挪的……）、为什么
- 谁往里挪：网页（删模块、复活时换下来的、删存档）和 agent（照人的删除请求），都记名字
- 还原：原样挪回去；原位置已经有东西，先问人，人点了确认才把现有的也挪进回收站再还原
- **彻底删掉**是第二个动作：只由人在清理页点、只删「定性过的存档」以前进来的、再确认一次
"""
from __future__ import annotations

import atomic
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import notebook
import store
from project import Project

DIR = "回收站"
LIST = "清单.md"
_HEAD = re.compile(r"^## (X\d+) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?) · (.+?)\s*$")
_NO = {".git", "索引", DIR}                          # 这些顶层文件夹里的东西不许挪
IN, BACK, GONE = "在回收站", "已还原", "已彻底删掉"


def _list_file(p: Project) -> Path:
    return p.root / DIR / LIST


def read(p: Project) -> list[dict]:
    """清单里的每一件，新的在前。status：在回收站 / 已还原 / 已彻底删掉。"""
    f = _list_file(p)
    out, cur = [], None
    if not f.is_file():
        return out
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _HEAD.match(line)
        if m:
            cur = {"code": m.group(1), "at": m.group(2), "by": m.group(3), "status": m.group(4), "fields": {}}
            out.append(cur)
        elif cur is not None and line.startswith("- ") and "：" in line:
            k, v = line[2:].split("：", 1)
            cur["fields"][k] = v
    out.sort(key=lambda e: int(e["code"][1:]), reverse=True)
    return out


def _target(p: Project, path: str) -> tuple[Path, str]:
    root = p.root.resolve()
    src = (root / (path or "").replace("\\", "/")).resolve()
    if not src.is_relative_to(root) or src == root:
        raise store.Refused("路径要在项目里面（从项目根算），而且不能是项目根本身")
    rel = src.relative_to(root)
    if rel.parts[0] in _NO or rel.parts[:2] == ("笔记", "历史"):
        raise store.Refused(f"「{rel.as_posix()}」不许挪：版本库、工具自己的库、回收站本身、笔记历史都不动")
    if not src.exists():
        raise store.Refused(f"找不到「{rel.as_posix()}」")
    return src, rel.as_posix()


def _one_line(s: str) -> str:
    return " / ".join(x.strip() for x in (s or "").strip().splitlines() if x.strip())


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _next_code(conn, p: Project) -> str:
    n = int(store._meta(conn, "trash_seq") or 0)
    n = max([n] + [int(e["code"][1:]) for e in read(p)])
    store._set_meta(conn, "trash_seq", str(n + 1))
    return f"X{n + 1}"


def _append(p: Project, code: str, now: datetime, by: str, fields: list[tuple[str, str]]) -> None:
    f = _list_file(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    head = "" if f.exists() else ("# 回收站 · 清单\n\n> 一件（或一批）一条，编号 X1、X2…。按原来的路径原样放着，还原就照着挪回去。"
                                  "\n> 彻底删掉是第二个动作：只由人在清理页点，只删定性过的存档以前进来的。\n")
    body = "".join(f"- {k}：{_one_line(v)}\n" for k, v in fields if _one_line(v))
    with open(f, "a", encoding="utf-8") as w:
        w.write(head + f"\n## {code} · {now:%Y-%m-%d %H:%M} · {by} · {IN}\n{body}")


def _set_status(p: Project, code: str, status: str, note: str) -> None:
    """改清单里某一件的状态，末尾补一行；先写临时文件再换，写到一半断电清单也不坏。"""
    f = _list_file(p)
    lines = f.read_text(encoding="utf-8").split("\n")
    i = next(k for k, l in enumerate(lines) if (m := _HEAD.match(l)) and m.group(1) == code)
    m = _HEAD.match(lines[i])
    lines[i] = f"## {code} · {m.group(2)} · {m.group(3)} · {status}"
    j = i + 1
    while j < len(lines) and lines[j].startswith("- "):
        j += 1
    lines.insert(j, note)
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    atomic.replace(tmp, f)


def move(conn, p: Project, path: str, *, by: str, reason: str, request: str = "", origin: str = "") -> dict:
    """把一个文件或文件夹挪进回收站，清单记一条。返回编号。"""
    return move_many(conn, p, [path], by=by, reason=reason, request=request, origin=origin)


def move_many(conn, p: Project, paths: list[str], *, by: str, reason: str, request: str = "", origin: str = "") -> dict:
    """一批东西挪进回收站，算一件（一个编号）：复活时换下来的、删一个模块，都是一批。"""
    if not _one_line(reason):
        raise store.Refused("要写为什么挪进回收站")
    items = [_target(p, x) for x in paths]
    if not items:
        raise store.Refused("没有要挪的东西")
    with store.tx(conn):
        code = _next_code(conn, p)
        now = datetime.now()
        box = f"{now:%Y-%m-%d %H%M} {code}"
        size = 0
        for src, rel in items:
            size += _size(src)
            dest = p.root / DIR / box / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
        rels = [rel for _, rel in items]
        where = rels[0] if len(rels) == 1 else f"{rels[0]} 等 {len(rels)} 个（按原路径放在那个文件夹里）"
        placed = f"{DIR}/{box}/{rels[0]}" if len(rels) == 1 else f"{DIR}/{box}"
        _append(p, code, now, by, [("原来在", where), ("放在", placed), ("从哪来", origin), ("为什么", reason),
                                   ("删除请求", request), ("大小", f"{size} 字节")])
        store.log(conn, by, "挪进回收站", code, where)
    return {"code": code, "from": rels, "to": placed}


def _box(p: Project, e: dict) -> Path:
    return p.root / DIR / e["fields"]["放在"].split("/")[1]


def _entries(box: Path) -> list[Path]:
    """盒子里要放回去的东西：文件，和空文件夹（删掉的空模块）。"""
    out = []
    for x in box.rglob("*"):
        if x.is_file() or (x.is_dir() and not any(x.iterdir())):
            out.append(x)
    return out


def restore(conn, p: Project, code: str, *, by: str, swap: bool = False) -> dict:
    """原样挪回去。原位置已经有东西：不带 swap 就报出来让人定；带 swap（人确认过）就把现有的也挪进回收站再还原。"""
    e = next((x for x in read(p) if x["code"] == code), None)
    if e is None:
        raise store.Refused(f"回收站清单里没有 {code}")
    if e["status"] != IN:
        raise store.Refused(f"{code} 已经{e['status']}了")
    box = _box(p, e)
    if not box.exists():
        raise store.Refused(f"回收站里找不到 {e['fields']['放在']}")
    moves = [(x, p.root / x.relative_to(box)) for x in _entries(box)]
    taken = [d.relative_to(p.root).as_posix() for s, d in moves if d.exists() and not (s.is_dir() and d.is_dir())]
    if taken and not swap:
        raise store.NeedConfirm(f"原来的位置已经有 {len(taken)} 个同名的了（比如 {taken[0]}）。"
                                f"还原的话，它们会先挪进回收站（另一个编号，能再换回来）。确定吗？",
                                {"taken": taken[:50], "count": len(taken)})
    swapped = None
    if taken:
        swapped = move_many(conn, p, taken, by=by, reason=f"还原 {code} 时，原位置上的这些先让开", origin=f"还原 {code} 换下来的")["code"]
    with store.tx(conn):
        for src, dst in moves:
            if src.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
        shutil.rmtree(box, ignore_errors=True)          # 盒子里剩下的只是空文件夹
        _set_status(p, code, BACK, f"- 还原于：{datetime.now():%Y-%m-%d %H:%M}（{by}）" + (f"，原位置上的挪进了 {swapped}" if swapped else ""))
        store.log(conn, by, "从回收站还原", code, e["fields"]["原来在"])
    return {"code": code, "back_to": e["fields"]["原来在"], "swapped": swapped}


def purge(conn, p: Project, codes: list[str], *, by: str, before: str | None = None) -> dict:
    """彻底删掉（收不回来）：还在回收站里的才删。作者 10-07「垃圾桶的东西应该可以直接删吧？」——不再要求先定性一档存档；
    before 只留给老的调用（给了就照旧只删那个时间以前进来的）。只有人在网页上点、确认过才走到这，agent 没有这个工具。"""
    got = {x["code"]: x for x in read(p)}
    bad = [c for c in codes if c not in got or got[c]["status"] != IN or (before and got[c]["at"] > before)]
    if bad:
        raise store.Refused(f"{'、'.join(bad)} 不能彻底删：不在回收站里了" + (f"，或是 {before} 以后才进来的" if before else ""))
    freed = 0
    with store.tx(conn):
        for c in codes:
            box = _box(p, got[c])
            if box.exists():
                freed += _size(box)
                shutil.rmtree(box)
            _set_status(p, c, GONE, f"- 彻底删于：{datetime.now():%Y-%m-%d %H:%M}（{by}）")
        store.log(conn, by, "彻底删掉", None, "、".join(codes))
    return {"codes": codes, "freed": freed}


def pending_requests(p: Project, modules: list[str]) -> list[dict]:
    """笔记里的删除请求，还没有哪件回收站的东西对上它的（按编号对）。"""
    done = {e["fields"].get("删除请求", "") for e in read(p)}
    out = []
    for s in notebook.scopes(p, modules):
        for e in notebook.read(p, s["scope"]):
            if e["kind"] == "删除请求" and not any(e["id"] in d for d in done):
                out.append({"scope": s["scope"], **e})
    out.sort(key=lambda e: e["at"], reverse=True)
    return out
