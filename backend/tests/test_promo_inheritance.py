"""真实宣传片内置闭包和两代复制；不执行支持脚本或读取用户视频。"""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import pytest

import content_modules as cm
import new_project
from project import CODE_DIR, Project

MODULE = '资料/宣传片'
BUNDLE = MODULE + '/方法'                    # 10-07 统一内置：资料/宣传片/内置/方法 并进 资料/宣传片/方法


def data(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_bundle(root):
    base = root / BUNDLE
    manifest = data(base / '目录.json')
    assert len(manifest['items']) == 5 and manifest['runtime_enabled'] is False
    assert len(manifest['files']) == 158
    for item in manifest['files']:
        assert sha(base / item['path']) == item['sha256'], item['path']
    source_lock = data(base / 'sources.lock.json')
    assert len(source_lock['files']) == 138
    for source in source_lock['files']:
        assert sha(base / source['local_path']) == source['sha256'], source['local_path']
    # Method entrypoints and adapted source notes must resolve inside the copied
    # module. Raw upstream references may mention intentionally unbundled assets.
    docs = [root / MODULE / ('方法/' + n) for n in
            ('开始这里.md', '开始这里.en.md', '阶段路线.md', '阶段路线.en.md')]
    docs += [base / n for n in ('README.md', 'README.en.md')]
    for item in manifest['items']:
        docs += [base / item[key] for key in ('zh', 'en', 'source')]
        assert (base / item['license']).is_file()
    for doc in docs:
        for link in re.findall(r'\]\(<?([^\s)>]+)>?\)', doc.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):
                continue
            target = (doc.parent / link.split('#')[0]).resolve()
            assert target.is_relative_to((root / MODULE).resolve()), (doc, link)
            assert target.is_file(), (doc, link)
    # Representative Python support files that explicit inner-file marking would
    # reject are ordinary members of this explicitly selected built-in folder.
    assert list(base.glob('sources/*/*/scripts/_common/__init__.py'))
    assert list(base.glob('sources/*/*/src/video_editing_skill/__main__.py'))


def _now(rel):
    """迁移对照是历史记录，写的是当时的路径；10-07 统一内置又搬过一次，照 自动化/清理/内置搬家.json 一路找到现在的位置。"""
    import builtin
    rows = data(CODE_DIR / builtin.LAYOUT_RECORD)
    moves = {m['from']: m['to'] for r in rows for m in r['moves']}
    seen = set()
    while rel in moves and rel not in seen:
        seen.add(rel)
        rel = moves[rel]
    return rel


def test_promo_migration_retains_all_nine_original_bytes_and_leaves_workspaces_empty():
    migration = data(CODE_DIR / MODULE / '迁移对照.json')          # 10-07 统一内置：从 内置/ 搬到模块根，内容一字不改
    assert len(migration['files']) == 9 and migration['checkpoint'] == 'C178'
    for item in migration['files']:
        assert sha(CODE_DIR / _now(MODULE + '/内置/' + item['original'])) == item['original_sha256']
        assert (CODE_DIR / _now(item['new_path'])).is_file()      # 现在那份：统一内置时改过里面的路径，指纹跟当时不一样了
    assert not (CODE_DIR / '资料/剪辑').exists()
    assert_bundle(CODE_DIR)


def test_actual_promo_module_is_selected_and_inherited_twice_without_new_work(monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    with tempfile.TemporaryDirectory(prefix='pv-', dir=os.environ.get('TEMP')) as working:
        first, second, omitted = (Path(working) / n for n in ('a', 'b', 'c'))
        # Exact production copy, retaining the source profile's existing core,
        # mandatory modules and method selection; no patched copying helpers.
        new_project.make(first, CODE_DIR, business_modules=['宣传片'])
        marked = set(data(CODE_DIR / '内置标记.json')['paths'])      # 作者用小锁标过的成品才跟着走（10-07 作者标了一个成果视频）
        for folder in ('素材', '成果'):
            target = first / MODULE / folder
            assert target.is_dir() and all(f'{MODULE}/{folder}/{x.name}' in marked for x in target.iterdir())
            (target / '一代私人工作.md').write_text('SYNTHETIC_PRIVATE_DO_NOT_INHERIT', encoding='utf-8')
        new_project.make(second, first)
        new_project.make(omitted, first, business_modules=[])
        for target in (first, second):
            assert_bundle(target)
            cfg = data(target / '模板配置.json')
            assert cfg['business_modules'] == ['宣传片']
            assert cfg['module_labels']['宣传片'] == 'Promo Video'
            assert not (target / '资料/剪辑').exists()
            view = cm.workspace(Project(target), '宣传片')
            assert not view['problems'] and [s['folder'] for s in view['sections']] == ['素材', '成果']
            if target == second:
                assert all(not s['files'] for s in view['sections'])
            copied = {r['path'] for r in data(target / '新项目复制清单.json')['files']}
            assert not any('一代私人工作' in path for path in copied)
        assert not (omitted / MODULE).exists()
        assert not any(name in new_project.available_business_modules(omitted) for name in ('宣传片', '剪辑'))


def test_promo_profile_retains_plugin_identity_and_business_option():
    profiles = data(CODE_DIR / 'backend/template_profiles.json')['profiles']
    for name, cfg in profiles.items():
        assert not any(r.startswith('资料/剪辑') for r in cfg['template_roots'])   # 插件本来就固定带（插件/ 是核心）
        assert '剪辑' not in cfg['modules']
        assert cfg['module_labels']['宣传片'] == 'Promo Video'
    assert '宣传片' in profiles['business']['modules']
    assert {'资料/宣传片/方法', '资料/宣传片/工作台'} <= set(profiles['business']['template_roots'])
    options = new_project.preview(CODE_DIR, business_modules=['宣传片'])['business_options']
    assert next(row for row in options if row['name'] == '宣传片')['selected'] is True
    assert all(row['name'] != '剪辑' for row in options)
