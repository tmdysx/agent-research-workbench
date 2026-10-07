"""人在文件阅读页删除：先移入回收站，普通清单与机器日志留给 agent 读取。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import threading
from datetime import datetime
from pathlib import Path, PureWindowsPath

import files
import builtin
import governance_paths
import journal
import library
import store
import trash

_LOCK = threading.RLock()
_PROTECTED = {".git", "索引", "回收站", "笔记", "存档", "归档"}
_CACHE = {"__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}
_DEVICE = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def project_key(p) -> str:
    return os.path.normcase(os.path.abspath(p.root)).replace("\\", "/")


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise store.Refused("请选择当前项目里的一个文件")
    value = value.replace("\\", "/")
    if (value.startswith("/") or PureWindowsPath(value).drive
            or any(ord(c) < 32 for c in value) or any(c in value for c in ':*?"<>|')):
        raise store.Refused("删除路径必须是当前项目内的相对路径")
    if any(part in ("", ".", "..") or part.endswith((".", " ")) or _DEVICE.match(part)
           for part in value.split("/")):
        raise store.Refused("删除路径不能越界或使用路径别名")
    return value


def _linked(info) -> bool:
    return (stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", None)
            == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003))


def _stamp(info) -> tuple:
    return tuple(getattr(info, f, None) for f in
                 ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns", "st_reparse_tag"))


def _mapped_path(p, path: Path) -> tuple[Path, Path]:
    """展开项目根的8.3名字，子路径仍逐段lstat，不能resolve掉联接。"""
    given = Path(os.path.abspath(p.root))
    info = given.lstat()
    if _linked(info):
        raise store.Refused("项目根是符号链接或目录联接，不能在这里删除原件")
    root = given.resolve()
    path = Path(os.path.abspath(path))
    for base in (given, root):
        try:
            return root, root.joinpath(*path.relative_to(base).parts)
        except ValueError:
            continue
    raise store.Refused("这个文件在项目外，不能从网页移入本项目回收站")


def _ordinary(p, path: Path, *, missing: bool = False) -> tuple:
    root, path = _mapped_path(p, path)
    parts = path.relative_to(root).parts
    here, final = root, None
    for part in (None, *parts):
        if part is not None:
            here /= part
        try:
            info = here.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise store.Refused("文件已经移走或不存在，请重新打开目录") from None
        if _linked(info):
            raise store.Refused("符号链接或目录联接只能阅读，不能在这里删除原件")
        if here != path and not stat.S_ISDIR(info.st_mode):
            raise store.Refused("文件的上级路径不是普通文件夹")
        final = info
    return _stamp(final) if final is not None else ()


def _checked(p, rel: str) -> tuple[Path, tuple]:
    rel = _relative(rel)
    parts = rel.split("/")
    if parts[0] in _PROTECTED:
        raise store.Refused("笔记、历史、存档、回收站和系统索引不能在文件阅读页删除")
    if (len(parts) >= 5 and parts[0] == "资料" and parts[2] == library.READ
            and re.match(r"^L\d+(?:\s|$)", parts[3])
            and parts[4:] in ([library.PARTS[0], library.NOTE_FILE],
                            [library.PARTS[0], library.NOTE_HISTORY], [library.MARK_FILE])):
        raise store.Refused("阅读页的笔记、笔记历史和批注请在原阅读页处理，不能直接删除整份记录")
    if any(part in _CACHE or part.startswith(".") for part in parts[:-1]):
        raise store.Refused("隐藏文件夹和运行缓存不能在文件阅读页删除")
    target = Path(os.path.abspath(p.root)) / rel
    stamp = _ordinary(p, target)
    if not stamp or not stat.S_ISREG(stamp[2]):
        raise store.Refused("这里只能删除单个文件，不能删除文件夹或整个模块")
    return target, stamp


def _revision(p, rel: str, stamp: tuple) -> str:
    # Windows 原地等长改写后可恢复 mtime，stat 仍相同；版本还须绑定实际正文。
    target = Path(os.path.abspath(p.root)) / rel
    changed = "读取期间文件或路径发生变化，请重新打开后再删除"
    if _ordinary(p, target) != stamp:
        raise store.Refused(changed)
    with target.open("rb") as source:
        opened = _stamp(os.fstat(source.fileno()))
        # Python 3.12 的 Windows fstat 创建时间可与 lstat 不同；句柄前后自己比。
        if opened[:5] != stamp[:5]:
            raise store.Refused(changed)
        previous = None
        # 已读过的块也可能等长改写并恢复 mtime；两遍正文一致才发出删除版本。
        for attempt in range(2):
            if attempt:
                source.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
            if _stamp(os.fstat(source.fileno())) != opened or _ordinary(p, target) != stamp:
                raise store.Refused(changed)
            current = digest.hexdigest()
            if previous is not None and current != previous:
                raise store.Refused(changed)
            previous = current
    body = [project_key(p), rel, list(stamp), current]
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def preview_action(p, target: Path, *, original: Path | None = None) -> dict:
    out = {"allowed": False, "path": "", "project": project_key(p), "revision": "", "reason": ""}
    try:
        root, target = _mapped_path(p, target)
        if original is not None:
            # 不让 resolve 后消失的符号链接/目录联接冒充一个普通项目文件；旧治理别名可以缺失。
            _ordinary(p, original, missing=True)
        rel = target.relative_to(root).as_posix()
        out["path"] = rel
        _, stamp = _checked(p, rel)
        out.update(allowed=True, revision=_revision(p, rel, stamp))
    except (OSError, ValueError, store.Refused) as exc:
        out["reason"] = str(exc) or "这个文件不能在阅读页删除"
    return out


def preview_file(p, target: Path, rel: str, *, original: Path | None = None) -> dict:
    """把删除版本绑定到实际阅读的这一版内容，阅读期间变化就禁用本次删除。"""
    before = preview_action(p, target, original=original)
    out = files.preview_path(target, rel)
    after = preview_action(p, target, original=original)
    if before != after:
        after.update(allowed=False, revision="", reason="读取期间文件发生变化，请重新打开后再删除")
    out["delete_action"] = after
    try:
        root, actual = _mapped_path(p, target)
        out["builtin_action"] = builtin.mark_state(root, actual.relative_to(root).as_posix(), original=original)
    except (OSError, ValueError, store.Refused) as exc:
        out["builtin_action"] = {"path": after.get("path", ""), "state": "ineligible", "enabled": False,
                                 "toggle_allowed": False, "reason": str(exc)}
    return out


def builtin_status(p, rel: str) -> dict:
    """旧治理入口映射到同一真实文件；映射前后都查链接，不猜测移走的原件。"""
    state = builtin.mark_state(p.root, rel)
    if state["state"] == "ineligible":
        return state
    canonical = governance_paths.central(rel)
    if rel == "资料/蓝图/蓝图.md" and (p.root / "治理/任务/蓝图.md").is_file():
        canonical = "治理/任务/蓝图.md"
    if canonical != rel and (p.root / canonical).is_file():
        return builtin.mark_state(p.root, canonical, original=p.root / rel)
    return state


def _outputs(conn, p, rel: str) -> None:
    # 原有垃圾箱/清单/日志若被挂到项目外，不让写动作跟着越界。
    for output in (p.root / "回收站", p.root / "回收站" / "清单.md",
                   p.root / "笔记", p.root / "笔记" / "日志",
                   p.root / "笔记" / "日志" / f"{datetime.now():%Y-%m}.md"):
        _ordinary(p, output, missing=True)
    # 同名 orphan box（一次异常写入留下的盒子）也须是普通路径。
    next_n = max([int(store._meta(conn, "trash_seq") or 0)]
                 + [int(e["code"][1:]) for e in trash.read(p)]) + 1
    box = p.root / "回收站" / f"{datetime.now():%Y-%m-%d %H%M} X{next_n}"
    destination = box / rel
    _ordinary(p, destination, missing=True)
    if destination.exists():
        raise store.Refused("回收站目标位置已经有文件，本次删除未执行，请先检查回收站清单")


def move_file(conn, p, path: str, project: str, revision: str, reason: str = "网页文件阅读页手动删除") -> dict:
    """只响应当前项目、当前文件版本；调用原回收站存法，不做彻底删除。"""
    if project != project_key(p):
        raise store.Refused("项目已经切换，请重新打开当前项目的文件后再删除")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{64}", revision):
        raise store.Refused("缺少文件阅读版本，请重新打开文件后再删除")
    reason = " / ".join(x.strip() for x in (reason or "").splitlines() if x.strip())
    if not reason or len(reason) > 2000:
        raise store.Refused("删除原因不能为空或过长")
    with _LOCK:
        target, stamp = _checked(p, path)
        rel = target.relative_to(Path(os.path.abspath(p.root))).as_posix()
        if _revision(p, rel, stamp) != revision:
            raise store.Refused("文件在打开后发生变化，请重新阅读最新内容后再删除")
        _outputs(conn, p, rel)
        _, latest = _checked(p, rel)
        if latest != stamp or _revision(p, rel, latest) != revision:
            raise store.Refused("文件或路径刚刚发生变化，请重新打开后再删除")
        moved = trash.move(conn, p, rel, by="人", reason=reason, origin="网页文件阅读页")
        text = (f"原路径：{rel}\n回收站编号：{moved['code']}\n保存位置：{moved['to']}\n"
                f"原因：{reason}\n原文件版本：{revision}\n操作来源：网页文件阅读页\n状态：在回收站，可还原")
        scope = rel.split("/")[1] if rel.startswith("资料/") and len(rel.split("/")) > 2 else "总览"
        result = {**moved, "action": "移入回收站", "status": trash.IN,
                  "record_path": "回收站/清单.md", "log_id": None}
        try:
            entry = journal.add(conn, p, text, kind="删除文件", by="人", scope=scope)
            result["log_id"] = entry["id"]
        except (OSError, sqlite3.Error):
            result["warning"] = "文件已移入回收站，日志写入失败；删除记录仍可在回收站/清单.md读取"
        return result
