"""agent 档案：报到、编号 G、职责跟着项目变（正本见 自动化/协议.md「报到和档案」）。

作者 2026-09-30：「我觉得得给agent注册，就是一个agent刚刚接手的时候，要有一个注册档案和编号，职责啥的都可以随着项目变迁」；
「agent可以让人自定义……我还是想让玩家可以自己动手diy」。
- 一个 agent 一个文件：`自动化/agent/G1 claude-code.md`——开头几行（编号 · 名字 · 用什么 · 一句话 · 报到 · 管哪些 · 不碰 ·
  改核心 · 技能 · 开工的话）+ 正文「交代」+ 最下面「变迁」（只增：每次改记 何时 · 谁 · 改了什么 · 为什么）
- 编号 G 号不回收；认人靠名字（agent 调接口报的名字：claude-code、codex、claude-code#2），同名再来接上原档案
- 没报到的领不到活（dispatch、MCP 查 require）；「管哪些」空着 = 都能领；「不碰」的不给；「改核心」不能的拿不到核心锁
- 人能提前建、改、复制、删（进回收站）；agent 能改自己的一句话、交代这些，「改核心」那格只有人改
- 名册、一件的时间线：从已有的记录现算（档案、库里的动静、认领、交付单、本机 git），不另存
- 分工（S1-8 S2-38，样图 R3；作者 10-02「agent的管理……也要有层级，等级和分工……有的agent负责做规划蓝图，有的负责审阅有的负责验收」）：
  岗位 规划 · 审核 · 干活 · 验收 · 带队（能兼，没写算干活）· 等级 见习 · 正式 · 资深（没写算正式）· 上级（别的 agent 或「人」，一棵树）；
  这三格只有人改。参考三省六部（规划 → 审核能打回 → 派活 → 干活）和 Paperclip（职位、每人一个上级），界面上只说规划、审核这些
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import atomic
import claims
import store
from project import Project
from skills import frontmatter

DIR = Path("自动化") / "agent"
_G = re.compile(r"G(\d+)")
FIELDS = [("code", "编号"), ("name", "名字"), ("program", "用什么"), ("line", "一句话"), ("joined", "报到"),
          ("roles", "岗位"), ("level", "等级"), ("boss", "上级"),
          ("crafts", "工种"), ("scope", "管哪些"), ("avoid", "不碰"), ("core", "改核心"),
          ("auto", "自动运行"), ("plan_required", "计划审核"), ("paused", "暂停"),
          ("skills", "技能"), ("opener", "开工的话")]
LISTS = ("roles", "crafts", "scope", "avoid", "skills")
SWITCHES = ("auto", "plan_required", "paused")
EDIT = ("program", "line", "roles", "level", "boss", "crafts", "scope", "avoid", "core", *SWITCHES, "skills", "opener", "brief")
HUMAN_ONLY = ("core", "roles", "level", "boss", "crafts", "scope", "avoid", *SWITCHES)
CRAFTS = ("程序", "网页", "文档", "翻译", "优化")
ROLES = ("规划", "审核", "干活", "验收", "带队")
LEVELS = ("见习", "正式", "资深")
HUMAN = "人"                                            # 上级写「人」= 直接向你汇报
DUTY = {"规划": "把需求拆成蓝图里的件（做什么 · 为了 · 怎么验）、写计划；只起草（propose_draft），进正式文件要审过、人点「行」",
        "审核": "看规划起草的件和计划：准，或打回写清理由；不审自己写的",
        "干活": "领件、做、照「怎么验」验、交付单",
        "验收": "复跑别人交付单里的检查、看东西对不对：过就做完，不过打回写清哪条；不验自己干的",
        "带队": "下面的人卡住了先报给你：去看看、帮一把，或让它放手换人"}
LABEL = dict(FIELDS) | {"brief": "交代"}
YES, NO = "能", "不能"
BUSY, STALL = 30 * 60, claims.TTL                        # 30 分钟内有动静 = 在干活；到 2 小时 = 停了；再久认领自动放掉

TEMPLATES = {                                           # 「＋ 新建 agent」从这几个样子开始（按岗位），都能再改
    "规划的": {"line": "把需求拆成蓝图里的件、写计划，只起草", "core": NO, "roles": ["规划"],
             "brief": "- 职责：照需求、想法把蓝图里还缺的件起草出来（做什么 · 为了哪条需求 · 怎么验，验要机器查得了），写计划\n- 做事：只用 propose_draft 起草，不直接改正式文件；审核打回了照理由改同一张\n- 不改程序"},
    "审核的": {"line": "审规划起草的件和计划：准或打回写理由", "core": NO, "roles": ["审核"],
             "brief": "- 职责：看草稿区里别人起草的件和计划：为了哪条需求对不对、怎么验机器查不查得了、有没有跑出方向\n- 准就写一句为什么准；打回写清哪里不行、怎么改；不审自己写的\n- 不改程序、不改正式文件"},
    "写代码的": {"line": "写程序、改网页，照测试验", "core": YES, "roles": ["干活"],
               "brief": "- 职责：照蓝图里的件改程序和网页；改之前先拿核心锁、存一档核心\n- 做事：先写计划，小步改，改完跑测试\n- 交东西：交付单写清跑了哪些测试、结果原样抄"},
    "写文档的": {"line": "写说明、计划、交接单，不改程序", "core": NO, "roles": ["干活"],
               "brief": "- 职责：写使用说明、计划、交接单、工具卡、插件说明\n- 做事：说人话，术语放括号；照作者原话数一遍再交\n- 不改 backend/、模板.html 这些程序文件"},
    "验收的": {"line": "复跑别人交付单里的检查，过或打回写清哪条", "core": NO, "roles": ["验收"],
             "brief": "- 职责：验别人交的交付单，照上面写的检查一条条自己再跑一遍、看东西对不对\n- 过了写一句看到了什么；没过写清哪条、实际看到什么，打回给干活的；不验自己干的\n- 不改别人做的东西"},
    "空白": {"line": "", "core": YES, "brief": ""},
}
OLD_TEMPLATES = {"复查的": "验收的"}                     # 以前的样子名


def short(agent: str) -> str:
    """「agent:claude-code」→「claude-code」：档案里的名字不带前缀；以前有的记录把备注写在名字后面的括号里（「claude-code（作者 09-30：只存核心）」），不算名字。"""
    a = " ".join((agent or "").split())
    a = a[6:] if a.startswith("agent:") else a
    a = re.sub(r"-mcp-client$", "", a)                # Codex 连上来自报「codex-mcp-client」：就是 codex
    return re.split(r"[（(]", a, maxsplit=1)[0].strip()


def actor(name: str) -> str:
    return "agent:" + short(name)


def _dir(p: Project) -> Path:
    return p.root / DIR


def _flat(s) -> str:
    return " ".join(str(s or "").split())


def _split(v) -> list[str]:
    if isinstance(v, (list, tuple)):
        v = "、".join(str(x) for x in v)
    return list(dict.fromkeys(x for x in (_flat(x) for x in re.split(r"[、，,]", v or "")) if x))


def _on(value) -> bool:
    return value is True or str(value or "").strip().lower() in ("开", "是", "能", "on", "true", "1", "启用")


def _parse(f: Path) -> dict | None:
    text = f.read_text(encoding="utf-8", errors="replace")
    fm = frontmatter(text)
    m = _G.fullmatch(fm.get("编号", ""))
    if not m or not fm.get("名字"):
        return None
    a = {k: fm.get(w, "") for k, w in FIELDS} | {"n": int(m.group(1)), "file": f.name}
    for k in LISTS:
        a[k] = _split(a[k])
    for k in SWITCHES:
        a[k] = _on(a[k])
    a["core"] = NO if a["core"] == NO else YES
    a["roles"] = [r for r in a["roles"] if r in ROLES]
    a["level"] = a["level"] if a["level"] in LEVELS else "正式"
    a["boss"] = a["boss"] or HUMAN
    body = text[text.find("\n---", 3) + 4:] if text.startswith("---") else text
    sec, cur = {"交代": [], "变迁": []}, None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip() if line[3:].strip() in sec else None
        elif line.startswith("# "):
            continue
        elif cur:
            sec[cur].append(line)
    a["brief"] = "\n".join(sec["交代"]).strip()
    a["history"] = [x[2:].strip() for x in sec["变迁"] if x.startswith("- ")]
    # 旧档案、用户 DIY 的附加字段和非标准历史备注不能在改一格时消失。
    a["_extra_frontmatter"] = {k: v for k, v in fm.items() if k not in dict(FIELDS).values()}
    a["_history_body"] = "\n".join(sec["变迁"]).strip()
    a["_history_count"] = len(a["history"])
    extra, current = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip() not in sec
        if current:
            extra.append(line)
    a["_extra_body"] = "\n".join(extra).strip()
    return a


def _text(a: dict) -> str:
    head = [f"{w}: {_flat('、'.join(a.get(k) or []) if k in LISTS else ('开' if a.get(k) else '关') if k in SWITCHES else a.get(k, ''))}".rstrip() for k, w in FIELDS]
    head += [f"{k}: {v}" for k, v in a.get("_extra_frontmatter", {}).items()]
    out = ["---", *head, "---", f"# {a['code']} {a['name']}", "", "## 交代", ""]
    out += [a["brief"].strip(), ""] if a.get("brief", "").strip() else []
    out += ["## 变迁", ""]
    if a.get("_history_body"):
        out += [a["_history_body"], *[f"- {x}" for x in a.get("history", [])[a.get("_history_count", 0):]]]
    else:
        out += [f"- {x}" for x in a.get("history", [])]
    if a.get("_extra_body"):
        out += ["", a["_extra_body"]]
    return "\n".join(out).rstrip("\n") + "\n"


def _write(p: Project, a: dict) -> dict:
    d = _dir(p)
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]', "-", a["name"]).strip() or "未命名"
    f = d / f"{a['code']} {safe}.md"
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(_text(a), encoding="utf-8")
    atomic.replace(tmp, f)
    a["file"] = f.name
    return a


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- 读

def list_all(p: Project) -> list[dict]:
    d = _dir(p)
    out = [a for f in d.glob("G*.md") if (a := _parse(f))] if d.is_dir() else []
    return sorted(out, key=lambda a: a["n"])


def find(p: Project, key: str) -> dict | None:
    """按编号（G1）或名字（claude-code / agent:claude-code）找。"""
    k = short(key)
    return next((a for a in list_all(p) if a["code"] == k or a["name"] == k), None)


def get(p: Project, key: str) -> dict:
    a = find(p, key)
    if a is None:
        raise store.Refused(f"没有 agent 档案 {key}")
    return a


def jobs(a: dict | None) -> list[str]:
    """它的岗位：没写算干活（以前的档案都是干活的）。"""
    return (a or {}).get("roles") or ["干活"]


def boss_name(p: Project, boss: str) -> str:
    if not boss or boss == HUMAN:
        return "你"
    b = find(p, boss)
    return f"{b['code']} {b['name']}" if b else boss


def require(p: Project, agent: str) -> dict:
    """领活前查：没报到的领不到（作者 09-30：「得给agent注册」）。"""
    a = find(p, agent)
    if a is None:
        raise store.Refused(f"「{short(agent)}」还没报到：先调 register_agent（名字、用的哪家、一句话自己是干什么的），"
                            "拿到编号和档案再领活；人也可以先在「自动化 → Agent 管理」给你建好")
    return a


# ---------------------------------------------------------------- 写

def _next(conn, p: Project) -> str:
    n = int(store._meta(conn, "agent_seq") or 0)
    n = max([n] + [a["n"] for a in list_all(p)]) + 1
    store._set_meta(conn, "agent_seq", str(n))
    return f"G{n}"


def _new(conn, p: Project, name: str, fields: dict, by: str, what: str) -> dict:
    name = short(name)
    if not name or name == "agent":
        raise store.Refused("要写一个名字：你调接口时报的名字，如 codex、claude-code#2")
    if re.search(r'[\\/:*?"<>|]', name):
        raise store.Refused('名字里不能有 \\ / : * ? " < > |')
    with store.tx(conn):
        if find(p, name):
            raise store.Refused(f"「{name}」已经有档案了：{find(p, name)['code']}")
        a = {k: "" for k, _ in FIELDS} | {"brief": "", "history": []}
        a |= {k: v for k, v in fields.items() if k in EDIT}
        for k in LISTS:
            a[k] = _split(a.get(k, ""))
        for k in SWITCHES:
            a[k] = _on(a.get(k))
        if any(c not in CRAFTS for c in a["crafts"]):
            raise store.Refused(f"工种只能是 {' · '.join(CRAFTS)}")
        a["core"] = NO if a.get("core") == NO else YES
        a["roles"] = [r for r in a["roles"] if r in ROLES]
        a["level"] = a["level"] if a.get("level") in LEVELS else "正式"
        a["boss"] = a.get("boss") or HUMAN
        a |= {"code": _next(conn, p), "name": name, "joined": _now()}
        a["history"] = [f"{_now()} · {by} · {what}"]
        _write(p, a)
        store.log(conn, by, what, a["code"], name)
    return get(p, a["code"])


def register(conn, p: Project, name: str, program: str = "", line: str = "") -> dict:
    """agent 报到：没档案就建一份、给编号；有了就接上原来那份（同名再来）。→ {agent, new}。"""
    old = find(p, name)
    if old:
        return {"agent": old, "new": False}
    a = _new(conn, p, name, {"program": _flat(program), "line": _flat(line)}, actor(name),
             "报到" + (f" · 用 {_flat(program)}" if _flat(program) else ""))
    return {"agent": a, "new": True}


def create(conn, p: Project, name: str, template: str = "空白", *, by: str = "人", **fields) -> dict:
    """人提前建一份（从样子开始）：那个 agent 来了报同样的名字就接上。"""
    template = OLD_TEMPLATES.get(template, template)
    base = TEMPLATES.get(template) or TEMPLATES["空白"]
    return _new(conn, p, name, base | {k: v for k, v in fields.items() if v not in (None, "")}, by,
                f"建档案（照「{template}」的样子）" if template in TEMPLATES and template != "空白" else "建档案")


def update(conn, p: Project, key: str, fields: dict, *, by: str = "人", why: str = "", _authorized: bool = False) -> dict:
    """改档案：只改带上的；每改一格「变迁」记一行。agent（by 是 agent:…）改不了「改核心」，也只能改自己的。"""
    a = get(p, key)
    if by.startswith("agent:") and not _authorized:
        if short(by) != a["name"]:
            raise store.Refused(f"只能改自己的档案（{a['code']} 是 {a['name']} 的）")
        if any(k in fields for k in HUMAN_ONLY):
            raise store.Refused("岗位、等级、上级、工种、范围、核心权限和运行开关只有人能改；有人的授权时走配置专用入口")
    changes = []
    for k, v in fields.items():
        if k not in EDIT:
            continue
        if k in LISTS:
            v = _split(v)
            if k == "roles" and [r for r in v if r not in ROLES]:
                raise store.Refused(f"岗位只能是 {' · '.join(ROLES)}（能兼几个）")
            if k == "crafts" and [c for c in v if c not in CRAFTS]:
                raise store.Refused(f"工种只能是 {' · '.join(CRAFTS)}（能兼几个）")
        elif k in SWITCHES:
            v = _on(v)
        elif k == "level":
            v = _flat(v)
            if v not in LEVELS:
                raise store.Refused(f"等级只能是 {' · '.join(LEVELS)}")
        elif k == "boss":
            v = _boss(p, a, v)
        elif k == "core":
            v = NO if v in (NO, False, "false", "否") else YES
        elif k == "brief":
            v = str(v or "").strip()
        else:
            v = _flat(v)
        if v != a[k]:
            show = (lambda x: ("开" if x else "关") if isinstance(x, bool) else ("、".join(x) if isinstance(x, list) else (x if len(x) <= 40 else x[:40] + "…")) or "（空）")
            changes.append(f"{LABEL[k]}：{show(a[k])} → {show(v)}" if k != "brief" else "改了交代")
            a[k] = v
    if not changes:
        return a
    _check_rank(p, a)
    with store.tx(conn):
        a["history"].append(f"{_now()} · {by} · " + "；".join(changes) + (f"（{_flat(why)}）" if _flat(why) else ""))
        _write(p, a)
        store.log(conn, by, "改了档案", a["code"], "；".join(changes)[:200])
    return get(p, a["code"])


def configure(conn, p: Project, key: str, fields: dict, *, by: str, authorization: str) -> dict:
    """人的授权配置入口。调用者须先核实授权；保存实际操作者及授权原话，普通 my_profile 不能走这里。"""
    if not _flat(authorization):
        raise store.Refused("配置员工权限要写清人的授权来源")
    return update(conn, p, key, fields, by=by, why=f"人的授权：{_flat(authorization)}", _authorized=True)


def _check_rank(p: Project, a: dict) -> None:
    """等级管权限（S1-8 S2-41）：带队要资深；上级要资深；降等级前先给下面的人换上级。"""
    if "带队" in a["roles"] and a["level"] != "资深":
        raise store.Refused("带队要资深：先把等级改成资深")
    if a["boss"] != HUMAN:
        b = find(p, a["boss"])
        if b and b["level"] != "资深":
            raise store.Refused(f"上级要资深：{b['code']} {b['name']} 是{b['level']}")
    if a["level"] != "资深":
        kids = [x["code"] for x in list_all(p) if x["boss"] == a["code"]]
        if kids:
            raise store.Refused(f"{a['code']} 下面还有 {'、'.join(kids)}：先给它们换上级，再降等级")


def suggest(a: dict | None, passed: int, sent_back: int) -> str:
    """按交付记录建议升级（升不升人点）：见习通过 10 件、没被打回 → 正式；正式通过 30 件、打回不到一成 → 资深。"""
    if not a:
        return ""
    if a["level"] == "见习" and passed >= 10 and sent_back == 0:
        return f"通过 {passed} 件、打回 0 件，可以升正式"
    if a["level"] == "正式" and passed >= 30 and sent_back * 10 < passed:
        return f"通过 {passed} 件、打回 {sent_back} 件，可以升资深"
    return ""


def _boss(p: Project, a: dict, v) -> str:
    """上级：「人」「你」或空 = 直接向你汇报；写编号或名字 = 那个 agent。不能是自己，不能绕圈（G2 管 G3、G3 又管 G2）。"""
    v = _flat(v)
    if v in ("", HUMAN, "你"):
        return HUMAN
    b = find(p, v)
    if b is None:
        raise store.Refused(f"上级「{v}」没有档案")
    if b["code"] == a["code"]:
        raise store.Refused("上级不能是自己")
    seen, cur = {a["code"]}, b
    while cur and cur["boss"] != HUMAN:                   # 顺着新上级往上走，走回自己就是绕圈
        if cur["boss"] in seen:
            raise store.Refused(f"绕圈了：{b['code']} 往上数会数回 {a['code']}")
        seen.add(cur["code"])
        cur = find(p, cur["boss"])
    return b["code"]


def copy(conn, p: Project, key: str, name: str, *, by: str = "人") -> dict:
    a = get(p, key)
    return _new(conn, p, name, {k: a[k] for k in EDIT}, by, f"建档案（照 {a['code']} {a['name']} 复制）")


def delete(conn, p: Project, key: str, *, by: str = "人", reason: str = "") -> dict:
    """删档案：挪进回收站（能还原）；它领着的活放手。"""
    import trash
    a = get(p, key)
    got = trash.move(conn, p, (DIR / a["file"]).as_posix(), by=by, reason=_flat(reason) or f"删 agent 档案 {a['code']} {a['name']}")
    for r in claims.of(conn, actor(a["name"])):
        claims.release(conn, r["goal"], r["sub"], note=f"档案 {a['code']} 删了")
    return got


# ---------------------------------------------------------------- 照档案管

def _hits(entries: list[str], g: dict, x: dict) -> bool:
    keys = {g["code"], f"{g['code']} {x['code']}", *claims.lanes_of(g, x), *(g.get("modules") or [])}
    return any(e in keys for e in entries)


def allows(a: dict | None, g: dict, x: dict) -> bool:
    """这件能不能给他：没档案（测试、旧调用）都行；「管哪些」空着都行，写了只给里面的；「不碰」的不给。"""
    return not allows_reason(a, g, x)


def task_crafts(x: dict) -> list[str]:
    """只认任务明确写出的工种前缀，不按任务意思猜。多个前缀须全部符合。"""
    text = str(x.get("what") or x.get("title") or x.get("name") or "").lstrip()
    out = []
    while (m := re.match(r"〔([^〕]+)〕\s*", text)):
        if m.group(1) in CRAFTS:
            out.append(m.group(1))
        text = text[m.end():]
    return list(dict.fromkeys(out))


def allows_reason(a: dict | None, g: dict, x: dict) -> str:
    """没有拒因返回空串；派活、手工领活和看板使用同一判断。旧档案工种空着保持可领。"""
    if not a:
        return ""
    if a.get("paused"):
        return "员工已暂停"
    scope, avoid = a.get("scope") or [], a.get("avoid") or []
    if scope and not _hits(scope, g, x):
        return "不在负责范围（管哪些）"
    if avoid and _hits(avoid, g, x):
        return "属于档案里的不碰范围"
    required, trained = task_crafts(x), a.get("crafts") or []
    if trained and any(c not in trained for c in required):
        return "工种不匹配：需要" + "、".join(required) + "，员工负责" + "、".join(trained)
    return ""


def take_core(conn, p: Project, agent: str, why: str = "") -> dict:
    a = require(p, agent)
    if a.get("paused"):
        raise store.Refused(f"{a['code']} {a['name']} 已暂停，不能拿核心锁")
    if a["level"] == "见习":
        raise store.Refused(f"{a['code']} {a['name']} 是见习：见习不能改核心，请人升了等级再来")
    if a["core"] == NO:
        raise store.Refused(f"{a['code']} {a['name']} 的档案写着「改核心：不能」：要改核心，请人在档案上改成「能」")
    return claims.take_core(conn, actor(a["name"]), why)


def brief_text(a: dict) -> str:
    """领活时告诉它的：你是谁、管哪些、交代、先读的技能。"""
    out = [f"你是 {a['code']} {a['name']}" + (f"（{a['line']}）" if a["line"] else "") + f"。档案：{DIR.as_posix()}/{a['file']}"]
    out.append(f"岗位：{'、'.join(jobs(a))} · 等级：{a['level']} · 上级：{'人（直接向人汇报）' if a['boss'] == HUMAN else a['boss']}")
    out.append("工种：" + ("、".join(a.get("crafts") or []) or "未限定") +
               f" · 自动运行：{'开' if a.get('auto') else '关'} · 计划审核：{'开' if a.get('plan_required') else '关'} · 暂停：{'是' if a.get('paused') else '否'}")
    if a["level"] == "见习":
        out.append("- 见习：交的每件都要验收过才算做完；不能改核心")
    out += [f"- {r}：{DUTY[r]}" for r in jobs(a)]
    if a["scope"] or a["avoid"]:
        out.append("管哪些：" + ("、".join(a["scope"]) or "都能领") + ("；不碰：" + "、".join(a["avoid"]) if a["avoid"] else ""))
    out.append(f"改核心：{a['core']}")
    if a["skills"]:
        out.append("先读的技能：" + "、".join(a["skills"]))
    if a["brief"]:
        out.append("交代：\n" + a["brief"])
    return "\n".join(out)


# ---------------------------------------------------------------- 名册 · 时间线

def roster(conn, p: Project) -> list[dict]:
    """档案上的 + 来干过、没档案的，一人一行；灯看它领着的活最后一次动静。"""
    import deliveries
    import vcs
    held = {}
    for r in claims.active(conn):
        held.setdefault(r["agent"], []).append(r)
    seen = {r[0]: r[1] for r in conn.execute("SELECT actor, MAX(at) FROM event WHERE actor LIKE 'agent:%' GROUP BY actor")}
    js = deliveries.list_all(p)
    commits = {}
    for c in vcs.log(p, 500):
        commits[c["who"]] = commits.get(c["who"], 0) + 1
    people = [(a["name"], a) for a in list_all(p)]
    names = {n for n, _ in people}
    for x, at in list(seen.items()):                   # 名字后面带备注的，并进本名
        n = actor(short(x))
        if n != x:
            seen[n] = max(seen.get(n) or "", at or "")
    people += [(n, None) for n in sorted({short(x) for x in seen}) if n not in names and n not in ("", "agent")]
    out = []
    for name, a in people:
        who = actor(name)
        mine = [r for r in held.get(who, []) if r["goal"] != claims.CORE]
        idle = min((r["idle"] for r in held.get(who, [])), default=None)
        lamp = ("在干活" if idle < busy(conn) else "停了") if idle is not None else "空着"
        mine_js = [j for j in js if j.get("by") in (who, name)]
        passed = sum(1 for j in mine_js if j["state"] == "验收通过")
        sent_back = sum(1 for j in mine_js if j["state"] == "打回")
        out.append({"code": a["code"] if a else "", "name": name, "program": a["program"] if a else "", "line": a["line"] if a else "",
                    "roles": jobs(a) if a else [], "level": a["level"] if a else "", "boss": a["boss"] if a else "",
                    "crafts": a.get("crafts", []) if a else [],
                    **{k: bool(a and a.get(k)) for k in SWITCHES},
                    "passed": passed, "sent_back": sent_back, "suggest": suggest(a, passed, sent_back),
                    "file": a["file"] if a else "", "core": a["core"] if a else "", "scope": a["scope"] if a else [],
                    "avoid": a["avoid"] if a else [], "registered": bool(a), "lamp": lamp, "idle": idle,
                    "holding": [{"goal": r["goal"], "sub": r["sub"], "what": r["what"]} for r in mine],
                    "core_lock": any(r["goal"] == claims.CORE for r in held.get(who, [])),
                    "seen": (seen.get(who) or "")[:16].replace("T", " "),
                    "delivered": [j["code"] for j in js if j.get("by") in (who, name)],
                    "commits": commits.get(who, 0) + commits.get(name, 0)})
    return out


def stuck(conn, p: Project) -> list[dict]:
    """卡住了的（S1-8 S2-36；照三省六部的停滞处理：提醒自己 → 报上级 → 报人 → 退回）：领着活半小时没动静的一件一行。
    to：现在该叫谁——半小时起报给它的上级；一小时起（或上级就是人）也报给人；两小时 claims 自动放手、件回到能做。现算，不另存。"""
    profs = {a["name"]: a for a in list_all(p)}
    boss_s, human_s = busy(conn), _knob(conn, "stuck_human_min", 2 * BUSY // 60) * 60
    out = []
    for r in claims.active(conn):
        if r["goal"] == claims.CORE or r["idle"] < boss_s:
            continue
        name = short(r["agent"])
        a = profs.get(name)
        boss = a["boss"] if a else HUMAN
        out.append({"agent": name, "code": a["code"] if a else "", "goal": r["goal"], "sub": r["sub"], "what": r["what"], "idle": r["idle"],
                    "boss": boss, "to": HUMAN if boss == HUMAN or r["idle"] >= human_s else boss, "left": max(0, claims.ttl(conn) - r["idle"])})
    return out


def wake_text(conn, p: Project, agent: str) -> str:
    """上级领活时先看到的：下面谁卡住了、卡了多久、能怎么办（「叫你是因为……」）。"""
    me = find(p, agent)
    rows = [r for r in stuck(conn, p) if me and r["boss"] == me["code"]]
    if not rows:
        return ""
    return ("## 叫你是因为：你是上级，下面的人卡住了\n" + "\n".join(
        f"- {r['code']} {r['agent']} 领着 {(r['goal'] + ' ' + r['sub']).strip()}（{r['what']}）{r['idle'] // 60} 分没动静：看看它的会话、帮一把；"
        f"实在不动了用 release_task(goal=\"{r['goal']}\", sub=\"{r['sub']}\", for_agent=\"{r['code']}\", note=\"为什么\") 让它放手，件回到能做。"
        f"再过 {r['left'] // 60} 分没动静会自动放手" + ("；已经一小时了，人那边也看得到" if r["to"] == HUMAN else "") for r in rows) + "\n\n")


def _knob(conn, name: str, default: int) -> int:
    try:
        import knobs
        return int(knobs.get(conn, name))
    except Exception:
        return default


def busy(conn) -> int:
    """多久没动静算卡住、报上级（秒）：照设置（S1-8 S2-57），默认 30 分钟。"""
    return _knob(conn, "stuck_boss_min", BUSY // 60) * 60


def release_for(conn, p: Project, boss: str, who: str, goal: str, sub: str, note: str = "") -> str:
    """上级让下面卡住的人放手（半小时没动静才行）。→ 放了什么；不行抛 Refused。"""
    b, them = find(p, boss), find(p, who)
    if not b or not them or them["boss"] != b["code"]:
        raise store.Refused(f"你不是 {who} 的上级")
    row = next((r for r in claims.active(conn) if r["goal"] == goal and r["sub"] == sub and short(r["agent"]) == them["name"]), None)
    if row is None:
        raise store.Refused(f"{them['code']} 没领着 {goal} {sub}")
    if row["idle"] < busy(conn):
        raise store.Refused(f"{them['code']} {busy(conn) // 60} 分钟内还有动静，先问问它")
    claims.release(conn, goal, sub, note=f"上级 {b['code']} 让它放手" + (f"：{_flat(note)}" if _flat(note) else ""))
    return f"{goal} {sub}"


def org(conn, p: Project) -> dict:
    """组织和流程（S1-8 S2-38，样图 R3）：每个 agent 的岗位、等级、上级、下面的人；一件事要过的几关，每关几件、谁管。现算。"""
    import board
    import dispatch
    import drafts
    rows = [r for r in roster(conn, p) if r["registered"]]
    for r in rows:
        r["reports"] = [x["code"] for x in rows if x["boss"] == r["code"]]
    who = {k: [r["code"] for r in rows if k in r["roles"]] for k in ROLES}
    counts = {k: 0 for k in board.COLS} | {"等验收": 0}
    for x in board.items(conn, p):
        if x["col"] in counts:
            counts[x["col"]] += 1
    ds = [d for d in drafts.listing(p) if d["state"] == drafts.WAIT]
    waiting = [d for d in ds if drafts.stage(p, d) == "等审"]
    ready = [r for r in dispatch.plan_status(p) if not r["final"] and not r["missing"]]
    flow = [
        {"key": "human", "name": "你：方向和需求", "n": len(store.list_pending(conn)), "unit": "条问题等你答", "who": [], "human": True, "go": "s:inbox"},
        {"key": "规划", "name": "规划", "n": len(ds), "unit": "件草稿在草稿区", "who": who["规划"], "none": "没人：你或干活的顺手起草"},
        {"key": "审核", "name": "审核", "n": len(waiting), "unit": "件等审", "who": who["审核"], "none": "没人：草稿等你点「行」"},
        {"key": "final", "name": "你：定稿", "n": len(ready), "unit": "块齐了等你按", "who": [], "human": True, "go": "s:plan"},
        {"key": "干活", "name": "干活", "n": counts["在做"], "unit": f"件在做 · 能做 {counts['能做']}", "who": who["干活"], "none": "没人", "go": "s:board"},
        {"key": "验收", "name": "验收", "n": counts["等验收"], "unit": "件等验", "who": who["验收"], "none": "没人：检查全过默认通过", "go": "s:review"},
        {"key": "done", "name": "做完", "n": counts["做完"], "unit": "件，你随时能抽查、打回", "who": [], "go": "s:board"},
    ]
    return {"people": rows, "flow": flow, "roles": list(ROLES), "levels": list(LEVELS), "duty": DUTY, "stuck": stuck(conn, p)}


def timeline(conn, p: Project, goal: str, sub: str) -> list[dict]:
    """一件的来龙去脉：领了 · 放手 · 交付 · 默认通过 / 验收 · 打回 · 本机 git，按时间排。"""
    import vcs
    what = f"{goal} {sub}".strip()
    rows = conn.execute("SELECT at, actor, action, target, detail FROM event WHERE (target = ? AND action IN ('领了', '放手'))"
                        " OR (detail = ? AND action IN ('交付', '验收通过', '打回')) ORDER BY at, id", (what, what)).fetchall()
    out = [{"at": r["at"][:16].replace("T", " "), "who": r["actor"], "what": r["action"],
            "detail": r["target"] if r["action"] in ("交付", "验收通过", "打回") else (r["detail"] or "")} for r in rows]
    if vcs.enabled(p):
        code, log = vcs._run(p, "log", "-50", "-F", f"--grep= · {what} · ", "--pretty=format:%h%x1f%an%x1f%ad%x1f%s",
                             "--date=format:%Y-%m-%d %H:%M")
        for line in (log.splitlines() if code == 0 else []):
            h, who, at, msg = (line.split("\x1f") + ["", "", "", ""])[:4]
            out.append({"at": at, "who": who, "what": "本机 git", "detail": f"{h} · {msg[:60]}"})
    return sorted(out, key=lambda e: e["at"])


def handovers(p: Project) -> list[dict]:
    """交接单 H…：新的在前。收进归档的也列（archived，path 是归档里的路径；S1-8 S2-61）。"""
    import archive
    d = p.root / "自动化" / "交接"
    out = []
    files = [(f, False) for f in (d.glob("H*.md") if d.is_dir() else [])] + [(f, True) for f in archive.archived_files(p, "自动化/交接", "H*.md")]
    for f, old in files:
        m = re.match(r"H(\d+)", f.name)
        if m:
            parts = [x.strip() for x in f.stem.split("·")]
            out.append({"code": f"H{m.group(1)}", "n": int(m.group(1)), "file": f.name, "date": parts[1] if len(parts) > 1 else "",
                        "who": parts[2] if len(parts) > 2 else "", "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)),
                        "path": f.relative_to(p.root).as_posix(), "archived": old})
    return sorted(out, key=lambda x: (x["n"], x["mtime"]), reverse=True)


# ---------------------------------------------------------------- 开工脚本（S1-8 S2-47；网页终端里点「开工」用）
#
# 照档案生成：「用什么」写 Claude Code（Sonnet 5.5）/ Codex（gpt-6-astra）这样，括号里是模型；开工的话照协议走一圈，
# 接口（research-console）用跑应用的那个 Python 接上（本机 PATH 里的 python 可能是乱码）。只生成文件，不启动——人在网页上点了才跑。

def _launch_prompt(a: dict, model: str, codex: bool) -> str:
    n, c = a["name"], a["code"]
    extra = (a.get("opener") or "").strip()
    return (f"你叫 {n}（档案 {c}），模型 {model or '用户默认模型'}。本 MCP 已绑定你的名字，所有 agent 参数一律写 {n}。"
            "先读 AGENTS.md、项目自带技能和最新交接单，照 自动化/协议.md 与 自动化/工作流/W1 自动推进.md 做。"
            "先 my_profile 看岗位、工种、范围与交代，get_overview，然后 next_task。"
            "按照 next_task 返回的动作、接口及参数做本轮工作：施工先提交施工计划；已启用计划审核的必须审过才动手。"
            "审核员只审核别人计划，验收员复跑别人交付的检查；不得自己审计划、自己验交付。打回按理由修订同一份，修改施工范围必须重新审核。"
            "已批准计划的文件范围之外不改；改核心前拿核心锁并存档，改完记日志。做完照『怎么验』验，deliver。"
            "本次进程只执行一个动作，再查询 next_task 确认状态、通过 MCP 留下本轮结果和接手信息，然后退出；下一件由外层运行器另开一轮。"
            "当前动作是待审、等验收、已停止、没活、没有合适岗位或只剩等人的事项时，本轮直接退出，不循环等、不睡眠轮询。"
            "人叫停或档案已暂停就停止修改，记录接手后退出。单件失败次数、运行圈数到上限也退出。"
            "遇到派错、卡住、来回打回、协议没写清，通过 MCP 记实际情况。只在彻底删除、公开发布、改方向时请求人的决定。"
            + (f"开工的话：{extra}" if extra else ""))


def _model(a: dict) -> str:
    m = re.search(r"[（(]([^）)]+)[）)]", a.get("program") or "")
    return m.group(1).strip() if m else ""


def codex_executable() -> str:
    """本机显式设置优先，再找桌面安装的真 exe，最后 PATH；不优先损坏的 npm shim。"""
    import machine
    override = machine.get("tools", "codex-cli")
    if override:
        target = Path(os.path.expandvars(override)).expanduser()
        if target.is_dir():
            target = target / ("codex.exe" if os.name == "nt" else "codex")
        if not target.is_file():
            raise store.Refused(f"本机设置 codex-cli 指向的程序不存在：{target}")
        return str(target)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        base = Path(local) / "OpenAI" / "Codex" / "bin"
        found = sorted(base.glob("*/codex.exe"), key=lambda f: f.stat().st_mtime, reverse=True)
        if found:
            return str(found[0])
    return shutil.which("codex") or "codex"


def codex_command(p: Project, key: str, prompt: str | None = None) -> list[str]:
    """运行器的一轮 Codex 命令；固定项目和 MCP 员工身份，模型未写就使用用户默认。"""
    from project import CODE_DIR
    a = get(p, key)
    if "codex" not in (a.get("program") or "").lower():
        raise store.Refused(f"{a['code']} {a['name']} 的程序不是 Codex")
    root = p.root.resolve().as_posix()
    mcp = (CODE_DIR / "backend" / "mcp_server.py").as_posix()
    model = _model(a)
    args = [codex_executable(), "exec", "--approve-for-me", "-C", root, "--skip-git-repo-check"]
    if model:
        args += ["-m", model]
    args += ["-c", "mcp_servers.research-console.command=" + json.dumps(sys.executable.replace("\\", "/")),
             "-c", "mcp_servers.research-console.args=" + json.dumps([mcp, "--project", root, "--agent", a["name"]], ensure_ascii=False),
             prompt if prompt is not None else _launch_prompt(a, model, True)]
    return args


def launcher(p: Project, key: str, *, code_dir: Path | None = None, tag: str = "") -> dict:
    """照档案写 索引/开工/start-<编号>.ps1，返回在 PowerShell 里跑它的那一行。
    世界树的枝（S1-8 S2-55）：p 是枝，code_dir 是枝自己的程序（接枝自己的接口），tag 是枝号（窗口标题「枝-3 · G5 名字」）。"""
    from project import CODE_DIR
    code_dir = code_dir or CODE_DIR
    a = get(p, key)
    prog = a.get("program") or ""
    model = _model(a)
    low = prog.lower()
    d = p.index_dir / "开工"
    d.mkdir(parents=True, exist_ok=True)
    py = sys.executable.replace("\\", "/")
    mcp = (code_dir / "backend" / "mcp_server.py").as_posix()
    if "claude" in low:
        ml = model.lower()
        alias = next((x for x in ("opus", "sonnet", "haiku") if x in ml), "")
        cfg = d / f"mcp-claude-{a['code']}.json"
        cfg.write_text(json.dumps({"mcpServers": {"research-console": {"command": py,
                                  "args": [mcp, "--project", p.root.resolve().as_posix(), "--agent", a["name"]]}}}, ensure_ascii=False), encoding="utf-8")
        args = ["claude"] + (["--model", alias] if alias else []) + ["--permission-mode", "auto", "--mcp-config", cfg.as_posix(),
                                                                     "--strict-mcp-config", "/loop " + _launch_prompt(a, model, False)]
    elif "codex" in low:
        # 外层一轮一轮启动非交互 Codex，才能可靠施加次数限制、暂停与恢复。
        args = [py, (code_dir / "backend" / "employee_runner.py").as_posix(),
                "--project", p.root.resolve().as_posix(), "--agent", a["name"]]
    else:
        raise store.Refused(f"{a['code']} {a['name']} 的「用什么」是「{prog or '空的'}」，认不出是哪家：写成「Claude Code（Sonnet 5.5）」或「Codex（gpt-6-astra）」这样")
    q = lambda s: "'" + str(s).replace("'", "''") + "'"
    f = d / f"start-{a['code']}.ps1"
    f.write_text("\r\n".join(["[Console]::OutputEncoding = [System.Text.Encoding]::UTF8", "$OutputEncoding = [System.Text.Encoding]::UTF8",
                              f"Set-Location -LiteralPath {q(p.root.as_posix())}", "& " + " ".join(q(x) for x in args)]) + "\r\n", encoding="utf-8-sig")
    return {"title": (f"{tag} · " if tag else "") + f"{a['code']} {a['name']}", "cmd": f"& {q(str(f))}" + ('; exit' if 'codex' in low else ''), "path": f"索引/开工/{f.name}", "program": prog,
            "model": model, "agent": a["name"], "project": p.root.resolve().as_posix(), "args": args,
            "prompt": _launch_prompt(a, model, "codex" in low)}
