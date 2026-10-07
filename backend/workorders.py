"""开工单：自动化的一张张单子，一张一个文件，编号 K1、K2…（号不回收）。

作者 2026-09-27：「自动化模块应该是一张清单……左边目录应该是每个自定义清单的一个文件，然后这个文件要有蓝图，戒律，
等等其他模块的链接，然后我们准备好了之后，按照要求把这些交给agent」；又说那是个抽象的例子，要「内化成我这个应用」。
- 放在项目的 `自动化/开工单/K1 文献模块装修.md`：开头几行写要做成什么、目标（S1 或几件 S2）、用到的戒律 / 模块 / 工具 / 材料 / 存档、
  档位；正文「交代」分三格：要做到 · 建议 · 不许。人、agent、网页都能改
- 每样用到的东西一盏灯（readiness 现算）；灯全绿（或只剩黄）人才能「交给 agent」；同一时间只有一张在跑
- 文件里只存 备料 / 在跑 / 搁置；「等你验收」「做完」是算出来的
- 09-27 作者：「我们现在这个自动化是模块装修的自动化」——新开一张先选**哪个模块**：目标 = 这个模块（整个 / 几条需求 / 几件），
  需求、蓝图、戒律、材料自己带上。戒律四层自动算（readiness.rule_stack），文件里「戒律:」只记另加的
"""
from __future__ import annotations

import atomic
import os
import re
from datetime import datetime
from pathlib import Path

import blueprint
import governance_paths as gp
import deliveries
import project as proj
import readiness
import runs
import snapshot
import store
import tools
from project import Project
from skills import frontmatter

DIR = Path("自动化") / "开工单"
STORED = ("备料", "在跑", "搁置")
LISTS = {"rules": "戒律", "modules": "模块", "tools": "工具", "materials": "材料", "saves": "存档"}
NOTES = ("要做到", "建议", "不许")
_K = re.compile(r"K(\d+)")
_SCOPE = re.compile(r"S\d+-\d+(?: S\d+-\d+)?")          # 「S1-10」一整个目标，或「S1-10 S2-3」一件
_PATHS = ("rules", "materials")                           # 路径只用「、」分；别的「、，,」都行


def _dir(p: Project) -> Path:
    return p.root / DIR


def _flat(s) -> str:
    return " ".join(str(s or "").split())


def _split(v: str, key: str) -> list[str]:
    sep = r"、" if key in _PATHS else r"[、，,]"
    out = []
    for x in re.split(sep, v or ""):
        x = _flat(x)
        if x and x not in out:
            out.append(x)
    return out


def _sections(body: str) -> tuple[dict, str]:
    """正文 → (交代三格, 别的「## 」段原样)。"""
    notes = {k: [] for k in NOTES}
    rest, cur, in_notes = [], None, False
    for line in body.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            continue                                   # 标题每次重写
        if line.startswith("## "):
            in_notes = line[3:].strip() == "交代"
            cur = None
            if not in_notes:
                rest.append(line)
            continue
        m = re.match(r"^###\s*(要做到|建议|不许)\s*$", line) if in_notes else None
        if m:
            cur = m.group(1)
        elif in_notes:
            if cur:
                notes[cur].append(line)
        else:
            rest.append(line)
    return {k: "\n".join(v).strip() for k, v in notes.items()}, "\n".join(rest).strip()


def _parse(f: Path) -> dict | None:
    text = f.read_text(encoding="utf-8", errors="replace")
    fm = frontmatter(text)
    m = _K.fullmatch(fm.get("编号", ""))
    if not m:
        return None
    body = text[text.find("\n---", 3) + 4:].lstrip() if text.startswith("---") else text
    notes, rest = _sections(body)
    wo = {"code": fm["编号"], "n": int(m.group(1)), "name": fm.get("名字", "") or f.stem.split(" ", 1)[-1],
          "stored": fm.get("状态", "") if fm.get("状态", "") in STORED else "备料",
          "product": fm.get("做成", ""), "target": _split(fm.get("目标", ""), "target"),
          "level": _int(fm.get("档位"), 1), "rounds": _int(fm.get("圈数"), 5), "fails": _int(fm.get("失败几次停"), 2),
          "started": fm.get("开始", ""), "notes": notes, "rest": rest, "file": f.name}
    for k, word in LISTS.items():
        wo[k] = _split(fm.get(word, ""), k)
    auto = {"AGENTS.md"} | {f"资料/{m}/戒律.md" for m in wo["modules"]}   # 自动带上的不算「另加」（旧单上写了的也去掉）
    wo["rules"] = [r for r in wo["rules"] if r not in auto and not re.match(r"^资料/戒律/[12] ", r)]
    # 给 readiness 用的名字
    wo["scope"] = wo["target"]
    return wo


