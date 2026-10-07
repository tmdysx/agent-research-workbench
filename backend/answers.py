"""自动化答疑：agent 有问题，先在记录里找；找到了照做、写明用的哪条，找不到才转给人（待拍板）。

答疑记录跟笔记分开（作者 2026-09-25：「自动化要有自己的专属自动化日志和答疑不要跟笔记混在一起」）：
`自动化/答疑/<年-月>.md`，一个问题一条，编号 Q1、Q2…（号不回收）。
只用记录里人说过的话，不编（戒律 通-14）。找答案靠的是字面相近，**判断是不是真答过了，是 agent 的事**。
"""
from __future__ import annotations

import atomic
import os
import re
from datetime import datetime
from pathlib import Path

import notebook
import governance_paths as gp
import store
from project import Project

DIR = Path("自动化") / "答疑"
_HEAD = re.compile(r"^## (Q\d+) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?) · (.+?)\s*$")
_ROW_CODE = re.compile(r"^\|\s*([^|\s]+-\d+)\s*\|")
_BULLET_CODE = re.compile(r"^-\s+([^\s\d|][^\s|]*-\d+)\s")   # AGENTS.md 里一行一条的「- 通-1 …」
_TEXT = re.compile(r"[\w一-鿿]+")
# 太常见、不带意思的两个字，不拿来比
_STOP = set("什么 怎么 是不 不是 一个 这个 那个 可以 要不 不要 我们 你们 他们 的话 如果 还是 或者 就是 已经 应该 需要 "
            "现在 时候 因为 所以 但是 没有 有没 能不 不能 这样 那样 是否 哪个 哪些 为啥 为什 么要 要用 用什".split())
MIN_SCORE = 0.4             # 问题里至少四成的词在这条记录里出现过，且至少 3 个，才算「可能答过」


def _grams(text: str) -> set[str]:
    out = set()
    for w in _TEXT.findall(text.lower()):
        out |= {w[i:i + 2] for i in range(len(w) - 1)}
    return out - _STOP


def _lines(f: Path):
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if len(line) >= 6 and not line.startswith(("|---", "---", "```")):
            yield i, line


def _units(conn, p: Project):
    """能拿来答问题的记录：人拍过的板、戒律、计划、蓝图、人的笔记。"""
    for d in store.list_decisions(conn, 1000):
        yield f"决定 {d['code']}", f"问：{d['detail']} → 答：{d['text']}"
    rules = set(gp.rule_files(p)) | set(gp.records(p, "模块戒律").values())   # 模块戒律跟着模块走
    for f in sorted(rules) + [p.root / "AGENTS.md"]:
        for i, line in _lines(f):
            m = _ROW_CODE.match(line) or _BULLET_CODE.match(line)
            yield (f"戒律 {m.group(1)}" if m else f"{f.name} 第 {i} 行"), line
    for rel, f in gp.plan_files(p).items():
        if f.name.startswith('原文') or '（原文）' in f.stem:
            continue
        code = f"{f.parent.name.split(' ')[0]} · {f.stem.split(' ')[0]}" if '/' in rel else f.stem
        for i, line in _lines(f):
            yield f'计划 {code}', line
    for f in sorted(gp.goal_files(p)):
        if f.name == "戒律.md":                          # 蓝图模块自己的戒律，上面已经算过
            continue
        for i, line in _lines(f):
            m = _ROW_CODE.match(line)
            yield f"蓝图 {f.stem.split(' ')[0]}" + (f" {m.group(1)}" if m else ""), line
    notes = notebook.note_dir(p)
    if notes.is_dir():
        for f in sorted(notes.glob("*.md")):
            for e in notebook.parse(f.read_text(encoding="utf-8", errors="replace")):
                if e["kind"] == "笔记":                   # 只算人亲手写的；网页自动记的操作（新建模块、放进来…）不是答案
                    yield f"笔记 {e['id']}", e["body"]


