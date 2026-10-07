"""内置继承：普通文件配置、路径检查、复制清单和设置预览共用一套规则。

10-07 起统一管理（作者：「我想统一内置模块，去掉每个模块自己的内置模块统一管理」「每个模块都干净一点，文件分拣可以精确到每个模块的具体文件夹」）：
- 项目里不再有各处的 `内置/` 文件夹；要带进新项目的，只看项目根 `内置标记.json` 这一份清单，里面可以是文件，也可以是整个文件夹
- 固定带的另算：程序和网页（CORE_*）、`backend/builtin_resources.json` 列的应用资源、各内容模块的 `工作台/`（随模块带）
- 老样子的项目（还有 `内置/` 的）用 migrate_layout 搬一次：资料/<模块>/内置/通用 → 工作台/，其余 → 方法/；资料以外的去掉「内置」这一层
"""
from __future__ import annotations

import json
import os
import re
import hashlib
import stat
import tempfile
import threading
import time
import sqlite3
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath

PROTECTED = {'索引', '存档', '回收站'}
RUN_RECORDS = {'agent', '开工单', '施工计划', '交付', '交接', '答疑', '日志', '运行状态', '世界树', '清理', '摘要', '重写单', '流程状态'}
SKIP = {'.git', '.claude', '.pytest_cache', '__pycache__', '.venv', 'venv', 'node_modules'}
CORE_DIRS = ['backend', '技能库', '快捷指令', '插件', '外观', '品牌', '自动化/工作流',
             '工具库/安装指南', '工具库/应用']        # 10-07 统一内置：原来在 工具库/内置/ 里、每个新项目都带的工具指南和应用卡
CORE_FILES = ['治理界面.js', '模板.html', '界面英文.js', '代码地图.js', '启动.bat', '新项目.bat',
              '.mcp.json', '.gitignore', '使用说明.md', '使用说明.en.md',
              'CLAUDE.md', 'DESIGN.md', '治理/戒律/1 通用戒律.md', 'LICENSE', 'NOTICE', '第三方许可证.md',
              '自动化/协议.md', '.claude/settings.json', 'README.md', 'README.en.md', '模板配置.json',
              '自动化/交付策略.json', '工具库/下载/许可证来源.json']      # 10-07：原来在 自动化/内置/、工具库/下载/内置/


class Invalid(ValueError):
    pass


class Conflict(Invalid):
    """The caller must refresh its view before changing another revision."""


MARKS_FILE = '内置标记.json'
MAX_MARKS = 500
MAX_MARKS_BYTES = 512 * 1024
_MARKS_LOCK = threading.RLock()
_MARKS_LOCAL = threading.local()


