"""Explicit, repeatable starter examples. Never run from a GET or ordinary scan.

validate() reads only selected manifests/sources before project creation.
initialize() uses that validated selection in an explicit create/setup operation;
it never overwrites working files, personal notes, or an existing library entry.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import threading
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import content_modules
import downloads
import library
from project import Project

MANIFEST = '工作台/入门示例.json'                   # 10-07 统一内置：从 内置/通用/ 搬到模块的 工作台/
MODULES = ('PPT', '文献')
MAX_MANIFEST = 128 * 1024
MAX_SOURCE = 64 * 1024 * 1024
MAX_GUIDE = 1024 * 1024
_LOCK = threading.RLock()


class Invalid(ValueError):
    pass


def _rel(value: object) -> str:
    try:
        return content_modules._relative(value)
    except (TypeError, ValueError) as exc:
        raise Invalid(str(exc)) from exc


def _ordinary(root: Path, rel: str, *, missing: bool = False) -> Path:
    target = root / _rel(rel)
    try:
        info = content_modules._ordinary(Project(root), target, missing=missing)
    except (ValueError, OSError) as exc:
        raise Invalid(str(exc)) from exc
    if info is not None and not stat.S_ISREG(info.st_mode):
        raise Invalid('示例需要普通文件：' + rel)
    return target


def _read(root: Path, rel: str, limit: int) -> bytes:
    target = _ordinary(root, rel)
    if target.stat().st_size > limit:
        raise Invalid('示例文件过大：' + rel)
    data = target.read_bytes()
    if len(data) > limit:
        raise Invalid('示例文件过大：' + rel)
    _ordinary(root, rel)  # Recheck path after reading; selected content is fingerprinted.
    return data


def _text(value: object, field: str, maximum: int = 1000, *, required: bool = True) -> str:
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > maximum:
        raise Invalid('示例字段不合法：' + field)
    if any(ord(c) < 32 for c in value) or '|' in value:
        raise Invalid('示例字段不能包含控制符或表格分隔符：' + field)
    return value.strip()


def _list(data: dict, key: str, maximum: int) -> list:
    value = data.get(key, [])
    if not isinstance(value, list) or len(value) > maximum or any(not isinstance(x, dict) for x in value):
        raise Invalid('入门示例的 ' + key + ' 格式不对')
    return value


def validate(source: Path, copied_paths: list[str]) -> dict:
    """Read selected files only; no directory creation, database or network use.

