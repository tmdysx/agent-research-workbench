"""存档：游戏存档那样，过了一关存一个好节点，出事能回去。项目根 `存档/`，跟 回收站/ 并排。

作者 2026-09-22：「就是打游戏先储存，死了之后到复活点复活」「做完一个阶段的压力测试、过了之后保存一个好的节点」。
作者 2026-09-25：「除了保存一份文件的指纹之外，还可以按照用户的需求，复制特定的文件到那个存档的文件夹里」「存档也要有全量保存的选项」。
- 一档一个文件夹 `存档/C3 名字/`：档.json（名字、为什么、存法、检查、凭据、定性）· 指纹.json（全部文件的指纹）·
  库.sqlite（当时的数据库）· 文件/（真复制进来的文件，按原路径放）。每档自己完整，删一档就是挪走一个文件夹
- 存法三种：全量（全复制）· 自定义（复制你勾的）· 只记指纹（不复制）。每档都记下全部文件的指纹，所以哪一档都能比
- 先写进 `存档/.正在存/`，写完再改名，存到一半断电也不会留下坏档
- 复活：换下来的现有文件、这一档之后新加的，一律进回收站（一批一个编号）；笔记、计划、日志、答疑不倒回
- **只存核心、只留 10 档**（作者 2026-09-30：「没必要每次都全量存档，还有很多老版本其实可以丢了，只保留10个左右的存档就行了」
  「对，只存核心就行了……像那种外部文件和其他的乱七八糟的文件不存，那些都是测试文件」）：
  存法对人和 agent 只剩「核心」（程序和规矩，见 CORE）和「只记指纹」；全量、自定义只留给老档和测试。
  每存一档自动清：留最近 KEEP 档 + 最近一档定性过的，别的彻底丢掉（记进 存档/已丢.json、清单、日志）；
  老的全量档瘦身成核心档（slim）
- **只记改动、哪一档都能还原成一整份**（S1-8 S2-53；作者 10-03「只有要有分支的节点要全量；不分支的记录改动的地方就行」）：
  文件按内容（sha256）只存一份，放 `存档/.对象/ab/abcdef…`，几档共用；一档自己只留清单（指纹.json）+ 档.json + 库.sqlite。
  新存一档只多存改了的文件，所以人和 agent 存的都是「全量」（清单写全项目），不再分核心、只记指纹；
  老档的 `文件/` 迁进对象库（migrate_objects）；取文件先看这一档自己的 `文件/`（老档），再看对象库。
  复活默认只换程序和规矩（CORE）；要整份回到那一档，用世界树从那一档长一根枝
- **照设置存、照设置留**（S1-8 S2-59；作者 10-03「存档可以设计成最多存多少档，默认如何存档等等，可以自定义多一点」）：
  最多留几档、自动存的另留几个、改核心前 / 交付后 / 定时自动存、空间上限，都在 设置 → 存档（knobs）。
  自动存的档名字带「自动 ·」、档.json 里 auto=true，另算个数，不挤掉人和 agent 手动存的；定性过的、长了枝的总留着；
  超了空间上限先丢最老的自动档
"""
from __future__ import annotations

import hashlib
import json
import atomic
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import blueprint
import builtin
import notebook
import store
import trash
from project import _BAD_CHARS, _RESERVED, Project

DIR = "存档"
LIST = "清单.md"
IGNORE = "存档忽略.txt"
TMP = ".正在存"
MODES = ("核心", "只记指纹", "全量", "自定义")      # 对人和 agent 只给前两个（OFFERED）；后两个是老档和测试用的
OFFERED = ("全量",)                                   # 10-03 起人和 agent 都存全量：内容进对象库只存一份，不重抄
OBJ = ".对象"                                          # 存档/.对象/ab/abcdef…：按 sha256 只存一份的文件内容
CORE = ["backend", "模板.html", "界面英文.js", "治理界面.js", "启动.bat", "新项目.bat", ".mcp.json", ".claude/settings.json", ".gitignore",
        "AGENTS.md", "CLAUDE.md", "DESIGN.md", "README.md", "使用说明.md", "使用说明.en.md", "LICENSE", "NOTICE", "第三方许可证.md",
        "治理", "技能库", "工具库", "插件", "快捷指令", "自动化", "外观", builtin.MARKS_FILE]   # 程序和规矩；资料/、笔记/、根目录零碎文件不存
