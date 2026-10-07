"""数据库读写：模块、事件、待拍板和决定都存在这；程序里只有它写数据库。

人（网页）和 agent（MCP）都调这里的函数，写进同一张表，都记 created_by。
网页进程和 MCP 进程各开各的连接；WAL 模式下可以一边读一边写。

表：
  module          文件夹模块（资料/ 下一个文件夹一行：default / human / agent / folder）；
                  还留着 09-22 从 蓝图.json 同步来的旧行（source=blueprint），不删，也不再读——
                  蓝图现在是 资料/蓝图/ 里的 S0、S1 文件，blueprint.py 现读
  note            人的草稿、导出过的指令、待拍板、决定
  event           谁、什么时候、干了什么。最大 id 兼当「版本号」，网页靠它判断要不要刷新
  meta            零碎键值（上次同步的蓝图指纹）
  schema_version  建表迁移记录
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import blueprint
import project as proj
from project import Project

STATUSES = blueprint.STATUSES

# 每个版本一组语句。只许往后加，不许改已有的——老库靠它们一步步升上来。
MIGRATIONS: list[list[str]] = [
    [  # v1
        """CREATE TABLE module(
            id          INTEGER PRIMARY KEY,
            code        TEXT NOT NULL UNIQUE,          -- 编号：B-01 / X-01
            layer       TEXT NOT NULL DEFAULT '',      -- 层：后端 / 前端 / 机制 / 空=新加的
            name        TEXT NOT NULL,
            one_line    TEXT NOT NULL DEFAULT '',
            deps        TEXT NOT NULL DEFAULT '[]',    -- 靠谁，JSON 编号列表
            status      TEXT NOT NULL DEFAULT 'bad',   -- ok / warn / todo / bad
            acceptance  TEXT NOT NULL DEFAULT '',
            points      TEXT NOT NULL DEFAULT '[]',    -- 功能点，JSON
            moat        INTEGER NOT NULL DEFAULT 0,
            remark      TEXT NOT NULL DEFAULT '',
            ord         INTEGER NOT NULL DEFAULT 0,    -- 在蓝图里的顺序
            source      TEXT NOT NULL,                 -- blueprint / human / agent
            created_by  TEXT NOT NULL,                 -- 蓝图.json / 人 / agent:claude-code
            created_at  TEXT NOT NULL,
            gone        INTEGER NOT NULL DEFAULT 0,    -- 蓝图里已经没有这一行了
            deleted_at  TEXT,                          -- 非空 = 在回收站
            deleted_by  TEXT,
            user_id     TEXT                           -- 多人预留，第一版恒空
        )""",
        """CREATE TABLE note(
            id          INTEGER PRIMARY KEY,
            kind        TEXT NOT NULL,                 -- 草稿 / 指令 / 待拍板 / 决定
            code        TEXT UNIQUE,                   -- 待拍板 D-01，决定 A-01
            text        TEXT NOT NULL,
            detail      TEXT NOT NULL DEFAULT '',      -- 待拍板=背景；决定=当时的问题
            ref         TEXT,                          -- 待拍板↔决定 互指
            created_by  TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            closed_at   TEXT,                          -- 待拍板被拍板的时间
            user_id     TEXT
        )""",
        """CREATE TABLE event(
            id      INTEGER PRIMARY KEY,
            at      TEXT NOT NULL,
            actor   TEXT NOT NULL,
            action  TEXT NOT NULL,
            target  TEXT,
            detail  TEXT,
            user_id TEXT
        )""",
        "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        "CREATE INDEX note_kind ON note(kind, closed_at)",
    ],
    [  # v2：模块有了自己的文件夹和页面，也有自己的图标
        "ALTER TABLE module ADD COLUMN emoji TEXT NOT NULL DEFAULT ''",
    ],
    [  # v3：作者 2026-09-23「图标去掉，要中英文」——图标不用了（列留着），改记英文名
        "ALTER TABLE module ADD COLUMN en TEXT NOT NULL DEFAULT ''",
    ],
    [  # v4：外部资料入口 Intake——外面的材料先进 资料/_外部资料入口/，分拣记录在这
        """CREATE TABLE intake(
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,                 -- 在 _外部资料入口/ 里的文件名
            orig        TEXT NOT NULL,                 -- 拖进来时的原名（可能带子文件夹）
            sha256      TEXT NOT NULL,                 -- 去重靠它：同一个文件拖十次只留一份
            size        INTEGER NOT NULL,
            candidates  TEXT NOT NULL DEFAULT '[]',    -- [{module, conf: 高/中/低, reason, by}]
            status      TEXT NOT NULL DEFAULT 'waiting',   -- waiting / sorted / gone
            sorted_to   TEXT,
            sorted_by   TEXT,
            sorted_at   TEXT,
            created_by  TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            user_id     TEXT
        )""",
        "CREATE INDEX intake_sha ON intake(sha256)",
    ],
]


class Refused(Exception):
    """按规矩不能做（比如删蓝图里的模块）。消息是给人看的。"""


class Duplicate(Exception):
    def __init__(self, existing: dict):
        self.existing = existing
        super().__init__(f"已经有一个叫「{existing['name']}」的模块了（{existing['code']}）")


class NeedConfirm(Exception):
    """要人再确认一次才做（删有文件的模块、复活、还原到有东西的位置……）。消息就是弹给人看的警告，info 是细节。"""
    def __init__(self, message: str, info: dict | None = None):
        self.info = info or {}
        super().__init__(message)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- 连接与迁移

def connect(db_path: Path) -> sqlite3.Connection:
    fresh = not db_path.exists()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")           # 先设等待：几个 agent 同时连进来时排队，不立刻报「锁住了」
    for i in range(20):                                # 全新的库被两个连接同时设 WAL，会撞上「锁住了」：稍等再试
        try:
            if conn.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
                conn.execute("PRAGMA journal_mode=WAL")
            break
        except sqlite3.OperationalError:
            if i == 19:
                raise
            time.sleep(0.05 * (i + 1))
    if fresh:
        migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """把库升到最新版本，返回版本号。两个进程同时启动也安全：写锁排队，锁里再看一次版本。"""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    with tx(conn):
        cur = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]
        for v in range(cur + 1, len(MIGRATIONS) + 1):
            for stmt in MIGRATIONS[v - 1]:
                conn.execute(stmt)
            conn.execute("INSERT INTO schema_version VALUES(?, ?)", (v, now()))
    return len(MIGRATIONS)


@contextmanager
def tx(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def log(conn, actor: str, action: str, target: str | None = None, detail: str | None = None) -> int:
    return conn.execute(
        "INSERT INTO event(at, actor, action, target, detail) VALUES(?, ?, ?, ?, ?)",
        (now(), actor, action, target, detail),
    ).lastrowid


def version(conn) -> int:
    return conn.execute("SELECT COALESCE(MAX(id), 0) FROM event").fetchone()[0]


def _meta(conn, key: str) -> str | None:
    r = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return r[0] if r else None


SCAN_MODES = ("实时", "慢扫", "只看最上一层")             # S1-8 S2-42 用过的；S2-43 起改在 自动化/扫描规则.md（scanmap.migrate 搬一次）


def scan_modes(conn) -> dict:
    """{模块名: 慢扫 / 只看最上一层}：以前「模块」表里设的，只留着给 scanmap.migrate 搬家。"""
    try:
        d = json.loads(_meta(conn, "scan_modes") or "{}")
    except ValueError:
        return {}
    return {k: v for k, v in d.items() if v in SCAN_MODES and v != "实时"}


def _set_meta(conn, key: str, value: str) -> None:
    conn.execute("INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                 (key, value))


# ---------------------------------------------------------------- 模块
#
# - 旧的蓝图行（source=blueprint）：09-22 从 蓝图.json 同步来的，留在库里不删，哪儿都不用
# - 文件夹模块：资料/ 下一个文件夹一行。default=工具建的（固定三个 + 起步模块） · human=你点＋加的 · agent=agent 加的 ·
#   folder=在资源管理器里自己建的（不知道是谁）。文件夹在，模块就在；文件夹没了只标 gone，留底可溯源

def _module(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["deps"] = json.loads(d["deps"])
    d["points"] = json.loads(d["points"])
    d["moat"] = bool(d["moat"])
    d["gone"] = bool(d["gone"])
    for k in ("ord", "user_id", "deleted_at", "deleted_by", "emoji"):
        d.pop(k, None)
    return d


def get_module(conn, code: str) -> dict | None:
    r = conn.execute("SELECT * FROM module WHERE code = ?", (code,)).fetchone()
    return _module(r) if r else None


def _folder_rows(conn) -> dict[str, sqlite3.Row]:
    """文件夹模块，按名字（不分大小写）只留最新一行——同名文件夹删了又建，算同一个模块。"""
    rows = {}
    for r in conn.execute("SELECT * FROM module WHERE source != 'blueprint' AND deleted_at IS NULL ORDER BY id"):
        rows[r["name"].lower()] = r
    return rows


def _default_en(name: str, labels: dict | None = None) -> str:
    return (labels or {}).get(name) or proj.KNOWN_EN.get(name, "")


def list_folder_modules(conn, project: Project) -> list[dict]:
    """网页中间那条要画的：还在的文件夹模块 + 各自的文件数、大小、最近变动。
    固定的三个（蓝图 · 戒律 · 源代码）永远排最前、带 fixed（设置页里不给删）。"""
    fixed = {n: i for i, n in enumerate(proj.FIXED_NAMES)}
    order = {n: i for i, n in enumerate(proj.STARTER_NAMES)}
    labels = proj.template_module_labels(project.root)
    import scanmap
    out = []
    for r in _folder_rows(conn).values():
        if r["gone"]:
            continue
        m = _module(r)
        m["en"] = m["en"] or _default_en(m["name"], labels)
        m.update(scanmap.module_stats(project, m["name"]))      # 后台在跑：用扫完那一片留下的数，不每次重数（S1-8 S2-43）
        m["dirty"] = scanmap.dirty_of(project, m["name"])        # 有变动、还没扫（走进去再扫）：第二栏标签亮小点
        m["fixed"] = m["name"] in fixed
        m["rules"] = __import__("governance_paths").module_rule(project, m["name"]).is_file()   # 有没有模块戒律（跟着模块走的规矩）
        # 排序：固定的三个在最前；其余设了 ord 的按 ord（比如按写论文的顺序排），没设的起步模块在前、再按加入先后
        m["_k"] = (0, fixed[m["name"]], 0) if m["fixed"] else (1, r["ord"] or 1000 + order.get(m["name"], len(order)), m["id"])
        out.append(m)
    out.sort(key=lambda m: m.pop("_k"))
    return out


def find_module(conn, name: str) -> dict | None:
    r = _folder_rows(conn).get(name.lower())
    return _module(r) if r and not r["gone"] else None


def sync_folders(conn, project: Project) -> None:
    """资料/ 下的文件夹跟库对账：新出现的补一行，不见了的标 gone，回来了取消 gone。都记事件。
    没变化就不拿写锁。"""
    def plan(rows):
        dirs = {d.lower(): d for d in proj.module_dirs(project)}
        add = [d for k, d in dirs.items() if k not in rows]
        gone = [r for k, r in rows.items() if not r["gone"] and k not in dirs]
        back = [r for k, r in rows.items() if r["gone"] and k in dirs]
        return add, gone, back

    if not any(plan(_folder_rows(conn))):
        return
    with tx(conn):
        add, gone, back = plan(_folder_rows(conn))      # 锁里再算一次，别的进程可能刚对过账
        for d in add:
            default = d in proj.DEFAULT_NAMES
            code = _next_code(conn, "X", "module")
            conn.execute(
                "INSERT INTO module(code, name, en, ord, source, created_by, created_at) VALUES(?, ?, ?, 0, ?, ?, ?)",
                (code, d, _default_en(d), "default" if default else "folder",
                 "默认" if default else "文件夹里发现的", now()),
            )
            log(conn, "资料/", "默认模块就位" if default else "发现新文件夹", code, d)
        for r in gone:
            conn.execute("UPDATE module SET gone = 1 WHERE id = ?", (r["id"],))
            log(conn, "资料/", "文件夹不见了", r["code"], r["name"])
        for r in back:
            conn.execute("UPDATE module SET gone = 0 WHERE id = ?", (r["id"],))
            log(conn, "资料/", "文件夹回来了", r["code"], r["name"])


def _next_code(conn, kind_prefix: str, table: str) -> str:
    n = 0
    for (code,) in conn.execute(f"SELECT code FROM {table} WHERE code LIKE ?", (kind_prefix + "-%",)):
        m = re.fullmatch(re.escape(kind_prefix) + r"-(\d+)", code or "")
        if m:
            n = max(n, int(m.group(1)))
    return f"{kind_prefix}-{n + 1:02d}"


def add_module(conn, project: Project, name: str, *, by: str, source: str,
               one_line: str = "", en: str = "") -> dict:
    """人点「＋」和 agent 调 MCP 都走这里：建一个 资料/<名>/ 文件夹，库里记一行，记下是谁加的。

    网页上没有「删模块」：删只能是人把删除指令写进笔记，交给 agent 去做（先存档、挪进回收站）。
    """
    try:
        name = proj.check_name(name)
    except ValueError as e:
        raise Refused(str(e)) from None
    if source not in ("human", "agent"):
        raise ValueError(source)
    sync_folders(conn, project)                          # 先对账：你刚在资源管理器里建的也算数
    with tx(conn):
        dup = find_module(conn, name)
        if dup:
            raise Duplicate(dup)
        code = _next_code(conn, "X", "module")
        conn.execute(
            "INSERT INTO module(code, name, one_line, en, ord, source, created_by, created_at) "
            "VALUES(?, ?, ?, ?, 0, ?, ?, ?)",
            (code, name, one_line.strip(), " ".join((en or "").split())[:40], source, by, now()),
        )
        try:                                             # 在事务里建：建不成就回滚，库里不会多一行空的
            (project.materials / name).mkdir(parents=True, exist_ok=False)
        except OSError as e:
            raise Refused(f"建文件夹 资料/{name}/ 没成功：{e}") from None
        log(conn, by, "加模块", code, name)
    m = get_module(conn, code)
    m.update(proj.module_stats(project, name))
    return m


def set_module_info(conn, name: str, *, by: str, en: str | None = None, one_line: str | None = None) -> dict:
    """设置页改模块的英文名、一句话。改名、删掉不在这——那是挪文件夹，写进笔记交给 agent。扫描在 设置 → 扫描（自动化/扫描规则.md）。"""
    with tx(conn):
        m = find_module(conn, name)
        if not m:
            raise Refused(f"没有「{name}」这个模块")
        sets, vals, said = [], [], []
        if en is not None:
            en = " ".join(en.split())[:40]
            sets.append("en = ?"); vals.append(en); said.append(f"英文名「{en or '（空）'}」")
        if one_line is not None:
            one_line = " ".join(one_line.split())[:120]
            sets.append("one_line = ?"); vals.append(one_line); said.append(f"一句话「{one_line or '（空）'}」")
        if sets:
            conn.execute(f"UPDATE module SET {', '.join(sets)} WHERE id = ?", (*vals, m["id"]))
            log(conn, by, "改模块说明", m["code"], f"{m['name']}：" + "，".join(said))
    return find_module(conn, name)


def set_module_order(conn, project: Project, names: list[str], *, by: str) -> list[str]:
    """设置页排第二栏的顺序。固定的三个永远在最前，不参与排；没列到的排在后面，照旧。"""
    with tx(conn):
        rows = _folder_rows(conn)
        fixed = set(proj.FIXED_NAMES)
        order = [n for n in names if n.lower() in rows and n not in fixed and not rows[n.lower()]["gone"]]
        for i, n in enumerate(order, 1):
            conn.execute("UPDATE module SET ord = ? WHERE id = ?", (i, rows[n.lower()]["id"]))
        log(conn, by, "改模块顺序", None, " · ".join(order))
    return [m["name"] for m in list_folder_modules(conn, project)]


def remove_module(conn, project: Project, name: str, *, by: str, confirm: bool = False) -> dict:
    """删模块：整个文件夹挪进回收站（不是真删，能还原）。空的直接做；有文件要人再确认一次。
    作者 2026-09-25：「比如那个模块的加减之类的，如果模块有文件之类的要出警告，空的就无所谓」。固定的三个不能删。"""
    import trash                                          # 放这里：trash 也 import store
    m = find_module(conn, name)
    if not m:
        raise Refused(f"没有「{name}」这个模块")
    if m["name"] in proj.FIXED_NAMES:
        raise Refused(f"「{m['name']}」是固定模块，不能删")
    d = project.materials / m["name"]
    got = [f for f in d.rglob("*") if f.is_file()] if d.is_dir() else []
    size = sum(f.stat().st_size for f in got)
    if got and not confirm:
        from snapshot import _human
        raise NeedConfirm(f"「{m['name']}」里有 {len(got)} 个文件（{_human(size)}）。整个文件夹挪进回收站吗？回收站里能还原。",
                          {"files": len(got), "bytes": size})
    r = trash.move(conn, project, f"资料/{m['name']}", by=by, reason="设置里删模块", origin="设置里删模块")
    sync_folders(conn, project)
    return {**r, "files": len(got)}


# ---------------------------------------------------------------- 笔记 / 待拍板 / 决定

def _note(r: sqlite3.Row) -> dict:
    d = dict(r)
    d.pop("user_id", None)
    return d


def draft_backups(conn, limit: int = 20) -> list[dict]:
    """草稿留底：新的在前。"""
    return [{"id": r["id"], "text": r["text"], "at": r["created_at"]} for r in conn.execute(
        "SELECT id, text, created_at FROM note WHERE kind = ? ORDER BY id DESC LIMIT ?", (DRAFT_KEEP, limit))]


def get_draft(conn) -> dict:
    r = conn.execute("SELECT text, updated_at FROM note WHERE kind = '草稿' ORDER BY id LIMIT 1").fetchone()
    return {"text": r["text"], "updated_at": r["updated_at"]} if r else {"text": "", "updated_at": None}


DRAFT_KEEP = "草稿留底"


def _big_loss(old: str, new: str) -> bool:
    """这一下少了一大截（清空、整段删掉）？一个字一个字删的不算。"""
    o, n = old.strip(), new.strip()
    return bool(o) and (not n or (len(o) - len(n) >= 10 and len(n) < len(o) * 0.6))


def save_draft(conn, text: str, *, by: str = "人", recorded: bool = False) -> dict:
    """边打字边存。不记事件——一个字一条事件会把日志淹了。
    草稿只有一份、每次覆盖，所以一下子少了一大截（清空、整段删掉）时，旧的先留一份「草稿留底」，能找回来
    （作者 09-29：「系统稳定之后不能有这种bug」）；刚「记下」的不用留——已经在笔记本里了。"""
    with tx(conn):
        r = conn.execute("SELECT id, text FROM note WHERE kind = '草稿' ORDER BY id LIMIT 1").fetchone()
        if r and not recorded and _big_loss(r["text"] or "", text):
            conn.execute("INSERT INTO note(kind, text, created_by, created_at, updated_at) VALUES(?, ?, ?, ?, ?)",
                         (DRAFT_KEEP, r["text"], by, now(), now()))
        if r:
            conn.execute("UPDATE note SET text = ?, updated_at = ? WHERE id = ?", (text, now(), r["id"]))
        else:
            conn.execute("INSERT INTO note(kind, text, created_by, created_at, updated_at) VALUES('草稿', ?, ?, ?, ?)",
                         (text, by, now(), now()))
    return get_draft(conn)


def export_instruction(conn, text: str, *, by: str = "人") -> dict:
    """人点了「复制为 agent 指令」。留一份，三个月后还知道当时让 agent 干了什么。"""
    if not text.strip():
        raise Refused("指令是空的")
    with tx(conn):
        nid = conn.execute(
            "INSERT INTO note(kind, text, created_by, created_at, updated_at) VALUES('指令', ?, ?, ?, ?)",
            (text, by, now(), now()),
        ).lastrowid
        log(conn, by, "导出指令", None, text.splitlines()[0][:60] if text else "")
    return _note(conn.execute("SELECT * FROM note WHERE id = ?", (nid,)).fetchone())


def list_instructions(conn, limit: int = 5) -> list[dict]:
    return [_note(r) for r in conn.execute(
        "SELECT * FROM note WHERE kind = '指令' ORDER BY id DESC LIMIT ?", (limit,))]


def ask_human(conn, question: str, *, by: str, context: str = "") -> dict:
    """agent 有事要人定：写进网页，不打断人。人攒着一起拍板。"""
    question = question.strip()
    if not question:
        raise Refused("问题是空的")
    with tx(conn):
        dup = conn.execute("SELECT * FROM note WHERE kind = '待拍板' AND closed_at IS NULL AND text = ?",
                           (question,)).fetchone()
        if dup:
            return _note(dup)
        code = _next_code(conn, "D", "note")
        conn.execute(
            "INSERT INTO note(kind, code, text, detail, created_by, created_at, updated_at) "
            "VALUES('待拍板', ?, ?, ?, ?, ?, ?)",
            (code, question, context.strip(), by, now(), now()),
        )
        log(conn, by, "提问", code, question[:60])
    return _note(conn.execute("SELECT * FROM note WHERE code = ?", (code,)).fetchone())


def withdraw(conn, code: str, why: str, *, by: str) -> bool:
    """问的人自己收回一条还没人答的「待拍板」（比如监管发现是自己报错了）：关掉、写明为什么，不算人拍过板。"""
    q = conn.execute("SELECT * FROM note WHERE code = ? AND kind = '待拍板' AND closed_at IS NULL", (code,)).fetchone()
    if not q:
        return False
    conn.execute("UPDATE note SET closed_at = ?, ref = ?, detail = ?, updated_at = ? WHERE code = ?",
                 (now(), "收回", ((q["detail"] or "") + f"\n\n收回：{why}").strip(), now(), code))
    log(conn, by, "收回问题", code, why[:60])
    return True


def answer(conn, code: str, text: str, *, by: str = "人") -> dict:
    """人拍板：待拍板关掉，生成一条决定。"""
    text = text.strip()
    if not text:
        raise Refused("拍板要写点什么")
    with tx(conn):
        q = conn.execute("SELECT * FROM note WHERE code = ? AND kind = '待拍板'", (code,)).fetchone()
        if not q:
            raise Refused(f"没有 {code} 这个待拍板")
        if q["closed_at"]:
            raise Refused(f"{code} 已经拍过板了（{q['ref']}）")
        a = _next_code(conn, "A", "note")
        conn.execute(
            "INSERT INTO note(kind, code, text, detail, ref, created_by, created_at, updated_at) "
            "VALUES('决定', ?, ?, ?, ?, ?, ?, ?)",
            (a, text, q["text"], code, by, now(), now()),
        )
        conn.execute("UPDATE note SET closed_at = ?, ref = ?, updated_at = ? WHERE code = ?", (now(), a, now(), code))
        log(conn, by, "拍板", a, f"{code} → {text[:60]}")
    return _note(conn.execute("SELECT * FROM note WHERE code = ?", (a,)).fetchone())


# ---------------------------------------------------------------- 你问 agent
# 作者 2026-09-27：「我觉得问答需要两个模块，一个是agent不懂的问人，一个是人不懂的问机器人」。
# 跟「待拍板 D → 决定 A」对着：你问的 问-01（kind 人问，detail 写出处）→ agent 答的 答-01（kind 机答，ref 指回去）。
# agent 下一次看全貌（get_overview）时看到，先答再干活；网页不替它答（项-2）。

def ask_agent(conn, question: str, *, by: str = "人", where: str = "") -> dict:
    question = question.strip()
    if not question:
        raise Refused("问题是空的")
    with tx(conn):
        code = _next_code(conn, "问", "note")
        conn.execute(
            "INSERT INTO note(kind, code, text, detail, created_by, created_at, updated_at) VALUES('人问', ?, ?, ?, ?, ?, ?)",
            (code, question, where.strip(), by, now(), now()),
        )
        log(conn, by, "问 agent", code, question[:60])
    return _note(conn.execute("SELECT * FROM note WHERE code = ?", (code,)).fetchone())


def answer_person(conn, code: str, text: str, *, by: str) -> dict:
    """agent 答人问的：生成一条「机答」，那条问题关掉。"""
    text = text.strip()
    if not text:
        raise Refused("答案是空的")
    with tx(conn):
        q = conn.execute("SELECT * FROM note WHERE code = ? AND kind = '人问'", (code,)).fetchone()
        if not q:
            raise Refused(f"没有 {code} 这个问题")
        if q["closed_at"]:
            raise Refused(f"{code} 已经答过了（{q['ref']}）")
        a = _next_code(conn, "答", "note")
        conn.execute(
            "INSERT INTO note(kind, code, text, detail, ref, created_by, created_at, updated_at) VALUES('机答', ?, ?, ?, ?, ?, ?, ?)",
            (a, text, q["text"], code, by, now(), now()),
        )
        conn.execute("UPDATE note SET closed_at = ?, ref = ?, updated_at = ? WHERE code = ?", (now(), a, now(), code))
        log(conn, by, "答人问", a, f"{code} → {text[:60]}")
    return _note(conn.execute("SELECT * FROM note WHERE code = ?", (a,)).fetchone())


def list_asked(conn) -> list[dict]:
    """你问 agent 的：还没答的在前；答了的带上答案。"""
    ans = {r["ref"]: _note(r) for r in conn.execute("SELECT * FROM note WHERE kind = '机答'")}
    out = [_note(r) | {"answer": ans.get(r["code"])} for r in conn.execute("SELECT * FROM note WHERE kind = '人问' ORDER BY id DESC")]
    out.sort(key=lambda q: q["closed_at"] is not None)
    return out


def list_pending(conn) -> list[dict]:
    return [_note(r) for r in conn.execute(
        "SELECT * FROM note WHERE kind = '待拍板' AND closed_at IS NULL ORDER BY id DESC")]


def list_decisions(conn, limit: int = 20) -> list[dict]:
    return [_note(r) for r in conn.execute(
        "SELECT * FROM note WHERE kind = '决定' ORDER BY id DESC LIMIT ?", (limit,))]


def recent_events(conn, limit: int = 50) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, at, actor, action, target, detail FROM event ORDER BY id DESC LIMIT ?", (limit,))]


# ---------------------------------------------------------------- 整页状态

def get_state(conn, project: Project) -> dict:
    """网页一次拿全。数都从库和磁盘现算，一个都不手写。"""
    import intake                                        # 放这里：intake 也 import store，顶上引会绕圈
    import runs                                          # 同上
    import snapshot                                      # 同上
    import panorama
    bp = blueprint.pyramid(project)                     # 蓝图：资料/蓝图/ 里的 S0、S1，现读
    sync_folders(conn, project)
    intake.sync(conn, project)
    modules = list_folder_modules(conn, project)
    pending = list_pending(conn)
    save = snapshot.latest(project)
    scene = panorama.build(project, bp, modules, pending, save)
    problems = list(bp["problems"])
    for m in modules:
        problems += proj.read_links(project, m["name"])[1]
    return {
        "v": version(conn),
        "project": {
            "name": _meta(conn, "project_name") or project.root.name,
            "one_line": (bp["s0"] or {}).get("one_line") or _meta(conn, "project_one_line") or "",   # S0 那句
            "root": str(project.root),
        },
        "problems": problems + scene["problems"],
        "panorama": scene,                                # 蓝图统一入口；旧字段与接口保持兼容
        "counts": bp["counts"],                          # 蓝图里的 S2 各种状态有几个
        "s0": bp["s0"],                                  # 终极目标
        "blueprint": bp["goals"],                        # S1 那一层，每个带底下的 S2：总览「④ 蓝图」表
        "module_blueprint": bp["modules"],               # 各模块自己的蓝图（模块装修）：总览表里接在 S1 后面
        "modules": modules,                              # 文件夹模块：中间那条 + 各自一页
        "pending": pending,
        "decisions": list_decisions(conn),
        "note": get_draft(conn),
        "inbox": len(intake.waiting(conn)),              # 外部资料入口还有几个没分拣
        "auto": runs.latest(project),                    # 自动化：最近一次运行（总览顶上那一行）
        "save": save,                                    # 存档：最近一档
        "auto_settings": runs.settings(conn),            # 档位、每次最多几圈
        "materials": {
            "exists": project.materials.is_dir(),
            "total": sum(m["files"] for m in modules),
        },
    }