Manifest sources are relative to their own module and must be under 工作台/.
Unselected declarations are not read. Invalid selected declarations fail before
new_project.make creates the target.
"""
    try:
        root = content_modules._root(Project(Path(source)))
    except (ValueError, OSError) as exc:
        raise Invalid(str(exc)) from exc
    if not isinstance(copied_paths, (list, tuple, set)) or any(not isinstance(x, str) for x in copied_paths):
        raise Invalid('复制清单必须是项目相对文件路径')
    selected = set(copied_paths)
    fingerprints, modules, manifests = {}, [], {}
    for module in MODULES:
        base = '资料/' + module + '/'
        manifest = base + MANIFEST
        if manifest not in selected:
            continue
        raw = _read(root, manifest, MAX_MANIFEST)
        try:
            data = json.loads(raw.decode('utf-8-sig'))
        except (ValueError, UnicodeError) as exc:
            raise Invalid('入门示例 JSON 读不了：' + manifest) from exc
        if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
            raise Invalid('入门示例版本必须为 1：' + manifest)
        if set(data) - {'version', 'files', 'library', 'downloads'}:
            raise Invalid('入门示例存在未知字段：' + manifest)
        manifests[manifest] = hashlib.sha256(raw).hexdigest()

        def read_source(value, suffixes, limit=MAX_SOURCE):
            rel = _rel(value)
            if not rel.startswith('工作台/') or Path(rel).suffix.lower() not in suffixes:
                raise Invalid('示例来源须是本模块 工作台/ 里的指定格式：' + rel)
            full = base + rel
            if full not in selected:
                raise Invalid('示例来源没有纳入本次复制范围：' + full)
            blob = _read(root, full, limit)
            fingerprints[full] = hashlib.sha256(blob).hexdigest()
            return full, blob

        spec = {'module': module, 'files': [], 'library': [], 'downloads': []}
        used_targets = set()
        for item in _list(data, 'files', 8):
            if module != 'PPT' or set(item) != {'source', 'target'}:
                raise Invalid('files 只用于 PPT 的 source/target 文件')
            src, blob = read_source(item['source'], {'.pptx', '.pdf'})
            target = _rel(item['target'])
            if (len(target.split('/')) != 2 or not target.startswith('导出/')
                    or Path(target).suffix.lower() != Path(src).suffix.lower()):
                raise Invalid('PPT 示例只能进入导出/，且保持 pptx 或 pdf 格式')
            if target.casefold() in used_targets:
                raise Invalid('入门示例重复写入同一路径：' + target)
            used_targets.add(target.casefold())
            if Path(src).suffix.lower() == '.pdf' and not blob.startswith(b'%PDF'):
                raise Invalid('示例 PDF 文件头不正确：' + src)
            if Path(src).suffix.lower() == '.pptx' and not blob.startswith(b'PK'):
                raise Invalid('示例 PPTX 文件头不正确：' + src)
            spec['files'].append({'source': src, 'target': base + target})
        for item in _list(data, 'library', 1):
            if module != '文献' or set(item) - {'source', 'title', 'guide', 'authors', 'year', 'url'}:
                raise Invalid('library 只用于文献 PDF 示例')
            src, blob = read_source(item.get('source'), {'.pdf'})
            if not blob.startswith(b'%PDF'):
                raise Invalid('示例 PDF 文件头不正确：' + src)
            title = _text(item.get('title'), 'title', 200)
            guide, guide_raw = read_source(item.get('guide'), {'.md'}, MAX_GUIDE)
            try:
                guide_raw.decode('utf-8-sig')
            except UnicodeError as exc:
                raise Invalid('示例讲解应为 UTF-8 文本') from exc
            authors = _text(item.get('authors', 'MiracleHarness 作者'), 'authors', 500)
            year = _text(item.get('year', '2026'), 'year', 4)
            if not re.fullmatch(r'\d{4}', year):
                raise Invalid('示例年份应为四位数字')
            url = _text(item.get('url', ''), 'url', 2000, required=False)
            if url and (urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).hostname):
                raise Invalid('示例链接须为 http 或 https')
            # library.add chooses PDF metadata first; predict its actual folder
            # for pre-creation Windows path checks rather than assuming title.
            pdf_title, _ = library.pdf_meta(root / src)
            actual_title = pdf_title if len(pdf_title) >= 8 and not pdf_title.lower().startswith(('microsoft word', 'untitled')) else title
            spec['library'].append({'source': src, 'guide': guide, 'title': title,
                                    'folder_title': library.short(actual_title),
                                    'authors': authors, 'year': year, 'url': url})
        seen_links = set()
        for item in _list(data, 'downloads', 20):
            if module != '文献' or set(item) - {'title', 'url', 'doi', 'authors', 'year', 'venue', 'why', 'note'}:
                raise Invalid('downloads 只用于文献的下载条目')
            row = {key: _text(item.get(key, ''), key, 2000 if key == 'url' else 1000,
                              required=key in {'title', 'url', 'authors', 'year', 'venue'})
                   for key in ('title', 'url', 'doi', 'authors', 'year', 'venue', 'why', 'note')}
            parsed = urlsplit(row['url'])
            if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
                raise Invalid('示例下载链接须为普通 http/https 地址')
            row['doi'] = downloads.normal_doi(row['doi'])
            # The existing add() resolves metadata only when no direct URL or
            # missing author/year/venue. Requiring these avoids background I/O.
            if not downloads.direct_of(row):
                raise Invalid('下载示例须提供可识别的官方 arXiv 或 PDF 直链，避免初始化联网补信息')
            key = row['doi'] or row['url']
            if key in seen_links:
                raise Invalid('下载示例重复：' + key)
            seen_links.add(key)
            spec['downloads'].append(row)
        modules.append(spec)
    return {'version': 1, 'modules': modules, 'manifests': manifests,
            'sources': fingerprints, 'copied_paths': sorted(set(manifests) | set(fingerprints))}


def planned_paths(plan: dict, *, first_library_number: int = 1) -> list[str]:
    """Additional ordinary files for new_project Windows preflight, not copies."""
    paths = []
    for spec in plan['modules']:
        paths.extend(x['target'] for x in spec['files'])
        for index, entry in enumerate(spec['library'], first_library_number):
            title = f"L{index} {entry['folder_title']}"
            paths += ['资料/文献/原文/' + title + '.pdf',
                      '资料/文献/解读/' + title + '/信息.json',
                      '资料/文献/解读/' + title + '/文本/讲解.md']
        if spec['downloads']:
            paths.append('资料/文献/下载清单.md')
    if plan['modules']:
        paths.append('索引/state.db')
    return sorted(set(paths))


def _check_paths(root: Path, paths: list[str], *, windows: bool | None = None) -> None:
    windows = os.name == 'nt' if windows is None else windows
    for rel in paths:
        path = _ordinary(root, rel, missing=True)
        if windows:
            for candidate, limit in [(path, 260)] + [(x, 248) for x in path.parents if x == root or root in x.parents]:
                length = len(str(candidate).encode('utf-16-le')) // 2
                if length >= limit:
                    raise Invalid('入门示例的 Windows 路径太长：' + str(candidate))


def _library_paths(root: Path) -> None:
    """library.add traverses these folders; reject links before it can follow one."""
    for rel in ('资料/文献/原文', '资料/文献/解读'):
        base = root / rel
        try:
            content_modules._ordinary(Project(root), base, missing=True)
        except (ValueError, OSError) as exc:
            raise Invalid(str(exc)) from exc
        if not base.exists():
            continue
        if not base.is_dir():
            raise Invalid('文献目录不是普通文件夹：' + rel)
        # Original PDFs and interpretation metadata are exactly what pair()
        # reads. Reject any reparse point, including nested note/guide paths.
        for folder, dirs, names in os.walk(base, followlinks=False):
            for name in dirs + names:
                candidate = Path(folder) / name
                if content_modules._linked(candidate.lstat()):
                    raise Invalid('文献路径不能经过链接：' + str(candidate.relative_to(root)))


def _copy_missing(root: Path, src: str, dst: str, report: dict, expected: str) -> bool:
    source, target = _ordinary(root, src), _ordinary(root, dst, missing=True)
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise Invalid('示例来源在初始化时改变：' + src)
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            report['skipped'].append(dst)
        else:
            report['conflicts'].append({'path': dst, 'source': src, 'reason': '已有不同内容，保留双方，未覆盖'})
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    _ordinary(root, dst, missing=True)
    try:
        with target.open('xb') as out:
            out.write(content)
    except FileExistsError:
        report['conflicts'].append({'path': dst, 'source': src, 'reason': '目标刚被创建，未覆盖'})
        return False
    report['created'].append(dst)
    return True


def _existing_library(project: Project, fingerprint: str) -> tuple[dict | None, list[dict]]:
    """Simulate pairing read-only: pair() itself may repair older metadata."""
    free = {f.name: f for f in library._pdfs(project, '文献')}
    existing, conflicts = None, []
    for folder in library._folders(project, '文献'):
        info = library._info(folder)
        original = str(info.get('原文', '')).split('/')[-1]
        pdf = free.get(original)
        number = library.num(folder.name)
        if pdf is None and number is not None:
            pdf = next((f for f in free.values() if library.num(f.name) == number), None)
        if pdf is None and info.get('指纹'):
            pdf = next((f for f in free.values() if library.sha(f) == info['指纹']), None)
        if pdf is None:
            continue
        free.pop(pdf.name)
        if original != pdf.name:
            conflicts.append({'path': folder.relative_to(project.root).as_posix() + '/信息.json',
                              'reason': '已有原文关联需要修复；内置初始化未改写这条记录'})
        if info.get('指纹') == fingerprint:
            if library.sha(pdf) != fingerprint:
                conflicts.append({'path': pdf.relative_to(project.root).as_posix(),
                                  'reason': '原文与已记指纹不符；未覆盖或重复导入'})
            else:
                existing = {'code': info.get('编号') or 'L' + str(number), 'pdf': '原文/' + pdf.name}
    return existing, conflicts


def initialize(conn, project: Project, plan: dict, *, by: str = '程序（内置示例）') -> dict:
    """Explicit initializer; caller owns project creation/authorization and log.