KEEP = 10
DROPPED = "已丢.json"
SKIP_TOP = {DIR, trash.DIR, "索引", ".git"}                 # 这些顶层文件夹不存（存档/.对象 也在 存档/ 里）
SKIP_ANY = {"__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".mypy_cache"}
SKIP_REL = {".claude/worktrees"}                       # agent 开的工作副本（整个项目又一份），不扫不存
HISTORY = ("笔记/", "计划/", "治理/计划/", "自动化/日志/", "自动化/答疑/")   # 发生过的事：复活不倒回
_DIR_NAME = re.compile(r"^C(\d+) ")


# ---------------------------------------------------------------- 扫文件、算指纹

def _ignored(p: Project) -> list[str]:
    f = p.root / IGNORE
    if not f.is_file():
        return []
    out = []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#", 1)[0].strip().replace("\\", "/").strip("/")
        if line:
            out.append(line)
    return out


def _under(rel: str, prefixes: list[str]) -> bool:
    return any(x == "" or rel == x or rel.startswith(x.rstrip("/") + "/") for x in prefixes)


def _walk(p: Project):
    """项目里要存的每个文件：(相对路径, 真路径, stat)。跳过 存档/ 回收站/ 索引/ .git、缓存、存档忽略.txt 里写的。"""
    skip = _ignored(p)
    stack = [(p.root, "")]
    while stack:
        d, rel = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            r = f"{rel}/{e.name}" if rel else e.name
            if (not rel and e.name in SKIP_TOP) or e.name in SKIP_ANY or r in SKIP_REL or e.name.endswith(".pyc") or _under(r, skip):
                continue
            if e.is_symlink():
                continue
            if e.is_dir():
                stack.append((Path(e.path), r))
            elif e.is_file():
                try:
                    yield r, Path(e.path), e.stat()
                except OSError:
                    continue


def _sha(f: Path) -> str:
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_hash(src: Path, dst: Path) -> str:
    """一边复制一边算指纹：复制进档的那一份是什么，指纹就是什么。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with open(src, "rb") as a, open(dst, "wb") as b:
        for chunk in iter(lambda: a.read(1 << 20), b""):
            h.update(chunk)
            b.write(chunk)
    shutil.copystat(src, dst)
    return h.hexdigest()


def _objdir(p: Project) -> Path:
    return p.root / DIR / OBJ


def obj_path(p: Project, sha: str) -> Path:
    return _objdir(p) / sha[:2] / sha


def _put(p: Project, src: Path, sha: str | None = None) -> str | None:
    """把一个文件的内容放进对象库（已经有一样的就不重存）。→ 它的 sha256；读不了返回 None。
    给了 sha（大小、时间跟上一档一样，指纹沿用）且对象库里有：一个字节都不读。"""
    if sha and obj_path(p, sha).is_file():
        return sha
    tmp = _objdir(p) / ".正在放" / f"{os.getpid()}-{abs(hash(str(src))) % 10**9}"
    try:
        got = _copy_hash(src, tmp)
    except OSError:
        tmp.unlink(missing_ok=True)
        return None
    dst = obj_path(p, got)
    if dst.is_file():
        tmp.unlink(missing_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp, dst)
    return got


def _content(p: Project, folder: Path, rel: str, v: list) -> Path | None:
    """这一档里这个文件那时候的内容在哪：这一档自己的 文件/（老档）→ 对象库；都没有返回 None。"""
    if v[3]:
        own = folder / "文件" / rel
        if own.is_file():
            return own
        o = obj_path(p, v[2])
        if o.is_file():
            return o
    return None


def scan(p: Project, reuse: dict | None = None) -> dict:
    """现在全部文件的指纹：{相对路径: [大小, 修改时间, 指纹, 0]}。大小和修改时间跟 reuse 里一样的，指纹直接用，不重算。"""
    reuse = reuse or {}
    out = {}
    for rel, f, st in _walk(p):
        old = reuse.get(rel)
        sha = old[2] if old and old[0] == st.st_size and old[1] == st.st_mtime_ns else None
        if sha is None:
            try:
                sha = _sha(f)
            except OSError:
                continue
        out[rel] = [st.st_size, st.st_mtime_ns, sha, 0]
    return out


# ---------------------------------------------------------------- 读档

def _root(p: Project) -> Path:
    return p.root / DIR


def _folders(p: Project) -> dict[str, Path]:
    d = _root(p)
    out = {}
    if d.is_dir():
        for x in d.iterdir():
            m = _DIR_NAME.match(x.name)
            if m and x.is_dir() and (x / "档.json").is_file():
                out[f"C{m.group(1)}"] = x
    return out


def _folder(p: Project, code: str) -> Path:
    f = _folders(p).get(code)
    if not f:
        raise store.Refused(f"没有 {code} 这一档")
    return f


def _meta(folder: Path) -> dict:
    return json.loads((folder / "档.json").read_text(encoding="utf-8"))


def _files(folder: Path) -> dict:
    return json.loads((folder / "指纹.json").read_text(encoding="utf-8"))["files"]


def list_saves(p: Project) -> list[dict]:
    """全部存档，新的在前。每档带上这个文件夹多大。"""
    out = []
    for code, f in _folders(p).items():
        try:
            m = _meta(f)
        except (OSError, ValueError):
            continue
        out.append(m)
    out.sort(key=lambda m: int(m["code"][1:]), reverse=True)
    return out


def latest(p: Project) -> dict | None:
    s = list_saves(p)
    return s[0] if s else None


def settled_cutoff(p: Project) -> str | None:
    """最近一档定性过的存档是什么时候存的（YYYY-MM-DD HH:MM）：回收站里在它以前进来的，可以彻底删。"""
    s = [m for m in list_saves(p) if m.get("settled")]
    return max(m["at"] for m in s) if s else None


def detail(p: Project, code: str) -> dict:
    f = _folder(p, code)
    m = _meta(f)
    m["copied"] = sorted(r for r, v in _files(f).items() if v[3])
    return m


def total_size(p: Project) -> int:
    d = _root(p)
    return sum(x.stat().st_size for x in d.rglob("*") if x.is_file()) if d.is_dir() else 0


# ---------------------------------------------------------------- 存

def _check_name(name: str) -> str:
    name = " ".join((name or "").split())
    if not name:
        raise store.Refused("给这一档起个名字，比如「表1跑完」")
    if len(name) > 40:
        raise store.Refused("名字太长了，40 个字以内")
    if _BAD_CHARS.search(name) or name.endswith((".", " ")) or name.upper() in _RESERVED:
        raise store.Refused('名字里不能有 \\ / : * ? " < > | 这些符号（它要当文件夹名）')
    return name


def offered(mode: str) -> str:
    """人和 agent 存的都是全量（10-03 起：内容进对象库只存一份，全量不再费地方）。选什么都按全量存。"""
    return "全量"


def _picked(files: dict, mode: str, picks: list[str]) -> list[str]:
    if mode == "全量":
        return list(files)
    if mode == "核心":
        return [r for r in files if _under(r, picks or CORE)]
    if mode == "自定义":
        return [r for r in files if _under(r, picks)]
    return []


def _norm_picks(picks: list[str] | None) -> list[str]:
    out = []
    for x in picks or []:
        x = (x or "").replace("\\", "/").strip().strip("/")
        if x and ".." not in x.split("/") and x not in out:
            out.append(x)
    return out


def tree(p: Project) -> list[dict]:
    """「自定义」打勾用：项目顶层每一项，文件夹再往下一层，都带文件数和大小。"""
    top: dict[str, dict] = {}
    for rel, _, st in _walk(p):
        parts = rel.split("/")
        t = top.setdefault(parts[0], {"path": parts[0], "dir": len(parts) > 1, "files": 0, "bytes": 0, "children": {}})
        t["files"] += 1
        t["bytes"] += st.st_size
        if len(parts) > 1:
            t["dir"] = True
            c = t["children"].setdefault(parts[1], {"path": f"{parts[0]}/{parts[1]}", "dir": len(parts) > 2, "files": 0, "bytes": 0})
            c["files"] += 1
            c["bytes"] += st.st_size
    out = []
    for t in sorted(top.values(), key=lambda t: (not t["dir"], t["path"])):
        t["children"] = sorted(t["children"].values(), key=lambda c: (not c["dir"], c["path"]))
        out.append(t)
    return out


def estimate(p: Project, mode: str, picks: list[str] | None) -> dict:
    """存之前先算：要复制几个文件、多大；整个项目多少文件、多大。不算指纹，很快。"""
    if mode not in MODES:
        raise store.Refused(f"存法只有 {' / '.join(MODES)}")
    picks = list(CORE) + builtin.folders(p.root) + builtin.read_marks(p.root)["paths"] if mode == "核心" else _norm_picks(picks)
    prev = latest(p)
    try:
        last = _files(_folder(p, prev["code"])) if prev else {}
    except (store.Refused, OSError, ValueError):
        last = {}
    n = b = allf = allb = nb = 0
    for rel, _, st in _walk(p):
        allf += 1
        allb += st.st_size
        if mode == "全量" or (mode in ("自定义", "核心") and _under(rel, picks)):
            n += 1
            b += st.st_size
            old = last.get(rel)
            if not (old and old[0] == st.st_size and old[1] == st.st_mtime_ns and old[3] and obj_path(p, old[2]).is_file()):
                nb += st.st_size                         # 改过、新加的：要新存
    return {"mode": mode, "picks": picks, "files": n, "bytes": b, "new_bytes": nb, "all_files": allf, "all_bytes": allb,
            "free": shutil.disk_usage(p.root).free}


def _git(p: Project) -> str:
    """项目有 git 的话，记下当时的版本号（只读 .git 里的文件，不跑 git）。"""
    head = p.root / ".git" / "HEAD"
    try:
        h = head.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not h.startswith("ref: "):
        return h[:10]
    ref = h[5:]
    f = p.root / ".git" / ref
    try:
        return f"{ref.split('/')[-1]} {f.read_text(encoding='utf-8').strip()[:10]}"
    except OSError:
        pass
    packed = p.root / ".git" / "packed-refs"
    try:
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.endswith(" " + ref):
                return f"{ref.split('/')[-1]} {line[:10]}"
    except OSError:
        pass
    return ref.split("/")[-1]


def _credentials(conn, p: Project) -> dict:
    """当时的凭据：蓝图进度、待拍板几条、最近一条笔记、git 版本号。"""
    bp = blueprint.pyramid(p)
    notes = notebook.read(p, notebook.MAIN)
    return {
        "blueprint": {"counts": bp["counts"], "goals": [[g["code"], g["name"], g["done"], g["total"]] for g in bp["goals"]]},
        "pending": len(store.list_pending(conn)),
        "last_note": notes[-1]["id"] if notes else "",
        "git": _git(p),
    }


def _norm_checks(checks: list[dict] | None) -> list[dict]:
    out = []
    for c in checks or []:
        name = str(c.get("name") or c.get("名") or c.get("检查") or "").strip()
        if not name:
            continue
        ok = c.get("ok", c.get("过了", c.get("passed")))
        out.append({"name": name, "ok": bool(ok) if ok is not None else False,
                    "detail": str(c.get("detail") or c.get("说明") or c.get("结果") or "").strip()})
    return out


def _next_code(conn, p: Project) -> str:
    n = int(store._meta(conn, "ckpt_seq") or 0)
    n = max([n] + [int(c[1:]) for c in _folders(p)])
    store._set_meta(conn, "ckpt_seq", str(n + 1))
    return f"C{n + 1}"


def _capture_builtin_marks(p: Project, files: dict) -> dict:
    """历史名单只从本次实际入对象库的字节取得；没存上不能伪称可恢复。"""
    rel = builtin.MARKS_FILE
    entry = files.get(rel)
    if entry and entry[3]:
        raw = obj_path(p, entry[2]).read_bytes()
        try:
            marks = builtin.parse_marks(raw)
        except builtin.Invalid as exc:
            raise store.Refused("这一档的内置标记无效：" + str(exc)) from exc
        missing = [r for r in marks["paths"] if not files.get(r, [0, 0, "", 0])[3]]
        return {"builtin_marks_version": 1, "builtin_marks": marks["paths"],
                "builtin_marks_revision": hashlib.sha256(raw).hexdigest(),
                "builtin_marks_status": "recorded", "builtin_marks_missing": missing}
    if entry or (p.root / rel).exists():
        return {"builtin_marks_status": "not_saved",
                "builtin_marks_warning": "内置标记正本未保存内容，不能据此恢复名单"}
    return {"builtin_marks_version": 1, "builtin_marks": [],
            "builtin_marks_revision": hashlib.sha256(b"").hexdigest(),
            "builtin_marks_status": "recorded", "builtin_marks_missing": []}


def _historical_builtin_marks(meta: dict) -> list[str] | None:
    if meta.get("builtin_marks_version") != 1:
        return None  # 老档未知，不等于明确空名单。
    try:
        raw = json.dumps({"version": 1, "paths": meta.get("builtin_marks")}, ensure_ascii=False).encode("utf-8")
        return builtin.parse_marks(raw)["paths"]
    except (builtin.Invalid, TypeError, ValueError) as exc:
        raise store.Refused("存档的内置标记快照无效：" + str(exc)) from exc


def _current_marks_bytes(root: Path) -> bytes:
    f = root / builtin.MARKS_FILE
    builtin.marks_revision(root)  # 共用正本大小、普通文件和链接边界；损坏JSON可完整恢复。
    return f.read_bytes() if f.is_file() else b""


def _restore_builtin_plan(p: Project, meta: dict, paths: list[str], back: dict, extra: list[str], revision=None) -> dict:
    raw = _current_marks_bytes(p.root)
    current_revision = hashlib.sha256(raw).hexdigest()
    if revision is not None and revision != current_revision:
        raise store.Refused("内置标记在确认期间已变化，请重新预览恢复")
    historical = _historical_builtin_marks(meta)
    out = {"known": historical is not None, "revision": current_revision,
           "changed": False, "added": [], "removed": [], "paths": None,
           "missing_content": meta.get("builtin_marks_missing", [])}
    if historical is None:
        out["reason"] = meta.get("builtin_marks_warning") or "旧档未记录内置标记，保留现在的名单"
        return out
    full = not paths or builtin.MARKS_FILE in paths
    try:
        current = builtin.parse_marks(raw)["paths"] if raw else []
    except builtin.Invalid as exc:
        if not full:
            raise store.Refused("现在的内置标记无效，不能局部恢复名单：" + str(exc)) from exc
        current = None  # 完整恢复可以修复损坏正本。
    if full:
        desired = set(historical)
    else:
        affected = set(back) | set(extra)
        desired = (set(current) - affected) | (set(historical) & affected)
    old = set(current or [])
    out.update(paths=sorted(desired), added=sorted(desired - old), removed=sorted(old - desired),
               changed=current is None or old != desired, scope="完整名单" if full else "本次实际恢复文件")
    return out


def _commit_restore(conn, p, *, back, replace, missing, extra, marks, by, code, name):
    """确认后持同一标记锁；内容先备齐，失败回滚，名单最后原子写。"""
    moved = None
    rel = builtin.MARKS_FILE
    written = []
    # 临时副本防止复制源中途不可读；此处尚未改项目原件。
    with tempfile.TemporaryDirectory(prefix="research-console-restore-") as folder:
        stage = Path(folder)
        for index, path in enumerate(r for r in replace + missing if r != rel):
            src = stage / str(index)
            shutil.copy2(back[path], src)
            back[path] = src
        if hashlib.sha256(_current_marks_bytes(p.root)).hexdigest() != marks["revision"]:
            raise store.Refused("内置标记在恢复期间已变化，请重新预览恢复")
        try:
            if replace or extra:
                moved = trash.move_many(conn, p, replace + extra, by=by,
                                        reason=f"复活 {code}「{name}」", origin=f"复活 {code} 换下来的")["code"]
            for path in replace + missing:
                if path == rel:
                    continue
                dst = p.root / path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(back[path], dst)
                written.append(path)
            if marks["changed"]:
                # 换下的标记已随同一批进回收站；持锁时没有其他人能插入新名单。
                builtin.replace_marks(p.root, marks["paths"], hashlib.sha256(b"").hexdigest())
                written.append(rel)
        except BaseException:
            new_files = [r for r in missing if (p.root / r).is_file()]
            if new_files:
                trash.move_many(conn, p, new_files, by=by, reason=f"复活 {code} 失败回滚新增文件", origin="恢复失败回滚")
            if moved:
                trash.restore(conn, p, moved, by=by, swap=True)
            raise
    return moved


def save(conn, p: Project, *, name: str, why: str = "", mode: str = "核心", picks: list[str] | None = None,
         by: str, checks: list[dict] | None = None, auto: bool = False) -> dict:
    """存一档。先写进 存档/.正在存/，全部写完再改名成 存档/C3 名字/。auto：程序照设置自动存的（名字带「自动 ·」，另算个数）。"""
    if auto:
        name = ("自动 · " + " ".join((name or "").split()))[:40].rstrip(" .")
    name = _check_name(name)
    if mode not in MODES:
        raise store.Refused(f"存法只有 {' / '.join(MODES)}")
    builtin_scope = builtin.folders(p.root)
    picks = _norm_picks(picks) if mode == "自定义" else list(CORE) + builtin_scope + builtin.read_marks(p.root)["paths"] if mode == "核心" else []
    if mode == "自定义" and not picks:
        raise store.Refused("自定义要勾上至少一个文件或文件夹；什么都不复制就选「只记指纹」")
    checks = _norm_checks(checks)
    prev = latest(p)
    reuse = _files(_folder(p, prev["code"])) if prev else {}
    est = estimate(p, mode, picks)
    if est["new_bytes"] + (50 << 20) > est["free"]:
        raise store.Refused(f"硬盘不够：这一档要新存 {_human(est['new_bytes'])}，盘上只剩 {_human(est['free'])}")
    root = _root(p)
    tmp = root / TMP
    if tmp.exists():
        shutil.rmtree(tmp)                               # 上次存到一半断了留下的，不算数
    tmp.mkdir(parents=True)
    try:
        files = scan(p, reuse)
        copied_bytes = new_bytes = 0
        for rel in _picked(files, mode, picks):
            v = files[rel]
            had = obj_path(p, v[2]).is_file()
            got = _put(p, p.root / rel, v[2] if had else None)
            if got is None:
                continue                                 # 正被别的程序占着：记着指纹，没存上
            v[2], v[3] = got, 1
            copied_bytes += v[0]
            new_bytes += 0 if had else v[0]
        marks_meta = _capture_builtin_marks(p, files)
        saved_marks = [r for r in marks_meta.get("builtin_marks", []) if files.get(r, [0, 0, "", 0])[3]]
        builtin_scope = sorted(set(builtin_scope) | set(saved_marks))
        if p.db_path.is_file():
            src, dst = sqlite3.connect(p.db_path), sqlite3.connect(tmp / "库.sqlite")
            try:
                src.backup(dst)
            finally:
                src.close()
                dst.close()
        with store.tx(conn):
            code = _next_code(conn, p)
            meta = {
                "code": code, "name": name, "why": " ".join((why or "").split()), "mode": mode, "picks": picks,
                "by": by, "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "grade": "绿档" if checks and all(c["ok"] for c in checks) else "黄档", "checks": checks,
                "settled": None, "credentials": _credentials(conn, p),
                "total_files": len(files), "total_bytes": sum(v[0] for v in files.values()),
                "copied_files": sum(v[3] for v in files.values()), "copied_bytes": copied_bytes,
                "new_bytes": new_bytes, "objects": True,         # 内容在对象库；这一档实际只多占 new_bytes
                "auto": bool(auto),
                "builtin_scope": builtin_scope,             # 目录模板与该档历史人工名单，恢复不按现在的小锁猜。
                **marks_meta,
                "folder": f"{DIR}/{code} {name}",
            }
            (tmp / "指纹.json").write_text(json.dumps({"files": files}, ensure_ascii=False), encoding="utf-8")
            (tmp / "档.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            os.rename(tmp, root / f"{code} {name}")
            if mode == "自定义":
                store._set_meta(conn, "ckpt_picks", json.dumps(picks, ensure_ascii=False))
            store.log(conn, by, "存档", code, f"{name} · {mode} · {meta['copied_files']} 个文件 · 新存 {_human(new_bytes)}")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    prune(conn, p, by=by)                                # 照设置留几档（+ 定性的、长了枝的），别的丢掉；也写清单
    return meta


def auto_save(conn, p: Project, when: str, *, name: str, why: str = "", by: str, checks: list[dict] | None = None) -> dict | None:
    """照设置自动存一档（when：on_core 改核心前 · on_deliver 交付后 · every_h 定时）。设置里关着就不存；存不了（盘满、正在存）不挡正事。"""
    import knobs
    if when != "every_h" and not knobs.get(conn, when):
        return None
    try:
        return save(conn, p, name=name, why=why, mode="全量", by=by, checks=checks, auto=True)
    except (store.Refused, OSError) as e:
        store.log(conn, by, "自动存档没存上", when, str(e)[:200])
        return None


def timed_save(conn, p: Project, now: datetime | None = None) -> dict | None:
    """定时存（设置里「有改动就每隔几小时存一档」）：到点了、跟最新一档比有改动才存。后台每分钟问一次。"""
    import knobs
    hours = knobs.get(conn, "every_h")
    if not hours:
        return None
    now = now or datetime.now()
    last = latest(p)
    if last:
        try:
            if (now - datetime.strptime(last["at"], "%Y-%m-%d %H:%M")).total_seconds() < hours * 3600:
                return None
        except ValueError:
            pass
        old = _files(_folder(p, last["code"]))
        cur = scan(p, old)
        if {k: v[2] for k, v in cur.items()} == {k: v[2] for k, v in old.items()}:
            return None                                  # 没改动：不存
    return auto_save(conn, p, "every_h", name="定时", why=f"每 {hours} 小时有改动就存一档（设置里定的）", by="程序")


def ignore_rows(p: Project) -> list[dict]:
    """存档忽略.txt 一行一条：{path, why}（# 后面是为什么）。"""
    f = p.root / IGNORE
    out = []
    if f.is_file():
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            path, _, why = line.partition("#")
            path = path.strip().replace("\\", "/").strip("/")
            if path:
                out.append({"path": path, "why": why.strip()})
    return out


def set_ignore(conn, p: Project, rows: list[dict], *, by: str = "人") -> list[dict]:
    """改「不存的」：整张表写回 存档忽略.txt。路径从项目根写，不能出项目。"""
    clean = []
    for r in rows or []:
        path = str(r.get("path") or "").strip().replace("\\", "/").strip("/")
        if not path:
            continue
        if path.startswith("..") or ":" in path or "/../" in f"/{path}/":
            raise store.Refused(f"「{path}」要从项目根写，不能出项目")
        clean.append({"path": path, "why": " ".join(str(r.get("why") or "").split()).replace("#", "")})
    text = "# 存档不存这些（从项目根写，一行一个；# 后面写为什么）。设置 → 存档 里改\n" + "".join(
        f"{r['path']}" + (f"  # {r['why']}" if r["why"] else "") + "\n" for r in clean)
    tmp = p.root / (IGNORE + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    atomic.replace(tmp, p.root / IGNORE)
    store.log(conn, by, "改了存档不存的", IGNORE, "、".join(r["path"] for r in clean)[:300])
    return ignore_rows(p)


def status(p: Project) -> dict:
    """设置 → 存档 最上面那行：一共多大、几档（手动 / 自动）、对象库多少文件、已丢几档。"""
    saves = list_saves(p)
    od = _objdir(p)
    objs = sum(1 for x in od.glob("*/*") if x.is_file()) if od.is_dir() else 0
    return {"total": total_size(p), "saves": len(saves), "auto": sum(1 for m in saves if m.get("auto")),
            "settled": sum(1 for m in saves if m.get("settled")), "pinned": len(set(pins(p).values())),
            "objects": objs, "dropped": len(dropped(p))}


def last_picks(conn) -> list[str]:
    try:
        return json.loads(store._meta(conn, "ckpt_picks") or "[]")
    except ValueError:
        return []


# ---------------------------------------------------------------- 比、取旧文件

def _find_copy(p: Project, sha: str, prefer: str = "") -> tuple[str, Path] | None:
    """哪一档里有这个指纹的真文件（先看对象库，再看 prefer 那一档、别的老档）。"""
    folders = _folders(p)
    if obj_path(p, sha).is_file():                       # 内容在对象库：标上是哪一档存的（先 prefer，再新的）
        for c in ([prefer] if prefer in folders else []) + sorted(folders, key=lambda c: -int(c[1:])):
            try:
                if any(v[3] and v[2] == sha for v in _files(folders[c]).values()):
                    return c, obj_path(p, sha)
            except (OSError, ValueError):
                continue
        return "对象库", obj_path(p, sha)
    order = ([prefer] if prefer in folders else []) + [c for c in sorted(folders, key=lambda c: -int(c[1:])) if c != prefer]
    for c in order:
        f = folders[c]
        for rel, v in _files(f).items():
            if v[3] and v[2] == sha:
                return c, f / "文件" / rel
    return None


def diff(p: Project, code: str, against: str = "now") -> dict:
    """从这一档到 against（现在 / 另一档）：新加、改了、删了哪些文件。每个标上这一档有没有副本（能不能拿回来）。"""
    a = _files(_folder(p, code))
    b = scan(p, a) if against == "now" else _files(_folder(p, against))
    added = sorted(r for r in b if r not in a)
    removed = sorted(r for r in a if r not in b)
    changed = sorted(r for r in a if r in b and a[r][2] != b[r][2])
    item = lambda r: {"path": r, "copy": bool(a[r][3])}
    return {"code": code, "against": against, "added": added,
            "changed": [item(r) for r in changed], "removed": [item(r) for r in removed]}


def old_file(p: Project, code: str, rel: str) -> tuple[Path, str]:
    """这一档里某个文件那时候的样子：这一档复制了就用它；没复制但别的档有一模一样指纹的副本，也行。"""
    rel = (rel or "").replace("\\", "/").strip("/")
    files = _files(_folder(p, code))
    v = files.get(rel)
    if v is None:
        raise store.Refused(f"{code} 里没有「{rel}」")
    got = _content(p, _folder(p, code), rel, v)
    if got:
        return got, code
    hit = _find_copy(p, v[2], code)
    if not hit:
        raise store.Refused(f"{code} 只记了「{rel}」的指纹，没留副本；别的档里也没有一模一样的")
    return hit[1], hit[0]


# ---------------------------------------------------------------- 复活

def _history(rel: str) -> bool:
    return not builtin.is_template(rel) and rel.startswith(HISTORY)


def restore(conn, p: Project, code: str, *, by: str, paths: list[str] | None = None, confirm: bool = False,
            whole: bool | None = None, builtin_revision: str | None = None) -> dict:
    """复活：把这一档复制了的文件放回原位。现有的（改过的）和这一档之后新加的，先一起挪进回收站（一个编号）。
    笔记、计划、日志、答疑不倒回。没带 confirm 先返回要做什么（弹警告用）。
    whole：False＝全量档也只换程序和规矩（网页、agent 默认这样，免得把那之后放进资料的东西挪进回收站）；True＝整份回去；None＝照老规矩（全量档整份）。"""
    folder = _folder(p, code)
    m, files = _meta(folder), _files(folder)
    paths = _norm_picks(paths)
    if m["mode"] == "只记指纹" and not paths:
        raise store.Refused(f"{code} 只记了指纹、没复制文件，整档复活不了；可以挑某个文件，看别的档里有没有它的副本")
    scope = paths or (m["picks"] if m["mode"] in ("自定义", "核心") else list(CORE) + m.get("builtin_scope", []) if whole is False else [""])
    import governance_paths as gp
    legacy_core = (gp.active(p) and 'backend/main.py' in files and 'backend/governance_paths.py' not in files
                   and _under('backend/main.py', scope))
    if legacy_core and m.get("slimmed") and not paths:
        raise store.Refused(f'{code} 是 09-30 集中治理以前的程序，瘦身后只留了核心文件，整档回不去了；要哪个文件，点「看那时候」单独取出来。')
    if legacy_core and scope != ['']:
        raise store.Refused('这一档的程序使用旧目录；请整档复活以同时恢复匹配的目录，或只选资料文件。计划、笔记、日志仍会保留。')
    central_layout = gp.active(p) and not legacy_core
    original = {gp.central(r) if central_layout else r: r for r in files}
    if central_layout:
        files = {gp.central(r): v for r, v in files.items()}
        paths = [gp.central(r) for r in paths]
        scope = [gp.central(r) if r else r for r in scope]
    now = scan(p, files)
    back: dict[str, Path] = {}                           # 要放回去的：相对路径 → 副本在哪
    for rel, v in files.items():
        if rel == builtin.MARKS_FILE or not _under(rel, scope) or _history(rel):
            continue
        got = _content(p, folder, original[rel], v)
        if got:
            back[rel] = got
        elif rel in paths:                               # 点名要的单个文件，这一档没复制：去别的档找一模一样的
            hit = _find_copy(p, v[2], code)
            if hit:
                back[rel] = hit[1]
    replace = sorted(r for r in back if r in now and now[r][2] != files[r][2])
    missing = sorted(r for r in back if r not in now)
    extra = sorted(r for r in now if _under(r, scope) and not _history(r) and r not in files
                   and r not in ("治理/迁移记录.json", "治理/迁移清单.md", builtin.MARKS_FILE)
                   and r not in m.get("builtin_marks_missing", [])
                   and (paths or "builtin_scope" in m or not builtin.is_template(r)))
    if legacy_core:
        extra = [r for r in extra if not r.startswith('治理/')] + ['治理']
    marks = _restore_builtin_plan(p, m, paths, back, extra, builtin_revision)
    if marks["changed"]:
        (replace if (p.root / builtin.MARKS_FILE).is_file() else missing).append(builtin.MARKS_FILE)
        replace.sort()
        missing.sort()
    if not (replace or missing or extra):
        return {"code": code, "nothing": True, "builtin_marks": marks}
    if not confirm:
        marks_words = (f"内置标记：开启 {len(marks['added'])} 个、解除 {len(marks['removed'])} 个。" if marks["changed"] else "")
        marks_scope = ((marks.get("reason") or "此档没有可用的内置名单，保留当前名单") + "。" if not marks["known"]
                       else "本次仅恢复所选文件的内置标记，其他文件的标记保留。" if paths and builtin.MARKS_FILE not in paths
                       else "内置名单随这一档恢复。")
        unavailable = (f"这一档有 {len(marks['missing_content'])} 个已标记原件未保存内容，本次不据此恢复或移除它们。" if marks["missing_content"] else "")
        raise store.NeedConfirm(
            f"复活 {code}「{m['name']}」：{len(replace)} 个文件换回那时的样子，{len(missing)} 个放回来，"
            f"{len(extra)} 个是那之后新加的、会挪进回收站。换下来的都进回收站（一个编号），能还原。"
            f"{marks_words}{marks_scope}{unavailable}笔记、计划、日志不倒回。确定吗？",
            {"replace": replace[:50], "missing": missing[:50], "extra": extra[:50],
             "counts": [len(replace), len(missing), len(extra)], "builtin_marks": marks})
    moved = None
    preserved_plans = []
    if legacy_core:
        # 旧程序读计划/：把最新计划保留到它能读的位置，中央原件随整个目录进回收站。
        central_plans = p.root / '治理/计划'
        for source in sorted(central_plans.rglob('*')):
            if not source.is_file():
                continue
            target = gp.safe(p, '计划/' + source.relative_to(central_plans).as_posix())
            if target.is_file() and target.read_bytes() != source.read_bytes():
                suffix = 1
                candidate = target.with_name(target.stem + ' · 集中治理保留' + target.suffix)
                while candidate.exists() and candidate.read_bytes() != source.read_bytes():
                    suffix += 1
                    candidate = target.with_name(target.stem + f' · 集中治理保留{suffix}' + target.suffix)
                target = candidate
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            preserved_plans.append(gp.relative(p, target))
    with builtin.marks_guard(p.root):
        current_revision = hashlib.sha256(_current_marks_bytes(p.root)).hexdigest()
        if current_revision != marks["revision"]:
            raise store.Refused("内置标记在恢复期间已变化，请重新预览恢复")
        moved = _commit_restore(conn, p, back=back, replace=replace, missing=missing, extra=extra,
                                marks=marks, by=by, code=code, name=m["name"])
    store.log(conn, by, "复活", code, f"换回 {len(replace)} · 放回 {len(missing)} · 挪走 {len(extra)}")
    return {"code": code, "replaced": len(replace), "restored": len(missing), "trashed": len(extra), "trash_code": moved,
            "preserved_plans": preserved_plans, "legacy_layout": bool(legacy_core), "builtin_marks": marks}


# ---------------------------------------------------------------- 定性、删档

def _rewrite_meta(folder: Path, m: dict) -> None:
    tmp = folder / "档.json.tmp"
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    atomic.replace(tmp, folder / "档.json")


def settle(conn, p: Project, code: str, *, by: str) -> dict:
    """定性：人说「这一档是安全点」。只有人能点（通-7）。"""
    folder = _folder(p, code)
    m = _meta(folder)
    m["settled"] = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "by": by}
    _rewrite_meta(folder, m)
    store.log(conn, by, "存档定性", code, m["name"])
    _write_list(p)
    return m


def remove(conn, p: Project, code: str, *, by: str, confirm: bool = False) -> dict:
    """删一档：整个档案夹挪进回收站（有编号，能还原）。定性过的要多确认一次。"""
    folder = _folder(p, code)
    m = _meta(folder)
    if m.get("settled") and not confirm:
        raise store.NeedConfirm(f"{code}「{m['name']}」定性过，是安全点。确定挪进回收站吗？（回收站里能还原）", {"settled": True})
    r = trash.move(conn, p, f"{DIR}/{folder.name}", by=by, reason=f"删掉存档 {code}「{m['name']}」", origin=f"删掉的存档 {code}")
    _write_list(p)
    return {"code": code, "trash_code": r["code"]}


# ---------------------------------------------------------------- 只留 10 档；老档瘦身成核心档

def dropped(p: Project) -> list[dict]:
    try:
        return json.loads((_root(p) / DROPPED).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def prune(conn, p: Project, *, keep: int | None = None, by: str = "程序") -> list[str]:
    """照设置留：手动存的留最近 keep 档（0 = 不限）、自动存的另留最近 keep_auto 个；定性过的、长了枝的总留着；
    超了空间上限再从最老的自动档丢起。别的彻底丢掉（作者 09-30 批的，不进回收站）。记进 已丢.json、清单、日志。→ 丢了哪些。"""
    import journal
    import knobs
    keep = knobs.get(conn, "keep") if keep is None else keep
    keep_auto = knobs.get(conn, "keep_auto")
    saves = list_saves(p)                                # 新的在前
    hand = [m for m in saves if not m.get("auto")]
    autos = [m for m in saves if m.get("auto")]
    stay = {m["code"] for m in (hand[:keep] if keep else hand)} | {m["code"] for m in autos[:keep_auto]}
    stay |= {m["code"] for m in saves if m.get("settled")}   # 定性过的：你认过的安全点，都留着
    stay |= set(pins(p).values())                        # 世界树上有枝从这一档长出来：留着
    gone = [m for m in saves if m["code"] not in stay]
    cap = knobs.get(conn, "cap_gb") << 30
    if cap and total_size(p) > cap:                      # 超了空间上限：再从最老的自动档丢起（手动的、定性的、长了枝的不动）
        spare = [m for m in reversed(autos) if m["code"] in stay and not m.get("settled") and m["code"] not in pins(p).values()]
        if spare:
            gone.append(spare[0])                        # 一次丢一个，下回存档再看；不一口气清空
    folders = _folders(p)
    rec = dropped(p)
    for m in gone:
        shutil.rmtree(folders[m["code"]], ignore_errors=True)
        rec.append({"code": m["code"], "name": m["name"], "at": m["at"], "mode": m["mode"],
                    "dropped": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "why": f"自动存的只留最近 {keep_auto} 个" if m.get("auto") else f"只留最近 {keep} 档"})
        store.log(conn, by, "丢存档", m["code"], m["name"])
    if gone:
        gc_objects(p)                                     # 丢掉的档独用的内容一起收掉
        (_root(p) / DROPPED).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        hand_gone = [m for m in gone if not m.get("auto")]
        if hand_gone:                                     # 自动档轮换不记日志（每存一次挤掉一个，记了全是噪音；已丢.json、清单里照样有）
            journal.add(conn, p, f"照设置留档（手动的 {keep or '不限'} 档、自动的 {keep_auto} 个，定性的、长了枝的总留）：丢了 "
                        + "、".join(m["code"] for m in gone), kind="丢存档", by=by)
    _write_list(p)
    return [m["code"] for m in gone]


PIN = "钉住.json"


def pins(p: Project) -> dict:
    """世界树钉住的档：{枝号: 档号}。"""
    try:
        return json.loads((_root(p) / PIN).read_text(encoding="utf-8")).get("by") or {}
    except (OSError, ValueError):
        return {}


def _write_pins(p: Project, by: dict) -> None:
    sha: set[str] = set()
    folders = _folders(p)
    for code in set(by.values()):
        try:
            sha |= {v[2] for v in _files(folders[code]).values() if v[3]}
        except (KeyError, OSError, ValueError):
            continue
    f = _root(p) / PIN
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps({"by": by, "sha": sorted(sha)}, ensure_ascii=False, indent=1), encoding="utf-8")
    atomic.replace(tmp, f)


def pin(p: Project, code: str, branch: str) -> None:
    """一根枝从这一档长出来：钉住它（清理旧档时不丢，内容留着做合并的底）。"""
    by = pins(p)
    by[branch] = code
    _write_pins(p, by)


def unpin(p: Project, code: str, branch: str) -> None:
    by = pins(p)
    if by.pop(branch, None) is not None:
        _write_pins(p, by)


def _referenced(p: Project) -> set[str]:
    """还有档用到的对象（各档清单里存了内容的那些 sha），加上世界树钉住的（枝长出来的那一档要留着做合并的底）。"""
    keep: set[str] = set()
    for f in _folders(p).values():
        try:
            keep |= {v[2] for v in _files(f).values() if v[3]}
        except (OSError, ValueError):
            continue
    pin = _root(p) / "钉住.json"
    try:
        keep |= set(json.loads(pin.read_text(encoding="utf-8")).get("sha") or [])
    except (OSError, ValueError):
        pass
    return keep


def gc_objects(p: Project) -> dict:
    """对象库里没有任何档用到的内容删掉。→ {removed, freed}。"""
    d = _objdir(p)
    if not d.is_dir():
        return {"removed": 0, "freed": 0}
    keep = _referenced(p)
    removed = freed = 0
    for f in d.glob("*/*"):
        if f.is_file() and f.parent.name != ".正在放" and f.name not in keep:
            try:
                freed += f.stat().st_size
                f.unlink()
                removed += 1
            except OSError:
                pass
    return {"removed": removed, "freed": freed}


def migrate_objects(conn, p: Project, *, by: str = "程序") -> dict:
    """老档的 文件/ 迁进对象库（一次）：每个复制件先重算 sha256，跟清单上的对得上才挪进去（对象库里已有一样的就删掉这份）；
    挪完逐档核一遍——清单上存了内容的每个文件都在对象库里、大小对得上——核过才删空的 文件/。对不上的原样留在 文件/，写进结果。"""
    out = {"checkpoints": [], "moved": 0, "deduped": 0, "mismatch": [], "freed": 0}
    seen: dict[str, int] = {}
    for code, folder in sorted(_folders(p).items(), key=lambda x: int(x[0][1:])):
        own = folder / "文件"
        if not own.is_dir():
            continue
        files = _files(folder)
        before = len(out["mismatch"])
        for rel, v in files.items():
            src = own / rel
            if not (v[3] and src.is_file()):
                continue
            sha = _sha(src)
            if sha != v[2]:
                out["mismatch"].append(f"{code} {rel}")
                continue
            dst = obj_path(p, sha)
            if dst.is_file():
                if dst.stat().st_size != src.stat().st_size:
                    out["mismatch"].append(f"{code} {rel}（对象库里同名的大小不对）")
                    continue
                out["freed"] += src.stat().st_size
                src.unlink()
                out["deduped"] += 1
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.replace(src, dst)
                out["moved"] += 1
            seen[sha] = v[0]
        bad = [rel for rel, v in files.items() if v[3] and not (own / rel).is_file()
               and not (obj_path(p, v[2]).is_file() and obj_path(p, v[2]).stat().st_size == v[0])]
        if bad:
            out["mismatch"] += [f"{code} {rel}（迁完取不出来）" for rel in bad]
        if len(out["mismatch"]) > before:                # 这一档有对不上的：别的照样进了对象库，但这档不算迁完，文件/ 留着
            continue
        for sub in sorted((x for x in own.rglob("*") if x.is_dir()), key=lambda x: -len(x.parts)):
            try:
                sub.rmdir()
            except OSError:
                pass
        try:
            own.rmdir()
        except OSError:
            pass
        m = _meta(folder)
        m["objects"] = True
        _rewrite_meta(folder, m)
        out["checkpoints"].append(code)
    store.log(conn, by, "存档迁进对象库", None, f"{len(out['checkpoints'])} 档 · 挪 {out['moved']} · 去重 {out['deduped']} · 省 {_human(out['freed'])}"
              + (f" · 对不上 {len(out['mismatch'])}" if out["mismatch"] else ""))
    _write_list(p)
    return out


def slim(conn, p: Project, code: str, *, by: str = "程序") -> dict:
    """把一档老的全量 / 自定义档瘦身成核心档：删掉复制进来的核心以外的文件（资料/、笔记/、根目录零碎），指纹照留。
    瘦完照「核心」复活（不再动资料）。→ {code, freed}。"""
    folder = _folder(p, code)
    m, files = _meta(folder), _files(folder)
    if m["mode"] in ("核心", "只记指纹"):
        return {"code": code, "freed": 0}
    scope = list(CORE) + m.get("builtin_scope", [])
    freed = 0
    for rel, v in files.items():
        if v[3] and not _under(rel, scope):
            f = folder / "文件" / rel
            try:
                freed += f.stat().st_size
                f.unlink()
            except OSError:
                pass
            v[3] = 0                                     # 内容在对象库的：不再引用，下面没人用的一起收掉
    d = folder / "文件"
    for sub in sorted((x for x in d.rglob("*") if x.is_dir()), key=lambda x: -len(x.parts)) if d.is_dir() else []:
        try:
            sub.rmdir()                                  # 空了的文件夹
        except OSError:
            pass
    (folder / "指纹.json").write_text(json.dumps({"files": files}, ensure_ascii=False), encoding="utf-8")
    freed += gc_objects(p)["freed"]
    m["slimmed"] = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "from": m["mode"], "freed": freed}
    m["mode"], m["picks"] = "核心", scope
    m["copied_files"] = sum(1 for v in files.values() if v[3])
    m["copied_bytes"] = sum(v[0] for v in files.values() if v[3])
    (folder / "指纹.json").write_text(json.dumps({"files": files}, ensure_ascii=False), encoding="utf-8")
    _rewrite_meta(folder, m)
    store.log(conn, by, "存档瘦身", code, f"{m['slimmed']['from']} → 核心，省 {_human(freed)}")
    return {"code": code, "freed": freed}