def _mark_rel(value: object) -> str:
    """Pure validation shared by live and historical mark documents."""
    if (not isinstance(value, str) or not value or len(value) > 2048
            or value != value.strip() or '\\' in value):
        raise Invalid('内置标记需要规范的项目相对文件路径')
    parts = value.split('/')
    if (PureWindowsPath(value).drive or value.startswith('/')
            or any(p in ('', '.', '..') or p.startswith(('.', '_')) or p.endswith((' ', '.')) for p in parts)
            or any(re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', p, re.I) for p in parts)
            or any(c in value for c in ':*?"<>|') or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise Invalid('内置标记路径不能越界、隐藏或使用 Windows 路径别名')
    if (parts[0] in PROTECTED or '原件' in parts or '历史' in parts or '预览缓存' in parts
            or any(p.casefold() in {s.casefold() for s in SKIP} for p in parts)
            or (parts[0] == '归档' and parts[1:2] != ['内置'])):
        raise Invalid('系统索引、存档、回收站、缓存和历史原件不能人工标记内置')
    if (parts[0] == '自动化' and len(parts) > 1
            and parts[1].casefold() in {p.casefold() for p in RUN_RECORDS} and '内置' not in parts):
        raise Invalid('自动化运行记录不能人工标记内置，请使用独立内置模板')
    if parts[:3] == ['自动化', '工作流', '项目'] or parts[:2] == ['自动化', '流程状态']:
        raise Invalid('项目工作流和运行状态不能人工标记内置')
    if value in (MARKS_FILE, '内置配置.json', '新项目复制清单.json'):
        raise Invalid('内置标记和生成清单由程序管理，不能再标记自身')
    return value


def parse_marks(raw: bytes) -> dict:
    """Validate v1 ordinary-file metadata without requiring originals to exist."""
    if not isinstance(raw, bytes) or len(raw) > MAX_MARKS_BYTES:
        raise Invalid('内置标记文件超过允许大小')
    try:
        data = json.loads(raw.decode('utf-8-sig'))
    except (ValueError, UnicodeError) as exc:
        raise Invalid('内置标记 JSON 读不了，请先修复；没有把损坏清单当成空清单') from exc
    if (not isinstance(data, dict) or set(data) != {'version', 'paths'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['paths'], list) or len(data['paths']) > MAX_MARKS):
        raise Invalid('内置标记应为 version=1、paths 路径列表（文件或文件夹），最多 500 项')
    result, seen = [], set()
    for value in data['paths']:
        rel = _mark_rel(value)
        key = rel.casefold()
        if key in seen:
            raise Invalid('内置标记重复或有大小写路径别名：' + rel)
        seen.add(key)
        result.append(rel)
    return {'version': 1, 'paths': sorted(result, key=lambda x: (x.casefold(), x))}


def _marks_root(root: Path) -> Path:
    root = Path(os.path.abspath(root))
    if _linked(root) or not root.is_dir():
        raise Invalid('内置标记的项目根必须是普通文件夹，不能是链接')
    return root.resolve()


def project_key(root: Path) -> str:
    return os.path.normcase(str(_marks_root(root))).replace('\\', '/')


def _mark_ordinary(root: Path, target: Path, *, missing: bool = False, file: bool = True) -> Path:
    """Check every component before following it; permits absent history paths."""
    try:
        parts = target.absolute().relative_to(root).parts
    except ValueError as exc:
        raise Invalid('内置标记路径离开项目') from exc
    if not parts or any(part in ('.', '..') for part in parts):
        raise Invalid('内置标记路径不能含上级目录或指向项目根')
    current = root
    for index, part in enumerate(parts):
        current /= part
        if _linked(current):
            raise Invalid('内置标记不能经过符号链接或目录联接')
        try:
            info = current.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise Invalid('内置标记文件已移动或不存在：' + '/'.join(parts)) from None
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise Invalid('内置标记的上级路径不是文件夹')
        if index == len(parts) - 1 and file and not stat.S_ISREG(info.st_mode):
            raise Invalid('这里只能标记单个普通文件')
    return target


def _marks_bytes(root: Path) -> tuple[bytes, bool]:
    root = _marks_root(root)
    f = _mark_ordinary(root, root / MARKS_FILE, missing=True)
    exists = f.is_file()
    if exists:
        if f.stat().st_size > MAX_MARKS_BYTES:
            raise Invalid('内置标记文件超过允许大小')
        before = f.stat()
        raw = f.read_bytes()
        if len(raw) > MAX_MARKS_BYTES:
            raise Invalid('内置标记文件超过允许大小')
        _mark_ordinary(root, f)
        after = f.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise Conflict('读取时内置标记改变，请刷新后重试')
    else:
        raw = b''
    return raw, exists


def marks_revision(root: Path) -> str:
    """Raw CAS token, also usable when a full restore repairs malformed JSON."""
    return hashlib.sha256(_marks_bytes(root)[0]).hexdigest()


def read_marks(root: Path) -> dict:
    """Read-only. An absent manifest has a stable revision and creates nothing."""
    root = _marks_root(root)
    raw, exists = _marks_bytes(root)
    data = parse_marks(raw) if exists else {'version': 1, 'paths': []}
    return {**data, 'revision': hashlib.sha256(raw).hexdigest(), 'exists': exists,
            'project': project_key(root)}


@contextmanager
def marks_guard(root: Path):
    """Reentrant in this thread; OS-locked across cooperating processes."""
    root = _marks_root(root)
    key = project_key(root)
    with _MARKS_LOCK:
        depths = getattr(_MARKS_LOCAL, 'depths', None)
        if depths is None:
            depths = _MARKS_LOCAL.depths = {}
        if depths.get(key, 0):
            depths[key] += 1
            try:
                yield
            finally:
                depths[key] -= 1
            return
        directory = _mark_ordinary(root, root / '索引', missing=True, file=False)
        directory.mkdir(exist_ok=True)
        f = _mark_ordinary(root, directory / '内置标记.lock', missing=True)
        with f.open('a+b') as handle:
            _mark_ordinary(root, f)
            if f.stat().st_size == 0:
                handle.write(b'0')
                handle.flush()
            acquired = False
            for attempt in range(40):
                try:
                    handle.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError:
                    time.sleep(0.05)
            if not acquired:
                raise Conflict('另一处正在修改内置标记，请稍后重试')
            depths[key] = 1
            try:
                yield
            finally:
                depths.pop(key, None)
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def replace_marks(root: Path, paths: list[str], expected_revision: str) -> dict:
    """CAS + atomic replacement for explicit changes/restores. Does not log."""
    root = _marks_root(root)
    if not isinstance(expected_revision, str) or not re.fullmatch('[a-f0-9]{64}', expected_revision):
        raise Invalid('缺少内置标记版本，请重新读取')
    data = parse_marks(json.dumps({'version': 1, 'paths': paths}, ensure_ascii=False).encode('utf-8'))
    with marks_guard(root):
        raw, exists = _marks_bytes(root)
        if hashlib.sha256(raw).hexdigest() != expected_revision:
            raise Conflict('内置标记已在另一处改变，请刷新后重试')
        try:
            current_paths = parse_marks(raw)['paths'] if exists else []
        except Invalid:
            current_paths = None  # A whole-manifest restore can repair it.
        if data['paths'] == current_paths:
            return read_marks(root)
        raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        fd, name = tempfile.mkstemp(prefix='.内置标记-', suffix='.tmp', dir=root)
        staged = Path(name)
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(raw)
                out.flush()
                os.fsync(out.fileno())
            _mark_ordinary(root, root / MARKS_FILE, missing=True)
            if marks_revision(root) != expected_revision:
                raise Conflict('内置标记在写入前改变，请刷新后重试')
            import atomic
            atomic.replace(staged, root / MARKS_FILE)
        finally:
            if staged.exists():
                staged.unlink()
        return read_marks(root)


def _mark_state(root: Path, rel: str, marks: dict, *, original: Path | None = None) -> dict:
    parts = rel.split('/') if isinstance(rel, str) else []
    owner = parts[1] if len(parts) > 2 and parts[0] == '资料' else ''
    out = {'path': rel, 'project': marks['project'], 'revision': marks['revision'],
           'state': 'ineligible', 'enabled': False, 'toggle_allowed': False, 'reason': '',
           'owner_module': owner, 'origin': ''}
    try:
        if original is not None:
            _mark_ordinary(root, Path(os.path.abspath(original)), missing=True)
        if rel == MARKS_FILE:
            out.update(state='required', enabled=True, origin='generated', reason='内置标记随实际复制内容生成')
            return out
        if not isinstance(rel, str):
            raise Invalid('内置标记需要规范的项目相对文件路径')
        if rel.casefold() not in {r.casefold() for r in CORE_FILES}:
            _mark_rel(rel)
        target = _mark_ordinary(root, root / rel, missing=True, file=not (root / rel).is_dir())
        canonical = target.resolve().relative_to(root).as_posix()
        if canonical.casefold() != rel.casefold():
            raise Invalid('请使用文件的完整规范路径，不能使用短文件名别名')
        if rel.casefold() == 'agents.md' and target.exists():
            out.update(state='required', enabled=True, origin='generated', reason='接手说明由新项目生成，默认带上')
            return out
        required = next((r for r in mandatory_paths(root)
                         if rel.casefold() == r.casefold() or rel.casefold().startswith(r.casefold() + '/')), None)
        # Required hidden core files still display their true inherited state.
        if required:
            _mark_ordinary(root, root / rel, file=not (root / rel).is_dir())
            out.update(state='required', enabled=True, origin='core', reason='应用核心或运行依赖默认带上')
            return out
        rel = _mark_rel(rel)
        marked = rel.casefold() in {x.casefold() for x in marks['paths']}
        out['kind'] = 'folder' if target.is_dir() else 'file'
        holder = next((x for x in marks['paths'] if rel.casefold().startswith(x.casefold() + '/')
                       and (root / x).is_dir()), None)
        bench = next((x for x in workbench_dirs(root) if rel.casefold().startswith(x.casefold() + '/')
                      or rel.casefold() == x.casefold()), None)
        if not target.exists():
            out.update(state='missing', enabled=marked, toggle_allowed=marked,
                       origin='manual' if marked else '', reason='原文件已移动或不存在；可解除已有标记')
        elif bench:
            out.update(state='required', enabled=True, origin='module', reason='模块工作台随模块带上')
        elif is_template(rel) or holder:
            out.update(state='required', enabled=True, origin='folder',
                       reason=f'所在文件夹「{holder}」整个带上；要改去 设置 → 内置' if holder else '内置文件夹中的文件默认带上')
        else:
            out.update(state='marked' if marked else 'unmarked', enabled=marked,
                       toggle_allowed=True, origin='manual' if marked else '')
    except (OSError, ValueError) as exc:
        out['reason'] = str(exc)
    return out


def mark_state(root: Path, path: str, *, original: Path | None = None) -> dict:
    root = _marks_root(root)
    return _mark_state(root, path, read_marks(root), original=original)


def list_marks(root: Path) -> dict:
    root = _marks_root(root)
    marks = read_marks(root)
    return {**marks, 'items': [_mark_state(root, rel, marks) for rel in marks['paths']]}


def set_mark(conn, project, path: str, enabled: bool, project_key: str, revision: str, *, by: str = '人') -> dict:
    """One explicit UI/MCP action; records its actual outcome in machine logs."""
    import journal
    root = _marks_root(project.root)
    if type(enabled) is not bool:
        raise Invalid('内置标记开关必须是 true 或 false')
    if not isinstance(by, str) or not by.strip() or len(by) > 200 or any(ord(c) < 32 for c in by):
        raise Invalid('标记操作者须是单行名称')
    with marks_guard(root):
        current = read_marks(root)
        if project_key != current['project']:
            raise Conflict('项目已切换，请重新打开当前项目文件')
        if revision != current['revision']:
            raise Conflict('内置标记已改变，请刷新后重试')
        database = next((r[2] for r in conn.execute('PRAGMA database_list') if r[1] == 'main'), '')
        expected_db = Path(os.path.abspath(project.db_path))
        _mark_ordinary(root, expected_db)
        if not database or os.path.normcase(str(Path(database).resolve())) != os.path.normcase(str(expected_db.resolve())):
            raise Invalid('记录内置标记的数据库不属于当前项目')
        action = _mark_state(root, path, current)
        if not action['toggle_allowed'] or (enabled and action['state'] == 'missing'):
            raise Invalid(action['reason'] or '这个文件不能修改内置标记')
        if enabled and os.path.normcase(str(root / path)) == os.path.normcase(str(expected_db)):
            raise Invalid('当前项目索引数据库不能人工标记内置')
        if enabled:
            # Windows lookup is case-insensitive; store the existing spelling so
            # a child keeps the same module identity and remains portable.
            folder = (root / _mark_rel(path)).is_dir()
            target = _mark_ordinary(root, root / _mark_rel(path), file=not folder)
            path = target.resolve().relative_to(root).as_posix()
            _mark_ordinary(root, root / path, file=not folder)
        # Validate log outputs before writing the live manifest.
        from datetime import datetime
        log = root / '笔记/日志' / f'{datetime.now():%Y-%m}.md'
        _mark_ordinary(root, log, missing=True)
        paths = [r for r in current['paths'] if r.casefold() != path.casefold()]
        if enabled:
            paths.append(_mark_rel(path))
        updated = replace_marks(root, paths, revision)
        result = _mark_state(root, path, updated)
        result['changed'] = updated['revision'] != current['revision']
        if result['changed']:
            try:
                entry = journal.add(conn, project, f'{"文件夹" if result.get("kind") == "folder" else "文件"}：{path}\n内置标记：{"开启" if enabled else "关闭"}\n'
                                    '作用：新建项目随所选模块继承；不限制文件编辑，不改变全量存档范围。',
                                    kind='内置标记', by=by, scope=result['owner_module'] or '总览')
                result['log_id'] = entry['id']
            except (OSError, ValueError, sqlite3.Error) as exc:
                result['warning'] = '标记已保存，日志写入失败：' + str(exc)
        return result


def project_marks(root: Path, copied_paths: list[str]) -> dict:
    """A new project receives only manual marks whose files it actually copied."""
    marks = read_marks(root)
    return {'version': 1, 'paths': copied_marks(marks['paths'], copied_paths)}


def copied_marks(paths: list[str], copied_paths: list[str]) -> list[str]:
    """新项目留下的标记：文件要真带走了；文件夹要带走了里面至少一个文件。"""
    copied = {x.casefold(): x for x in copied_paths}
    out = []
    for rel in paths:
        key = rel.casefold()
        if key in copied:
            out.append(copied[key])
        elif any(c.startswith(key + '/') for c in copied):
            out.append(rel)
    return out


def is_template(rel: str) -> bool:
    """内置目录中的文件是可继承模板，不是当前项目的运行记录。"""
    return '内置' in rel.replace('\\', '/').split('/')[:-1]


def _linked(p: Path) -> bool:
    return p.is_symlink() or p.is_junction()


def path(root: Path, value: str, *, exists: bool = True) -> Path:
    """只允许项目内明确路径，拒绝受保护记录及链接，避免复制时越界。"""
    root = root.resolve()
    if not isinstance(value, str):
        raise Invalid('路径必须是文字')
    value = value.strip().replace('\\', '/').rstrip('/')
    parts = value.split('/')
    if (not value or PureWindowsPath(value).drive or value.startswith('/')
            or any(p in ('', '.', '..') or p.startswith('.') or p.endswith((' ', '.')) for p in parts)
            or any(re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', p, re.I) for p in parts)
            or any(c in value for c in ':*?"<>|\x00')):
        raise Invalid('只填写项目内的相对文件或文件夹路径')
    if parts[0] in PROTECTED or any(p.startswith('_') for p in parts) or '原件' in parts or '历史' in parts:
        raise Invalid('运行记录、外部入口和历史原件不作为内置')
    if parts[0] == '自动化' and len(parts) > 1 and parts[1] in RUN_RECORDS and '内置' not in parts:
        raise Invalid('自动化运行记录不作为内置，请使用其中独立的内置目录')
    if parts[:3] == ['自动化', '工作流', '项目']:
        raise Invalid('项目私有工作流及历史不作为内置，通用工作流模板仍可继承')
    if parts[:2] == ['自动化', '流程状态']:
        raise Invalid('启用快照及停用守卫不作为内置，新项目自行配置流程')
    candidate = root
    for part in parts:
        candidate /= part
        if _linked(candidate):
            raise Invalid('内置不能包含软链接或目录联接：' + value)
    if not candidate.resolve().is_relative_to(root):
        raise Invalid('内置路径不能离开项目')
    if exists and not candidate.exists():
        raise Invalid('找不到内置路径：' + value)
    return candidate.resolve()


def validate(root: Path, config: dict) -> dict:
    if not isinstance(config, dict) or config.get('version', 1) != 1:
        raise Invalid('内置配置格式不对，应为第1版')
    if config.get('disabled'):
        raise Invalid('内置固定必带，不能取消')
    out = {'version': 1, 'extra': []}
    for key in ('extra',):
        values = config.get(key, [])
        if not isinstance(values, list) or len(values) > 500:
            raise Invalid(key + '应是最多500条路径的列表')
        for value in values:
            p = path(root, value)
            rel = p.relative_to(root.resolve()).as_posix()
            if key == 'extra' and (rel in CORE_DIRS or rel in {'资料', '治理', '自动化', '工具库', '归档'}):
                raise Invalid('请选择具体模块内的文件或资料文件夹')
            if rel not in out[key]:
                out[key].append(rel)
    return out


def files(root: Path, selected: Path, *, core: bool = False) -> list[str]:
    """只列路径和大小，不读材料正文；被选目录中的链接一律报错。"""
    root = root.resolve()
    try:
        rel = selected.absolute().relative_to(root)
    except ValueError as exc:
        raise Invalid('复制路径不能离开项目') from exc
    candidate = root
    for part in rel.parts:
        candidate /= part
        if _linked(candidate):
            raise Invalid('内置不能包含链接：' + rel.as_posix())
    if not selected.resolve().is_relative_to(root):
        raise Invalid('复制路径不能离开项目')
    if selected.is_file():
        return [selected.relative_to(root).as_posix()]
    out = []
    for folder, dirs, names in os.walk(selected, followlinks=False):
        base = Path(folder)
        for n in dirs + names:
            if n not in SKIP and _linked(base / n):
                raise Invalid('复制目录中有链接：' + (base / n).relative_to(root).as_posix())
            if not core and n.startswith('.') and n != '.gitkeep' and n not in SKIP:
                raise Invalid('内置目录中有隐藏项：' + (base / n).relative_to(root).as_posix())
        dirs[:] = sorted(d for d in dirs if d not in SKIP and (not core or d != '内置')
                         and not (base.relative_to(root).as_posix() == '自动化/工作流' and d == '项目'))
        for n in sorted(names):
            if core and n.endswith(('.pyc', '.pyo', '.tmp', '.log', '.part')):
                continue
            out.append((base / n).relative_to(root).as_posix())
    return out


def workbench_dirs(root: Path) -> list[str]:
    """各内容模块的 工作台/（工作台设置、模板、示例）：选了这个模块就随模块带上。"""
    base = root / '资料'
    out = []
    for m in sorted(base.iterdir()) if base.is_dir() else []:
        d = m / '工作台'
        if m.is_dir() and not m.name.startswith(('.', '_')) and not _linked(m) and d.is_dir() and not _linked(d):
            out.append(f'资料/{m.name}/工作台')
    return out


def folders(root: Path) -> list[str]:
    """整个带走的文件夹：清单里勾的文件夹 + 各内容模块的 工作台/。不再到处找 内置/（10-07 统一管理）。"""
    root = root.resolve()
    out = workbench_dirs(root)
    try:
        marked = read_marks(root)['paths']
    except Invalid:
        marked = []                                  # 清单坏了由 preview 报，这里不替它当空清单用
    for rel in marked:
        d = root / rel
        if d.is_dir() and not _linked(d):
            path(root, rel)
            out.append(rel)
    return sorted(set(out))


def legacy_folders(root: Path) -> list[str]:
    """老样子留下的 内置/ 文件夹（10-07 以前到处都有）：只找最外层的，历史、原件、存档、回收站、索引里的不算。"""
    root = root.resolve()
    out = []
    for top in sorted(root.iterdir()) if root.is_dir() else []:
        if not top.is_dir() or top.name.startswith(('.', '_')) or top.name in PROTECTED or top.name in SKIP or _linked(top):
            continue
        for folder, dirs, _ in os.walk(top, followlinks=False):
            base = Path(folder)
            if '内置' in dirs and not _linked(base / '内置'):
                out.append((base / '内置').relative_to(root).as_posix())
            dirs[:] = sorted(d for d in dirs if d != '内置' and not d.startswith(('.', '_'))
                             and d not in SKIP | {'原件', '历史', '预览缓存'} and not _linked(base / d))
    return sorted(set(out))


def mandatory_paths(root: Path) -> list[str]:
    paths = [p for p in CORE_FILES if (root / p).is_file()]
    paths += [p for p in CORE_DIRS if (root / p).is_dir()]
    manifest = root / 'backend' / 'builtin_resources.json'
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding='utf-8-sig'))
            extra = data['paths']
            if data.get('version') != 1 or not isinstance(extra, list):
                raise ValueError('格式不对')
            for rel in extra:
                path(root, rel)
            paths += extra
        except (KeyError, ValueError, UnicodeError) as exc:
            raise Invalid('应用内置资源清单读不了：' + str(exc)) from exc
    return list(dict.fromkeys(paths))


def preview(root: Path, config: dict | None = None) -> dict:
    root = root.resolve()
    config = validate(root, config or {})
    mandatory = mandatory_paths(root)
    selected = set()
    for rel in mandatory:
        selected.update(files(root, root / rel, core=True))
    rows = []
    for rel in folders(root):
        xs = files(root, root / rel)
        rows.append({'path': rel, 'selected': True, 'files': len(xs), 'bytes': sum((root / x).stat().st_size for x in xs)})
        selected.update(xs)
    marks = read_marks(root)
    mark_issues = []
    for rel in marks['paths']:
        state = _mark_state(root, rel, marks)
        if state['state'] in {'ineligible', 'missing'}:
            mark_issues.append({'path': rel, 'reason': state['reason']})
        elif state.get('kind') == 'folder':
            continue                                 # 整个文件夹已经在上面 folders() 里算了
        elif state['state'] != 'required':
            selected.add((root / rel).resolve().relative_to(root).as_posix())
    base = set(selected)
    for rel in config['extra']:
        selected.update(files(root, path(root, rel)))
    # Generated/project-specific versions are written by make; never borrow the current project's content.
    selected.discard('内置配置.json')
    selected.discard(MARKS_FILE)  # Each child gets its filtered projection.
    selected.discard('AGENTS.md')
    copied = sorted(selected)
    extra_files = selected - base
    return {'config': config, 'folders': rows, 'mandatory': mandatory,
            'marks': marks, 'marked_paths': marks['paths'], 'mark_issues': mark_issues,
            'files': len(copied), 'bytes': sum((root / x).stat().st_size for x in copied), 'copied_paths': copied,
            'extra_files': len(extra_files), 'extra_bytes': sum((root / x).stat().st_size for x in extra_files),
            'default_parent': str(root.parent)}


def browse(root: Path, rel: str = '') -> dict:
    """额外资料弹窗逐层列目录；核心和内置只显示必带，不读文件内容。"""
    root = root.resolve()
    d = path(root, rel) if rel else root
    if not d.is_dir():
        raise Invalid('这里只展开文件夹')
    required = mandatory_paths(root) + folders(root)
    def is_required(p):
        return any(p == x or p.startswith(x + '/') for x in required)
    rows = []
    for f in sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.casefold())):
        r = f.relative_to(root).as_posix()
        if f.name.startswith(('.', '_')) or f.name in SKIP or _linked(f) or r.casefold() == MARKS_FILE.casefold():
            continue
        try:
            path(root, r)
        except Invalid:
            continue
        container = r in {'资料', '治理', '自动化', '工具库', '归档'}
        rows.append({'path': r, 'name': f.name, 'kind': 'folder' if f.is_dir() else 'file',
                     'bytes': f.stat().st_size if f.is_file() else 0, 'required': r == 'AGENTS.md' or is_required(r),
                     'selectable': not container, 'children': f.is_dir()})
    return {'path': rel, 'parent': d.parent.relative_to(root).as_posix() if d != root else '', 'items': rows}