def find(conn, p: Project, question: str, limit: int = 6) -> list[dict]:
    """在记录里找跟这个问题最像的几条，每条带出处。"""
    q = _grams(question)
    if not q:
        return []
    hits = []
    need = 2 if len(q) <= 6 else 3                      # 问题很短时，对上 2 个词就算
    for src, text in _units(conn, p):
        g = _grams(text)
        n = len(q & g)
        score = n / len(q)
        if n >= need and score >= MIN_SCORE:
            hits.append({"src": src, "text": text[:240], "score": round(score, 2)})
    hits.sort(key=lambda h: -h["score"])
    seen, out = set(), []
    for h in hits:                                      # 同一处出来好几行的，只留最像的一行
        if h["src"] not in seen:
            seen.add(h["src"])
            out.append(h)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- 答疑记录

def _file(p: Project, month: str) -> Path:
    return p.root / DIR / f"{month}.md"


def _one_line(s: str) -> str:
    return " / ".join(x.strip() for x in (s or "").strip().splitlines() if x.strip())


def read(p: Project) -> list[dict]:
    """全部答疑记录，新的在前。"""
    d = p.root / DIR
    out = []
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.md")):
        cur = None
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = _HEAD.match(line)
            if m:
                cur = {"code": m.group(1), "at": m.group(2), "by": m.group(3), "result": m.group(4), "lines": []}
                out.append(cur)
            elif cur is not None and line.startswith("- "):
                cur["lines"].append(line[2:])
    for e in out:
        e["fields"] = dict(x.split("：", 1) for x in e["lines"] if "：" in x)
    out.sort(key=lambda e: int(e["code"][1:]), reverse=True)
    return out


def _next_code(conn, p: Project) -> str:
    n = int(store._meta(conn, "q_seq") or 0)
    for e in read(p):
        n = max(n, int(e["code"][1:]))
    store._set_meta(conn, "q_seq", str(n + 1))
    return f"Q{n + 1}"


def log(conn, p: Project, question: str, *, by: str, result: str, run: str = "", checked: str = "",
        used: str = "", answer: str = "", pending: str = "") -> dict:
    """记一条答疑。result：自动答上 / 转给你了。"""
    fields = [("问题", question), ("运行", run), ("查过", checked), ("用的", used), ("答案", answer), ("转成待拍板", pending)]
    with store.tx(conn):
        code = _next_code(conn, p)
        now = datetime.now()
        at = now.strftime("%Y-%m-%d %H:%M")
        f = _file(p, now.strftime("%Y-%m"))
        f.parent.mkdir(parents=True, exist_ok=True)
        head = "" if f.exists() else (f"# 答疑记录 · {now:%Y-%m}\n\n> agent 干活时的问题：先查记录，查到就自动答上、写明用的哪条；"
                                      "查不到才转给人（待拍板）。跟笔记分开放。\n")
        body = "".join(f"- {k}：{_one_line(v)}\n" for k, v in fields if _one_line(v))
        with open(f, "a", encoding="utf-8") as w:
            w.write(head + f"\n## {code} · {at} · {by} · {result}\n{body}")
        store.log(conn, by, "答疑", code, result)
    return {"code": code, "at": at, "result": result}


def close_pending(conn, p: Project, pending: str, decision: str, text: str) -> str | None:
    """人给一条待拍板拍了板：从这条待拍板来的答疑，标上「你拍板了」和决定编号。返回那条 Q 的编号。"""
    d = p.root / DIR
    if not d.is_dir():
        return None
    mark = f"- 转成待拍板：{pending}"
    with store.tx(conn):
        for f in sorted(d.glob("*.md")):
            lines = f.read_text(encoding="utf-8").split("\n")
            if mark not in lines:
                continue
            i = lines.index(mark)
            h = i
            while h > 0 and not _HEAD.match(lines[h]):
                h -= 1
            m = _HEAD.match(lines[h])
            lines[h] = f"## {m.group(1)} · {m.group(2)} · {m.group(3)} · 你拍板了"
            lines.insert(i + 1, f"- 你拍板：{decision} {_one_line(text)}")
            tmp = f.with_suffix(".md.tmp")
            tmp.write_text("\n".join(lines), encoding="utf-8")
            atomic.replace(tmp, f)
            return m.group(1)
    return None