# ---------------------------------------------------------------- 清单.md（给人看的目录，从各档的 档.json 生成）

def _human(b: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024 or u == "GB":
            return f"{b:.0f} {u}" if u == "B" else f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} GB"


def _write_list(p: Project) -> None:
    root = _root(p)
    root.mkdir(parents=True, exist_ok=True)
    lines = ["# 存档 · 清单", "",
             "> 一档一个文件夹，编号 C1、C2…（号不回收）。每档记下全部文件的指纹（指纹.json）；文件内容按 sha256 只存一份在 `存档/.对象/`，几档共用，新存一档只多存改了的（10-03 起）。",
             "> 10-03 起每档都是全量（哪一档都能还原成一整份）；老档里还有核心、只记指纹、自定义的。"
             f"照设置只留最近 {__import__('knobs').peek(p, 'keep') or '不限'} 档（自动存的另算；定性过的、长了枝的总留），别的丢掉。绿档 = 带了检查且全过；定性 = 你认过的安全点。", ""]
    for m in list_saves(p):
        flag = " · 已定性" if m.get("settled") else ""
        lines.append(f"## {m['code']} · {m['name']} · {m['at']} · {m['by']} · {m['mode']} · {m['grade']}{flag}")
        fields = [("为什么", m.get("why", "")),
                  ("存了", f"{m['copied_files']} 个文件，{_human(m['copied_bytes'])}" + (f"（{'、'.join(m['picks'])}）" if m["picks"] else "")
                   + (f"；这一档新存 {_human(m['new_bytes'])}" if "new_bytes" in m else "") + ("；内容在对象库" if m.get("objects") else "")),
                  ("全部", f"{m['total_files']} 个文件，{_human(m['total_bytes'])}（都记了指纹）"),
                  ("检查", "；".join(f"{c['name']} {'过了' if c['ok'] else '没过'}" + (f"（{c['detail']}）" if c["detail"] else "") for c in m["checks"])),
                  ("文件夹", m["folder"] + "/"),
                  ("定性", f"{m['settled']['at']}（{m['settled']['by']}）" if m.get("settled") else ""),
                  ("瘦身", f"{m['slimmed']['at']} 从{m['slimmed']['from']}瘦成核心，省了 {_human(m['slimmed']['freed'])}" if m.get("slimmed") else "")]
        lines += [f"- {k}：{v}" for k, v in fields if v]
        lines.append("")
    gone = dropped(p)
    if gone:
        import knobs
        lines += [f"## 已丢（只留最近 {knobs.peek(p, 'keep') or '不限'} 档）", ""]
        lines += [f"- {x['code']} · {x['name']} · {x['at']} · {x['mode']} · {x['dropped']} 丢的" for x in reversed(gone)]
        lines.append("")
    tmp = root / (LIST + ".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    atomic.replace(tmp, root / LIST)