def _int(v, default: int) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _text(wo: dict) -> str:
    head = [("编号", wo["code"]), ("名字", wo["name"]), ("状态", wo["stored"]), ("做成", wo["product"]),
            ("目标", "、".join(wo["target"]))]
    head += [(word, "、".join(wo[k])) for k, word in LISTS.items()]
    head += [("档位", wo["level"]), ("圈数", wo["rounds"]), ("失败几次停", wo["fails"]), ("开始", wo["started"])]
    out = ["---"] + [f"{k}: {_flat(v)}".rstrip() for k, v in head] + ["---", f"# {wo['code']} {wo['name']}", "", "## 交代", ""]
    for k in NOTES:
        out += [f"### {k}", ""] + ([wo["notes"].get(k, "").strip(), ""] if wo["notes"].get(k, "").strip() else [])
    if wo.get("rest"):
        out += [wo["rest"].strip(), ""]
    return "\n".join(out).rstrip("\n") + "\n"


def _write(p: Project, wo: dict) -> dict:
    d = _dir(p)
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]', "", wo["name"]).strip() or "未命名"
    f = d / f"{wo['code']} {safe}.md"
    old = wo.get("file")
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(_text(wo), encoding="utf-8")
    atomic.replace(tmp, f)
    if old and old != f.name and (d / old).is_file():  # 改了名字：文件名跟着改
        (d / old).unlink()
    wo["file"] = f.name
    return wo


# ---------------------------------------------------------------- 读

def list_all(p: Project) -> list[dict]:
    d = _dir(p)
    out = [x for f in d.glob("K*.md") if (x := _parse(f))] if d.is_dir() else []
    out.sort(key=lambda x: x["n"])
    return out


def get(p: Project, code: str) -> dict:
    wo = next((x for x in list_all(p) if x["code"] == code), None)
    if wo is None:
        raise store.Refused(f"没有开工单 {code}")
    return wo


def running(p: Project) -> dict | None:
    return next((x for x in list_all(p) if x["stored"] == "在跑"), None)


def mine(p: Project, code: str) -> list[dict]:
    """这张单的交付单：交的时候它在跑（交付单上写着 开工单: K1）。"""
    return [j for j in deliveries.list_all(p) if j.get("workorder") == code]


def state(p: Project, wo: dict, js: list | None = None) -> str:
    """显示的状态：在跑 / 搁置 照文件；不然 目标里每件都做完 = 做完；有交付单等你 = 等你验收；其余 = 备料。"""
    if wo["stored"] in ("在跑", "搁置"):
        return wo["stored"]
    if wo["target"] and _all_done(p, wo):
        return "做完"
    js = mine(p, wo["code"]) if js is None else js
    if any(j["state"] == "待你验收" for j in js):
        return "等你验收"
    return "备料"


def _all_done(p: Project, wo: dict) -> bool:
    """目标里的每件（不算「以后」）都是做完；目标得真在蓝图里、真有做完的。"""
    import requirements
    bp = blueprint.pyramid(p)
    seen = 0
    for s in wo["target"]:
        code, sub = readiness.split_target(s)
        if sub.startswith('需-'):
            q = next((q for q in requirements.catalog(p, bp) if q['scope'] == code and q['code'] == sub), None)
            if q is None:
                return False
            subs = [x for x in q['tasks'] if not x['text'].startswith('以后')]
        else:
            g = blueprint.find(bp, code)
            if g is None:
                return False
            subs = [x for x in g['subs'] if (not sub or x['code'] == sub) and not x['text'].startswith('以后')]
        if not subs:
            return False
        if any(x["status"] != "ok" for x in subs):
            return False
        seen += len(subs)
    return seen > 0


