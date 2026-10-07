"""清理 → 重生（S1-8 S2-64；需-30）：全量备份 + 重生计划。

作者 10-04：「重生文件夹放在清理里面，因为死亡就是新生，全量按钮好，最好是能看到进度条的那种」
「全量备份可以选择要备份存档或者不备份存档」「现在先这样先别做太细」。
- 全量备份：整个项目和世界树文件夹原样复制到项目旁边 `<项目名> · 全量备份 <日期 时分>/`，里面是
  `<项目名>/` 和 `<项目名> 世界树/` 两个文件夹（备份里双击 启动.bat，世界树照样找得到）。
  能选不带 `存档/`。在后台一个线程里复制，一次只跑一份；分三段：数文件 → 复制 → 核对，网页每秒来拿进度。
  正在用的库用 SQLite 自带的备份复制（不会抄到写了一半的），它的 -wal / -shm 不抄；核对时库另外查能不能打开。
  复制完两边比：每个文件都在、大小一样才算「对上了」；复制时还在变的、被删的单独列出来，不算没对上。
  跑的时候进度写在 `自动化/重生/正在备份.json`（这个不复制，免得备份抄到自己在变的记录），跑完记进 `自动化/重生/备份.json`；
  后台中途重启了，那一份标「断了」。
- 重生计划：不另外存一份，就是 治理/计划/ 里开头写着「重生:」的那几份（作者 10-04「这两份计划都要放进计划里」）。
开始重生、只重生几个模块、给 agent 的接口这些，写在计划「重生按钮以后做细」里，作者说做细再做。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

import store
from project import Project

DIR = "自动化/重生"
SAVES = "存档"
CHUNK = 1 << 20
_lock = threading.Lock()
_job: dict = {}                                          # 正在跑（或刚跑完）的那份：网页每秒来拿


def _record_file(p: Project) -> Path:
    return p.root / DIR / "备份.json"


def _live_file(p: Project) -> Path:
    return p.root / DIR / "正在备份.json"


def history(p: Project) -> list[dict]:
    try:
        rows = json.loads(_record_file(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    try:
        live = json.loads(_live_file(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        live = None
    if live and not (running() and _job.get("dest") == live.get("dest")):
        live["state"] = "断了"                            # 记着在跑、其实线程已经没了（后台重启过）
    if live and all(r.get("dest") != live.get("dest") for r in rows):
        rows.append(live)
    return sorted(rows, key=lambda r: r.get("at", ""), reverse=True)


def _save_live(p: Project, rec: dict) -> None:
    f = _live_file(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({k: v for k, v in rec.items() if not k.startswith("_")}, ensure_ascii=False, indent=1), encoding="utf-8")


def _save_record(p: Project, rec: dict) -> None:
    f = _record_file(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    try:
        rows = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    keep = {k: v for k, v in rec.items() if not k.startswith("_")}
    rows = [r for r in rows if r.get("dest") != rec["dest"]] + [keep]
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def _forest(p: Project) -> Path:
    import worldtree
    return worldtree.forest(p)


def _long(path: Path) -> str:
    """Windows 路径超过 260 个字也能写：加 \\\\?\\ 前缀。"""
    s = str(path.resolve())
    return "\\\\?\\" + s if os.name == "nt" and not s.startswith("\\\\?\\") else s


def _sources(p: Project, with_saves: bool) -> list[tuple[Path, str]]:
    """要复制的：(哪个文件夹, 在备份里叫什么)。"""
    out = [(p.root, p.root.name)]
    f = _forest(p)
    if f.is_dir():
        out.append((f, f.name))
    return out


def _skip(p: Project, with_saves: bool):
    db = p.db_path.resolve() if p.db_path.is_file() else None
    side = {Path(str(db) + s) for s in ("-wal", "-shm", "-journal")} if db else set()
    saves = (p.root / SAVES).resolve()

    def skip_dir(d: Path) -> bool:
        return not with_saves and d.resolve() == saves

    live = _live_file(p).resolve()

    def skip_file(f: Path) -> bool:                    # 库本身最后用 SQLite 的备份单独抄；正在备份.json 是这次自己的进度
        if f.name == live.name and f.resolve() == live:
            return True
        return f.name.startswith(db.name) and (f.resolve() == db or f.resolve() in side) if db else False

    return db, skip_dir, skip_file


def _walk(p: Project, with_saves: bool, job: dict | None = None) -> tuple[list[tuple[Path, str, int]], list[str]]:
    """数文件：[(源文件, 备份里的相对路径, 大小)]，以及要建的空文件夹。"""
    db, skip_dir, skip_file = _skip(p, with_saves)
    files, dirs = [], []
    for src, name in _sources(p, with_saves):
        for here, subdirs, names in os.walk(src):
            hp = Path(here)
            subdirs[:] = [d for d in subdirs if not skip_dir(hp / d)]
            rel_dir = (Path(name) / hp.relative_to(src)).as_posix()
            dirs.append(rel_dir)
            for n in names:
                f = hp / n
                if skip_file(f):
                    continue
                try:
                    size = f.stat().st_size
                except OSError:
                    continue
                files.append((f, f"{rel_dir}/{n}", size))
                if job is not None and len(files) % 500 == 0:
                    job.update(total_files=len(files), current=f"{rel_dir}/{n}")
    return files, dirs


_size_cache: dict = {}


def sizes(p: Project, fresh: bool = False) -> dict:
    """带存档、不带存档各要多大，磁盘还剩多少（数一遍要一两秒：存五分钟）。"""
    hit = _size_cache.get(str(p.root))
    if hit and not fresh and time.time() - hit["_t"] < 300:
        return {k: v for k, v in hit.items() if k != "_t"}
    files, _ = _walk(p, True)
    saves = (p.root / SAVES).resolve()
    in_saves = [s for f, _, s in files if saves in f.resolve().parents]
    db = p.db_path.stat().st_size if p.db_path.is_file() else 0
    total, n = sum(s for _, _, s in files) + db, len(files) + (1 if db else 0)
    out = {"with_saves": {"files": n, "bytes": total}, "without_saves": {"files": n - len(in_saves), "bytes": total - sum(in_saves)},
           "free": shutil.disk_usage(p.root.parent).free, "where": str(p.root.parent), "forest": _forest(p).is_dir()}
    _size_cache[str(p.root)] = out | {"_t": time.time()}
    return out


def dest_for(p: Project) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d %H%M")
    d = p.root.parent / f"{p.root.name} · 全量备份 {stamp}"
    n = 2
    while d.exists():
        d = p.root.parent / f"{p.root.name} · 全量备份 {stamp}-{n}"
        n += 1
    return d


def status(p: Project) -> dict:
    with _lock:
        job = {k: v for k, v in _job.items() if not k.startswith("_")}
    if job.get("state") == "复制" and job.get("done_bytes"):
        took = time.time() - job["started_t"]
        rate = job["done_bytes"] / took if took > 0 else 0
        job["rate"] = rate
        job["left_s"] = int((job["total_bytes"] - job["done_bytes"]) / rate) if rate else None
    return job


def running() -> bool:
    return _job.get("state") in ("数文件", "复制", "核对")


def start(p: Project, *, with_saves: bool, by: str, _free: int | None = None) -> dict:
    """开一份全量备份（后台线程）。一次只跑一份；磁盘不够拒。"""
    with _lock:
        if running():
            raise store.Refused(f"已经在备份了（{_job.get('state')}，{_job.get('dest_name')}）：等它跑完")
        need = sizes(p)["with_saves" if with_saves else "without_saves"]["bytes"]
        free = shutil.disk_usage(p.root.parent).free if _free is None else _free
        if free < need * 1.05 + (200 << 20):
            from snapshot import _human
            raise store.Refused(f"磁盘不够：要 {_human(need)}，{p.root.parent} 所在的盘只剩 {_human(free)}"
                                + ("；可以不带存档再试" if with_saves else ""))
        dest = dest_for(p)
        _job.clear()
        _job.update(state="数文件", dest=str(dest), dest_name=dest.name, with_saves=with_saves, by=by,
                    at=datetime.now().strftime("%Y-%m-%d %H:%M"), started_t=time.time(), total_files=0, total_bytes=0,
                    done_files=0, done_bytes=0, current="", result=None)
    _save_live(p, _job)
    t = threading.Thread(target=_run, args=(p,), name="全量备份", daemon=True)
    t.start()
    return status(p)


def _copy(src: Path, dst: str, job: dict) -> int:
    n = 0
    with open(_long(src), "rb") as a, open(dst, "wb") as b:
        while True:
            buf = a.read(CHUNK)
            if not buf:
                break
            b.write(buf)
            n += len(buf)
            job["done_bytes"] += len(buf)
    try:
        shutil.copystat(_long(src), dst)
    except OSError:
        pass
    return n


def _run(p: Project) -> None:
    job = _job
    dest = Path(job["dest"])
    try:
        files, dirs = _walk(p, job["with_saves"], job)
        job.update(total_files=len(files), total_bytes=sum(s for _, _, s in files), state="复制", started_t=time.time())
        _save_live(p, job)
        for d in dirs:
            os.makedirs(_long(dest / d), exist_ok=True)
        copied, failed, last = {}, [], time.time()
        for f, rel, _ in files:
            job["current"] = rel
            try:
                copied[rel] = _copy(f, _long(dest / rel), job)
            except FileNotFoundError:
                copied[rel] = None                       # 复制时被删了
            except OSError as e:
                failed.append({"file": rel, "why": str(e)[:200]})
            job["done_files"] += 1
            if time.time() - last > 5:
                _save_live(p, job)
                last = time.time()
        db, _, _ = _skip(p, job["with_saves"])
        db_ok = None
        if db:
            rel = (Path(p.root.name) / db.relative_to(p.root.resolve())).as_posix() if p.root.resolve() in db.parents else f"{p.root.name}/索引/{db.name}"
            out = dest / rel
            os.makedirs(_long(out.parent), exist_ok=True)
            src, dst = sqlite3.connect(db), sqlite3.connect(_long(out))
            try:
                src.backup(dst)
                db_ok = dst.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            finally:
                src.close()
                dst.close()
            job["db"] = rel
        job.update(state="核对", current="")
        _save_live(p, job)
        job["result"] = _verify(dest, files, copied, failed, job.get("db"), db_ok)
        job["state"] = "好了" if job["result"]["ok"] else "没对上"
    except Exception as e:                               # noqa: BLE001  后台线程：什么错都记下来给网页看
        job.update(state="出错", error=f"{type(e).__name__}: {e}"[:300])
    job["took_s"] = int(time.time() - job["started_t"])
    _save_record(p, dict(job))
    try:
        _live_file(p).unlink()
    except OSError:
        pass
    try:
        import journal
        from snapshot import _human
        r = job.get("result") or {}
        c = store.connect(p.db_path)
        journal.add(c, p, f"{job['dest_name']}：{job['state']} · {r.get('files', 0)} 个文件 · {_human(r.get('bytes', 0))}"
                    + ("" if job["with_saves"] else " · 没带存档") + f" · {job['took_s']} 秒", kind="全量备份", by=job["by"])
        c.close()
    except Exception:                                    # noqa: BLE001  记日志失败不影响备份本身
        pass


def _verify(dest: Path, files, copied: dict, failed: list, db_rel: str | None, db_ok) -> dict:
    """两边比：备份里每个文件都在、大小跟复制时一样；复制时还在变的、被删的单独列。"""
    have = {}
    for here, _, names in os.walk(_long(dest)):
        for n in names:
            full = os.path.join(here, n)
            rel = Path(full[len(_long(dest)):].lstrip("\\/")).as_posix()
            try:
                have[rel] = os.stat(full).st_size
            except OSError:
                pass
    missing, wrong, moving, gone = [], [], [], []
    for f, rel, size in files:
        got = copied.get(rel, "失败")
        if got is None:
            gone.append(rel)
            continue
        if got == "失败":
            continue                                     # 在 failed 里
        if rel not in have:
            missing.append(rel)
        elif have[rel] != got:
            wrong.append(rel)
        elif got != size:
            moving.append(rel)                           # 数的时候和复制的时候不一样大：复制时还在写
    expect = {rel for _, rel, _ in files if copied.get(rel) not in (None, "失败")} | ({db_rel} if db_rel else set())
    extra = sorted(set(have) - expect)
    n_files = len(have)
    ok = not (missing or wrong or failed or extra) and db_ok is not False
    return {"ok": ok, "files": n_files, "bytes": sum(have.values()), "expected_files": len(expect),
            "missing": missing[:50], "wrong": wrong[:50], "failed": failed[:50], "extra": extra[:50],
            "moving": moving[:50], "gone": gone[:50], "db_ok": db_ok,
            "counts": {"missing": len(missing), "wrong": len(wrong), "failed": len(failed), "extra": len(extra), "moving": len(moving), "gone": len(gone)}}


def plans(p: Project) -> list[dict]:
    """重生计划：治理/计划/ 里开头写着「重生:」的那几份。"""
    import governance_paths as gp
    from skills import frontmatter
    out = []
    for rel, f in gp.plan_files(p).items():
        if f.suffix != ".md":
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = frontmatter(text)
        if "重生" not in fm:
            continue
        title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), f.stem)
        out.append({"path": gp.relative(p, f), "name": f.stem, "code": f.stem.split(" ")[0], "title": title, "short": f.stem.split(" · ")[-1],
                    "kind": fm.get("重生", ""), "state": re.split(r"[（(]", fm.get("状态", ""))[0].strip(), "state_note": fm.get("状态", ""),
                    "at": fm.get("时间", ""), "text": text})
    return sorted(out, key=lambda x: x["name"])
