"""设置里的自动化档位和存档（S1-8 S2-57、S2-59；需-28）：这些数存在项目库的 meta 里，别的模块从这取，不再写死。

作者 10-03：「就是自动化的程度吧，有档位，一个是单agent，单存档，自动按照蓝图需求任务一个个跑，高档位就是，同时开多个agent，
多个节点多个分支一起做项目，然后优中选优……还有存档可以设计成最多存多少档，默认如何存档等等，可以自定义多一点」。
- 自动化四档：1 一条线 · 2 主干上几个人 · 3 分枝并行 · 4 优中选优；选一档把「同时最多几个、每件几根枝」一起填好，每个数还能自己调
- 存档：最多存几档、自动存的另留几个、什么时候自动存、自动定性、空间上限、世界树的几样
- 网页上改 = 人改（记日志）；agent 不能改（G1 代改走 configure_automation）
- 不同的数用不同的 meta 键；以前就有的三个（auto_launch_max、auto_rounds）照旧用原来的键
"""
from __future__ import annotations

import sqlite3

import store
from project import Project

LEVELS = {1: "一条线", 2: "主干上几个人", 3: "分枝并行", 4: "优中选优"}
LEVEL_SAYS = {1: "一个 agent，主干上一条存档线，照蓝图顺序一件件做",
              2: "几个 agent 在主干上各领不同的件（一条道一个人，改核心排队）",
              3: "能做的件各长一根枝，一个人上去做；结了果，验收过了合回主干",
              4: "同一件长几根枝，几个人各做一版；都结了果，挑最好的一根合回，其余砍掉"}
PRESETS = {1: {"max_agents": 1, "per_item": 1}, 2: {"max_agents": 3, "per_item": 1},
           3: {"max_agents": 3, "per_item": 1}, 4: {"max_agents": 4, "per_item": 2}}
SCOPES = ("全部", "动到核心的")
PICKERS = ("验收的员工", "按检查自动挑", "G1", "你")
AFTER = ("直接合", "等你点")
WT_AFTER = ("挪进 .回收", "留在原处")

# 名字: (meta 键, 默认, 类型, 能取的值——元组是只能选这几个、列表 [小, 大] 是范围)
SPEC: dict[str, tuple] = {
    # 自动化
    "level": ("auto_mode", 2, int, list(LEVELS)),
    "max_agents": ("auto_launch_max", 3, int, [1, 12]),
    "per_item": ("auto_per_item", 1, int, [1, 4]),
    "compare_wait_h": ("auto_compare_wait_h", 4, int, [1, 72]),
    "branch_scope": ("auto_branch_scope", "全部", str, SCOPES),
    "picker": ("auto_picker", "验收的员工", str, PICKERS),
    "after_pick": ("auto_after_pick", "直接合", str, AFTER),
    "rounds": ("auto_rounds", 5, int, [1, 50]),
    "cooldown_min": ("auto_cooldown_min", 10, int, [1, 240]),
    "stuck_boss_min": ("auto_stuck_boss_min", 30, int, [5, 720]),
    "stuck_human_min": ("auto_stuck_human_min", 60, int, [5, 1440]),
    "release_min": ("auto_release_min", 120, int, [10, 2880]),
    # 存档
    "keep": ("ckpt_keep", 10, int, [0, 500]),                      # 0 = 不限
    "keep_auto": ("ckpt_keep_auto", 5, int, [0, 200]),
    "on_core": ("ckpt_on_core", True, bool, None),
    "on_deliver": ("ckpt_on_deliver", True, bool, None),
    "every_h": ("ckpt_every_h", 0, int, (0, 1, 2, 4, 8, 12, 24)),
    "auto_settle": ("ckpt_auto_settle", False, bool, None),
    "cap_gb": ("ckpt_cap_gb", 20, int, [0, 2000]),                  # 0 = 不限
    "wt_max": ("wt_max", 6, int, [1, 40]),
    "wt_dir": ("wt_dir", "", str, None),                            # 空 = 项目旁边「<项目名> 世界树」
    "wt_after": ("wt_after", "挪进 .回收", str, WT_AFTER),
    "wt_recycle_days": ("wt_recycle_days", 14, int, [1, 365]),
    # 清理（S1-8 S2-61；需-29）
    "archive_days": ("tidy_archive_days", 14, int, [1, 365]),
    "archive_auto": ("tidy_archive_auto", False, bool, None),
    "tidy_every_days": ("tidy_every_days", 7, int, (0, 1, 3, 7, 14, 30)),
    "long_kb": ("tidy_long_kb", 30, int, [5, 1000]),
    "digest_by": ("tidy_digest_by", "规划的员工", str, ("规划的员工", "G1")),
    "keep_recent": ("tidy_keep_recent", 30, int, [5, 200]),
    "now_days": ("tidy_now_days", 1, int, [1, 30]),
    "rewrite_auto": ("tidy_rewrite_auto", True, bool, None),       # 作者 10-03「我的想法是重铸由agent来做」：查乱报的自动派
}
AUTO = ("level", "max_agents", "per_item", "compare_wait_h", "branch_scope", "picker", "after_pick", "rounds", "cooldown_min",
        "stuck_boss_min", "stuck_human_min", "release_min")