def step(disp: str, wo: dict) -> int:
    """顶上四步：写单 0 → 备齐 1 → 在跑 2 → 验收 3。"""
    if disp in ("等你验收", "做完"):
        return 3
    if disp == "在跑":
        return 2
    return 1 if wo["target"] else 0


def detail(conn, p: Project, code: str) -> dict:
    wo = get(p, code)
    pnl = readiness.panel(conn, p, wo)
    js = mine(p, code)
    disp = state(p, wo, js=js)
    pnl["deliveries"] = js
    pnl["run"] = runs.latest(p, workorder=code)
    return {"wo": wo | {"state": disp, "step": step(disp, wo)}, "panel": pnl, "hrefs": hrefs(p, wo), "labels": labels(p, wo)}


def summary(conn, p: Project) -> dict:
    """左边目录：每张单一行（状态、最差的灯、绿了几样）。"""
    out = []
    orders = list_all(p)
    # Only this response shares parsed plans; the next call reads the directory afresh.
    all_plans = __import__("governance").plan_records(p) if orders else []
    for wo in orders:
        pnl = readiness.panel(conn, p, wo, all_plans=all_plans)
        disp = state(p, wo)
        lamp = max((d["lamp"] for d in pnl["devices"]), key=lambda x: readiness._RANK[x], default="ok")
        out.append({"code": wo["code"], "name": wo["name"], "state": disp, "lamp": lamp,
                    "green": pnl["green"], "total": pnl["total"], "ready": pnl["ready"]})
    r = running(p)
    return {"items": out, "running": r["code"] if r else None}


def hrefs(p: Project, wo: dict) -> dict:
    """单上每样东西点了跳到哪。"""
    out = {}
    for x in wo["rules"] + wo["materials"]:
        out[x] = readiness._path_href(x)
    for m in wo["modules"]:
        out[m] = "#/m/" + m
    for t in wo["tools"]:
        out[t] = "#/tools?t=" + t
    for c in wo["saves"]:
        out[c] = "#/saves?c=" + c
    bp = blueprint.pyramid(p)
    for x in wo["target"]:
        code = readiness.split_target(x)[0]
        g = blueprint.find(bp, code)
        if g and g.get("kind") == "module" or (not g and proj.module_dir(p, code)):
            out[x] = readiness._req_href(code)
        else:
            out[x] = "#/m/蓝图?f=" + g["file"].split("/")[-1] if g else ""
    for r in readiness.rule_stack(p, wo):
        if r.get("file"):
            out.setdefault(r["file"], readiness._path_href(r["file"]))
    return out


def labels(p: Project, wo: dict) -> dict:
    """目标每一项说成人话：「文献 · 整个模块」「需-2 能左右对照读译文」「S2-3 pdf.js 接进应用」。"""
    import requirements
    bp, out = blueprint.pyramid(p), {}
    for x in wo["target"]:
        code, sub = readiness.split_target(x)
        g = blueprint.find(bp, code)
        if not sub:
            out[x] = "整个模块" if (g and g.get("kind") == "module") or proj.module_dir(p, code) else (g["name"] if g else "")
        elif sub.startswith("需-"):
            q = next((q for q in (requirements.read(p, code) or {"reqs": []})["reqs"] if q["code"] == sub), None)
            out[x] = q["func"] if q else ""
        else:
            it = next((i for i in (g["subs"] if g else []) if i["code"] == sub), None)
            out[x] = it["what"] if it else ""
    return out


def options(p: Project, code: str, limit: int = 400) -> dict:
    """「＋ 加一样」能挑的：戒律文件、模块、工具卡、材料（资料/ 里的文件，单上列的模块排前面）、存档。"""
    wo = get(p, code)
    mods = sorted(proj.module_dirs(p))
    auto = {r.get("file") for r in readiness.rule_stack(p, wo)}                     # 自动带上的不用再加
    rules = []
    if (p.materials / "戒律").is_dir():
        rules += sorted(gp.relative(p, f) for f in gp.rule_files(p))
    rules += [gp.relative(p, gp.module_rule(p, m)) for m in mods if m != "戒律" and gp.module_rule(p, m).is_file()]
    rules = [r for r in rules if r not in auto]
    mats = []
    for m in [x for x in wo["modules"] if x in mods] + [x for x in mods if x not in wo["modules"]]:   # 单上列的模块排前面
        base = p.materials / m
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "_")))
            for f in sorted(filenames):
                if f.startswith((".", "~$")) or f == "戒律.md":
                    continue
                mats.append((Path(dirpath) / f).relative_to(p.root).as_posix())
                if len(mats) >= limit:
                    break
            if len(mats) >= limit:
                break
    return {"rules": rules, "modules": mods,
            "tools": [{"code": t["code"], "name": t["name"], "kind": t["kind"], "state": t["state"]} for t in tools.list_tools(p.root / "工具库")],
            "materials": mats, "more": len(mats) >= limit,
            "saves": [{"code": s["code"], "name": s["name"], "settled": bool(s.get("settled"))} for s in snapshot.list_saves(p)]}


