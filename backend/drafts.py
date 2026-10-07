"""草稿区：agent 起草的需求、任务先放这，人点「行」才进正式文件（蓝图 S2-4）。

作者 10-01：「需求蓝图等等东西这个是最重要的，要先和人一起规划，这个完毕之后才是全自动」「蓝图定稿」。
- agent 用 MCP propose_draft 提：一条一份 治理/草稿/草-<号>.md（号不回收），状态「等你看」
- 人在蓝图「草稿区」逐条点：行（照原样或改一下再收）→ 写进正式的任务表 / 需求表，编号接着排；不要 → 留着、状态写「不要」
- 正式文件只在人点「行」时由程序写；网页先记一条「人」的事件，监管不当越界
- 纯文字文件：哪家 agent、谁的电脑都读得懂；格是两列小表（格 · 写什么），值里的「|」换成「／」
- 审核关（S1-8 S2-40，样图 R3）：有岗位写着「审核」的 agent（不是写的那个）时，草稿先给它审：准，或打回写理由；打回了写的人用
  propose_draft(revise="草-3") 改同一张，再审；三轮还不过就不再转、等人看。人随时能点「行」「不要」，审没审过都行。最下面「## 审核」一行一轮
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import atomic
import blueprint
import governance_paths as gp
import store
from project import Project

DIR = "治理/草稿"
KINDS = {"任务": ("做什么", "为了", "怎么验"), "需求": ("要什么功能", "要什么效果", "来自", "关联目标", "承接模块")}
MUST = {"任务": "做什么", "需求": "要什么功能"}
WAIT, TAKEN, DROPPED = "等你看", "收了", "不要"
OK, NO, FIXED = "准", "打回", "改了"                   # 审核那一节一行一种
MAX_ROUNDS = 3
_CODE = re.compile(r"^草-(\d+)\.md$")


def _dir(p: Project) -> Path:
    return p.root / DIR


def _clean(v) -> str:
    return " ".join(str(v or "").replace("|", "／").split())


def _write(f: Path, text: str) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))              # 照给的换行写，不让 Windows 再加一遍 \r
    atomic.replace(tmp, f)


def _where_ok(p: Project, kind: str, where: str) -> str:
    """放到哪：任务放 S1（S1-8）或模块；需求放「项目」或模块。认不出就拒。"""
    import project as proj
    where = where.strip()
    if kind == "需求" and where == "项目":
        return where
    if re.match(r"^S\d+-\d+$", where):
        if kind == "需求":
            raise store.Refused("需求放「项目」或某个模块；S1 的需求写进「项目」，关联目标填 S1 编号")
        if not any(g["code"] == where for g in blueprint.pyramid(p)["goals"]):
            raise store.Refused(f"蓝图里没有 {where}")
        return where
    names = [m.name if hasattr(m, "name") else str(m) for m in proj.module_dirs(p)]
    if where not in names:
        raise store.Refused(f"没有「{where}」这个模块（任务放 S1 编号或模块名，需求放「项目」或模块名）")
    return where


def _render(d: dict) -> str:
    rows = "".join(f"| {k} | {_clean(v)} |\n" for k, v in d["fields"].items())
    revs = "".join(f"- {r['at']} · {r['by']} · {r['act']}：{_clean(r['why'])}\n" for r in d.get("reviews") or [])
    return (f"# {d['code']} · {d['kind']} · {d['where']}\n\n状态：{d['state']}\n谁提的：{d['by']}\n什么时候：{d['at']}\n理由：{_clean(d['reason'])}\n"
            + (f"结果：{d['result']}\n" if d.get("result") else "") + f"\n| 格 | 写什么 |\n|---|---|\n{rows}" + (f"\n## 审核\n\n{revs}" if revs else ""))


def _parse(f: Path) -> dict | None:
    try:
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    m = re.match(r"^# (草-\d+) · (任务|需求) · (.+)$", text.split("\n", 1)[0].strip())
    if not m:
        return None
    body, _, tail = text.partition("\n## 审核\n")
    head = {k: v.strip() for k, v in (x.split("：", 1) for x in body.splitlines() if "：" in x and not x.startswith(("|", "#", "- ")))}
    reviews = []
    for x in tail.splitlines():
        m2 = re.match(r"^- (.+?) · (.+?) · (准|打回|改了)：(.*)$", x.strip())
        if m2:
            reviews.append({"at": m2.group(1), "by": m2.group(2), "act": m2.group(3), "why": m2.group(4)})
    fields = {}
    for line in body.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(c) == 2 and c[0] not in ("格", "---") and not set(c[0]) <= set("-:"):
            fields[c[0]] = c[1]
    return {"code": m.group(1), "kind": m.group(2), "where": m.group(3), "state": head.get("状态", WAIT), "by": head.get("谁提的", ""),
            "at": head.get("什么时候", ""), "reason": head.get("理由", ""), "result": head.get("结果", ""), "fields": fields,
            "reviews": reviews, "file": f"{DIR}/{f.name}"}


def rounds(d: dict) -> int:
    return sum(1 for r in d.get("reviews") or [] if r["act"] == NO)


def reviewers(p: Project, author: str) -> list[dict]:
    """能审这张的 agent：岗位里有「审核」、不是写的那个。"""
    import agents
    me = agents.short(author)
    return [a for a in agents.list_all(p) if "审核" in a["roles"] and a["name"] != me]


def stage(p: Project, d: dict) -> str:
    """这张草稿在审核这一关走到哪：等审 · 准 · 打回（等写的人改）· 交给你（三轮没过）· 没人审（等你点）· ""（已经收了 / 不要）。"""
    if d["state"] != WAIT:
        return ""
    last = (d.get("reviews") or [{}])[-1].get("act")
    if last == OK:
        return "准"
    if rounds(d) >= MAX_ROUNDS:
        return "交给你"
    if last == NO:
        return "打回"
    return "等审" if reviewers(p, d["by"]) else "没人审"


def review(p: Project, code: str, ok: bool, why: str, by: str) -> dict:
    """审核的 agent 审一张：准，或打回写理由（S1-8 S2-40）。不审自己写的。"""
    import agents
    a = agents.require(p, by)
    if "审核" not in a["roles"]:
        raise store.Refused(f"{a['code']} {a['name']} 的岗位里没有「审核」：要审，请人在档案上加")
    d = next((x for x in listing(p) if x["code"] == code), None)
    if d is None:
        raise store.Refused(f"没有 {code}")
    if agents.short(d["by"]) == a["name"]:
        raise store.Refused("不审自己写的")
    if stage(p, d) != "等审":
        raise store.Refused(f"{code} 现在不用审（{stage(p, d) or d['state']}）")
    why = _clean(why)
    if not why:
        raise store.Refused("写一句理由：准为什么准；打回写清哪里不行、怎么改")
    d.setdefault("reviews", []).append({"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "by": f"{a['code']} {a['name']}", "act": OK if ok else NO, "why": why})
    _write(p.root / d["file"], _render(d))
    return d


def revise(p: Project, code: str, fields: dict, reason: str, by: str) -> dict:
    """写的人照打回的理由改同一张，改完再审。"""
    import agents
    d = next((x for x in listing(p) if x["code"] == code), None)
    if d is None:
        raise store.Refused(f"没有 {code}")
    if agents.short(d["by"]) != agents.short(by):
        raise store.Refused(f"{code} 是 {d['by']} 写的：只能改自己写的")
    if stage(p, d) != "打回":
        raise store.Refused(f"{code} 没被打回（{stage(p, d) or d['state']}），不用改")
    for k in KINDS[d["kind"]]:
        if k in d["fields"] and fields.get(k) not in (None, ""):
            d["fields"][k] = _clean(fields[k])
    if d["kind"] == "任务" and not d["fields"].get("怎么验"):
        raise store.Refused("任务要写「怎么验」")
    d["reviews"].append({"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "by": by, "act": FIXED, "why": _clean(reason) or "照打回的理由改了"})
    _write(p.root / d["file"], _render(d))
    return d


def listing(p: Project) -> list[dict]:
    """全部草稿，新的在前；等你看的排最前。"""
    d = _dir(p)
    out = [x for f in d.glob("草-*.md") if _CODE.match(f.name) and (x := _parse(f))] if d.is_dir() else []
    return sorted(out, key=lambda x: (x["state"] != WAIT, -int(x["code"][2:])))


def propose(p: Project, kind: str, where: str, fields: dict, reason: str, by: str) -> dict:
    """agent 起草一条：放进草稿区，正式文件不动。"""
    if kind not in KINDS:
        raise store.Refused("kind 只能是「任务」或「需求」")
    where = _where_ok(p, kind, where)
    keep = {k: _clean(fields.get(k, "")) for k in KINDS[kind] if not (kind == "需求" and where != "项目" and k in ("关联目标", "承接模块"))}
    if not keep[MUST[kind]]:
        raise store.Refused(f"「{MUST[kind]}」不能空")
    if kind == "任务" and not keep["怎么验"]:
        raise store.Refused("任务要写「怎么验」（机器能查的：跑哪条测试 / 哪个文件在不在 / 页面上看得到什么）")
    if not reason.strip():
        raise store.Refused("写一句理由：为什么要加这一条")
    d = _dir(p)
    d.mkdir(parents=True, exist_ok=True)
    n = max([int(m.group(1)) for f in d.iterdir() if (m := _CODE.match(f.name))] or [0]) + 1
    x = {"code": f"草-{n}", "kind": kind, "where": where, "state": WAIT, "by": by, "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
         "reason": reason, "fields": keep}
    _write(d / f"草-{n}.md", _render(x))
    return dict(x, file=f"{DIR}/草-{n}.md")


def _target(p: Project, kind: str, where: str) -> Path:
    if kind == "任务" and where.startswith("S"):
        f = next((x for x in gp.goal_files(p) if x.is_file() and x.name.startswith(where + " ")), None)
        if f is None:
            raise store.Refused(f"找不到 {where} 的文件")
        return f
    if kind == "任务":
        f = gp.resolve(p, f"资料/{where}/蓝图.md", write=True)
        if not f.is_file():
            _write(f, f"# {where} · 任务\n\n> 照本模块需求要做的几件。\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n")
        return f
    if where == "项目":
        f = p.root / "治理" / "需求" / "项目.md"
        if not f.is_file():
            _write(f, "# 项目需求\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 | 关联目标 | 承接模块 |\n|---|---|---|---|---|---|\n")
        return f
    f = gp.resolve(p, f"资料/{where}/需求.md", write=True)
    if not f.is_file():
        _write(f, f"# {where} · 需求\n\n| | 要什么功能 | 要什么效果（打开能看见什么） | 来自 |\n|---|---|---|---|\n")
    return f


def _append(f: Path, kind: str, fields: dict, by: str) -> str:
    """接在那张表最后一行后面；编号接着排（S2-<号>、需-<号>），列照表头填。返回新编号。"""
    raw = f.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    lines = raw.replace("\r\n", "\n").split("\n")
    key = "做什么" if kind == "任务" else "要什么功能"
    heads = [i for i, x in enumerate(lines) if x.startswith("|") and key in x]
    if not heads:
        raise store.Refused(f"「{f.name}」里没有{kind}表（表头要有「{key}」）")
    h = heads[-1]
    end = h + 1
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    pre = "S2-" if kind == "任务" else "需-"
    n = max([int(m.group(1)) for x in lines if (m := re.match(r"^\|\s*" + pre + r"(\d+)\s*\|", x))] or [0]) + 1
    code = f"{pre}{n}"
    cells = []
    for name in [c.strip() for c in lines[h].strip().strip("|").split("|")][1:]:
        if name == "状态":
            cells.append("没做")
        elif name.startswith("来自") and not fields.get("来自"):
            cells.append(f"{datetime.now().strftime('%m-%d')} 草稿区，{by} 提的")
        else:
            cells.append(_clean(next((v for k, v in fields.items() if name.startswith(k) or k.startswith(name)), "")))
    lines.insert(end, "| " + " | ".join([code] + cells) + " |")
    text = "\n".join(lines)
    _write(f, text.replace("\n", "\r\n") if crlf else text)
    return code


def decide(p: Project, code: str, act: str, fields: dict | None = None) -> dict:
    """人点：行（收进正式文件；fields 给了就用改过的）/ 不要。"""
    d = next((x for x in listing(p) if x["code"] == code), None)
    if d is None:
        raise store.Refused(f"没有 {code}")
    if d["state"] != WAIT:
        raise store.Refused(f"{code} 已经{d['state']}了")
    if act == "不要":
        d.update(state=DROPPED, result=f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 人点了不要")
    elif act == "行":
        use = {k: _clean((fields or {}).get(k, v)) for k, v in d["fields"].items()}
        if not use.get(MUST[d["kind"]]):
            raise store.Refused(f"「{MUST[d['kind']]}」不能空")
        f = _target(p, d["kind"], d["where"])
        new = _append(f, d["kind"], use, d["by"].replace("agent:", ""))
        d.update(fields=use, state=TAKEN, result=f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 收进 {gp.relative(p, f)}，编号 {new}")
        d["new"] = new
    else:
        raise store.Refused("只能点「行」或「不要」")
    _write(p.root / d["file"], _render(d))
    return d