# ---------------------------------------------------------------- 搬家：老样子的 内置/ → 模块自己的文件夹（10-07）

LAYOUT_RECORD = '自动化/清理/内置搬家.json'
# 资料/<模块>/内置/ 里这几样不进「方法/」：做好的演示稿是作品；剪辑改宣传片留下的迁移底稿放回模块根、不进清单（是历史）
_SPECIAL = {('PPT', 'MiracleHarness项目介绍'): '作品/MiracleHarness项目介绍',
            ('宣传片', '迁移前文档'): '迁移前文档', ('宣传片', '迁移对照.json'): '迁移对照.json'}
_HISTORY = ('迁移前文档', '迁移对照.json')
_TEXT = ('.json', '.md', '.txt', '.csv')


def _module_parent(parent: str) -> str | None:
    parts = parent.split('/')
    return parts[1] if len(parts) == 2 and parts[0] == '资料' else None


def _layout_target(parent: str, rest: str) -> str:
    """内置/ 里的一样东西搬到哪：资料/<模块>/内置/通用 → 工作台/，别的 → 方法/；资料以外去掉「内置」这一层。"""
    module = _module_parent(parent)
    if module is None:
        return f'{parent}/{rest}'
    first, _, tail = rest.partition('/')
    if first == '通用':
        head = '工作台'
    elif first in ('方法', '工作台', '作品'):         # 本来就叫这个的，直接并进去，不套两层
        head = first
    else:
        head = _SPECIAL.get((module, first)) or f'方法/{first}'
    return f'{parent}/{head}' + (f'/{tail}' if tail else '')


