"""人在文件阅读页删除：先移入回收站，普通清单与机器日志留给 agent 读取。
移到入口（10-08）：资料/<模块>/ 里放错的普通材料挪回外部资料入口重新分拣，记下原位置、可一键放回；网页和 MCP 走同一个函数。"""
from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import sqlite3
import stat
import threading
from datetime import datetime
from pathlib import Path, PureWindowsPath

import files
import builtin
import downloads
import governance_paths
import intake
import journal
import library
import project as proj
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


def _content(p, rel: str, stamp: tuple) -> str:
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
    return current


def _revision(p, rel: str, stamp: tuple, content: str | None = None) -> str:
    """阅读版本 = 项目 + 路径 + stat + 正文指纹；已经读过正文的（移到入口）直接给 content，不再读一遍。"""
    body = [project_key(p), rel, list(stamp), content or _content(p, rel, stamp)]
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
    out["inbox_action"] = inbox_action(p, after, out["builtin_action"])
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


# ---- 移到入口：资料/<模块>/ 里放错的普通材料挪回 资料/_外部资料入口/ 重新分拣（10-08 作者定：挪、不复制，记下原位置）----

WEB, MCP = "网页文件阅读页", "MCP move_to_inbox"


# 删除那边的原话里讲「回收站」的：移到入口跟回收站无关，换成中性的说法
_MOVE_WORDS = {"这个文件在项目外，不能从网页移入本项目回收站": "这个文件在项目外，不能从网页移动"}


def _as_move(msg: str) -> str:
    return _MOVE_WORDS.get(msg, msg).replace("删除", "移动")


def _canonical(p, rel: str) -> str:
    """按磁盘上真实的各级名字重写 rel（不分大小写的磁盘上——Windows、macOS——资料/文献/A.md 其实是 a.md）。
    找不到、或不分大小写对上不止一个，就原样返回——后面的检查会拒。"""
    here, out = os.path.abspath(p.root), []
    for part in rel.split("/"):
        try:
            names = os.listdir(here)
        except OSError:
            return rel
        if part in names:
            real = part
        elif intake.CASELESS or os.path.lexists(os.path.join(here, part)):
            hits = [n for n in names if n.casefold() == part.casefold()]
            if len(hits) != 1:
                return rel
            real = hits[0]
        else:
            return rel
        out.append(real)
        here = os.path.join(here, real)
    return "/".join(out)


def _inbox_scope(rel: str) -> tuple[str, str] | None:
    """资料/<模块>/…/文件 才谈得上移到入口：返回 (模块, 所在文件夹)；None = 不适用（按钮不显示）。"""
    parts = rel.split("/") if isinstance(rel, str) else []
    if len(parts) < 3 or parts[0] != "资料" or not parts[1] or parts[1].startswith(("_", ".")):
        return None
    return parts[1], "/".join(parts[2:-1])


def _linked_by(p, rel: str) -> tuple[str, str] | None:
    """哪个模块的 .链接.txt 挂着这个文件（或它所在的文件夹）：挪走链接就断了。
    每个模块的 .链接.txt 只读一遍、只比文字（不逐行找目标），挂着就停。"""
    key = intake.name_key(rel)
    for m in proj.module_dirs(p):
        f = p.materials / m / proj.LINKS_FILE
        if not f.is_file():
            continue
        for raw in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.split("#", 1)[0].strip().replace("\\", "/")
            if not line or line.startswith("/"):
                continue
            line = posixpath.normpath(line)      # ./资料/a.md、资料//a.md、资料/./a.md 跟 资料/a.md 是同一个
            if line == "." or line.startswith(".."):
                continue
            if key == intake.name_key(line) or key.startswith(intake.name_key(line) + "/"):
                return m, line
    return None