SAVES = ("keep", "keep_auto", "on_core", "on_deliver", "every_h", "auto_settle", "cap_gb", "wt_max", "wt_dir", "wt_after", "wt_recycle_days")
TIDY = ("archive_days", "archive_auto", "tidy_every_days", "long_kb", "digest_by", "keep_recent", "now_days", "rewrite_auto")


def _cast(name: str, raw):
    key, default, kind, _ = SPEC[name]
    if raw is None or raw == "":
        return default
    try:
        if kind is bool:
            return str(raw).strip().lower() in ("1", "true", "开", "on", "yes")
        return kind(raw)
    except (TypeError, ValueError):
        return default


def get(conn, name: str):
    try:
        raw = store._meta(conn, SPEC[name][0])
    except sqlite3.OperationalError:                      # 还没建表的新库
        raw = None
    return _cast(name, raw)


_PEEK: dict = {}


def peek(p: Project, name: str):
    """没有现成连接时（比如算世界树放哪、派活时看档位）：开一下这个项目的库读一个数，读不了用默认。两秒内读过的直接用。"""
    import time
    hit = _PEEK.get((str(p.db_path), name))
    if hit and time.time() - hit[0] < 2:
        return hit[1]
    v = _peek(p, name)
    _PEEK[(str(p.db_path), name)] = (time.time(), v)
    return v


def _peek(p: Project, name: str):
    try:
        if not p.db_path.is_file():
            return SPEC[name][1]
        c = store.connect(p.db_path)
        try:
            return get(c, name)
        finally:
            c.close()
    except Exception:
        return SPEC[name][1]


def _check(name: str, v):
    _, _, kind, allow = SPEC[name]
    if kind is bool:
        return bool(v)
    if kind is int:
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise store.Refused(f"「{name}」要写数字") from None
    if kind is str:
        v = " ".join(str(v or "").split())
    if isinstance(allow, tuple) and v not in allow:
        raise store.Refused(f"「{name}」只能是 {' / '.join(map(str, allow))}")
    if isinstance(allow, list) and len(allow) == 2 and not allow[0] <= v <= allow[1]:
        raise store.Refused(f"「{name}」要在 {allow[0]}～{allow[1]} 之间")
    if isinstance(allow, list) and len(allow) > 2 and v not in allow:
        raise store.Refused(f"「{name}」只能是 {' / '.join(map(str, allow))}")
    return v


def _consistent(d: dict) -> None:
    if not d["stuck_boss_min"] <= d["stuck_human_min"] <= d["release_min"]:
        raise store.Refused("没动静的时间要「报上级 ≤ 告诉你 ≤ 算放手」")
    if d["level"] == 1 and d["max_agents"] != 1:
        raise store.Refused("档位 1 一条线只开 1 个 agent；要几个人一起做选档位 2 以上")
    if d["level"] == 4 and d["per_item"] < 2:
        raise store.Refused("档位 4 优中选优每件至少 2 根枝")
    if d["level"] in (2, 3) and d["per_item"] != 1:
        raise store.Refused("每件几根枝只在档位 4 优中选优里有用")


def all_auto(conn) -> dict:
    d = {k: get(conn, k) for k in AUTO}
    pre = PRESETS[d["level"]]
    d["custom"] = any(d[k] != v for k, v in pre.items())
    return d


def all_saves(conn) -> dict:
    return {k: get(conn, k) for k in SAVES}


def set_many(conn, patch: dict, *, by: str = "人") -> dict:
    """改几个数。带了 level 又没带同时最多几个 / 每件几根：照那一档填好。→ 改完的全部。"""
    patch = {k: v for k, v in (patch or {}).items() if k in SPEC}
    if not patch:
        raise store.Refused("没有要改的")
    new = {k: _check(k, v) for k, v in patch.items()}
    if "level" in new:
        for k, v in PRESETS[new["level"]].items():
            new.setdefault(k, v)
    merged = {k: get(conn, k) for k in AUTO} | {k: v for k, v in new.items() if k in AUTO}
    _consistent(merged)
    old = {k: get(conn, k) for k in new}
    _PEEK.clear()
    with store.tx(conn):
        for k, v in new.items():
            store._set_meta(conn, SPEC[k][0], ("1" if v else "0") if SPEC[k][2] is bool else str(v))
        changed = {k: (old[k], v) for k, v in new.items() if old[k] != v}
        if changed:
            store.log(conn, by, "改了设置", "自动化和存档", "；".join(f"{k}: {a} → {b}" for k, (a, b) in changed.items())[:500])
    return {"auto": all_auto(conn), "saves": all_saves(conn), "tidy": {k: get(conn, k) for k in TIDY}, "changed": list(changed)}


def describe() -> dict:
    """网页画设置用：四档、每档填什么、各项能取的值。"""
    return {"levels": [{"level": k, "name": v, "says": LEVEL_SAYS[k], "preset": PRESETS[k]} for k, v in LEVELS.items()],
            "allow": {k: (list(a) if isinstance(a, (tuple, list)) else None) for k, (_, _, _, a) in SPEC.items()},
            "defaults": {k: d for k, (_, d, _, _) in SPEC.items()}}