def _mandatory(root: Path, rel: str) -> bool:
    try:
        fixed = mandatory_paths(root)
    except Invalid:
        fixed = CORE_FILES + CORE_DIRS
    return any(rel.casefold() == x.casefold() or rel.casefold().startswith(x.casefold() + '/') for x in fixed)


def plan_layout(root: Path) -> dict:
    """只算不动：每个老 内置/ 里的文件搬到哪、空的有哪些、文件里写着的旧路径换成什么、哪些进清单。"""
    root = root.resolve()
    moves, empty, pairs, listed = [], [], [], []
    for d in legacy_folders(root):
        parent = d.rsplit('/', 1)[0]
        base = root / d
        files = []
        for folder, dirs, names in os.walk(base, followlinks=False):
            dirs[:] = sorted(x for x in dirs if not _linked(Path(folder) / x))
            files += [Path(folder) / n for n in sorted(names) if n != '.gitkeep' and not _linked(Path(folder) / n)]
        if not files:
            empty.append(d)
            continue
        firsts = []
        for p in files:
            rest = p.relative_to(base).as_posix()
            moves.append({'from': f'{d}/{rest}', 'to': _layout_target(parent, rest)})
            if rest.split('/')[0] not in firsts:
                firsts.append(rest.split('/')[0])
        module = _module_parent(parent)
        for first in firsts:
            new = _layout_target(parent, first)
            pairs.append({'old': f'{d}/{first}', 'new': new, 'within': ''})
            if module:                                   # 模块里自己的设置写的是「内置/通用/模板/…」这种相对路径
                pairs.append({'old': f'内置/{first}', 'new': new[len(parent) + 1:], 'within': parent + '/'})
            if module and first == '通用':
                continue                                 # 工作台随模块带，不用进清单
            if (module and first in _HISTORY) or any(x in _HISTORY for x in parent.split('/')):
                continue
            entry = f'{parent}/方法' if module and new.startswith(f'{parent}/方法/') else new
            if not _mandatory(root, entry) and entry not in listed:
                listed.append(entry)
    pairs.sort(key=lambda x: -len(x['old']))
    return {'folders': legacy_folders(root), 'moves': moves, 'empty': empty, 'pairs': pairs, 'listed': listed}


