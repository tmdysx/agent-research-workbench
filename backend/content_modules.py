"""文献、论文和测试的内容工作台：只读目录，同源安全保存正文和旧稿历史。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path, PureWindowsPath

import atomic
import journal
import store

MODULES = ("文献", "论文", "测试", "PPT", "宣传片")
CONFIG = "工作台/工作台.json"                       # 10-07 起不再放 内置/通用/：模块自己的 工作台/（随模块带进新项目）
TEMPLATES = "工作台/模板/"
ROOTS = {"论文": ("正文", "项目文书"), "测试": ("数据集", "实验结果", "测试代码", "测试记录"),
         "PPT": ("材料", "大纲", "幻灯片", "导出", "检查"), "宣传片": ("素材", "成果")}
EXTENSIONS = {".md", ".txt", ".json", ".csv", ".py"}
MAX_BYTES = 2 * 1024 * 1024
MAX_CONFIG = 128 * 1024
MAX_FILES = 2000
MAX_DEPTH = 16
_DEVICE = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_PROTECTED = {"历史", "内置", "工作台", "笔记", "日志", "索引", "存档", "回收站", "__pycache__", "node_modules", "venv"}
_PROTECTED_FOLD = {x.casefold() for x in _PROTECTED}
_L = re.compile(r"^L([1-9]\d*)(?:\s|$)")


class Invalid(ValueError):
    pass


class Missing(Invalid):
    pass


class Conflict(Invalid):
    pass


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise Invalid("请指定模块内的文件路径")
    value = value.replace("\\", "/")
    if value.startswith("/") or PureWindowsPath(value).drive:
        raise Invalid("文件路径必须从当前模块开始")
    for part in value.split("/"):
        if (part in ("", ".", "..") or part.startswith(".") or part.endswith((".", " "))
                or len(part) > 255 or any(ord(c) < 32 or c in ':*?"<>|' for c in part)
                or part.split(".", 1)[0].rstrip(" ").upper() in _DEVICE):
            raise Invalid("文件路径不能越界或使用 Windows 路径别名")
    return value


def _linked(info) -> bool:
    return bool(stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0))


def _stamp(info) -> tuple:
    return tuple(getattr(info, k, None) for k in
                 ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns", "st_reparse_tag"))


def _root(p) -> Path:
    given = Path(os.path.abspath(p.root))
    try:
        info = given.lstat()
    except OSError as e:
        raise Missing("项目文件夹不存在") from e
    if _linked(info) or not stat.S_ISDIR(info.st_mode):
        raise Invalid("项目根必须是普通文件夹，不能是符号链接或目录联接")
    # 仅展开根的 8.3 名称；子路径不 resolve，保留逐段检查。
    return given.resolve()


def _ordinary(p, target: Path, *, missing: bool = False):
    root = _root(p)
    try:
        parts = target.relative_to(root).parts
    except ValueError:
        raise Invalid("文件不能越出当前项目") from None
    here, final = root, root.lstat()
    absent = False
    for index, part in enumerate(parts):
        parent = here
        here /= part
        try:
            info = here.lstat()
        except FileNotFoundError:
            if missing:
                absent = True
                final = None
                continue
            raise Missing("文件或目录已经移走，请刷新工作台") from None
        if absent or _linked(info):
            raise Invalid("文件路径不能经过符号链接或目录联接")
        if os.name == "nt":
            # 已存在的短子路径别名不能冒充 manifest 中的普通文件名。
            with os.scandir(parent) as entries:
                if not any(e.name.casefold() == part.casefold() for e in entries):
                    raise Invalid("请使用文件的完整名称，不能使用短路径别名")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise Invalid("文件的上级必须是普通文件夹")
        final = info
    if os.name == "nt" and len(str(target)) >= 260:
        raise Invalid("文件路径过长，请缩短项目或文件名称")
    return final


def _module(p, module: str) -> Path:
    if module not in MODULES:
        raise Invalid("这个模块没有内容工作台")
    target = _root(p) / "资料" / module
    info = _ordinary(p, target)
    if not stat.S_ISDIR(info.st_mode):
        raise Missing("模块文件夹不存在")
    return target


def _snapshot(p, target: Path, limit: int = MAX_BYTES) -> tuple[bytes, str]:
    info = _ordinary(p, target)
    if not stat.S_ISREG(info.st_mode):
        raise Invalid("这里只能读取普通文件")
    if info.st_size > limit:
        raise Invalid(f"文件过大，最多允许 {limit // 1024} KiB")
    before = _stamp(info)
    with target.open("rb") as f:
        opened = _stamp(os.fstat(f.fileno()))
        if opened[:5] != before[:5]:
            raise Conflict("读取期间文件发生变化，请重新读取")
        first = f.read(limit + 1)
        f.seek(0)
        second = f.read(limit + 1)
        if (len(first) > limit or first != second or _stamp(os.fstat(f.fileno())) != opened
                or _stamp(_ordinary(p, target)) != before):
            raise Conflict("读取期间文件发生变化，请重新读取")
    return first, hashlib.sha256(first).hexdigest()


def _text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeError as e:
        raise Invalid("文件必须是 UTF-8 文本") from e


def _writable(module: str, rel: str) -> bool:
    if module not in ROOTS:
        return False
    if rel == CONFIG:
        return True
    parts = rel.split("/")
    return (len(parts) >= 2 and parts[0] in ROOTS[module] and Path(rel).suffix.lower() in EXTENSIONS
            and not any(s.casefold() in _PROTECTED_FOLD or s.startswith((".", "_")) for s in parts[1:]))


def validate_config(module: str, data: object) -> dict:
    if not isinstance(data, dict) or data.get("version") != 1 or isinstance(data.get("version"), bool):
        raise Invalid("工作台配置须是 version=1 的 JSON 对象")
    sections = data.get("sections")
    if not isinstance(sections, list) or not 1 <= len(sections) <= 100:
        raise Invalid("工作台配置须有 1 到 100 个分类")
    ids, kinds, result = set(), [], []
    for s in sections:
        if not isinstance(s, dict):
            raise Invalid("工作台分类须是对象")
        sid = s.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", sid) or sid in ids:
            raise Invalid("工作台分类 id 须是唯一的字母、数字、短横线或下划线")
        ids.add(sid)
        for field in ("title", "en"):
            if (not isinstance(s.get(field), str) or len(s[field]) > 120
                    or any(ord(c) < 32 for c in s[field]) or not s[field].strip()):
                raise Invalid("分类标题和英文名称须是 1 到 120 字的文字")
        kind, folder = s.get("kind"), s.get("folder")
        if not isinstance(folder, str):
            raise Invalid("分类 folder 须是模块内相对路径")
        if module == "文献":
            allowed = {"downloads": ("", "下载清单.md"), "reading": ("解读",),
                       "originals": ("原文",), "notes": ("解读",)}
            if kind not in allowed or folder not in allowed[kind]:
                raise Invalid("文献分类只能投影既有的下载、解读、原文或兼容旧笔记")
        else:
            folder = _relative(folder)
            if (kind != "documents" or folder.split("/")[0] not in ROOTS[module]
                    or any(x.casefold() in _PROTECTED_FOLD or x.startswith("_") for x in folder.split("/")[1:])):
                raise Invalid("分类目录不能扩大正文写入范围")
        paths = s.get("templates", [])
        if not isinstance(paths, list) or len(paths) > 100:
            raise Invalid("分类模板须是相对路径列表")
        checked = []
        for path in paths:
            path = _relative(path)
            if not path.startswith(TEMPLATES) or Path(path).suffix.lower() not in EXTENSIONS:
                raise Invalid("模板只能在 工作台/模板 里")
            checked.append(path)
        kinds.append(kind)
        result.append({"id": sid, "title": s["title"], "en": s["en"], "kind": kind,
                       "folder": folder, "templates": list(dict.fromkeys(checked))})
    if module == "文献" and (len(kinds) != len(set(kinds)) or set(kinds) not in (
            {"downloads", "reading", "originals"}, {"downloads", "reading", "originals", "notes"})):
        raise Invalid("文献工作台须保留下载列表、精读、原文三区；兼容旧 notes 分类")
    return {"version": 1, "sections": result}


def _config(p, module: str, base: Path) -> tuple[dict, str]:
    raw, revision = _snapshot(p, base / CONFIG, MAX_CONFIG)
    try:
        data = json.loads(_text(raw))
    except ValueError as e:
        raise Invalid("工作台配置不是合法 JSON") from e
    return validate_config(module, data), revision


def _metadata(p, base: Path, target: Path, module: str) -> dict:
    info = _ordinary(p, target)
    if not stat.S_ISREG(info.st_mode):
        raise Invalid("这里不是普通文件")
    rel = target.relative_to(base).as_posix()
    try:
        mtime = datetime.fromtimestamp(info.st_mtime).isoformat(timespec="seconds")
    except (ValueError, OverflowError, OSError) as e:
        raise Invalid("文件时间超出可显示范围") from e
    return {"path": rel, "name": target.name, "size": info.st_size, "mtime": mtime,
            "editable": _writable(module, rel)}


def _walk(p, base: Path, folder: Path, module: str, problems: list[str], budget: list[int], depth=0) -> list[dict]:
    try:
        info = _ordinary(p, folder)
    except Missing:
        return []
    except (Invalid, OSError) as e:
        problems.append(str(e))
        return []
    if not stat.S_ISDIR(info.st_mode):
        problems.append(f"目录不是普通文件夹：{folder.relative_to(base).as_posix()}")
        return []
    if depth >= MAX_DEPTH:
        problems.append("目录层数过深，未继续展开")
        return []
    out = []
    for e in sorted(os.scandir(folder), key=lambda e: e.name.casefold()):
        if budget[0] >= MAX_FILES:
            if "文件过多，只显示前 2000 项" not in problems:
                problems.append("文件过多，只显示前 2000 项")
            break
        if e.name.startswith((".", "_")) or e.name.casefold() in _PROTECTED_FOLD:
            continue
        budget[0] += 1
        try:
            _relative(e.name)
            target = Path(e.path)
            info = _ordinary(p, target)
            if stat.S_ISDIR(info.st_mode):
                out.extend(_walk(p, base, target, module, problems, budget, depth + 1))
            elif stat.S_ISREG(info.st_mode):
                out.append(_metadata(p, base, target, module))
        except (Invalid, OSError) as ex:
            problems.append(f"{e.name}：{ex}")
    return out


def _literature(p, base: Path, problems: list[str]) -> dict[str, list[dict]]:
    # 只读已经明确登记的 L 元数据；不配对、hash PDF、补信息或新建解读。
    budget = [0]
    original_problem_start = len(problems)
    originals = _walk(p, base, base / "原文", "文献", problems, budget)
    originals_truncated = any("只显示前" in p or "未继续展开" in p for p in problems[original_problem_start:])
    original_paths = {item["path"] for item in originals}
    reading = _walk(p, base, base / "解读", "文献", problems, budget)
    owners, codes = [], {}
    try:
        rd = base / "解读"
        _ordinary(p, rd)
        for index, e in enumerate(sorted(os.scandir(rd), key=lambda e: e.name.casefold())):
            if index >= MAX_FILES:
                problems.append("文献目录过多，只核对前 2000 项已有归属")
                break
            match = _L.match(e.name)
            if not match:
                continue
            folder = Path(e.path)
            try:
                if not stat.S_ISDIR(_ordinary(p, folder).st_mode):
                    continue
                raw, _ = _snapshot(p, folder / "信息.json", MAX_CONFIG)
                info = json.loads(_text(raw))
                code = info.get("编号") if isinstance(info, dict) else None
                if code != f"L{match.group(1)}":
                    problems.append(f"{e.name} 的文献编号未明确或与目录不符")
                    continue
                codes[code] = codes.get(code, 0) + 1
                owners.append((folder.relative_to(base).as_posix(), code, info.get("原文", "")))
            except Missing:
                continue
            except (Invalid, OSError, ValueError) as ex:
                problems.append(f"{e.name} 信息：{ex}")
    except Missing:
        pass
    except (Invalid, OSError) as ex:
        problems.append(str(ex))
    known = {folder: code for folder, code, _ in owners if codes[code] == 1}
    states = {}
    for folder, code, original in owners:
        source = f"{code}（{folder}/信息.json）"
        if not isinstance(original, str) or not original:
            states[folder] = {"unlinked_original": True}
            problems.append(f"{source} 未关联原文")
        elif original not in original_paths:
            if originals_truncated:
                states[folder] = {"original_unconfirmed": True}
                problems.append(f"{source} 原文列表未完整展开，是否缺失尚未确认：{original[:600]}")
            else:
                states[folder] = {"missing_original": True}
                problems.append(f"{source} 原文缺失或不是普通文件：{original[:600]}")
    for code, count in codes.items():
        if count > 1:
            problems.append(f"{code} 有多个解读目录，未提供精读入口")
    for item in reading:
        folder = "/".join(item["path"].split("/")[:2])
        item.update(states.get(folder, {}))
        if folder in known:
            item["reader_code"] = known[folder]
    for item in originals:
        matches = [code for _, code, original in owners if original == item["path"] and codes[code] == 1]
        if len(matches) == 1:
            item["reader_code"] = matches[0]
    notes = [x for x in reading if x["path"].endswith(("/文本/笔记.md", "/批注.json"))]
    reading = [x for x in reading if x["name"] not in ("笔记.md", "批注.json", "信息.json")]
    download = []
    try:
        download.append(_metadata(p, base, base / "下载清单.md", "文献"))
    except Missing:
        pass
    except (Invalid, OSError) as ex:
        problems.append(str(ex))
    return {"downloads": download, "reading": reading, "originals": originals, "notes": notes}


def workspace(p, module: str) -> dict:
    base = _module(p, module)
    problems, revision = [], ""
    try:
        cfg, revision = _config(p, module, base)
    except (Invalid, OSError) as e:
        problems.append(f"工作台配置：{e}")
        cfg = {"sections": []}
        if module == "文献":
            cfg["sections"] = [{"id": k, "title": t, "en": en, "kind": k, "folder": f, "templates": []}
                               for k, t, en, f in (("downloads", "下载列表", "Downloads", ""),
                                                   ("reading", "精读", "Reading", "解读"),
                                                   ("originals", "原文", "Originals", "原文"))]
    lit = _literature(p, base, problems) if module == "文献" else None
    sections, budget = [], [0]
    for s in cfg["sections"]:
        files = lit[s["kind"]] if lit is not None else _walk(p, base, base / s["folder"], module, problems, budget)
        templates = []
        for rel in s["templates"]:
            try:
                meta = _metadata(p, base, base / rel, module)
                templates.append({"path": rel, "name": meta["name"]})
            except (Invalid, OSError) as e:
                problems.append(f"模板 {rel}：{e}")
        sections.append({k: s[k] for k in ("id", "title", "en", "kind", "folder")} | {"files": files, "templates": templates})
    entry = None
    if module in {'论文', 'PPT'}:
        entry = {'path': '技能/SKILL.md', 'name': module + '技能',
                 'en': 'Paper skills' if module == '论文' else 'PPT skills',
                 'readonly': True, 'available': False}
        try:
            entry['available'] = stat.S_ISREG(_ordinary(p, base / entry['path']).st_mode)
        except Missing:
            pass  # 明确缺少正本；只读 GET 不创建目录或伪造入口。
        except (Invalid, OSError) as e:
            problems.append('模块技能入口：' + str(e))
    return {"module": module, "project_root": str(_root(p)), "config_revision": revision,
            "config_file": CONFIG, "sections": sections, "skill_entry": entry,
            "problems": list(dict.fromkeys(problems))}


def read_document(p, module: str, path: str) -> dict:
    base = _module(p, module)
    rel = _relative(path)
    editable = _writable(module, rel)
    if not editable and rel != CONFIG:
        cfg, _ = _config(p, module, base)
        declared = {t for s in cfg["sections"] for t in s["templates"]}
        if rel not in declared or not rel.startswith(TEMPLATES):
            raise Invalid("这个文件请从原阅读入口打开")
    raw, revision = _snapshot(p, base / rel, MAX_CONFIG if rel == CONFIG else MAX_BYTES)
    return {"module": module, "project_root": str(_root(p)), "path": rel,
            "text": _text(raw), "revision": revision, "editable": editable}


def _stage(p, target: Path, raw: bytes) -> Path:
    _ordinary(p, target, missing=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    _ordinary(p, target.parent)
    fd, name = tempfile.mkstemp(prefix=".内容工作台-", dir=target.parent)
    with os.fdopen(fd, "wb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
    return Path(name)


def _log_outputs(p) -> Path:
    d = _root(p) / "笔记" / "日志"
    _ordinary(p, d, missing=True)
    if d.exists():
        for f in sorted(d.glob("????-??.md")):
            info = _ordinary(p, f)
            if not stat.S_ISREG(info.st_mode):
                raise Invalid("机器日志必须是普通文件")
    target = d / f"{datetime.now():%Y-%m}.md"
    _ordinary(p, target, missing=True)
    return target


@contextmanager
def _write_transaction(conn, undo):
    """本系统保存与日志共用写锁；文件回退也覆盖 COMMIT 抛出的异常。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        try:
            undo()
        finally:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
        raise