def _inbox_checked(p, rel: str, *, marks: dict | None = None) -> tuple[Path, tuple, str, str]:
    """能不能移到入口：只收 资料/<模块>/ 里的普通材料；程序管的、治理模块的、挂着链接的、标了内置的都不收。"""
    try:
        rel = _relative(rel)
    except store.Refused as exc:
        raise store.Refused(_as_move(str(exc))) from None
    rel = _canonical(p, rel)                   # 后面比名字、记原路径、起入口名都用磁盘上的真名
    scope = _inbox_scope(rel)
    if scope is None:
        raise store.Refused("只有 资料/<模块>/ 里的普通材料能移到入口重新分拣")
    m, folder = scope
    parts = rel.split("/")
    if m in proj.TOOL_NAMES:
        raise store.Refused(f"「{m}」是固定的治理模块（想法 · 蓝图 · 戒律 · 源代码），里面的文件不移到入口")
    if proj.module_dir(p, m) is None:
        raise store.Refused(f"「{m}」不是模块文件夹")
    if any(x.startswith(".") for x in parts):
        raise store.Refused("点开头的隐藏文件和文件夹不移到入口")
    managed = {intake.name_key(x) for x in intake._NOT_A_PLACE | _CACHE | {"内置"}}
    if any(intake.name_key(x) in managed for x in parts[2:-1]):
        raise store.Refused("工作台、历史、预览缓存、原件、内置和缓存里的文件由程序管理，不移到入口")
    if len(parts) > 3 and intake.name_key(parts[2]) == intake.name_key(library.READ):
        raise store.Refused("文献解读（解读/）跟着原文走，由文献库管理，不移到入口")
    if len(parts) > 3 and parts[2] == "技能":
        raise store.Refused("模块技能（技能/）是写给 agent 的做法，不是材料，不移到入口")
    rel_k = "/".join(parts[:-1] + [intake.name_key(parts[-1])])
    if (governance_paths.central(rel_k) != rel_k
            or (len(parts) == 3 and intake.name_key(parts[2]) in {intake.name_key(downloads.FILE), intake.name_key("想法.md")})):
        raise store.Refused("模块的需求、任务、戒律和下载清单由程序维护，不移到入口")
    try:
        target, stamp = _checked(p, rel)       # 先查链接、联接：原因说得最清楚
    except store.Refused as exc:
        raise store.Refused(_as_move(str(exc))) from None
    try:
        ok = intake._folder(p, m, folder) == folder
    except store.Refused:
        ok = False
    if not ok:
        raise store.Refused(f"原来所在的文件夹「{folder}」不能当分拣去向，移过去就放不回来了")
    if marks is None:
        try:
            root, _ = _mapped_path(p, target)
            marks = builtin.mark_state(root, rel)
        except (OSError, ValueError) as exc:
            raise store.Refused(f"内置标记读不出来：{exc}") from None
    state = marks.get("state")
    if state == "marked":
        raise store.Refused("这个文件标了内置（新项目会带上）：先点旁边的小锁取消内置，再移到入口")
    if state == "required":
        raise store.Refused(f"随内置带走（{marks.get('reason') or '程序要求'}）：先在 设置 → 内置 取消，再移到入口")
    if state != "unmarked":
        raise store.Refused(marks.get("reason") or "读不出这个文件的内置状态，先不移到入口")
    linked = _linked_by(p, rel)
    if linked:
        raise store.Refused(f"「{linked[0]}」模块的 .链接.txt 挂着它（{linked[1]}）：挪走链接就断了；先改 .链接.txt 再移到入口")
    return target, stamp, m, folder


def inbox_action(p, delete: dict, marks: dict | None = None) -> dict:
    """阅读页「移到入口」按钮：适不适用、能不能点、为什么。版本跟删除共用（同一次阅读读出的正文），不再多读文件。"""
    out = {"applicable": False, "allowed": False, "path": delete.get("path", ""), "project": delete.get("project", ""),
           "revision": "", "reason": "", "module": "", "folder": ""}
    scope = _inbox_scope(out["path"])
    if scope is None:
        return out
    out.update(applicable=True, module=scope[0], folder=scope[1])
    try:
        _inbox_checked(p, out["path"], marks=marks)
    except (OSError, ValueError, store.Refused) as exc:
        out["reason"] = str(exc) or "这个文件不能移到入口"
        return out
    if not delete.get("allowed"):
        out["reason"] = _as_move(delete.get("reason") or "") or "这个文件不能移到入口"
        return out
    out.update(allowed=True, revision=delete.get("revision", ""))
    return out


