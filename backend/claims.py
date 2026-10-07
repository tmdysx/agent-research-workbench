"""分工：多个 agent 一起干，谁在干哪件（正本见 自动化/协议.md）。

作者 2026-09-30：「这样到时候你就可以开多个智能体按照相关要求开工这样速度就更快了，也能让codex也加入一起开发」。
- 领一件：蓝图里的一件（目标 + S2）同一时间只给一个 agent
- 一条道一个人：同一个模块同一时间只给一个 agent（模块蓝图的件，道就是模块名；总蓝图的件，道是 S1 写的「动到的模块」，
  没写就是这一件自己）——几个人同时改同一批文件最容易撞；改核心文件另有核心锁管
- 核心锁：改核心（backend/、模板.html、界面脚本、启动器）先拿，一次一个人
- 认领存在库里：查和写在同一个写锁里做（BEGIN IMMEDIATE），两个 agent 同时抢也只有一个拿到
- 2 小时没动静（没报一圈、没交付、没再领）就算放手，别人能接；agent 每用一次这些工具就续上
"""
from __future__ import annotations

import time

import store

TTL = 2 * 3600                       # 默认；设置里「领着活多久没动静算放手」能改（knobs.release_min）
CORE = "核心"
_TABLE = """CREATE TABLE IF NOT EXISTS claim(
    goal   TEXT NOT NULL,
    sub    TEXT NOT NULL,
    agent  TEXT NOT NULL,
    lanes  TEXT NOT NULL,          -- 占着的道，顿号隔开（模块名 / S1 编号 / 核心）
    what   TEXT NOT NULL DEFAULT '',
    since  TEXT NOT NULL,
    beat   REAL NOT NULL,          -- 最后一次有动静（秒）
    PRIMARY KEY(goal, sub)
)"""


def _ensure(conn) -> None:
    conn.execute(_TABLE)


def _rows(conn) -> list[dict]:
    _ensure(conn)
    return [dict(r) | {"lanes": [x for x in r["lanes"].split("、") if x]} for r in conn.execute("SELECT * FROM claim ORDER BY since")]


def ttl(conn) -> int:
    """多久没动静算放手（秒）：照设置（S1-8 S2-57），读不了用默认 2 小时。"""
    try:
        import knobs
        return int(knobs.get(conn, "release_min")) * 60
    except Exception:
        return TTL


def _purge(conn) -> None:
    conn.execute("DELETE FROM claim WHERE beat < ?", (time.time() - ttl(conn),))


def active(conn) -> list[dict]:
    """还在做的（2 小时内有动静的），先领的在前。"""
    _ensure(conn)
    cut = time.time() - ttl(conn)
    return [r | {"idle": int(time.time() - r["beat"])} for r in _rows(conn) if r["beat"] >= cut]


def lanes_of(g: dict, x: dict | None = None) -> list[str]:
    """一件占哪几条道：模块蓝图 → 模块名；总蓝图 S1 → 它「动到的模块」，没写就是这一件自己（如「S1-8 S2-12」）。
    改核心文件另有核心锁管，所以同一个 S1 里不同的件能几个人同时做。"""
    if g.get("kind") == "module":
        return [g["code"]]
    return list(g.get("modules") or []) or [f"{g['code']} {x['code']}" if x else g["code"]]


def claim(conn, goal: str, sub: str, agent: str, lanes: list[str], what: str = "") -> dict:
    """领一件。同一件别人在做、或它的道上有别人：拒（store.Refused，写清是谁）。自己领过的：续上。"""
    agent = (agent or "").strip() or "agent"
    lanes = [x for x in dict.fromkeys(lanes) if x]
    _ensure(conn)
    with store.tx(conn):
        _purge(conn)
        mine = conn.execute("SELECT * FROM claim WHERE goal = ? AND sub = ?", (goal, sub)).fetchone()
        if mine and mine["agent"] != agent:
            raise store.Refused(f"{goal} {sub} 已经是 {mine['agent']} 在做（{mine['since'][5:16].replace('T', ' ')} 领的）")
        for r in conn.execute("SELECT * FROM claim WHERE agent != ?", (agent,)):
            hit = set(r["lanes"].split("、")) & set(lanes)
            if hit:
                raise store.Refused(f"「{'、'.join(sorted(hit))}」这条道上 {r['agent']} 在做 {r['goal']} {r['sub']}".rstrip()
                                    + "：一条道同一时间只给一个人，换一件")
        now = time.time()
        if mine:
            conn.execute("UPDATE claim SET beat = ? WHERE goal = ? AND sub = ?", (now, goal, sub))
        else:
            conn.execute("INSERT INTO claim(goal, sub, agent, lanes, what, since, beat) VALUES(?, ?, ?, ?, ?, ?, ?)",
                         (goal, sub, agent, "、".join(lanes), what, store.now(), now))
            store.log(conn, agent, "领了", f"{goal} {sub}".strip(), "、".join(lanes))
    return next(r for r in active(conn) if r["goal"] == goal and r["sub"] == sub)


def release(conn, goal: str, sub: str, agent: str = "", note: str = "") -> bool:
    """放手。给了 agent：只放自己的。返回放没放。"""
    _ensure(conn)
    with store.tx(conn):
        r = conn.execute("SELECT agent FROM claim WHERE goal = ? AND sub = ?", (goal, sub)).fetchone()
        if r is None or (agent and r["agent"] != agent):
            return False
        conn.execute("DELETE FROM claim WHERE goal = ? AND sub = ?", (goal, sub))
        store.log(conn, r["agent"], "放手", f"{goal} {sub}".strip(), note or None)
    return True


def take_core(conn, agent: str, why: str = "") -> dict:
    """核心锁：一次一个人。"""
    return claim(conn, CORE, "", agent, [CORE], why)


def holds_core(conn, agent: str) -> bool:
    return any(r["goal"] == CORE and r["agent"] == agent for r in active(conn))


def beat(conn, agent: str) -> None:
    """这个 agent 有动静：它领着的都续上。"""
    _ensure(conn)
    with store.tx(conn):
        conn.execute("UPDATE claim SET beat = ? WHERE agent = ?", (time.time(), agent))


def of(conn, agent: str) -> list[dict]:
    return [r for r in active(conn) if r["agent"] == agent]
