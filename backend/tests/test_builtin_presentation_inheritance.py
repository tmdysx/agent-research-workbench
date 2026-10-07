"""真实内置方法与运行资源两代继承：只读程序/技能正本，不读作者材料正文。"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest

import new_project
import skills
import content_modules as cm
import downloads
import library
import outline
from project import Project, CODE_DIR


def data(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def put(root, rel, text):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding='utf-8')
    return f


def test_explicit_default_method_set_is_82_aris_ppt_and_nine_stages():
    cfg = new_project.profile_config(CODE_DIR, 'general')
    ids = cfg['builtin_skill_ids']
    assert len([s for s in ids if s.startswith('biz:paper:aris-module:')]) == 75
    assert len([s for s in ids if s.startswith('biz:paper:aris:')]) == 7
    assert len([s for s in ids if s.startswith('research-')]) == 9
    assert 'biz:presentation:ppt-master:presentation' in ids
    assert '业务' not in cfg['skills']
    assert cfg['modules'] == ['文献', '论文', '测试', 'PPT']


def test_actual_source_general_copy_inherits_real_methods_templates_and_brand_twice(monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    # Windows 正常路径上限是产品功能；测试目录刻意短，以核有效正常路径而不测试别名绕过。
    with tempfile.TemporaryDirectory(prefix='pptg-', dir=os.environ.get('TEMP')) as working:
        base = Path(working)
        first, second = base / 'g1', base / 'g2'
        source = CODE_DIR
        expected = new_project.profile_config(source, 'general')['builtin_skill_ids']
        new_project.make(first, source, profile='general')
        private = ['资料/论文/正文/引言/作者稿.md', '资料/PPT/材料/本次.md', '资料/PPT/导出/本次.pptx',
                   '资料/测试/测试记录/本次.md', '笔记/总览.md', '笔记/日志/本次.md',
                   '自动化/日志/本次.md', '工具库/下载/Blender/blender.exe']
        for rel in private:
            put(first, rel, 'SYNTHETIC_PRIVATE_DO_NOT_INHERIT')
        new_project.make(second, first)
        first_manifest = data(first / '技能库/业务/manifest.json')
        ids = {r['id'] for r in first_manifest['items']}
        assert ids == set(expected)
        assert all(r['business'] in {'paper', 'presentation'} for r in first_manifest['items'])
        source_rows = {r['id']: r for r in data(source / '技能库/业务/manifest.json')['items']}
        for target in (first, second):
            actual = data(target / '技能库/业务/manifest.json')
            assert {r['id'] for r in actual['items']} == ids
            for row in actual['items']:
                original = source_rows[row['id']]
                assert row['path'] == original['path']
                assert row['source'] == original['source']
                assert row['languages'] == original['languages']
                for rel in (row['path'], *row['languages'].values(), *row.get('support_files', []), *row['license']['files']):
                    assert (target / rel).read_bytes() == (source / rel).read_bytes(), rel
            rows = skills.inventory(Project(target))['items']
            selected = {r['id']: r for r in rows if r['id'] in ids}
            assert set(selected) == ids and all(r['available'] for r in selected.values())
            assert all(r['kind'] == 'skill' and r.get('runtime_status') != 'ready' for r in selected.values())
            for module in ('文献', '论文', '测试', 'PPT'):
                view = cm.workspace(Project(target), module)
                original_config = data(source / '资料' / module / cm.CONFIG)
                assert len(view['sections']) == len(original_config['sections']) and not view['problems']
                assert [(s['id'], s['kind']) for s in view['sections']] == [
                    (s['id'], s['kind']) for s in original_config['sections']]
                # 只允许显式入门示例重新生成，私人工作仍不得传给第二代。
                if target == second and module in ('论文', '测试'):
                    assert all(not s['files'] for s in view['sections'])
                if module != '文献':
                    assert all((target / '资料' / module / s['folder']).is_dir() for s in view['sections'])
            for rel in ['内容工作台.js', '模板.html', '界面英文.js', '外观/图标/玉金.svg', '外观/品牌/凤凰.png']:
                assert (target / rel).read_bytes() == (source / rel).read_bytes(), rel
            assert not any((target / '资料' / name).exists() for name in ('写小说', '剪辑'))
            copied = {r['path'] for r in data(target / '新项目复制清单.json')['files']}
            assert not any(rel in copied for rel in private)
            copy_report = data(target / '新项目复制清单.json')
            report = copy_report['onboarding_examples']
            assert not report['conflicts'] and len(report['library']) == 1
            assert len(report['downloads']) == 3 and all(x['state'] == '还没下' for x in report['downloads'])
            assert (target / '索引/state.db').read_bytes().startswith(b'SQLite format 3')
            assert '索引/state.db' in copied
            ppt_examples = data(source / '资料/PPT/工作台/入门示例.json')['files']
            for example in ppt_examples:
                rel = '资料/PPT/' + example['target']
                assert rel in copied
                assert (target / rel).read_bytes() == (source / '资料/PPT' / example['source']).read_bytes()
            entry = library.get(Project(target), '文献', report['library'][0]['code'])
            assert (target / '资料/文献' / entry['pdf']).is_file()
            assert (target / '资料/文献' / entry['folder'] / '文本/讲解.md').is_file()
            assert len(downloads.list_all(Project(target), '文献')) == 3
            navigation = outline.sections(Project(target), '文献', [])
            assert navigation['default'] == '#文献库:文献'
            assert [item['path'] for item in navigation['sections'][0]['items']] == [
                '#下载:文献', '#文献库:文献']
        assert all(not (second / rel).exists() for rel in private)


def test_declared_method_missing_or_source_fingerprint_wrong_refuses_before_creation(tmp_path):
    # 独立极小方法包模拟损坏，不更改项目真实技能或来源锁。
    source = tmp_path / 'source'
    package = '技能库/业务/paper/test/method'
    up = put(source, package + '/references/upstream.md', 'actual source')
    put(source, package + '/SKILL.md', '---\nname: mh-paper-test-method\n---\n# Method\n')
    put(source, package + '/LICENSE.txt', 'Synthetic MIT')
    row = {'id': 'biz:paper:test:method', 'business': 'paper', 'kind': 'skill', 'path': package + '/SKILL.md',
           'source': {'files': [{'local_path': package + '/references/upstream.md', 'sha256': '0' * 64}]},
           'license': {'id': 'MIT', 'files': [package + '/LICENSE.txt']}}
    put(source, '技能库/业务/manifest.json', json.dumps({'schema': 1, 'groups': [{'id': 'paper'}], 'items': [row]}))
    with pytest.raises(ValueError, match='不存在'):
        new_project._builtin_skill_files(source, ['biz:paper:test:missing'])
    with pytest.raises(ValueError, match='指纹'):
        new_project._builtin_skill_files(source, [row['id']])
    row['source']['files'][0]['sha256'] = hashlib.sha256(up.read_bytes()).hexdigest()
    row['support_files'] = ['笔记/私人.md']
    put(source, '笔记/私人.md', 'not a builtin')
    put(source, '技能库/业务/manifest.json', json.dumps({'schema': 1, 'groups': [{'id': 'paper'}], 'items': [row]}))
    with pytest.raises(ValueError, match='配套'):
        new_project._builtin_skill_files(source, [row['id']])