# ---------------------------------------------------------------- 照目标配齐

_PATH = re.compile(r"资料/[^\s`'\"（）()，。、；|*]+")


def derive(p: Project, target: list[str]) -> dict:
    """按目标推出该用到的：模块（S1 写的「动到的模块」，或目标本身就是模块）、需求和蓝图里提到的工具和文件、
    定性过的最近一档。戒律不用列：通用、项目、模块的自动带上（readiness.rule_stack）。"""
    import requirements
    bp = blueprint.pyramid(p)
    items, _ = readiness.scope_items(bp, target, p)
    gs = readiness.target_goals(bp, target)
    mods = []
    for g in gs:
        mods += [m for m in g["modules"] if m not in mods]
    for x in target:                                              # 还没写蓝图的模块也算上
        m = readiness.split_target(x)[0]
        if m not in mods and not re.match(r"S\d", m) and proj.module_dir(p, m):
            mods.append(m)
    texts = [g["one_line"] for g in gs] + [f"{x['what']} {x['how']}" for _, x in items]
    for m in mods:
        r = requirements.read(p, m)
        texts += [f"{q['func']} {q['effect']}" for q in (r["reqs"] if r else [])]
    mention = " ".join(texts)
    codes = re.findall(r"T\d+", mention)
    tl = [t["code"] for t in tools.list_tools(p.root / "工具库") if t["code"] in codes or (t["name"] and t["name"] in mention)]
    mats = [f"资料/{m}/技能/SKILL.md" for m in mods if (p.materials / m / "技能" / "SKILL.md").is_file()]   # 模块专属技能
    for x in _PATH.findall(mention):
        x = x.rstrip("/")
        if x not in mats and gp.resolve(p, x).exists() and not x.endswith(("需求.md", "蓝图.md", "戒律.md")):
            mats.append(x)
    settled = [s for s in snapshot.list_saves(p) if s.get("settled")]
    saves = [settled[0]["code"]] if settled else []
    return {"rules": [], "modules": mods, "tools": tl, "materials": mats, "saves": saves}


# ---------------------------------------------------------------- 写

def _next(conn, p: Project) -> str:
    n = int(store._meta(conn, "workorder_seq") or 0)
    n = max([n] + [x["n"] for x in list_all(p)]) + 1
    store._set_meta(conn, "workorder_seq", str(n))
    return f"K{n}"


def _check_target(p: Project, target: list[str]) -> list[str]:
    target = [" ".join(s.split()) for s in target if s and s.strip()]

    import requirements
    def ok(s: str) -> bool:
        goal = readiness.split_target(s)[0]
        if re.match(r"S\d", goal):
            return bool(_SCOPE.fullmatch(s))
        return bool(goal) and (proj.module_dir(p, goal) is not None or goal in {x["key"] for x in __import__("governance").module_catalog(p)} or (readiness.split_target(s)[1].startswith("需-") and requirements.read(p, goal) is not None))     # 模块：得真有这个模块
    bad = [s for s in target if not ok(s)]
    if bad:
        raise store.Refused(f"目标写成「文献」（整个模块）、「文献 需-2」「文献 S2-3」，或总蓝图的「S1-10」「S1-10 S2-3」：{'、'.join(bad)}")
    return target