def _rewrite_text(text: str, pairs: list[dict], rel: str) -> str:
    for x in pairs:
        if x['within'] and not rel.startswith(x['within']):
            continue
        text = re.sub(r'(?<![A-Za-z0-9_/.\-])' + re.escape(x['old']) + r'(?=[/"\'`)\]\s>|,]|$)', lambda _: x['new'], text, flags=re.M)
    return text


_LINKS = (re.compile(r'(\]\(<)([^>\n]+)(>)'), re.compile(r'(\]\()([^)<\s]+)(\))'),
          re.compile(r'((?:src|href)=")([^"\n]+)(")'))


def _mapper(moves: list[dict], pairs: list[dict]):
    """旧位置 → 新位置：先看文件一对一搬的，再看整个文件夹换了前缀的。"""
    files = {m['from']: m['to'] for m in moves}
    prefixes = sorted([x for x in pairs if not x['within']], key=lambda x: -len(x['old']))

    def to_new(old: str) -> str:
        if old in files:
            return files[old]
        for x in prefixes:
            if old == x['old'] or old.startswith(x['old'] + '/'):
                return x['new'] + old[len(x['old']):]
        return old
    return to_new


def _relink(text: str, old_rel: str, new_rel: str, to_new) -> str:
    """文件里的相对链接（[x](../a.md)、src="…"）：照旧位置算出指向谁，再从新位置重算一遍。网址、锚点、绝对路径不动。"""
    import posixpath
    from urllib.parse import quote, unquote

    def fix(m):
        link = m.group(2)
        if re.match(r'^(?:[a-z][a-z0-9+.-]*:|#|/)', link, re.I):
            return m.group(0)
        target, sep, anchor = link.partition('#')
        if not target:
            return m.group(0)
        raw = unquote(target)
        old_target = posixpath.normpath(posixpath.join(posixpath.dirname(old_rel), raw))
        if old_target.startswith('..'):
            return m.group(0)
        new_target = to_new(old_target)
        if new_target == old_target and old_rel == new_rel:
            return m.group(0)
        new_link = posixpath.relpath(new_target, posixpath.dirname(new_rel) or '.')
        if raw.endswith('/') and not new_link.endswith('/'):
            new_link += '/'
        if new_link == raw:
            return m.group(0)
        if '%' in target:
            new_link = quote(new_link, safe='/._-~')
        return m.group(1) + new_link + sep + anchor + m.group(3)

    for pattern in _LINKS:
        text = pattern.sub(fix, text)
    return text


