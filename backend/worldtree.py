"""世界树（S1-8 S2-55 长枝、S2-56 果实与合回主干）：从任意一档长出一根枝＝完整独立的项目副本，枝上的 agent 跟主干互不排队地干；
果实验收过了，识别枝改了什么，合回主干。

作者 10-03：「存档的世界树，因为我感觉全量存档天然就可以当一个独立的进程用来探索，这样并行agent就成了可能，在验收了世界树存档分支的
果实demo之后，如果合适就合并进主干；这样agent并发调度就成了可能，就跟现在这个对话分叉一样，我这个直接项目独立分叉；
最后识别改动的代码之后合并进主项目」；枝选「完整独立的项目副本」，合并选「G1 验收后直接合」。

- 枝放在项目旁边：`<项目名> 世界树/枝-<号> 名字/`（不在项目里面，免得被扫描、被监管当成乱改）
- 长枝：那一档的清单逐个从对象库取出来（snapshot._content），库用那一档的 库.sqlite；
  枝根上 `枝.json`（号、名字、为了什么、从哪一档、状态……）和 `.世界树底.json`（长出来那一档的清单，合并时当底）；
  主干上记一份 `自动化/世界树/枝-<号>.json`；长出来那一档钉住（存档清理时不丢，合并要它当底）
- 枝自己就是一个项目：它的 backend/ 跑起来是它自己的后台、端口、核心锁、认领、存档；agent 的接口（mcp_server）在枝的文件夹里跑，就只碰枝
- 结果实：枝上标「结果了」＋ demo 说明 ＋ 检查，存一档（在枝里调 bear_fruit）
- 合回主干（G1 验收后）：拿底比——只枝改的直接换上；两边都改了的文本用 git merge-file 三方合并；合不开的、二进制两边都改的，
  不覆盖主干，放进 `自动化/世界树/枝-<号>/冲突/` 交人处理；枝上自己的记录（交付单、日志、交接……）原样收进 `自动化/世界树/枝-<号>/记录/`，
  不并进主干的编号；合之前、合完各存一档；本机 git 记一次
- 砍掉：枝停掉，文件夹挪到 `<项目名> 世界树/.回收/`（能拿回来），记录留着
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import snapshot
import builtin
import store
from project import CODE_DIR, Project

META, BASE = "枝.json", ".世界树底.json"
REG = "自动化/世界树"
STATES = ("长着", "结果了", "合了", "砍了")
RECORDS = ("自动化/交付/", "自动化/日志/", "自动化/交接/", "自动化/答疑/", "自动化/施工计划/", "自动化/开工单/", "自动化/世界树/",
           "自动化/运行状态/", "自动化/agent/", "笔记/日志/", "计划/", "治理/计划/")   # 员工档案在枝上为干活改的（比如不审施工计划）不带回主干                       # 枝上自己的记录：原样收进主干的 自动化/世界树/枝-n/记录/，不并进主干编号
SKIP = (".世界树底.json", "枝.json")
PORTS = range(8771, 8800)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def forest(p: Project) -> Path:
    """枝都放这：默认项目旁边的「<项目名> 世界树」；设置 → 存档 → 世界树 里能换地方（S1-8 S2-59）。"""
    import knobs
    d = str(knobs.peek(p, "wt_dir") or "").strip()
    return Path(d) if d else p.root.parent / f"{p.root.name} 世界树"


def live(p: Project) -> list[dict]:
    """还活着的枝（长着、结果了，文件夹还在）。"""
    return [b for b in list_branches(p) if b.get("state") in ("长着", "结果了") and b.get("exists")]


def space(p: Project) -> dict:
    """存档和世界树一共占多大（枝按长出来时记下的大小算，不去数文件）：{saves, branches, recycle, total}。"""
    br = rc = 0
    for b in list_branches(p):
        if not Path(b.get("path", "")).is_dir():
            continue
        if b.get("state") in ("长着", "结果了"):
            br += int(b.get("bytes") or 0)
        else:
            rc += int(b.get("bytes") or 0)
    sv = snapshot.total_size(p)
    return {"saves": sv, "branches": br, "recycle": rc, "total": sv + br + rc}


def recycle_old(p: Project, days: int) -> list[dict]:
    """世界树 .回收 里放了超过 days 天的（提醒人清；彻底删要人点）。"""
    d = forest(p) / ".回收"
    out = []
    if d.is_dir():
        now = time.time()
        for x in d.iterdir():
            try:
                age = (now - x.stat().st_mtime) / 86400
            except OSError:
                continue
            if x.is_dir() and age >= days:
                out.append({"name": x.name, "days": int(age)})
    return out


def _reg(p: Project) -> Path:
    return p.root / REG


def is_branch(p: Project) -> dict | None:
    """这个项目自己是不是一根枝（枝根上有 枝.json）。"""
    try:
        return json.loads((p.root / META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(f: Path, d: dict) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def list_branches(p: Project) -> list[dict]:
    """主干记着的每根枝（新的在前），状态以枝自己的 枝.json 为准（枝上结了果实主干马上看得到）。"""
    out = []
    for f in sorted(_reg(p).glob("枝-*.json"), key=lambda f: -int(f.stem.split("-")[1])):
        try:
            b = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        live = None
        try:
            live = json.loads((Path(b["path"]) / META).read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError):
            pass
        if live and b.get("state") in ("长着", "结果了"):
            for k in ("state", "demo", "checks", "fruit_at", "fruit_by", "fruit_checkpoint"):
                if k in live:
                    b[k] = live[k]
        b["exists"] = Path(b.get("path", "")).is_dir()
        out.append(b)
    return out


def get(p: Project, code: str) -> dict:
    b = next((x for x in list_branches(p) if x["code"] == code), None)
    if b is None:
        raise store.Refused(f"没有 {code} 这根枝")
    return b


def _save_reg(p: Project, b: dict) -> None:
    _write(_reg(p) / f"{b['code']}.json", {k: v for k, v in b.items() if k != "exists"})


# ---------------------------------------------------------------- 长枝

def grow(conn, p: Project, *, name: str, by: str, why: str = "", base: str = "现在", for_: str = "", item: str = "",
         group: str = "") -> dict:
    """从一档（或现在：先存一档）长出一根枝：那一档完整取出来，放到项目旁边。
    受设置管着（S1-8 S2-59）：同时最多几根活着的枝、存档和世界树一共最多占多大。item / group：自动排枝（档位 3、4）时这根枝做哪件、属于哪张比较单。"""
    import knobs
    name = snapshot._check_name(name)
    n_live, most = len(live(p)), knobs.get(conn, "wt_max")
    if n_live >= most:
        raise store.Refused(f"已经有 {n_live} 根枝长着（设置里最多 {most} 根）：先合回或砍掉几根，或者在设置里调大")
    cap = knobs.get(conn, "cap_gb") << 30
    last = snapshot.latest(p)
    need = last.get("total_bytes", 0) if last else 0
    if cap and space(p)["total"] + need > cap:
        raise store.Refused(f"存档和世界树已经占 {snapshot._human(space(p)['total'])}，再长一根（约 {snapshot._human(need)}）"
                            f"就超出设置里的空间上限（{knobs.get(conn, 'cap_gb')} GB）：先合回或砍掉几根、清一下世界树的 .回收，或者在设置里调大")
    if base in ("", "现在"):
        m = snapshot.save(conn, p, name=f"长枝前 {name}"[:40], why=f"从现在长一根枝「{name}」：{why}"[:200], mode="全量", by=by,
                          auto=bool(item))                # 自动排枝存的算自动档，不挤掉手动的
        base = m["code"]
    folder = snapshot._folder(p, base)
    meta, manifest = snapshot._meta(folder), snapshot._files(folder)
    n = 1 + max([0] + [int(f.stem.split("-")[1]) for f in _reg(p).glob("枝-*.json")])
    code = f"枝-{n}"
    dest = forest(p) / f"{code} {name}"
    if dest.exists():
        raise store.Refused(f"{dest} 已经有了")
    missing = []
    try:
        for rel, v in manifest.items():
            src = snapshot._content(p, folder, rel, v)
            if src is None:
                missing.append(rel)                          # 老的核心档没存这些（资料、笔记……）：枝里没有
                continue
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
        db = folder / "库.sqlite"
        (dest / "索引").mkdir(parents=True, exist_ok=True)
        if db.is_file():
            shutil.copy2(db, dest / "索引" / "state.db")
        c = store.connect(dest / "索引" / "state.db")
        try:
            store.migrate(c)
            with store.tx(c):                            # 枝自己不自动开窗口、核心锁和认领从空的开始：枝上的活由主干派（assign / open_window）
                store._set_meta(c, "auto_launch", "0")
                c.execute("CREATE TABLE IF NOT EXISTS claim(goal TEXT NOT NULL, sub TEXT NOT NULL, agent TEXT NOT NULL, lanes TEXT NOT NULL, "
                          "what TEXT NOT NULL DEFAULT '', since TEXT NOT NULL, beat REAL NOT NULL, PRIMARY KEY(goal, sub))")
                c.execute("DELETE FROM claim")
        finally:
            c.close()
        gone = set(missing)
        _write(dest / BASE, {"base": base, "files": {k: v for k, v in manifest.items() if k not in gone}})   # 没取出来的不算底，免得合并时当成枝删了
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    b = {"code": code, "name": name, "why": " ".join(why.split()), "for": for_.strip(), "base": base, "base_at": meta.get("at", ""),
         "path": str(dest), "by": by, "at": _now(), "state": "长着", "port": None, "pid": None, "missing": missing[:200],
         "missing_count": len(missing), "files": len(manifest) - len(missing),
         "bytes": sum(v[0] for k, v in manifest.items() if k not in gone), "item": item, "group": group, "auto": bool(item)}
    _write(dest / META, b)
    _save_reg(p, b)
    snapshot.pin(p, base, code)
    store.log(conn, by, "长枝", code, f"{name} · 从 {base} · {b['files']} 个文件" + (f" · 那一档没存 {len(missing)} 个" if missing else ""))
    return b


# ---------------------------------------------------------------- 枝的后台（看 demo 用）

def _ping(port: int) -> bool:
    try:
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def _free() -> int:
    for port in PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise store.Refused("8771～8799 的端口都被占了")


def start(p: Project, code: str) -> dict:
    """把枝的后台起起来（在跑就接上），给它的网页地址。枝自己的 backend/main.py，自己的端口。"""
    b = get(p, code)
    if b.get("port") and _ping(b["port"]):
        return b | {"url": f"http://127.0.0.1:{b['port']}/", "running": True}
    root = Path(b["path"])
    if not (root / "backend" / "main.py").is_file():
        raise store.Refused(f"{code} 里没有 backend/main.py，起不了后台")
    port = _free()
    log = open(root / "索引" / "世界树后台.log", "ab") if (root / "索引").is_dir() else subprocess.DEVNULL
    proc = subprocess.Popen([sys.executable, str(root / "backend" / "main.py"), "--port", str(port), "--no-browser"], cwd=root,
                            stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    t0 = time.time()
    while time.time() - t0 < 30:
        if _ping(port):
            break
        time.sleep(0.4)
    else:
        raise store.Refused(f"{code} 的后台 30 秒没起来，看 {root / '索引' / '世界树后台.log'}")
    b.update(port=port, pid=proc.pid)
    _save_reg(p, b)
    return b | {"url": f"http://127.0.0.1:{port}/", "running": True}


def stop(p: Project, code: str) -> None:
    """停掉枝的后台（连它的子进程）。"""
    b = get(p, code)
    if b.get("pid"):
        subprocess.run(["taskkill", "/PID", str(b["pid"]), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    b.update(port=None, pid=None)
    _save_reg(p, b)


def running(b: dict) -> bool:
    return bool(b.get("port")) and _ping(b["port"])


# ---------------------------------------------------------------- 在枝上干活

def branch_db(b: dict) -> sqlite3.Connection:
    return store.connect(Path(b["path"]) / "索引" / "state.db")


def assign(conn, p: Project, code: str, agent_key: str, goal: str = "", sub: str = "", *, by: str, open_window: bool = True,
           call=None, plan_free: bool = False) -> dict:
    """派到枝上：给了哪件，就在枝自己的库里替这个员工领下（它在枝上开工、next_task 就拿到）；
    open_window：在主干的网页终端里给它开一个窗口，标题「枝-3 · G5 名字」，进的是枝的文件夹、接的是枝的接口。"""
    import agents
    import blueprint
    import claims
    b = get(p, code)
    if b["state"] != "长着":
        raise store.Refused(f"{code} 是「{b['state']}」，不再派活")
    bp = Project(Path(b["path"]))
    a = agents.get(bp, agent_key)
    who = agents.actor(a["name"])
    task = ""
    if goal and sub:
        g = blueprint.find(blueprint.pyramid(bp), goal)
        x = next((x for x in (g or {}).get("subs", []) if x["code"] == sub), None)
        if not g or not x:
            raise store.Refused(f"{code} 的蓝图里没有 {goal} {sub}")
        c = branch_db(b)
        try:
            claims.claim(c, goal, sub, who, claims.lanes_of(g, x), x.get("what", "")[:80])
            if plan_free and a.get("plan_required"):           # 自动排的枝上没人审施工计划：枝上这份档案不审，果实统一验（档案不带回主干）
                agents.update(c, bp, a["code"], {"plan_required": False}, by="自动排枝", why="枝上果实统一验收", _authorized=True)
        finally:
            c.close()
        task = f"{goal} {sub}"
    b.setdefault("agents", [])
    if a["code"] not in b["agents"]:
        b["agents"].append(a["code"])
    _save_reg(p, b)
    l = agents.launcher(bp, a["code"], code_dir=bp.root, tag=code)
    out = {"branch": code, "agent": a["code"], "name": a["name"], "task": task, "window": None,
           "launch": {"title": l["title"], "cmd": l["cmd"]}}          # 网页拿这个排进「窗口」开标签
    if open_window:                                                    # agent 派的、自动排的：后台直接在网页终端里开
        import autolaunch
        (call or (lambda m, path, body=None: autolaunch._call(p, m, path, body)))("POST", "/api/terms", {"title": l["title"], "cmd": l["cmd"]})
        out["window"] = l["title"]
    store.log(conn, by, "派到枝上", code, f"{a['code']} {a['name']}" + (f" · {task}" if task else "") + (" · 开了窗口" if open_window else ""))
    return out


def held(b: dict) -> list[dict]:
    """枝上谁领着什么（读枝自己的库）。"""
    import claims
    try:
        c = branch_db(b)
    except Exception:
        return []
    try:
        return claims.active(c)
    except Exception:
        return []
    finally:
        c.close()


# ---------------------------------------------------------------- 结果实（在枝里调）

def bear_fruit(conn, p: Project, *, demo: str, checks: list[dict] | None, by: str) -> dict:
    """枝上干完了：存一档、标「结果了」、写 demo 说明（怎么看、看什么）和检查。只能在枝里调。"""
    b = is_branch(p)
    if b is None:
        raise store.Refused("这里是主干，不是枝：结果实要在枝里做")
    if b.get("state") not in ("长着", "结果了"):
        raise store.Refused(f"这根枝是「{b.get('state')}」")
    demo = " ".join((demo or "").split())
    if not demo:
        raise store.Refused("写一句 demo 说明：怎么看、看什么")
    m = snapshot.save(conn, p, name=f"果实 {b['code']}"[:40], why=demo[:200], mode="全量", by=by, checks=checks)
    b.update(state="结果了", demo=demo, checks=snapshot._norm_checks(checks), fruit_at=_now(), fruit_by=by, fruit_checkpoint=m["code"])
    _write(p.root / META, b)
    store.log(conn, by, "结果了", b["code"], demo[:200])
    return b


# ---------------------------------------------------------------- 识别改动、合回主干

def _is_record(rel: str) -> bool:
    import builtin
    return not builtin.is_template(rel) and rel.startswith(RECORDS)


def changes(p: Project, code: str) -> dict:
    """拿长出来那一档当底，比枝和主干各改了什么，分成：只枝改（直接换上）· 枝删了 · 两边都改（要三方合并）· 两边改得一样 · 枝上的记录。"""
    b = get(p, code)
    root = Path(b["path"])
    base = json.loads((root / BASE).read_text(encoding="utf-8"))["files"]
    bp = Project(root)
    branch_now = snapshot.scan(bp, {k: v for k, v in base.items()})
    last = snapshot.latest(p)
    trunk_now = snapshot.scan(p, snapshot._files(snapshot._folder(p, last["code"])) if last else None)
    out = {"take": [], "delete": [], "both": [], "same": [], "records": [], "trunk_only": 0}
    for rel in sorted(set(base) | set(branch_now)):
        if rel in SKIP or rel.startswith("索引/"):
            continue
        b0 = base.get(rel, [None, None, None])[2]
        b1 = branch_now.get(rel, [None, None, None])[2]
        if b1 == b0:
            continue
        if _is_record(rel):
            if b1 is not None:
                out["records"].append(rel)
            continue
        t = trunk_now.get(rel, [None, None, None])[2]
        if t == b1:
            out["same"].append(rel)
        elif t == b0:
            (out["delete"] if b1 is None else out["take"]).append(rel)
        else:
            out["both"].append(rel)
    out["trunk_only"] = sum(1 for rel in set(base) | set(trunk_now)
                            if trunk_now.get(rel, [None] * 3)[2] != base.get(rel, [None] * 3)[2]
                            and branch_now.get(rel, [None] * 3)[2] == base.get(rel, [None] * 3)[2])   # 主干同期自己改的（合并不动）
    out["counts"] = {k: len(out[k]) for k in ("take", "delete", "both", "same", "records")}
    return out


def _core(rel: str) -> bool:
    import scanmap
    return rel == builtin.MARKS_FILE or rel.startswith("backend/") or rel in scanmap.CORE_FILES


def _git() -> str | None:
    import vcs
    try:
        return vcs._git() or shutil.which("git")
    except Exception:
        return shutil.which("git")


def _merge_text(p: Project, base_sha: str | None, ours: Path, theirs: Path) -> tuple[int, bytes]:
    """git merge-file：以那一档为底，把枝的改动合进主干这份。→ (冲突处数, 合出来的内容)；-1 = 没法合（不是文本、没 git）。"""
    git = _git()
    if not git:
        return -1, b""
    with tempfile.TemporaryDirectory() as d:
        bf = Path(d) / "base"
        src = snapshot.obj_path(p, base_sha) if base_sha else None
        bf.write_bytes(src.read_bytes() if src and src.is_file() else b"")
        of, tf = Path(d) / "ours", Path(d) / "theirs"
        shutil.copy2(ours, of)
        shutil.copy2(theirs, tf)
        for f in (of, bf, tf):
            if b"\0" in f.read_bytes()[:8000]:
                return -1, b""                                   # 二进制
        r = subprocess.run([git, "merge-file", "-p", "-L", "主干", "-L", "长枝那一档", "-L", "枝", str(of), str(bf), str(tf)],
                           capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (r.returncode if r.returncode >= 0 else -1), r.stdout


def _branch_marks_merge(p, branch, base, plan):
    """按文件路径集合三方合名单；新标记引用被删内容时留冲突，不复活内容。"""
    rel = builtin.MARKS_FILE
    touched = any(rel in plan[k] for k in ("take", "delete", "both", "same"))
    ours = builtin.read_marks(p.root)
    if not touched:
        return {"changed": False, "revision": ours["revision"], "paths": ours["paths"], "conflicts": []}
    root = Path(branch["path"])
    try:
        raw = snapshot._current_marks_bytes(root)
    except (builtin.Invalid, OSError, store.Refused) as exc:
        return {"changed": False, "revision": ours["revision"], "paths": ours["paths"],
                "conflicts": [{"path": rel, "why": "枝的内置标记正本不可读：" + str(exc)}]}
    old = base.get(rel)
    original = b""
    if old:
        hit = snapshot._find_copy(p, old[2], branch["base"])
        if not hit:
            return {"changed": False, "revision": ours["revision"], "paths": ours["paths"],
                    "conflicts": [{"path": rel, "why": "标记基底内容不存在，无法核对历史名单"}], "branch_raw": raw}
        original = hit[1].read_bytes()
    try:
        base_paths = set(builtin.parse_marks(original)["paths"] if original else [])
        branch_paths = set(builtin.parse_marks(raw)["paths"] if raw else [])
        current = set(ours["paths"])
        merged = (base_paths - (base_paths - current) - (base_paths - branch_paths)) | (current - base_paths) | (branch_paths - base_paths)
        # 删除或双方内容冲突不能被一条新锁掩盖；原有missing名单仍可保留。
        for path in sorted(merged - base_paths):
            if path in plan["delete"] or path in plan["both"]:
                raise builtin.Invalid("新标记的原件同时删除或内容待解决：" + path)
            target = root / path if path in plan["take"] else p.root / path
            builtin.path(root if path in plan["take"] else p.root, path, exists=False)
            if not target.is_file():
                raise builtin.Invalid("新标记在合并后没有对应原件：" + path)
        paths = builtin.parse_marks(json.dumps({"version": 1, "paths": sorted(merged)}, ensure_ascii=False).encode("utf-8"))["paths"]
    except (builtin.Invalid, OSError) as exc:
        return {"changed": False, "revision": ours["revision"], "paths": ours["paths"],
                "conflicts": [{"path": rel, "why": "内置标记合并待处理：" + str(exc)}], "branch_raw": raw, "base_raw": original}
    category = "merged" if rel in plan["both"] else "took"
    return {"changed": paths != ours["paths"], "revision": ours["revision"], "paths": paths,
            "conflicts": [], "category": category}


def merge(conn, p: Project, code: str, *, by: str) -> dict:
    with builtin.marks_guard(p.root):
        return _merge_locked(conn, p, code, by=by)


def _merge_locked(conn, p: Project, code: str, *, by: str) -> dict:
    """G1 验收过了，合回主干。合之前、合完各存一档；合不开的不覆盖，放进 自动化/世界树/枝-n/冲突/。"""
    import trash
    b = get(p, code)
    if b["state"] not in ("结果了", "长着"):
        raise store.Refused(f"{code} 是「{b['state']}」，合不了")
    root = Path(b["path"])
    base = json.loads((root / BASE).read_text(encoding="utf-8"))["files"]
    plan = changes(p, code)
    touch = plan["take"] + plan["delete"] + plan["both"]
    if any(_core(r) for r in touch):                      # 合进来的有核心文件：核心锁在别人手里就不合（他正改着，会撞）
        import claims
        other = next((r for r in claims.active(conn) if r["goal"] == claims.CORE and r["agent"] != by), None)
        if other:
            raise store.Refused(f"核心锁在 {other['agent']} 手里：等它交了再合 {code}（{code} 改到了核心文件）")
    marks = _branch_marks_merge(p, b, base, plan)
    for key in ("take", "delete", "both", "same"):
        plan[key] = [rel for rel in plan[key] if rel != builtin.MARKS_FILE]
    before = snapshot.save(conn, p, name=f"合{code}前"[:40], why=f"合回 {code}「{b['name']}」之前", mode="全量", by=by)
    arch = _reg(p) / code
    took, deleted, merged, conflicts = [], [], [], list(marks["conflicts"])
    if marks["conflicts"]:
        out = arch / "冲突" / builtin.MARKS_FILE
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(marks.get("branch_raw", b""))
        (out.parent / (builtin.MARKS_FILE + ".主干")).write_bytes(snapshot._current_marks_bytes(p.root))
        if "base_raw" in marks:
            (out.parent / (builtin.MARKS_FILE + ".基底")).write_bytes(marks["base_raw"])
    for rel in plan["take"]:
        dst = p.root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
        took.append(rel)
    if plan["delete"]:
        trash.move_many(conn, p, plan["delete"], by=by, reason=f"合回 {code}：枝上删了这些", origin=f"合 {code} 删的")
        deleted = list(plan["delete"])
    for rel in plan["both"]:
        ours, theirs = p.root / rel, root / rel
        if not theirs.is_file() or not ours.is_file():
            conflicts.append({"path": rel, "why": "一边删了、一边改了"})
            if theirs.is_file():
                (arch / "冲突" / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(theirs, arch / "冲突" / rel)
            continue
        n, text = _merge_text(p, base.get(rel, [None] * 3)[2], ours, theirs)
        if n == 0:
            ours.write_bytes(text)
            merged.append(rel)
        else:
            out = arch / "冲突" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            if n > 0:
                out.write_bytes(text)                            # 带冲突标记的那份，人或 agent 照着手合
            else:
                shutil.copy2(theirs, out)                        # 二进制：枝的那份放着
            conflicts.append({"path": rel, "why": f"{n} 处合不开" if n > 0 else "二进制，两边都改了"})
    if marks["changed"]:
        builtin.replace_marks(p.root, marks["paths"], marks["revision"])
        (merged if marks["category"] == "merged" else took).append(builtin.MARKS_FILE)
    for rel in plan["records"]:
        out = arch / "记录" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, out)
    after = snapshot.save(conn, p, name=f"合了{code}"[:40],
                          why=f"合回 {code}「{b['name']}」：换上 {len(took)}、三方合并 {len(merged)}、删 {len(deleted)}、合不开 {len(conflicts)}、记录 {len(plan['records'])}",
                          mode="全量", by=by)
    result = {"before": before["code"], "after": after["code"], "took": took, "merged": merged, "deleted": deleted,
              "conflicts": conflicts, "records": len(plan["records"]), "same": len(plan["same"]), "at": _now(), "by": by}
    _write(arch / "合并.json", result)
    try:
        import vcs
        if vcs.enabled(p):
            vcs.commit(p, took + merged + deleted + [REG], agent=by, message=f"合枝 {code} · {b['name']}")
    except Exception:
        pass
    try:
        stop(p, code)
    except Exception:
        pass
    b = get(p, code)
    b.update(state="合了", merged=result, merged_at=result["at"])
    try:
        _write(root / META, {**json.loads((root / META).read_text(encoding="utf-8")), "state": "合了", "merged_at": result["at"]})
    except (OSError, ValueError):
        pass
    import knobs
    if knobs.get(conn, "wt_after") == "挪进 .回收":
        moved = _shelve(p, root)                           # 合完枝的文件夹挪进 .回收（能拿回来；改动和记录已经在主干）
        if moved:
            b["path"] = str(moved)
    _save_reg(p, b)
    checks = b.get("checks") or []
    if knobs.get(conn, "auto_settle") and checks and all(c.get("ok") for c in checks) and not conflicts:
        snapshot.settle(conn, p, after["code"], by="人（设置里开了自动定性）")   # 果实检查全过、合得干净：合完那一档定性
    snapshot.unpin(p, b["base"], code)
    store.log(conn, by, "合回主干", code, f"换上 {len(took)} · 三方合并 {len(merged)} · 删 {len(deleted)} · 合不开 {len(conflicts)}")
    return result


def reject(conn, p: Project, code: str, *, by: str, why: str) -> dict:
    """验收不过，打回：枝接着长（状态回「长着」，打回的话写进 枝.json，枝上的 agent 看 world_tree 就知道）。"""
    b = get(p, code)
    if b["state"] != "结果了":
        raise store.Refused(f"{code} 是「{b['state']}」，没有果实可打回")
    why = " ".join((why or "").split())
    if not why:
        raise store.Refused("写一句为什么打回：哪里不对、要怎么改")
    root = Path(b["path"])
    live = json.loads((root / META).read_text(encoding="utf-8"))
    live.setdefault("rejected", []).append({"at": _now(), "by": by, "why": why, "fruit": live.get("fruit_checkpoint", "")})
    live["state"] = "长着"
    _write(root / META, live)
    b.update(state="长着", rejected=live["rejected"])
    _save_reg(p, b)
    store.log(conn, by, "打回果实", code, why[:200])
    return b


def _shelve(p: Project, src: Path) -> Path | None:
    """枝的文件夹挪到 <项目名> 世界树/.回收/（不删，能拿回来）。刚停的后台可能还占着文件：等一下再试，挪不动返回 None。"""
    if not src.is_dir():
        return None
    dst = forest(p) / ".回收" / f"{datetime.now().strftime('%m%d-%H%M')} {src.name}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    for i in range(10):
        try:
            os.replace(src, dst)
            return dst
        except OSError:
            time.sleep(0.5)
    return None


def cut(conn, p: Project, code: str, *, by: str, why: str = "") -> dict:
    """砍掉一根枝：停后台，文件夹挪到 <项目名> 世界树/.回收/（能拿回来），记录留着。"""
    b = get(p, code)
    if b["state"] == "合了":
        raise store.Refused(f"{code} 已经合回主干了")
    try:
        stop(p, code)
    except Exception:
        pass
    import knobs
    dst = _shelve(p, Path(b["path"])) if knobs.get(conn, "wt_after") == "挪进 .回收" else None
    if dst is None and Path(b["path"]).is_dir() and knobs.get(conn, "wt_after") == "挪进 .回收":
        raise store.Refused(f"{code} 的文件夹挪不动（可能还有程序开着它），关掉再砍")
    b = get(p, code)
    b.update(state="砍了", cut_at=_now(), cut_why=" ".join(why.split()), path=str(dst or b["path"]))
    _save_reg(p, b)
    snapshot.unpin(p, b["base"], code)
    store.log(conn, by, "砍枝", code, why[:200])
    return b