Only a newly created library entry receives guide/metadata. Any existing entry
with the same PDF fingerprint keeps its current fields and files unchanged.
"""
    with _LOCK:
        root = content_modules._root(project)
        _check_paths(root, ['索引/state.db'])
        databases = conn.execute('PRAGMA database_list').fetchall()
        db = next((row[2] for row in databases if row[1] == 'main'), '')
        if not db or os.path.normcase(str(Path(db).resolve())) != os.path.normcase(str((root / '索引/state.db').resolve())):
            raise Invalid('示例初始化连接的数据库不属于当前项目')
        fresh = validate(root, plan['copied_paths'])
        if fresh['manifests'] != plan['manifests'] or fresh['sources'] != plan['sources']:
            raise Invalid('示例来源在预检后改变，请重新预检；未初始化')
        has_library = any(x['library'] for x in fresh['modules'])
        next_number = 1
        if has_library:
            _library_paths(root)
            o, r = library.dirs(project, '文献')
            used = [library.num(x.name) or 0 for d in (o, r) if d.is_dir() for x in d.iterdir()]
            import store
            next_number = max(used + [int(store._meta(conn, 'library_seq:文献') or 0)]) + 1
        _check_paths(root, planned_paths(fresh, first_library_number=next_number))
        report = {'created': [], 'skipped': [], 'conflicts': [], 'library': [], 'downloads': []}
        for spec in fresh['modules']:
            for item in spec['files']:
                _copy_missing(root, item['source'], item['target'], report, fresh['sources'][item['source']])
            for item in spec['library']:
                existing, pairing_conflicts = _existing_library(project, fresh['sources'][item['source']])
                report['conflicts'].extend(pairing_conflicts)
                if existing:
                    report['skipped'].append('资料/文献/' + existing['pdf'])
                    report['library'].append({**existing, 'created': False})
                    continue
                if pairing_conflicts:
                    continue
                # Unique creation actor distinguishes a just-created entry from
                # a concurrent importer returning an existing SHA match.
                actor = by + ' ' + uuid.uuid4().hex[:12]
                if library.sha(root / item['source']) != fresh['sources'][item['source']]:
                    raise Invalid('示例原文在初始化时改变：' + item['source'])
                entry = library.add(conn, project, '文献', root / item['source'], name=item['title'] + '.pdf', by=actor)
                created = entry['info'].get('谁加的') == actor
                if created:
                    folder = root / '资料/文献' / entry['folder']
                    info = dict(entry['info'])
                    info.update({'标题': item['title'], '作者': item['authors'], '年份': item['year'],
                                 '期刊': '不适用（项目介绍示例）', 'DOI': '不适用', '链接': item['url'],
                                 '标签': ['内置示例'], '分组': ['平台入门'], '补信息': by})
                    library._write_info(folder, info)
                    report['created'].append('资料/文献/' + entry['pdf'])
                    _copy_missing(root, item['guide'], '资料/文献/' + entry['folder'] + '/文本/讲解.md', report,
                                  fresh['sources'][item['guide']])
                else:
                    report['skipped'].append('资料/文献/' + entry['pdf'])
                report['library'].append({'code': entry['code'], 'pdf': entry['pdf'], 'created': created})
            for row in spec['downloads']:
                old = downloads.list_all(project, spec['module'])
                before = {x['code'] for x in old}
                item = downloads.add(conn, project, spec['module'], **row, by=by)
                report['downloads'].append({'code': item['code'], 'title': item['title'],
                                            'created': item['code'] not in before, 'state': item['state']})
        return report
