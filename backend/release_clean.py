"""公开发行副本的清理。只写新建的暂存目录和发行目录，不修改使用中的项目。"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import posixpath
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import unquote

import builtin
import new_project
from project import check_module_labels

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif', '.ico', '.avif'}
EXAMPLE_ROOTS = ('资料/PPT/工作台/作品', '资料/文献/工作台/示例')
IMAGE_FIELDS = {'image', 'logo', 'image_kind', 'image_type', 'image_source', 'logo_source',
                'image_sha256', 'image_bytes', 'image_url', 'downloaded_url', 'content_type'}
MD_IMAGE = re.compile(r'!\[([^\]\n]*)\]\((<[^>\n]+>|[^)\n]+)\)')
MD_LINK = re.compile(r'(?<!!)\[([^\]\n]*)\]\((<[^>\n]+>|[^)\n]+)\)')
SKILL_LINK = re.compile(r'(?<!!)\[([^\n]+?)\]\((<[^>\n]+>|[^)\n]+)\)')
VIDEO_DEMO_NOTE = '宣传片目录中的视频是历史展示案例，画面中的旧网址仅作展示；保留来源与许可记录，本次没有对音轨作法律鉴定。'


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _remove(root: Path, rel: str) -> list[str]:
    """调用者只传自己创建的目录；删除前仍检查最终绝对路径和所有联接。"""
    root = root.resolve()
    path = root / rel
    if not path.exists():
        return []
    if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root) or path.resolve() == root:
        raise ValueError('发行清理路径离开副本或经过链接：' + rel)
    files = [path] if path.is_file() else list(path.rglob('*'))
    if any(f.is_symlink() or f.is_junction() or not f.resolve().is_relative_to(root) for f in files):
        raise ValueError('发行清理不能经过链接：' + rel)
    removed = [f.relative_to(root).as_posix() for f in files if f.is_file()]
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return removed


@contextmanager
def staged_source(src: Path, configs: list[dict], demo_overrides: dict[str, Path] | None = None,
                  public_payload_roots: tuple[str, ...] = (), public_module_labels: dict | None = None,
                  profile_names: tuple[str, ...] | None = None):
    """只读复制公共核心和两份模板声明，不继承任何作者人工资料标记。"""
    paths = set()
    for rel in builtin.mandatory_paths(src):
        paths.update(builtin.files(src, src / rel, core=True))
    roots = set()
    for cfg in configs:
        roots.update(cfg['template_roots'])
        roots.update(cfg['module_skills'])
        for rel in cfg['template_roots'] + cfg['module_skills']:
            paths.update(builtin.files(src, builtin.path(src, rel)))
        declared, _ = new_project._builtin_skill_files(src, cfg.get('builtin_skill_ids', []))
        paths.update(declared)
    if (not isinstance(public_payload_roots, (tuple, list)) or len(public_payload_roots) > 100
            or any(not isinstance(rel, str) for rel in public_payload_roots)):
        raise ValueError('公开示例载荷应是最多100个资料目录/文件相对路径')
    payload = list(dict.fromkeys(public_payload_roots))
    modules = []
    for rel in payload:
        parts = rel.split('/')
        if len(parts) < 3 or parts[0] != '资料':
            raise ValueError('公开示例载荷只能是资料/模块/目录或文件：' + rel)
        original = builtin.path(src, rel)
        paths.update(builtin.files(src, original))
        roots.add(rel)
        if parts[1] not in modules:
            modules.append(parts[1])
    labels = check_module_labels(public_module_labels or {})
    if any(module not in modules for module in labels):
        raise ValueError('公开示例标签须属于本次明确选择的载荷模块')
    if (src / 'AGENTS.md').is_file():
        paths.add('AGENTS.md')
    # 展示案例保留；替换公开副本需显式提供，避免把旧联系方式顺带公开。
    demo_overrides = demo_overrides or {}
    examples = []
    for module in ('PPT', '文献'):
        manifest = src / f'资料/{module}/工作台/入门示例.json'
        if manifest.is_file() and manifest.relative_to(src).as_posix() in paths:
            data = json.loads(manifest.read_text(encoding='utf-8-sig'))
            examples.extend(f'资料/{module}/' + x['source'] for key in ('files', 'library') for x in data.get(key, []))
    missing = sorted(set(examples) - set(demo_overrides))
    if missing:
        raise ValueError('发行展示案例须提供经过公开信息检查的副本：' + '、'.join(missing))
    for rel, replacement in demo_overrides.items():
        if rel not in paths or not any(rel.startswith(r + '/') for r in EXAMPLE_ROOTS):
            raise ValueError('展示案例替换须指向已选工作台案例：' + rel)
        if not replacement.is_file() or replacement.is_symlink() or replacement.is_junction():
            raise ValueError('展示案例替换需要普通文件：' + str(replacement))
    excluded = sorted(p for p in paths if p.startswith('backend/tests/evidence/'))
    paths.difference_update(excluded)
    with tempfile.TemporaryDirectory(prefix='miracle-release-') as temp:
        stage = Path(temp) / 'source'
        stage.mkdir()
        stage = stage.resolve()  # Windows TEMP 可能返回 8.3 用户名，后续路径必须用同一正本。
        for rel in sorted(paths):
            original = src / rel
            builtin.files(src, original, core=True)
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(demo_overrides.get(rel, original), target)
        for rel in roots:
            if (src / rel).is_file():
                continue
            folder = stage / rel
            folder.mkdir(parents=True, exist_ok=True)
            if not any(folder.iterdir()):
                (folder / '.gitkeep').write_bytes(b'')
        _write_json(stage / builtin.MARKS_FILE, {'version': 1, 'paths': sorted(roots)})
        profile_file = stage / 'backend/template_profiles.json'
        profiles = json.loads(profile_file.read_text(encoding='utf-8-sig'))
        for name, cfg in profiles['profiles'].items():
            if profile_names is not None and name not in profile_names:
                continue
            cfg['template_roots'] = list(dict.fromkeys(cfg['template_roots'] + payload))
            cfg['modules'] = list(dict.fromkeys(cfg['modules'] + modules))
            cfg['module_labels'] = {**cfg.get('module_labels', {}), **labels}
        _write_json(profile_file, profiles)
        marks = builtin.read_marks(src)
        yield stage, {'excluded_source_evidence': excluded,
                      'public_demo_replacements': sorted(demo_overrides),
                      'public_payload_roots': payload,
                      'public_module_labels': labels,
                      'excluded_source_marks': [p for p in marks['paths'] if p not in roots],
                      'stage_files': len(paths)}


def _local_path(document: str, link: str) -> str | None:
    link = link.strip().strip('<>')
    if re.match(r'^(?:[a-z][a-z0-9+.-]*:|#|/)', link, re.I):
        return None
    return posixpath.normpath(posixpath.join(posixpath.dirname(document), unquote(link.split('#')[0])))


def _prune_json(value: object, removed: set[str], counts: dict, *, root: Path, base: str) -> object:
    if isinstance(value, list):
        rows = []
        for row in value:
            refs = [row.get(k) for k in ('path', 'local_path', 'file')] if isinstance(row, dict) else []
            refs = [posixpath.normpath(unquote(ref) if ref.startswith(('工具库/', '品牌/', '资料/'))
                                      else posixpath.join(base, unquote(ref)))
                    for ref in refs if isinstance(ref, str) and Path(ref).suffix.lower() in IMAGE_SUFFIXES]
            if any(ref in removed or not (root / ref).is_file() for ref in refs):
                counts['asset_records_removed'] += 1
                continue
            rows.append(_prune_json(row, removed, counts, root=root, base=base))
        return rows
    if not isinstance(value, dict):
        return value
    result = {}
    stripped = any(isinstance(value.get(k), str) and value[k] in removed for k in ('image', 'logo'))
    for key, item in value.items():
        if stripped and key in IMAGE_FIELDS:
            continue
        if isinstance(item, str) and item in removed:
            continue
        result[key] = _prune_json(item, removed, counts, root=root, base=base)
    if stripped:
        counts['image_references_removed'] += 1
        for field in ('bytes', 'sha256', 'observation', 'method', 'reason'):
            result.pop(field, None)
        result['status'] = 'reference-link'
        result['image_unbundled_reason'] = 'Third-party screenshot or logo excluded from this release.'
    return result


def _project_lock(root: Path, path: Path, counts: dict) -> None:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    retained, excluded = 0, 0

    def prune(value):
        nonlocal retained, excluded
        if isinstance(value, list):
            out = []
            for row in value:
                if isinstance(row, dict) and isinstance(row.get('local_path'), str):
                    rel = row['local_path']
                    target = root / rel
                    if not target.is_file() or not target.resolve().is_relative_to(root):
                        excluded += 1
                        continue
                    actual = hashlib.sha256(target.read_bytes()).hexdigest()
                    if row.get('sha256', actual).lower() != actual:
                        raise ValueError('发行来源指纹不符：' + rel)
                    retained += 1
                out.append(prune(row))
            return out
        if isinstance(value, dict):
            return {k: prune(v) for k, v in value.items()}
        return value

    result = prune(data)
    excluded += data.get('release_projection', {}).get('excluded_records', 0)
    result['release_projection'] = {'rule': 'Only existing source snapshots with verified hashes',
                                    'retained_records': retained, 'excluded_records': excluded,
                                    'excluded_reason': 'Not selected for this package; absence is not a missing-license finding.'}
    # 原总账指纹记录的是原总账范围，不能假称仍是投影后的指纹。
    if 'audit_sha256' in result:
        result['upstream_audit_sha256'] = result.pop('audit_sha256')
    _write_json(path, result)
    counts['source_locks'].append({'path': path.relative_to(root).as_posix(),
                                  'retained_records': retained, 'excluded_records': excluded})


def sanitize(root: Path, *, public_payload_roots: tuple[str, ...] = ()) -> dict:
    """去除机器状态、截图与第三方小标识，保留官网文本入口、原许可和原创素材。"""
    root = root.resolve()
    counts = {'removed_files': [], 'asset_records_removed': 0, 'image_references_removed': 0,
              'markdown_image_references_removed': 0, 'markdown_files_updated': 0,
              'optional_skill_links_removed': 0, 'excluded_invalid_profiles': [], 'source_locks': []}
    if not public_payload_roots and (root / '新项目复制清单.json').is_file():
        copied = json.loads((root / '新项目复制清单.json').read_text(encoding='utf-8'))
        public_payload_roots = tuple(copied.get('release_cleanup', {}).get('public_payload_roots', []))
    public_method_roots = [rel for rel in public_payload_roots
                           if rel in {'资料/写小说/方法', '资料/写论文/方法'}]
    removed = set()
    for rel in ('存档', '回收站', '笔记', '治理/计划', '.pytest_cache', '__pycache__'):
        removed.update(_remove(root, rel))
    # make 只连接自己新建的库；保留公开案例/官方下载链接，绝不复制源项目库。
    index = root / '索引'
    if index.is_dir():
        for entry in list(index.iterdir()):
            if entry.name != 'state.db':
                removed.update(_remove(root, entry.relative_to(root).as_posix()))
    counts['fresh_public_demo_db'] = (index / 'state.db').is_file()
    if counts['fresh_public_demo_db']:
        counts['database_description'] = 'New database initialized only from public demonstration files and declared official download-link examples; source project database is never copied.'
    auto = root / '自动化'
    if auto.is_dir():
        for folder in list(auto.iterdir()):
            if folder.name not in {'协议.md', '工作流', '交付策略.json'}:
                removed.update(_remove(root, folder.relative_to(root).as_posix()))
    for f in list(root.rglob('*')):
        if f.is_file() and (f.suffix.lower() in {'.pyc', '.pyo'} or f.name in {'本机设置.json', '监管快照.json'}):
            removed.update(_remove(root, f.relative_to(root).as_posix()))
    guide_root = root / '工具库/安装指南'
    profile_file = root / 'backend/template_profiles.json'
    if profile_file.is_file():
        profiles = json.loads(profile_file.read_text(encoding='utf-8-sig'))
        if 'business' in profiles.get('profiles', {}):
            try:
                new_project.profile_config(root, 'business')
            except (ValueError, OSError):
                del profiles['profiles']['business']
                counts['excluded_invalid_profiles'].append('business')
                _write_json(profile_file, profiles)
    for name in ('应用截图', '应用图片'):
        directory = guide_root / name
        if directory.is_dir():
            for f in list(directory.rglob('*')):
                if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES and not f.name.startswith('miracleharness-'):
                    removed.update(_remove(root, f.relative_to(root).as_posix()))
    catalog = guide_root / 'catalog.json'
    if catalog.is_file():
        data = json.loads(catalog.read_text(encoding='utf-8-sig'))
        for row in data.get('items', []):
            for kind in ('image', 'logo'):
                if row.get(kind) in removed:
                    for key in list(row):
                        if key == kind or key.startswith(kind + '_'):
                            row.pop(key, None)
                    counts['image_references_removed'] += 1
            if not row.get('image'):
                if isinstance(row.get('notice'), str):
                    row['notice'] = row['notice'].replace('图片是官方文档示例。', '通过官方文字链接查看文档与安装入口。')
                if isinstance(row.get('notice_en'), str):
                    row['notice_en'] = row['notice_en'].replace('image is an official documentation example.',
                                                               'official text links provide documentation and setup references.')
        data['release_images'] = 'Original project artwork and official text links; third-party screenshots and logos are not distributed.'
        _write_json(catalog, data)
    for f in sorted(guide_root.rglob('*.json')) if guide_root.is_dir() else []:
        if f == catalog:
            continue
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        projected = _prune_json(data, removed, counts, root=root,
                               base=f.parent.relative_to(root).as_posix())
        if projected != data:
            projected['release_projection'] = 'Only bundled original assets are listed; official sources remain as text links.'
            _write_json(f, projected)
    for f in sorted(root.rglob('*.md')):
        rel = f.relative_to(root).as_posix()
        # 来源原件和上游技能全文按原许可/指纹保留，不能改动快照正文。
        public_method = any(rel.startswith(prefix + '/') for prefix in public_method_roots)
        if not (rel.startswith('工具库/安装指南/') or rel.startswith('资料/PPT/工作台/')
                or rel.startswith('资料/文献/工作台/') or public_method):
            continue
        text = f.read_text(encoding='utf-8-sig')

        def replace_image(match):
            if _local_path(rel, match[2]) not in removed:
                return match[0]
            counts['markdown_image_references_removed'] += 1
            fallback = {'开源项目.md': 'miracleharness-repo-links.png',
                        '网页链接.md': 'miracleharness-web-links.png'}.get(f.name)
            if fallback and (guide_root / '应用图片' / fallback).is_file():
                return '![MiracleHarness 原创示意](../应用图片/' + fallback + ')'
            return '-'

        changed = MD_IMAGE.sub(replace_image, text)
        changed = MD_LINK.sub(lambda m: m[1] if _local_path(rel, m[2]) in removed else m[0], changed)
        if public_method:
            def optional_skill(match):
                target = _local_path(rel, match[2])
                if (not target or not re.fullmatch(r'SKILL(?:\.[\w-]+)?\.md', Path(target).name, re.I)
                        or (root / target).is_file()):
                    return match[0]
                counts['optional_skill_links_removed'] += 1
                hint = (' (optional method; not bundled in this release)' if f.name.endswith('.en.md')
                        else '（可选方法，本发行包未内置）')
                return match[1] + hint

            changed = SKILL_LINK.sub(optional_skill, changed)
            if rel == '资料/写小说/方法/开始这里.md':
                changed = changed.replace('让它读路线技能及阶段路线，先确认实际阶段，再做一件有验收的任务。',
                                          '先让它读阶段路线并确认实际阶段；如选择额外方法，再准备对应技能，然后做一件有验收的任务。')
            elif rel == '资料/写小说/方法/开始这里.en.md':
                changed = changed.replace('Have it read the route skill/stage route, identify the actual stage, and complete one task with acceptance.',
                                          'Have it read the stage route and identify the actual stage; prepare the corresponding skill if choosing an extra method, then complete one task with acceptance.')
        # 表格仍保持列数，未随包带图的类型也不能继续声称是官网截图。
        changed = re.sub(r'(\|\s*-\s*\|)\s*官网截图\s*\|', r'\1 官网入口 |', changed)
        lines = []
        for line in changed.splitlines():
            if line.startswith('|') and '![MiracleHarness 原创示意]' in line:
                cells = line.split('|')
                if len(cells) == 9:
                    cells[6] = ' 原创示意图 '
                    cells[7] = ' MiracleHarness 原创；' + re.sub(r'实际截图页|来源页面|官网截图', '官网入口', cells[7]).strip() + ' '
                    line = '|'.join(cells)
            lines.append(line)
        changed = '\n'.join(lines) + ('\n' if changed.endswith('\n') else '')
        changed = changed.replace('## 官方页面截图', '## 官方页面入口')
        changed = re.sub(r'此图帮助识别官网入口，', '请从上述官网链接进入，', changed)
        changed = re.sub(r'图片明确区分实际官网截图与原创示意；', '发行版保留原创示意和官网文字入口；', changed)
        if rel == '资料/PPT/工作台/README.md' and not (root / '资料/PPT/作品/MiracleHarness项目介绍').exists():
            changed = changed.replace('原完整介绍包和素材仍在 `作品/MiracleHarness项目介绍/`，旧链接继续可用。',
                                      '发行展示案例保存在上述工作台/作品和导出目录；作者工作目录不随包复制。')
        changed = re.sub(r'`(?:[A-Za-z]:[\\/]|/Users/)[^`\n]*`',
                         lambda m: '`' + m[0].strip('`').replace('\\', '/').rsplit('/', 1)[-1] + '`', changed)
        for path in removed:
            changed = changed.replace('`' + path + '`', '（发行版不包含此资源）')
        if changed != text:
            f.write_text(changed, encoding='utf-8')
            counts['markdown_files_updated'] += 1
    # 图源文档保留历史来源信息，同时明确本包没有分发旧资产。
    for rel in ('工具库/安装指南/应用截图/来源.md', '工具库/安装指南/应用截图/链接来源.md',
                '工具库/安装指南/应用图片/来源.md'):
        path = root / rel
        if path.is_file():
            note = '> 发行说明：第三方截图和原样小标识未随本发行包分发。以下文字仅保留官网来源与权利记录；使用工具请打开官网链接。\n\n'
            text = path.read_text(encoding='utf-8')
            if not text.startswith(note):
                path.write_text(note + text, encoding='utf-8')
    readme = root / 'README.md'
    if '资料/宣传片/成果' in public_payload_roots and readme.is_file():
        text = readme.read_text(encoding='utf-8')
        if VIDEO_DEMO_NOTE not in text:
            readme.write_text(text.rstrip() + '\n\n' + VIDEO_DEMO_NOTE + '\n', encoding='utf-8')
            counts['markdown_files_updated'] += 1
    for f in sorted(root.rglob('sources.lock.json')):
        _project_lock(root, f, counts)
    marks_file = root / builtin.MARKS_FILE
    if marks_file.is_file():
        data = json.loads(marks_file.read_text(encoding='utf-8-sig'))
        actual = [f.relative_to(root).as_posix() for f in root.rglob('*') if f.is_file()]
        data['paths'] = builtin.copied_marks(data['paths'], actual)
        _write_json(marks_file, data)
    counts['removed_files'] = sorted(removed)
    counts['removed_file_count'] = len(removed)
    return counts


def refresh_copy_manifest(root: Path, cleanup: dict) -> None:
    path = root / '新项目复制清单.json'
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    files = [{'path': f.relative_to(root).as_posix(), 'bytes': f.stat().st_size}
             for f in sorted(root.rglob('*')) if f.is_file() and f != path and f.name != '发行清单.json']
    data.update(files=files, file_count=len(files), bytes=sum(f['bytes'] for f in files),
                release_cleanup=cleanup)
    # 展示案例与其全新索引保留，第一次打开即可展示；源项目库从未复制。
    if 'onboarding_examples' in data:
        data['onboarding_examples']['fresh_public_demo_db'] = cleanup['fresh_public_demo_db']
    if 'builtin_marks' in data:
        data['builtin_marks']['paths'] = json.loads((root / builtin.MARKS_FILE).read_text(encoding='utf-8'))['paths']
        data['builtin_marks'].pop('source_revision', None)
    _write_json(path, data)