def _rel(p: Project, x: str) -> str:
    """材料、戒律的路径：一律从项目根写、用 /；项目外面的不收。"""
    x = x.strip().strip('"').replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", x) or x.startswith("/"):
        try:
            x = Path(x).resolve().relative_to(p.root.resolve()).as_posix()
        except ValueError:
            raise store.Refused(f"要在项目里面：{x}（项目外面的先拖进项目）")
    while x.startswith("./"):
        x = x[2:]
    if ".." in x.split("/"):
        raise store.Refused(f"要在项目里面：{x}")
    return x


def create(conn, p: Project, name: str, target: list[str], product: str = "", *, module: str = "", by: str = "人") -> dict:
    """新开一张。给了 module：目标默认整个模块，名字默认「<模块>模块装修」，要做成什么用需求里那句。"""
    import requirements
    module = _flat(module)
    if module:
        if proj.module_dir(p, module) is None and module not in {x["key"] for x in __import__("governance").module_catalog(p)}:
            raise store.Refused(f"没有「{module}」这个模块")
        target = target or [module]
        name = _flat(name) or f"{module}模块装修"
        r = requirements.read(p, module)
        product = product or (r["one_line"] if r else "")
    name = _flat(name)
    if not name:
        raise store.Refused("开工单要有个名字")
    target = _check_target(p, target)
    st = runs.settings(conn)
    with store.tx(conn):
        code = _next(conn, p)
        wo = {"code": code, "name": name, "stored": "备料", "product": _flat(product), "target": target,
              "level": st["level"] if st["level"] in (1, 2) else 1, "rounds": st["rounds"], "fails": 2, "started": "",
              "notes": {k: "" for k in NOTES}, "rest": ""} | {k: [] for k in LISTS}
        if not wo["product"] and target:
            g = blueprint.find(blueprint.pyramid(p), readiness.split_target(target[0])[0])
            wo["product"] = g["one_line"] if g else ""
        for k, v in derive(p, target).items():
            wo[k] = v
        _write(p, wo)
        store.log(conn, by, "新开工单", code, name)
    return get(p, code)


def update(conn, p: Project, code: str, fields: dict, *, by: str = "人") -> dict:
    """改一张单：名字、做成、目标、用到的（整列换）、交代（三格）、档位、圈数、失败几次停。"""
    wo = get(p, code)
    if "name" in fields:
        wo["name"] = _flat(fields["name"]) or wo["name"]
    if "product" in fields:
        wo["product"] = _flat(fields["product"])
    if "target" in fields:
        wo["target"] = _check_target(p, fields["target"])
    for k in LISTS:
        if k in fields and fields[k] is not None:
            vals = [(_rel(p, x) if k in _PATHS else _flat(x)) for x in fields[k] if _flat(x)]
            wo[k] = list(dict.fromkeys(vals))
    if fields.get("notes"):
        for k in NOTES:
            if k in fields["notes"]:
                wo["notes"][k] = (fields["notes"][k] or "").strip()
    if "level" in fields and fields["level"] is not None:
        if fields["level"] not in (1, 2):
            raise store.Refused("档位：1 半自动（计划、验收等你点头）或 2 自动")
        wo["level"] = fields["level"]
    if "rounds" in fields and fields["rounds"] is not None:
        if not 1 <= fields["rounds"] <= 50:
            raise store.Refused("每次最多几圈：1 到 50")
        wo["rounds"] = fields["rounds"]
    if "fails" in fields and fields["fails"] is not None:
        if not 1 <= fields["fails"] <= 5:
            raise store.Refused("失败几次停：1 到 5")
        wo["fails"] = fields["fails"]
    with store.tx(conn):
        _write(p, wo)
        store.log(conn, by, "改开工单", code, None)
    return get(p, code)


def fill(conn, p: Project, code: str, *, by: str = "人") -> dict:
    """照目标配齐：推出来的加进去，已经列着的不动。"""
    wo = get(p, code)
    if not wo["target"]:
        raise store.Refused("先选目标（蓝图里的 S1，或几件 S2）")
    d = derive(p, wo["target"])
    return update(conn, p, code, {k: wo[k] + [x for x in d[k] if x not in wo[k]] for k in LISTS}, by=by)


def copy(conn, p: Project, code: str, *, by: str = "人") -> dict:
    src = get(p, code)
    with store.tx(conn):
        new = dict(src, code=_next(conn, p), name=src["name"] + "（复制）", stored="备料", started="", file=None,
                   notes=dict(src["notes"]))
        _write(p, new)
        store.log(conn, by, "复制开工单", new["code"], f"从 {code}")
    return get(p, new["code"])


