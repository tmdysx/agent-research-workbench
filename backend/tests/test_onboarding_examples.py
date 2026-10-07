"""Starter initialization uses synthetic TEMP projects only."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

import onboarding_examples as examples
import downloads
import library
import new_project
import store
from project import Project


def write(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else value.encode('utf-8'))
    return path


def manifest(root, module, value):
    return write(root, f'资料/{module}/{examples.MANIFEST}', json.dumps(value, ensure_ascii=False))


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '索引' not in p.relative_to(root).parts}


def selected(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '工作台' in p.parts)


def pdf(title='Starter project introduction'):
    stream = b'BT /F1 12 Tf 72 720 Td (Starter text) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
               b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', ('<< /Title (' + title + ') >>').encode()]
    out, offsets = bytearray(b'%PDF-1.4\n'), []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % index + obj + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 7\n0000000000 65535 f \n'
    out += b''.join(b'%010d 00000 n \n' % off for off in offsets)
    out += b'trailer\n<< /Size 7 /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n' % xref
    return bytes(out)


def paper(aid='1706.03762'):
    return {'title': 'Attention Is All You Need', 'url': 'https://arxiv.org/abs/' + aid,
            'doi': '10.48550/arXiv.' + aid, 'authors': 'Ashish Vaswani; Noam Shazeer 等',
            'year': '2017', 'venue': 'arXiv', 'why': '示例', 'note': '官方链接，尚未下载'}


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    root = tmp_path / 'source'
    root.mkdir()
    write(root, '资料/PPT/工作台/成果/demo.pdf', pdf())
    write(root, '资料/PPT/工作台/成果/demo.pptx', b'PK\x03\x04synthetic-pptx')
    manifest(root, 'PPT', {'version': 1, 'files': [
        {'source': '工作台/成果/demo.pdf', 'target': '导出/demo.pdf'},
        {'source': '工作台/成果/demo.pptx', 'target': '导出/demo.pptx'}]})
    write(root, '资料/文献/工作台/示例/demo.pdf', pdf())
    write(root, '资料/文献/工作台/示例/讲解.md', '# 示例\n\n## 第 1 页\n这是项目介绍。\n')
    manifest(root, '文献', {'version': 1, 'library': [
        {'source': '工作台/示例/demo.pdf', 'guide': '工作台/示例/讲解.md',
         'title': '项目介绍示例', 'authors': '作者', 'year': '2026'}],
        'downloads': [paper(), {**paper('2005.14165'), 'title': 'Language Models are Few-Shot Learners',
                              'authors': 'Tom B. Brown 等', 'year': '2020'},
                      {**paper('2210.03629'), 'title': 'ReAct: Synergizing Reasoning and Acting in Language Models',
                       'authors': 'Shunyu Yao 等', 'year': '2022'}]})
    return root


def test_validate_reads_only_and_projects_real_generated_paths(source):
    before = snapshot(source)
    plan = examples.validate(source, selected(source))
    assert len(plan['modules']) == 2
    paths = examples.planned_paths(plan)
    assert '资料/PPT/导出/demo.pdf' in paths
    assert '资料/文献/解读/L1 Starter project introduction/文本/讲解.md' in paths
    assert not (source / '索引').exists()
    assert snapshot(source) == before


def test_explicit_seed_is_repeatable_without_network_or_user_overwrite(source, monkeypatch):
    def no_thread(*args, **kwargs):
        raise AssertionError('initialization must not request metadata or downloads')
    monkeypatch.setattr(downloads.threading, 'Thread', no_thread)
    plan = examples.validate(source, selected(source))
    project = Project(source)
    conn = store.connect(source / '索引/state.db')
    try:
        report = examples.initialize(conn, project, plan)
        assert len(report['library']) == 1 and report['library'][0]['created']
        assert len(report['downloads']) == 3
        assert all(x['created'] and x['state'] == '还没下' for x in report['downloads'])
        entry = library.get(project, '文献', report['library'][0]['code'])
        folder = source / '资料/文献' / entry['folder']
        (folder / '文本/讲解.md').write_text('人改过的讲解', encoding='utf-8')
        (folder / '批注.json').write_text('{"by":"人"}', encoding='utf-8')
        info = json.loads((folder / '信息.json').read_text(encoding='utf-8'))
        info['阅读状态'] = '读完'
        (folder / '信息.json').write_text(json.dumps(info, ensure_ascii=False), encoding='utf-8')
        before = snapshot(source)
        again = examples.initialize(conn, project, plan)
        assert not again['created'] and not again['conflicts']
        assert not again['library'][0]['created']
        assert not any(x['created'] for x in again['downloads'])
        assert snapshot(source) == before
        assert len(list((source / '资料/文献/原文').glob('*.pdf'))) == 1
    finally:
        conn.close()


def test_existing_export_conflict_preserves_both(source):
    write(source, '资料/PPT/导出/demo.pdf', b'%PDF-user-work')
    plan = examples.validate(source, selected(source))
    conn = store.connect(source / '索引/state.db')
    try:
        report = examples.initialize(conn, Project(source), plan)
        assert report['conflicts'][0]['path'] == '资料/PPT/导出/demo.pdf'
        assert (source / '资料/PPT/导出/demo.pdf').read_bytes() == b'%PDF-user-work'
        assert (source / '资料/PPT/工作台/成果/demo.pdf').read_bytes() == pdf()
    finally:
        conn.close()


def test_existing_download_keeps_user_metadata_and_real_download_state(source):
    project = Project(source)
    conn = store.connect(source / '索引/state.db')
    try:
        row = downloads.add(conn, project, '文献', **{**paper(), 'title': '人的标题', 'note': '人的说明'}, by='人')
        original = '资料/文献/原文/人的下载.pdf'
        write(source, original, pdf('User downloaded original'))
        downloads._set(project, '文献', row['code'], at=original)
        original_list = downloads.path(project, '文献').read_text(encoding='utf-8')
        original_row = next(line for line in original_list.splitlines() if row['code'] in line)
        plan = examples.validate(source, selected(source))
        report = examples.initialize(conn, project, plan)
        same = next(x for x in report['downloads'] if x['code'] == row['code'])
        assert not same['created'] and same['state'] == '下好了'
        after = downloads.get(project, '文献', row['code'])
        assert after['title'] == '人的标题' and after['note'] == '人的说明'
        assert after['at'] == original and (source / original).read_bytes() == pdf('User downloaded original')
        assert original_row in downloads.path(project, '文献').read_text(encoding='utf-8').splitlines()
        assert len(downloads.list_all(project, '文献')) == 3
    finally:
        conn.close()


def test_unselected_ppt_manifest_is_not_read_or_seeded(source):
    write(source, '资料/PPT/' + examples.MANIFEST, 'invalid JSON must not be read')
    chosen = [x for x in selected(source) if x.startswith('资料/文献/')]
    plan = examples.validate(source, chosen)
    assert [x['module'] for x in plan['modules']] == ['文献']
    conn = store.connect(source / '索引/state.db')
    try:
        examples.initialize(conn, Project(source), plan)
        assert not (source / '资料/PPT/导出').exists()
    finally:
        conn.close()


def test_manifest_cannot_borrow_source_missing_from_copy_plan(source):
    chosen = [x for x in selected(source) if not x.endswith('成果/demo.pdf')]
    with pytest.raises(examples.Invalid, match='复制范围'):
        examples.validate(source, chosen)
    assert not (source / '索引').exists()


@pytest.mark.parametrize('target', ['../偷.pdf', '导出/../偷.pdf', '导出/CON.pdf', '导出/x.pdf ', '导出/a/b.pdf', '导出/demo.exe', '原文/demo.pdf'])
def test_invalid_windows_and_escaping_targets_fail_before_creation(source, target):
    manifest(source, 'PPT', {'version': 1, 'files': [{'source': '工作台/成果/demo.pdf', 'target': target}]})
    with pytest.raises(examples.Invalid):
        examples.validate(source, selected(source))
    assert not (source / '索引').exists()


def test_missing_metadata_or_non_direct_link_cannot_trigger_background_lookup(source):
    for change in [{'authors': ''}, {'year': ''}, {'venue': ''}, {'url': 'https://example.org/article'}]:
        manifest(source, '文献', {'version': 1, 'downloads': [{**paper(), **change}]})
        with pytest.raises(examples.Invalid):
            examples.validate(source, selected(source))


def test_changed_source_since_preflight_is_refused(source):
    plan = examples.validate(source, selected(source))
    write(source, '资料/PPT/工作台/成果/demo.pdf', pdf('Changed introduction'))
    conn = store.connect(source / '索引/state.db')
    try:
        with pytest.raises(examples.Invalid, match='预检后改变'):
            examples.initialize(conn, Project(source), plan)
        assert not (source / '资料/PPT/导出').exists()
        assert not (source / '资料/文献/原文').exists()
    finally:
        conn.close()


def test_wrong_project_database_refused(source, tmp_path):
    plan = examples.validate(source, selected(source))
    conn = store.connect(tmp_path / 'other/索引/state.db')
    try:
        with pytest.raises(examples.Invalid, match='数据库不属于'):
            examples.initialize(conn, Project(source), plan)
        assert not (source / '资料/PPT/导出').exists()
    finally:
        conn.close()


def test_two_generations_inherit_only_declared_examples(source, tmp_path):
    write(source, '资料/文献/原文/L88 私人.pdf', b'%PDF-private')
    write(source, '笔记/总览.md', 'PRIVATE NOTE')
    plan = examples.validate(source, selected(source))
    current = source
    for name in ['child', 'grandchild']:
        target = tmp_path / name
        for rel in plan['copied_paths']:
            write(target, rel, (current / rel).read_bytes())
        conn = store.connect(target / '索引/state.db')
        try:
            result = examples.initialize(conn, Project(target), plan)
            assert result['library'][0]['code'] == 'L1'
            assert len(downloads.list_all(Project(target), '文献')) == 3
            assert not (target / '资料/文献/原文/L88 私人.pdf').exists()
            assert not (target / '笔记/总览.md').exists()
        finally:
            conn.close()
        current = target


def test_windows_full_path_preflight_accounts_for_generated_paths(source):
    with pytest.raises(examples.Invalid, match='路径'):
        examples._check_paths(source, ['资料/文献/解读/' + '文' * 100 + '/文本/' + '字' * 100 + '.md'], windows=True)


def test_source_symlink_and_existing_destination_link_rejected(source, tmp_path):
    target = tmp_path / 'outside.pdf'
    target.write_bytes(pdf())
    link = source / '资料/PPT/工作台/成果/link.pdf'
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip('host does not permit symbolic-link creation')
    manifest(source, 'PPT', {'version': 1, 'files': [{'source': '工作台/成果/link.pdf', 'target': '导出/demo.pdf'}]})
    with pytest.raises(examples.Invalid, match='链接'):
        examples.validate(source, selected(source))


def test_duplicate_pdf_does_not_rewrite_user_metadata_or_invent_notes(source):
    project = Project(source)
    conn = store.connect(source / '索引/state.db')
    try:
        old = library.add(conn, project, '文献', source / '资料/文献/工作台/示例/demo.pdf', by='人')
        folder = source / '资料/文献' / old['folder']
        write(source, '资料/文献/' + old['folder'] + '/文本/笔记.md', '人的历史笔记')
        original_info = (folder / '信息.json').read_bytes()
        plan = examples.validate(source, selected(source))
        result = examples.initialize(conn, project, plan)
        assert not result['library'][0]['created']
        assert (folder / '信息.json').read_bytes() == original_info
        assert not (folder / '文本/讲解.md').exists()
        assert (folder / '文本/笔记.md').read_text(encoding='utf-8') == '人的历史笔记'
    finally:
        conn.close()


def test_destination_directory_junction_rejected_before_any_seed(source, tmp_path):
    if os.name != 'nt':
        pytest.skip('Windows junction test')
    outside = tmp_path / 'outside'
    outside.mkdir()
    destination = source / '资料/PPT/导出'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(destination), str(outside)],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        pytest.skip('host does not permit directory junctions')
    plan = examples.validate(source, selected(source))
    conn = store.connect(source / '索引/state.db')
    try:
        with pytest.raises(examples.Invalid, match='链接'):
            examples.initialize(conn, Project(source), plan)
        assert not list(outside.iterdir())
        assert not (source / '资料/文献/原文').exists()
    finally:
        conn.close()


def test_existing_mismatched_link_is_not_silently_repaired_by_repeat(source):
    project = Project(source)
    conn = store.connect(source / '索引/state.db')
    try:
        old = library.add(conn, project, '文献', source / '资料/文献/工作台/示例/demo.pdf', by='人')
        info_path = source / '资料/文献' / old['folder'] / '信息.json'
        info = json.loads(info_path.read_text(encoding='utf-8'))
        info['原文'] = '原文/用户旧名称.pdf'
        info_path.write_text(json.dumps(info, ensure_ascii=False), encoding='utf-8')
        before = info_path.read_bytes()
        plan = examples.validate(source, selected(source))
        report = examples.initialize(conn, project, plan)
        assert info_path.read_bytes() == before
        assert any(x['path'].endswith('/信息.json') for x in report['conflicts'])
    finally:
        conn.close()


def test_make_two_generations_seed_only_declared_examples_and_keep_copy_manifest(source, tmp_path, monkeypatch):
    def no_thread(*args, **kwargs):
        raise AssertionError('new-project examples must not start metadata or download work')
    monkeypatch.setattr(downloads.threading, 'Thread', no_thread)
    private = {'资料/文献/原文/L88 私人.pdf': pdf('Private paper'),
               '资料/PPT/导出/私人.pptx': b'PK-private',
               '笔记/总览.md': b'PRIVATE NOTE',
               '自动化/日志/本次.md': b'PRIVATE RUN'}
    for rel, content in private.items():
        write(source, rel, content)
    # A launcher may have RC_DB set to its live project. Neither generation
    # may open that connection or copy its index, even if it is not SQLite.
    source_index = write(source, '索引/state.db', b'PRIVATE INDEX DO NOT OPEN')
    monkeypatch.setenv('RC_DB', str(source_index))
    source_before = snapshot(source)
    parent = source
    for generation in ('child', 'grandchild'):
        target = tmp_path / generation
        done = new_project.make(target, parent, business_modules=['PPT'] if generation == 'child' else None)
        assert '新项目复制清单.json' in done
        assert source_index.read_bytes() == b'PRIVATE INDEX DO NOT OPEN'
        assert (target / '索引/state.db').read_bytes().startswith(b'SQLite format 3')
        assert (target / '资料/PPT/导出/demo.pdf').read_bytes() == pdf()
        assert (target / '资料/PPT/导出/demo.pptx').read_bytes() == b'PK\x03\x04synthetic-pptx'
        entry = library.get(Project(target), '文献', 'L1')
        assert entry['info']['标题'] == '项目介绍示例'
        guide = target / '资料/文献' / entry['folder'] / '文本/讲解.md'
        assert guide.read_text(encoding='utf-8') == '# 示例\n\n## 第 1 页\n这是项目介绍。\n'
        rows = downloads.list_all(Project(target), '文献')
        assert len(rows) == 3 and all(row['state'] == '还没下' for row in rows)
        assert all(not (target / rel).exists() for rel in private)
        report = json.loads((target / '新项目复制清单.json').read_text(encoding='utf-8'))
        seeded = report['onboarding_examples']
        assert seeded['library'][0]['created'] and seeded['library'][0]['code'] == 'L1'
        assert len(seeded['downloads']) == 3 and not seeded['conflicts']
        copied = {row['path'] for row in report['files']}
        assert set(examples.planned_paths(examples.validate(target, selected(target)))) <= copied
        assert report['file_count'] == len(report['files'])
        assert report['bytes'] == sum(row['bytes'] for row in report['files'])
        # User edits and additions in the first child are never the seed for
        # its descendant; only the unchanged builtin declaration is inherited.
        if generation == 'child':
            guide.write_text('PERSONAL READING', encoding='utf-8')
            for rel, content in private.items():
                write(target, rel, content)
        parent = target
    assert snapshot(source) == source_before


def test_make_unselected_ppt_does_not_read_declaration_or_export(source, tmp_path):
    manifest(source, 'PPT', {'version': 999})
    child, grandchild = tmp_path / 'child', tmp_path / 'grandchild'
    new_project.make(child, source, business_modules=[])
    new_project.make(grandchild, child)
    for target in (child, grandchild):
        assert not (target / '资料/PPT').exists()
        assert library.get(Project(target), '文献', 'L1')['info']['标题'] == '项目介绍示例'
        assert len(downloads.list_all(Project(target), '文献')) == 3
        report = json.loads((target / '新项目复制清单.json').read_text(encoding='utf-8'))
        assert not any(x['path'].startswith('资料/PPT/') for x in report['files'])


@pytest.mark.parametrize('bad', [
    {'version': 9},
    {'version': 1, 'files': [{'source': '工作台/不存在.pdf', 'target': '导出/demo.pdf'}]},
    {'version': 1, 'files': [{'source': '工作台/成果/demo.pdf', 'target': '导出/CON.pdf'}]},
])
def test_make_bad_selected_example_fails_before_creating_target(source, tmp_path, bad):
    manifest(source, 'PPT', bad)
    target = tmp_path / 'must-not-exist'
    with pytest.raises(ValueError):
        new_project.make(target, source, business_modules=['PPT'])
    assert not target.exists()


def test_make_preflights_generated_files_without_treating_them_as_copies(source, tmp_path, monkeypatch):
    checked = []
    original = new_project._windows_path_preflight
    def preflight(target, copied, *args, **kwargs):
        checked.extend(copied)
        return original(target, copied, *args, **kwargs)
    monkeypatch.setattr(new_project, '_windows_path_preflight', preflight)
    target = tmp_path / 'child'
    new_project.make(target, source, business_modules=['PPT'])
    assert '索引/state.db' in checked
    assert '资料/PPT/导出/demo.pdf' in checked
    assert '资料/文献/解读/L1 Starter project introduction/文本/讲解.md' in checked
    assert not (source / '资料/PPT/导出/demo.pdf').exists()