def relink_files(root: Path, moves: list[dict], pairs: list[dict], extra: list[str]) -> list[str]:
    """搬过的文件按新旧位置重算链接、改设置里的旧路径；extra 是没搬、但可能指向搬走东西的说明和设置。"""
    to_new = _mapper(moves, pairs)
    where = {m['to']: m['from'] for m in moves}
    changed = []
    for rel in sorted(set(where) | set(extra)):
        f = root / rel
        if not f.is_file() or not _rewritable(rel):
            continue
        try:
            old = f.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            continue
        new = _rewrite_text(old, pairs, rel)
        if rel.endswith(('.md', '.html')):
            new = _relink(new, where.get(rel, rel), rel, to_new)
        if new != old:
            f.write_text(new, encoding='utf-8', newline='')
            changed.append(rel)
    return changed


def live_docs(root: Path) -> list[str]:
    """没搬的、但可能写着旧路径的说明和设置：根目录的说明、技能库、工具库、插件、各模块的技能，以及装到项目里的技能副本。
    记录（日志、交付、交接、计划）和人的笔记是历史，不改。"""
    out = [f.name for f in root.glob('*.md')]
    for base in ('技能库', '工具库', '插件', '.claude/skills'):
        d = root / base
        if d.is_dir():
            out += [f.relative_to(root).as_posix() for f in d.rglob('*') if f.is_file() and not _linked(f)]
    for m in (root / '资料').glob('*/技能') if (root / '资料').is_dir() else []:
        out += [f.relative_to(root).as_posix() for f in m.rglob('*') if f.is_file() and not _linked(f)]
    return out


