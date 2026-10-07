"""监管：网页自己盯着项目——agent 报不报、读没读规矩，后台都看得到。

作者 2026-10-01：「我要做的是能自动化监管的活的网页端，不能全让agent来读取文件」；发现问题时：「继续推进不懂的放agent问答中」。
- 看什么：后台每扫一遍项目（main.watch，1.5 秒以上一遍）就比一比哪些文件加了、改了、没了；再对照库里谁领着哪件、谁拿着核心锁、
  网页上人刚做过什么。有会话记录时（sessions.py）还能说出是哪个 agent 改的
- 七条规矩（一条一行，人看得懂）：

  1 改核心先拿锁   backend/、模板.html、界面脚本、启动器变了，这时没人拿着核心锁               红
  2 删东西进回收站 项目里的文件没了，也没出现在回收站里                                       红 · 问人
  3 人的笔记只增   笔记/ 下已有的内容被改、被删（不算 笔记/日志/、笔记/历史/）               红 · 问人
  4 方向只有人改   治理/戒律/、治理/需求/、治理/目标/ 的正文变了（S2 那几行不算），不是网页上人改的   黄 · 问人
  5 改东西要领活   自动化在跑时，资料/<模块>/ 变了，没人领着这个模块那条道                    黄
  6 领着活要动     领着活半小时没动静；在跑的单一小时没人干                                   黄
  7 在干活就要报到 会话记录里有 agent 在调本项目接口，却没报到                                黄

- 发现了：**不停**——不叫停开工单、不放掉谁的活、不删不挪文件、不关 agent 的程序。记一条（同一件事只一条，表 finding）、
  写一行机器日志（kind「监管」）；2、3、4 条发到问答「agent 问你 · 待你判断」；那个 agent 下次领活、报一圈、交付时，
  返回里带一句「监管提醒」。网页上人刚做过操作（20 秒内）时改的，不算 agent 越界
- 自动化没在跑（没人领活、没单在跑）时，资料/ 里的文件变了多半是你自己在改：第 5 条不报
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path

import claims
import store
from project import Project

RULES = {1: ("改核心先拿锁", "红"), 2: ("删东西进回收站", "红"), 3: ("人的笔记只增", "红"), 4: ("方向只有人改", "黄"),
         5: ("改东西要领活", "黄"), 6: ("领着活要动", "黄"), 7: ("在干活就要报到", "黄")}
ASK = {2, 3, 4}                                       # 拿不准的：发到问答，人拍板
CORE = ("backend", "模板.html", "界面英文.js", "治理界面.js", "启动.bat", "新项目.bat", ".mcp.json")
NOT_MINE = ("存档/", "回收站/", "索引/", ".claude/", ".git/")   # 程序自己管的、别的会话的工作副本：不看
OPEN, FIXED, ACKED, ANSWERED = "开着", "已经好了", "知道了", "问答里定了"
HUMAN_WINDOW = 20                                     # 网页上人刚做过操作的这几秒里改的：算人改的
STALL, IDLE_ORDER = 30 * 60, 60 * 60

_TABLE = """CREATE TABLE IF NOT EXISTS finding(
    id        INTEGER PRIMARY KEY,
    rule      INTEGER NOT NULL,
    key       TEXT NOT NULL,                -- 同一条规矩、同一个 key 只记一条（文件路径 / 模块 / agent）
    text      TEXT NOT NULL,
    who       TEXT NOT NULL DEFAULT '',     -- 看得出是谁就写；看不出空着
    paths     TEXT NOT NULL DEFAULT '',     -- 涉及的文件，「、」隔开（最多 20 个）
    first_at  TEXT NOT NULL,
    last_at   TEXT NOT NULL,
    state     TEXT NOT NULL DEFAULT '开着',
    qa        TEXT NOT NULL DEFAULT '',     -- 发到问答的编号（D-…）
    UNIQUE(rule, key)
)"""
_TEXTS: dict[str, str] = {}                           # 笔记、治理文件上一回的内容（比「只增」「正文变没变」用）


def _ensure(conn) -> None:
    conn.execute(_TABLE)


def _watched_text(rel: str) -> bool:
    """要记住内容的文件：人的笔记、方向文件。"""
    if not rel.endswith(".md"):
        return False
    if rel.startswith("笔记/"):
        return not rel.startswith(("笔记/日志/", "笔记/历史/"))
    return rel.startswith(("治理/戒律/", "治理/需求/", "治理/目标/"))


def _read(p: Project, rel: str) -> str | None:
    try:
        return (p.root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _body(rel: str, text: str) -> str:
    """方向文件的「正文」：目标文件里 S2 那几行（任务和状态，agent 交付时会改）不算。"""
    if rel.startswith("治理/目标/"):
        return "\n".join(x for x in text.splitlines() if not x.lstrip().startswith("| S2-"))
    return text


def prime(p: Project, snap: dict) -> None:
    """头一回：记住笔记、方向文件现在的内容。"""
    for rel in snap:
        if _watched_text(rel) and rel not in _TEXTS:
            t = _read(p, rel)
            if t is not None:
                _TEXTS[rel] = t


def _state_file(p: Project) -> Path:
    return p.root / "索引" / "监管快照.json"


def restore(p: Project) -> dict | None:
    """上回看到的项目样子（每个文件的大小、时间，笔记和方向文件的内容）。
    改了 backend/ 的程序后台会整个重启：要是新进程拿「改完的样子」当起点，那次改动就永远看不到了（10-01 试的时候踩到）；
    关着的时候有人改的也一样。所以每扫一遍存一份，起来先跟它比。"""
    import json
    try:
        d = json.loads(_state_file(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    _TEXTS.clear()
    _TEXTS.update(d.get("texts") or {})
    return {k: tuple(v) for k, v in (d.get("snap") or {}).items()}


def _save(p: Project, snap: dict) -> None:
    import json
    import atomic
    f = _state_file(p)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_text(json.dumps({"snap": snap, "texts": _TEXTS}, ensure_ascii=False), encoding="utf-8")
        atomic.replace(tmp, f)
    except OSError:
        pass                                          # 存不上：下回再存，不挡着监管


def diff(old: dict, new: dict) -> tuple[list[str], list[str], list[str]]:
    """两遍扫描之间：新加的、改了的、没了的文件。"""
    added = [r for r in new if r not in old]
    changed = [r for r in new if r in old and new[r] != old[r]]
    removed = [r for r in old if r not in new]
    return added, changed, removed


def _human_recent(conn) -> bool:
    r = conn.execute("SELECT MAX(at) FROM event WHERE actor = '人'").fetchone()[0]
    try:
        return bool(r) and (datetime.now() - datetime.fromisoformat(r)).total_seconds() < HUMAN_WINDOW
    except ValueError:
        return False


def _in_archive(p: Project, rel: str) -> bool:
    """这个文件是被收进归档了（S1-8 S2-61）：归档/索引.json 里记着它。"""
    try:
        import archive
        return archive.is_archived(p, rel)
    except Exception:
        return False


def _moved_away(p: Project, rel: str) -> bool:
    """统一内置时从 内置/ 搬走的（10-07）：自动化/清理/内置搬家.json 里记着。"""
    try:
        import builtin
        return builtin.moved_away(p.root, rel)
    except Exception:
        return False


def _in_trash(p: Project, rel: str) -> bool:
    """这个文件是被挪进回收站了：回收站里最近的那几盒里原样放着它（按原路径）。"""
    box = p.root / "回收站"
    if not box.is_dir():
        return False
    cut = time.time() - 600
    for d in box.iterdir():
        try:
            if d.is_dir() and d.stat().st_mtime >= cut and (d / rel).exists():
                return True
        except OSError:
            continue
    return False


def _who(p: Project, rels: list[str], since: float, use_sessions: bool) -> str:
    if not use_sessions:
        return ""
    import sessions
    for rel in rels:
        w = sessions.who_edited(p.root / rel, since)
        if w:
            return w
    return ""


def record(conn, p: Project, rule: int, key: str, text: str, *, who: str = "", paths: list[str] | None = None,
           ask: str = "") -> dict | None:
    """记一条。新的（或关了又出现的）返回它：写日志、要问的发问答；已经开着的只更新时间和涉及的文件。"""
    _ensure(conn)
    now = store.now()
    paths = paths or []
    with store.tx(conn):
        r = conn.execute("SELECT * FROM finding WHERE rule = ? AND key = ?", (rule, key)).fetchone()
        if r and r["state"] == OPEN:
            merged = list(dict.fromkeys([x for x in r["paths"].split("、") if x] + paths))[:20]
            conn.execute("UPDATE finding SET last_at = ?, text = ?, paths = ?, who = COALESCE(NULLIF(?, ''), who) WHERE id = ?",
                         (now, text, "、".join(merged), who, r["id"]))
            return None
        if r:
            conn.execute("UPDATE finding SET text = ?, who = ?, paths = ?, first_at = ?, last_at = ?, state = ?, qa = '' WHERE id = ?",
                         (text, who, "、".join(paths[:20]), now, now, OPEN, r["id"]))
            fid = r["id"]
        else:
            fid = conn.execute("INSERT INTO finding(rule, key, text, who, paths, first_at, last_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                               (rule, key, text, who, "、".join(paths[:20]), now, now)).lastrowid
    import journal
    name, lamp = RULES[rule]
    journal.add(conn, p, f"监管 · {name}（{lamp}）：{text}" + (f"（看得出是 {who}）" if who else ""), by="监管", kind="监管")
    if rule in ASK and ask:
        q = store.ask_human(conn, ask, by="监管", context=f"规矩 {rule}「{name}」· {text}")
        with store.tx(conn):
            conn.execute("UPDATE finding SET qa = ? WHERE id = ?", (q.get("code", ""), fid))
    return dict(conn.execute("SELECT * FROM finding WHERE id = ?", (fid,)).fetchone())


def _restore_hint(p: Project) -> str:
    import snapshot
    saves = snapshot.list_saves(p)
    return f"最近的存档是 {saves[0]['code']}，本机 git 里也有之前的样子" if saves else "本机 git 里有之前的样子"


# 程序换文件时的临时文件：先写 x.tmp / x.tmp.<号> / 下载的 .part，写完换成正式文件，临时的就没了——不是删东西（S1-8 S2-27；
# 10-01 总览最上面一长串「repos.py.tmp.… 没了，回收站里也没有」「paperclip-main.zip.part 没了」都是这个）
_TEMP = re.compile(r"(\.tmp|\.part|\.crdownload|\.swp|~)$|\.tmp\.[^/]*$", re.I)
TEMP_WHY = "那是程序换文件时的临时文件（写完换成正式文件就没了），不是删东西，监管报错了"


def _temp(rel: str) -> bool:
    return bool(_TEMP.search(rel))


def on_scan(conn, p: Project, old: dict | None, new: dict, *, use_sessions: bool = False) -> list[dict]:
    """扫完一遍：对照规矩 1–5 看这几秒的文件变化。返回新记下的几条。old 是 None：头一回，记住现在的样子。"""
    if old is None:
        prime(p, new)
        _save(p, new)
        return []
    try:
        return _check_files(conn, p, old, new, use_sessions)
    finally:
        prime(p, new)                                 # 新出现的笔记、方向文件也记住内容
        _save(p, new)


def _check_files(conn, p: Project, old: dict, new: dict, use_sessions: bool) -> list[dict]:
    added, changed, removed = diff(old, new)
    mine = lambda r: not r.startswith(NOT_MINE) and not _temp(r)
    added, changed, removed = [r for r in added if mine(r)], [r for r in changed if mine(r)], [r for r in removed if mine(r)]
    if not (added or changed or removed):
        return []
    human = _human_recent(conn)
    active = claims.active(conn)
    core_holder = next((r["agent"] for r in active if r["goal"] == claims.CORE), "")
    lanes = {lane for r in active if r["goal"] != claims.CORE for lane in r["lanes"]}
    import workorders
    running = bool([r for r in active if r["goal"] != claims.CORE]) or bool(workorders.running(p))
    since = time.time() - 600
    got = []

    def keep(x):
        if x:
            got.append(x)

    # 1 改核心先拿锁
    core = [r for r in added + changed + removed if r.split("/")[0] in CORE]
    if core and not core_holder and not human:
        who = _who(p, core, since, use_sessions)
        keep(record(conn, p, 1, "核心", f"没拿核心锁就改了核心：{'、'.join(core[:5])}" + (f" 等 {len(core)} 个" if len(core) > 5 else ""),
                    who=who, paths=core))
    # 2 删东西进回收站
    moved = {Path(r).name for r in added}
    for rel in removed:
        if Path(rel).name in moved or _in_trash(p, rel) or _in_archive(p, rel) or _moved_away(p, rel) or human:
            continue
        who = _who(p, [rel], since, use_sessions)
        keep(record(conn, p, 2, rel, f"「{rel}」没了，回收站里也没有", who=who, paths=[rel],
                    ask=f"「{rel}」被删了（没进回收站）{'，看得出是 ' + who + ' 删的' if who else ''}。是你让删的吗？不是的话{_restore_hint(p)}，要我照着找回来吗？"))
    # 3 人的笔记只增 · 4 方向只有人改
    for rel in changed + removed + added:
        if not _watched_text(rel):
            continue
        new_text = _read(p, rel) if rel in new else None
        old_text = _TEXTS.get(rel)
        if new_text is not None:
            _TEXTS[rel] = new_text
        else:
            _TEXTS.pop(rel, None)
        if human or old_text is None:
            continue
        who = _who(p, [rel], since, use_sessions)
        if rel.startswith("笔记/"):
            if new_text is None or not new_text.startswith(old_text.rstrip()):
                keep(record(conn, p, 3, rel, f"人的笔记「{rel}」里已有的内容被{'删了' if new_text is None else '改了'}", who=who, paths=[rel],
                            ask=f"你的笔记「{rel}」里已有的内容被{'整份删了' if new_text is None else '改了'}{'，看得出是 ' + who if who else ''}。笔记只许加不许改，是你让改的吗？不是的话 笔记/历史/ 或{_restore_hint(p)}。"))
        elif new_text is None or _body(rel, new_text) != _body(rel, old_text):
            keep(record(conn, p, 4, rel, f"方向文件「{rel}」的正文{'没了' if new_text is None else '改了'}（不是网页上你改的）", who=who, paths=[rel],
                        ask=f"「{rel}」的正文被{'删了' if new_text is None else '改了'}{'，看得出是 ' + who if who else ''}。方向（S0、S1、需求、戒律）只有你能定，是你让改的吗？"))
    # 5 改东西要领活
    if running and not human:
        by_mod: dict[str, list[str]] = {}
        for rel in added + changed + removed:
            parts = rel.split("/")
            if len(parts) > 2 and parts[0] == "资料" and parts[1] not in ("_外部资料入口",) and parts[1] not in lanes:
                by_mod.setdefault(parts[1], []).append(rel)
        for m, rels in by_mod.items():
            who = _who(p, rels, since, use_sessions)
            keep(record(conn, p, 5, m, f"「{m}」模块里的文件在变（{'、'.join(rels[:3])}），可没人领着「{m}」的活", who=who, paths=rels))
    return got


def check_state(conn, p: Project, rows: list[dict] | None = None) -> list[dict]:
    """平时看一眼：6 领着活要动、7 在干活就要报到；问答里定了的、情况消失了的关掉。返回新记下的几条。"""
    _ensure(conn)
    import workorders
    got, now_keys = [], set()
    active = claims.active(conn)
    for r in active:
        if r["goal"] != claims.CORE and r["idle"] >= STALL:
            key = f"{r['agent']}|{r['goal']} {r['sub']}"
            now_keys.add((6, key))
            x = record(conn, p, 6, key, f"{r['agent'].replace('agent:', '')} 领着 {r['goal']} {r['sub']}，{r['idle'] // 60} 分钟没动静", who=r["agent"])
            if x:
                got.append(x)
    wo = workorders.running(p)
    if wo and not [r for r in active if r["goal"] != claims.CORE]:
        last = conn.execute("SELECT MAX(at) FROM event WHERE actor LIKE 'agent:%'").fetchone()[0]
        try:
            idle = (datetime.now() - datetime.fromisoformat(last)).total_seconds() if last else IDLE_ORDER
        except ValueError:
            idle = 0
        if idle >= IDLE_ORDER:
            key = f"单|{wo['code']}"
            now_keys.add((6, key))
            x = record(conn, p, 6, key, f"{wo['code']} 在跑，可 {int(idle // 60)} 分钟没有 agent 来干活")
            if x:
                got.append(x)
    for r in rows or []:
        if r.get("state") == "在跑" and not r.get("registered") and r.get("agent"):
            key = r["agent"]
            now_keys.add((7, key))
            x = record(conn, p, 7, key, f"{r['agent']} 在调这个项目的接口干活，可还没报到（register_agent）", who="agent:" + r["agent"])
            if x:
                got.append(x)
    with store.tx(conn):
        for f in conn.execute("SELECT id, rule, key, qa FROM finding WHERE state = ?", (OPEN,)).fetchall():
            if f["rule"] == 2 and _temp(f["key"]):            # 以前报错的临时文件：关掉，问人的那条收回
                conn.execute("UPDATE finding SET state = ?, last_at = ? WHERE id = ?", (FIXED, store.now(), f["id"]))
                if f["qa"]:
                    store.withdraw(conn, f["qa"], TEMP_WHY, by="监管")
            elif f["rule"] in (6, 7) and (f["rule"], f["key"]) not in now_keys:
                conn.execute("UPDATE finding SET state = ?, last_at = ? WHERE id = ?", (FIXED, store.now(), f["id"]))
            elif f["qa"]:
                q = conn.execute("SELECT closed_at FROM note WHERE code = ?", (f["qa"],)).fetchone()
                if q and q["closed_at"]:
                    conn.execute("UPDATE finding SET state = ?, last_at = ? WHERE id = ?", (ANSWERED, store.now(), f["id"]))
    return got


def listing(conn, limit: int = 12) -> dict:
    _ensure(conn)
    rows = [dict(r) | {"name": RULES[r["rule"]][0], "lamp": RULES[r["rule"]][1]}
            for r in conn.execute("SELECT * FROM finding ORDER BY last_at DESC, id DESC LIMIT 200")]
    return {"open": [r for r in rows if r["state"] == OPEN],
            "recent": [r for r in rows if r["state"] != OPEN][:limit],
            "rules": [{"n": n, "name": v[0], "lamp": v[1], "ask": n in ASK} for n, v in RULES.items()]}


def ack(conn, fid: int, by: str = "人") -> dict:
    _ensure(conn)
    with store.tx(conn):
        r = conn.execute("SELECT * FROM finding WHERE id = ?", (fid,)).fetchone()
        if r is None:
            raise store.Refused(f"没有这条监管记录 {fid}")
        conn.execute("UPDATE finding SET state = ?, last_at = ? WHERE id = ?", (ACKED, store.now(), fid))
        store.log(conn, by, "监管知道了", str(fid), r["text"][:120])
    return dict(conn.execute("SELECT * FROM finding WHERE id = ?", (fid,)).fetchone())


def reminders(conn, agent: str) -> list[str]:
    """给这个 agent 的提醒：开着的、看得出是它的，或看不出是谁的文件类（它可能就是那个人）。最多 3 条。"""
    _ensure(conn)
    out = []
    for r in conn.execute("SELECT * FROM finding WHERE state = ? ORDER BY last_at DESC LIMIT 20", (OPEN,)):
        mine = r["who"] in (agent, agent.replace("agent:", "")) or (not r["who"] and r["rule"] <= 5)
        if mine:
            out.append(f"规矩 {r['rule']}「{RULES[r['rule']][0]}」：{r['text']}" + (f"（已经问人了：{r['qa']}）" if r["qa"] else ""))
    return out[:3]


def reminder_text(conn, agent: str) -> str:
    rs = reminders(conn, agent)
    return ("\n\n## 监管提醒（网页自己看到的，照规矩改；不用停下来）\n" + "\n".join(f"- {x}" for x in rs)) if rs else ""