def _inbox_outputs(p) -> None:
    # 入口文件夹、笔记、日志若被挂到项目外，不让移动跟着越界。
    for output in (p.materials / proj.INBOX, p.root / "笔记", p.root / "笔记" / "日志",
                   p.root / "笔记" / "日志" / f"{datetime.now():%Y-%m}.md"):
        _ordinary(p, output, missing=True)


def move_to_inbox(conn, p, path: str, *, by: str, source: str, reason: str = "",
                  key: str | None = None, revision: str | None = None) -> dict:
    """移到入口：网页按钮（人，带阅读版本）和 MCP move_to_inbox（agent，写原因）共用。挪、不复制；原位置记成候选，能一键放回。"""
    try:
        return _move_to_inbox(conn, p, path, by=by, source=source, reason=reason, key=key, revision=revision)
    except store.Refused as exc:
        raise store.Refused(_as_move(str(exc))) from None


def _move_to_inbox(conn, p, path, *, by, source, reason, key, revision) -> dict:
    if source == WEB or key is not None:
        if key != project_key(p):
            raise store.Refused("项目已经切换，请重新打开当前项目的文件后再移动")
    if source == WEB or revision is not None:
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{64}", revision):
            raise store.Refused("缺少文件阅读版本，请重新打开文件后再移动")
    if (not isinstance(by, str) or not by.strip() or by != " ".join(by.split()) or len(by) > 200
            or by == intake.ORIGIN):
        raise store.Refused("操作者要写成一行名字（200 字以内），也不能叫「原位置」")
    reason = " / ".join(x.strip() for x in (reason or "").splitlines() if x.strip())
    if not reason:
        if by != "人":
            raise store.Refused("要写为什么挪回外部资料入口")
        reason = "人在文件阅读页点了「移到入口」"
    if len(reason) > 2000:
        raise store.Refused("原因太长了（最多 2000 字）")
    with _LOCK:
        try:                                   # 挪之前读文件、对账、查链接出的错（文件刚被占住、刚没了）都按「没挪成」回给人和 agent
            store.sync_folders(conn, p)
            target, stamp, module, folder = _inbox_checked(p, path)
            rel = target.relative_to(Path(os.path.abspath(p.root))).as_posix()
            content = _content(p, rel, stamp)
            if revision is not None and _revision(p, rel, stamp, content) != revision:
                raise store.Refused("文件在打开后发生变化，请重新阅读最新内容后再移动")
            if not store.find_module(conn, module):
                raise store.Refused(f"「{module}」不是模块文件夹")
            _inbox_outputs(p)
            _, latest = _checked(p, rel)
            if latest != stamp or _content(p, rel, latest) != content:
                raise store.Refused("文件或路径刚刚发生变化，请重新打开后再移动")
            item = intake.take_from_module(conn, p, target, orig=rel, sha=content, size=stamp[3], module=module,
                                           folder=folder, by=by, check=lambda d: _ordinary(p, d, missing=True))
        except OSError as exc:
            raise store.Refused(f"没挪成，文件还在原处：{exc}") from None
        to = f"资料/{proj.INBOX}/{item['name']}"
        back = f"{module}/{folder}" if folder else f"{module} 模块根目录"
        text = (f"原路径：{rel}\n现在在：{to}（入口 #{item['id']}）\n原位置：{back}；在入口点「放回原处」就放回去\n"
                f"原因：{reason}\n操作者：{by}\n操作来源：{source}\n文件指纹：{content}\n"
                + (f"阅读版本：{revision}\n" if source == WEB and revision else "")
                + "状态：在外部资料入口等分拣，可以放回原处")
        result = {"action": "移到外部资料入口", "from": rel, "to": to, "item": item,
                  "back": {"module": module, "folder": folder}, "by": by, "reason": reason, "log_id": None}
        try:
            entry = journal.add(conn, p, text, kind="移到外部资料入口", by=by, scope=module)
            result["log_id"] = entry["id"]
        except (OSError, sqlite3.Error):
            result["warning"] = "文件已移到外部资料入口，日志写入失败；入口里的记录仍在"
        return result