def _set_stored(conn, p: Project, wo: dict, stored: str, action: str, by: str) -> dict:
    wo["stored"] = stored
    if stored == "在跑":
        wo["started"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with store.tx(conn):
        _write(p, wo)
        store.log(conn, by, action, wo["code"], wo["name"])
    return get(p, wo["code"])


def start(conn, p: Project, code: str, *, by: str = "人") -> dict:
    """交给 agent：灯全绿（或只剩黄）、别的单没在跑、目标里还有要做的。"""
    wo = get(p, code)
    other = running(p)
    if other and other["code"] != code:
        raise store.Refused(f"{other['code']} {other['name']} 还在跑：一次只跑一张，先叫停它")
    if wo["stored"] == "在跑":
        return wo
    pnl = readiness.panel(conn, p, wo)
    if not pnl["ready"]:
        raise store.Refused("还有红的，交不出去：" + "、".join(pnl["red"]))
    if not any(x["status"] != "ok" for x in pnl["items"]):
        raise store.Refused("目标里没有要做的了")
    if by == "人":
        resume(conn, by)
    return _set_stored(conn, p, wo, "在跑", "交给 agent", by)


def stop(conn, p: Project, code: str, *, by: str = "人") -> dict:
    """叫停。人叫停的，agent 也不再自己开新单（dispatch 看 paused），直到人再交给 agent 或在对话里让开工。"""
    wo = get(p, code)
    if wo["stored"] != "在跑":
        raise store.Refused(f"{code} 没在跑")
    out = _set_stored(conn, p, wo, "备料", "叫停", by)
    if by == "人":
        with store.tx(conn):
            store._set_meta(conn, PAUSE, f"{datetime.now():%m-%d %H:%M} 叫停 {code}")
    return out


PAUSE = "auto_paused"


def paused(conn) -> str:
    """人叫停过、还没再开工：返回「09-30 15:20 叫停 K3」；没有返回空。"""
    return store._meta(conn, PAUSE) or ""


def resume(conn, by: str = "人") -> None:
    if paused(conn):
        with store.tx(conn):
            store._set_meta(conn, PAUSE, "")
            store.log(conn, by, "接着自动推进", None, None)


def finish(conn, p: Project, code: str, *, by: str = "人") -> dict:
    """在跑的单里 agent 没有能做的了：放下（在跑 → 备料；显示照算：做完 / 等你验收 / 备料），好开下一个目标的。"""
    wo = get(p, code)
    if wo["stored"] != "在跑":
        return wo
    return _set_stored(conn, p, wo, "备料", "跑完放下", by)


def shelve(conn, p: Project, code: str, on: bool = True, *, by: str = "人") -> dict:
    wo = get(p, code)
    if on and wo["stored"] == "在跑":
        raise store.Refused("在跑的先叫停再搁置")
    return _set_stored(conn, p, wo, "搁置" if on else "备料", "搁置开工单" if on else "拿回开工单", by)


# ---------------------------------------------------------------- 旧的全局开工单 → K1

def migrate(conn, p: Project) -> dict | None:
    """09-27 上午那版只有一张全局开工单（存在库里）。第一次打开新版时变成 K1，只做一次。"""
    if store._meta(conn, "workorder_migrated") or list_all(p):
        return None
    import json
    try:
        scope = json.loads(store._meta(conn, "auto_scope") or "[]")
    except ValueError:
        scope = []
    with store.tx(conn):
        store._set_meta(conn, "workorder_migrated", "1")
    if not scope:
        return None
    g = blueprint.find(blueprint.pyramid(p), readiness.split_target(scope[0])[0])
    wo = create(conn, p, g["name"] if g else "、".join(scope), scope, by="迁移")
    fails = _int(store._meta(conn, "auto_fails"), 2)
    wo = update(conn, p, wo["code"], {"fails": fails if 1 <= fails <= 5 else 2}, by="迁移")
    if store._meta(conn, "auto_state") == "已发动":
        wo = _set_stored(conn, p, wo, "在跑", "交给 agent", "迁移")
    return wo