def _rewritable(rel: str) -> bool:
    """只改我们自己写的设置和说明里的路径；第三方原件（来源/、sources/ 里的）一个字不动，迁移底稿是历史也不动。"""
    parts = rel.split('/')
    if not rel.endswith(_TEXT) or any(p in _HISTORY for p in parts):
        return False
    if '来源' in parts or 'sources' in parts:
        return rel.endswith(('lock.json', 'path-map.json')) and not rel.endswith('.original.json')
    return True


def migrate_layout(conn, p, *, by: str) -> dict:
    """照 plan_layout 搬：先搬文件（同名同内容的只留一份，不同内容的改名「（内置）」），再改设置里的旧路径，
    把模块里搬出来的加进清单，空了的 内置/ 一批进回收站，搬家对照记在 自动化/清理/内置搬家.json，日志记一条。
    能重复跑：没有 内置/ 了就什么都不做。调用的人负责先存档。"""
    import journal
    import trash
    from datetime import datetime
    root = p.root.resolve()
    done = {'moved': [], 'same': [], 'renamed': [], 'rewritten': [], 'listed': [], 'trashed': None, 'rounds': 0}
    while done['rounds'] < 5:
        plan = plan_layout(root)
        if not plan['folders']:
            break
        done['rounds'] += 1
        this_round = []
        for m in plan['moves']:
            src, dst = root / m['from'], root / m['to']
            if dst.exists():
                if dst.is_file() and dst.read_bytes() == src.read_bytes():
                    src.unlink()
                    done['same'].append(m)
                    continue
                stem, n = dst.stem, 1
                while dst.exists():
                    dst = dst.with_name(f'{stem}（内置{"" if n == 1 else n}）{dst.suffix}')
                    n += 1
                m = {**m, 'to': dst.relative_to(root).as_posix()}
                done['renamed'].append(m)
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dst)
            done['moved'].append(m)
            this_round.append(m)
        for rel in relink_files(root, this_round, plan['pairs'], live_docs(root)):
            if rel not in done['rewritten']:
                done['rewritten'].append(rel)
        done['listed'] += [x for x in plan['listed'] if x not in done['listed']]
        gone = [d for d in plan['folders'] if (root / d).is_dir()]
        leftover = [d for d in gone if any(x.is_file() and x.name != '.gitkeep' for x in (root / d).rglob('*'))]
        if leftover:
            raise Invalid('这些 内置/ 里还有没搬走的文件：' + '、'.join(leftover))
        if gone:
            r = trash.move_many(conn, p, gone, by=by, reason='统一内置：搬空的 内置/ 文件夹（里面只剩占位文件）')
            done['trashed'] = r.get('code') if isinstance(r, dict) else r
    if not done['rounds']:
        return done
    if done['listed']:
        with marks_guard(root):
            current = read_marks(root)
            have = {x.casefold() for x in current['paths']}
            add = [x for x in done['listed'] if x.casefold() not in have and (root / x).exists()]
            if add:
                replace_marks(root, current['paths'] + add, current['revision'])
    record = root / LAYOUT_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    try:
        rows = json.loads(record.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        rows = []
    rows.append({'at': datetime.now().strftime('%Y-%m-%d %H:%M'), 'by': by,
                 'moves': [{'from': m['from'], 'to': m['to']} for m in done['moved']],
                 'same': [m['from'] for m in done['same']], 'renamed': done['renamed'],
                 'rewritten': done['rewritten'], 'listed': done['listed'], 'trash': done['trashed']})
    record.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    journal.add(conn, p, f"统一内置：搬了 {len(done['moved'])} 个文件出 内置/（同样内容只留一份 {len(done['same'])} 个，"
                f"同名改名 {len(done['renamed'])} 个），改了 {len(done['rewritten'])} 份设置里的旧路径，清单加了 "
                f"{len(done['listed'])} 项，空的 内置/ 进了回收站 {done['trashed'] or '—'}。对照在 {LAYOUT_RECORD}",
                kind='统一内置', by=by)
    return done


def moved_away(root: Path, rel: str) -> bool:
    """这个路径是统一内置时搬走的（监管照这个认「搬了」，不报删了）。"""
    try:
        rows = json.loads((root / LAYOUT_RECORD).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    return any(rel == m.get('from') or rel in r.get('same', []) for r in rows for m in r.get('moves', []))