def write_document(conn, p, module: str, path: str, text: str, revision: str, project_root: str,
                   *, by: str, source: str, reason: str = "") -> dict:
    base = _module(p, module)
    rel = _relative(path)
    if not _writable(module, rel):
        raise Invalid("只能保存论文、测试、PPT、宣传片的工作文本或这些模块的工作台配置")
    if not isinstance(project_root, str) or not Path(project_root).is_absolute():
        raise Invalid("保存时必须声明当前项目根")
    from project import Project
    if os.path.normcase(str(_root(Project(Path(project_root))))) != os.path.normcase(str(_root(p))):
        raise Conflict("当前项目与读取时不同，不能保存到另一个项目")
    if not isinstance(revision, str) or (revision and not re.fullmatch(r"[0-9a-f]{64}", revision)):
        raise Invalid("文件版本不是完整 SHA256，请重新读取")
    if not isinstance(text, str) or not isinstance(reason, str) or len(reason) > 2000:
        raise Invalid("正文和修改原因须是文字，原因最多 2000 字")
    try:
        raw = text.encode("utf-8")
    except UnicodeError as e:
        raise Invalid("正文必须能保存为 UTF-8") from e
    if len(raw) > (MAX_CONFIG if rel == CONFIG else MAX_BYTES):
        raise Invalid("正文过大，普通正文最多 2 MiB，配置最多 128 KiB")
    if rel == CONFIG:
        try:
            validate_config(module, json.loads(text))
        except ValueError as e:
            raise Invalid(f"工作台配置不合法：{e}") from e
    if (not isinstance(by, str) or not by or len(by) > 100 or any(ord(c) < 32 for c in by)
            or " · " in by or source not in ("http", "mcp")):
        raise Invalid("保存必须有服务器确认的操作者和来源")
    target, staged, logstage = base / rel, None, None
    old, oldlog, saved, log_saved, history = None, None, False, False, None
    def undo():
        # 外部编辑器不遵守数据库锁；异常时也不覆盖它又写入的版本。
        if saved:
            if _snapshot(p, target, MAX_CONFIG if rel == CONFIG else MAX_BYTES)[1] != hashlib.sha256(raw).hexdigest():
                raise Conflict("保存异常后正文又有修改，已保留现场和旧稿历史，请刷新核对")
            if old is None:
                target.unlink(missing_ok=True)
            else:
                rollback = _stage(p, target, old)
                atomic.replace(rollback, target)
        if log_saved:
            if _snapshot(p, logtarget, 64 * 1024 * 1024)[1] != hashlib.sha256(lograw + journal._entry(entry).encode("utf-8")).hexdigest():
                raise Conflict("保存异常后机器日志又有修改，已保留现场，请核对")
            if oldlog is None:
                logtarget.unlink(missing_ok=True)
            else:
                rollback = _stage(p, logtarget, oldlog)
                atomic.replace(rollback, logtarget)
    # 与 journal.add 相同的数据库写锁，跨网页/MCP进程串行本系统的保存。
    # 本机外部编辑器不参与该锁；最后核对到 replace 的边界不是 OS 写锁。
    with _write_transaction(conn, undo):
        try:
            info = _ordinary(p, target, missing=True)
            if info is not None:
                old, current = _snapshot(p, target, MAX_CONFIG if rel == CONFIG else MAX_BYTES)
                _text(old)
                if not revision or current != revision:
                    raise Conflict("文件已经存在或版本已改变，请重新读取后合并")
            elif revision:
                raise Conflict("原文件已经移走，不能用旧版本新建")
            logtarget = _log_outputs(p)
            if logtarget.exists():
                oldlog, _ = _snapshot(p, logtarget, 64 * 1024 * 1024)
            at = datetime.now()
            history_root = base / "历史" / "内容工作台"
            _ordinary(p, history_root, missing=True)
            if old is not None:
                history = history_root / f"{at:%Y%m%d-%H%M%S}-{uuid.uuid4().hex}" / rel
                hstage = _stage(p, history, old)
                try:
                    os.link(hstage, history)
                finally:
                    hstage.unlink(missing_ok=True)
                metadata = history.parent / (history.name + ".保存信息.json")
                mstage = _stage(p, metadata, (json.dumps({"module": module, "path": rel, "revision": revision,
                                "project_root": str(_root(p)), "by": by, "source": source,
                                "at": at.isoformat(), "reason": reason}, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
                try:
                    os.link(mstage, metadata)
                finally:
                    mstage.unlink(missing_ok=True)
            staged = _stage(p, target, raw)
            # journal.add 自己开事务；这里复用格式/编号，在当前事务中记同一份日志。
            n = journal._next(conn, p)
            body = f"{source} · 资料/{module}/{rel}\n" + (reason.strip() + "\n" if reason.strip() else "")
            body += f"版本：{revision or '新建'} → {hashlib.sha256(raw).hexdigest()}"
            body = journal.notebook._clean(body)
            entry = {"id": f"志-{n:04d}", "at": at.strftime("%Y-%m-%d %H:%M"), "by": by,
                     "kind": "保存了内容正文", "scope": module, "body": body}
            lograw = oldlog if oldlog else journal._head(at.strftime("%Y-%m")).encode("utf-8")
            logstage = _stage(p, logtarget, lograw + journal._entry(entry).encode("utf-8"))
            _log_outputs(p)
            _ordinary(p, target, missing=old is None)
            if old is not None and _snapshot(p, target, MAX_CONFIG if rel == CONFIG else MAX_BYTES)[1] != revision:
                raise Conflict("保存前文件又有修改，请重新读取后合并")
            if old is None:
                try:
                    os.link(staged, target)  # 独占新建：撞名不会覆盖现有文件。
                except FileExistsError as e:
                    raise Conflict("同名文件已经出现，请换名或重新读取") from e
            else:
                atomic.replace(staged, target)
            saved = True
            atomic.replace(logstage, logtarget)
            log_saved = True
            store.log(conn, by, entry["kind"], entry["id"], body[:120])
        finally:
            for tmp in (staged, logstage):
                if tmp is not None:
                    tmp.unlink(missing_ok=True)
    return {"module": module, "project_root": str(_root(p)), "path": rel,
            "text": text, "revision": hashlib.sha256(raw).hexdigest(), "editable": True}
