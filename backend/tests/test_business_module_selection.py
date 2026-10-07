"""新建模块复选只带内置；合成资料、真实复制及HTTP，不触源项目材料。"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import new_project
import project
import store
from main import create_app


FIXED = ['想法', '蓝图', '戒律', '源代码', '测试', '文献', '论文']


def write(root, rel, text='合成模板'):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return p


@pytest.fixture
def source(tmp_path):
    root = tmp_path / '业务源'
    write(root, 'backend/main.py', '# 合成应用')
    write(root, 'backend/builtin_resources.json', json.dumps({'version': 1, 'paths': []}))
    write(root, '模板.html', '<html>合成应用</html>')
    write(root, '技能库/通用/SKILL.md', '# 通用技能')
    for name in FIXED + ['PPT', '剪辑', '写小说', '天气']:
        write(root, f'资料/{name}/内置/模板.md')
        write(root, f'资料/{name}/用户材料.md', '禁止随模块复制的合成私有资料')
    write(root, '资料/剪辑/样例/内置/嵌套.txt', '明确内置')
    write(root, '资料/剪辑/技能/SKILL.md', '# 已声明的模块技能')
    profiles = {'version': 1, 'profiles': {'general': {
        'modules': ['PPT', '天气'], 'skills': ['通用'],
        'template_roots': [f'资料/{n}/内置' for n in FIXED + ['PPT', '天气']],
        'module_skills': ['资料/剪辑/技能'], 'builtin_skill_ids': [],
        'module_labels': {'剪辑': 'Video Editing', '写小说': 'Novel Writing'}}}}
    write(root, 'backend/template_profiles.json', json.dumps(profiles, ensure_ascii=False))
    write(root, '模板配置.json', json.dumps({'version': 1, 'profile': 'general', 'modules': ['PPT', '天气'],
                                          'module_skills': ['资料/剪辑/技能']}, ensure_ascii=False))
    return root


def test_seven_fixed_modules_reappear_and_all_refuse_removal(tmp_path):
    p = project.Project(tmp_path / 'fixed')
    assert project.FIXED_NAMES == FIXED
    project.ensure_skeleton(p)
    optional = p.materials / '实验'
    optional.rename(p.root / '移走的实验')
    for name in ['测试', '文献', '论文']:
        (p.materials / name).rename(p.root / ('移走的' + name))
    assert project.ensure_skeleton(p) == ['测试', '文献', '论文']
    assert not optional.exists()
    with store.connect(p.db_path) as conn:
        rows = store.get_state(conn, p)['modules']
        assert [r['name'] for r in rows[:7]] == FIXED
        for name in FIXED:
            assert next(r for r in rows if r['name'] == name)['fixed'] is True
            with pytest.raises(store.Refused, match='固定模块'):
                store.remove_module(conn, p, name, by='人', confirm=True)


def test_explicit_module_selection_only_copies_builtin_and_declared_skill_for_two_generations(source, tmp_path):
    before = (source / '模板配置.json').read_bytes()
    first, second = tmp_path / 'one', tmp_path / 'two'
    selected = ['PPT', '剪辑']
    preview = new_project.preview(source, business_modules=selected)
    paths = preview['copied_paths']
    assert '资料/剪辑/样例/内置/嵌套.txt' in paths
    assert '资料/剪辑/技能/SKILL.md' in paths
    assert not any('用户材料' in p for p in paths)
    assert not any(p.startswith(('资料/天气/', '资料/写小说/')) for p in paths)
    new_project.make(first, source, business_modules=selected)
    write(first, '资料/剪辑/新用户材料.txt', '第一代的用户资料')
    new_project.make(second, first)
    for out in (first, second):
        for name in FIXED + selected:
            assert (out / f'资料/{name}/内置/模板.md').is_file()
        assert (out / '资料/剪辑/样例/内置/嵌套.txt').is_file()
        assert (out / '资料/剪辑/技能/SKILL.md').is_file()
        assert not (out / '资料/天气').exists()
        assert not (out / '资料/写小说').exists()
        assert not list(out.glob('资料/*/用户材料.md'))
        cfg = json.loads((out / '模板配置.json').read_text(encoding='utf-8'))
        assert cfg['business_modules'] == selected
        assert cfg['modules'] == selected
    assert not (second / '资料/剪辑/新用户材料.txt').exists()
    assert (source / '模板配置.json').read_bytes() == before


def test_empty_selection_is_not_treated_as_missing_and_keeps_shared_skills(source, tmp_path):
    out = tmp_path / 'no-business'
    new_project.make(out, source, business_modules=[])
    assert set(project.module_dirs(project.Project(out))) == set(FIXED)
    assert (out / '技能库/通用/SKILL.md').is_file()
    assert not (out / '资料/剪辑/技能').exists()
    assert json.loads((out / '模板配置.json').read_text(encoding='utf-8'))['business_modules'] == []


def test_unprofiled_selection_is_preserved_without_borrowing_a_profile(source, tmp_path):
    (source / '模板配置.json').unlink()
    first, second = tmp_path / 'unprofiled-one', tmp_path / 'unprofiled-two'
    new_project.make(first, source, business_modules=['写小说'])
    cfg = json.loads((first / '模板配置.json').read_text(encoding='utf-8'))
    assert 'profile' not in cfg and cfg['business_modules'] == ['写小说']
    new_project.make(second, first)
    assert set(project.module_dirs(project.Project(second))) == set(FIXED + ['写小说'])
    assert not list(second.glob('资料/*/用户材料.md'))


@pytest.mark.parametrize('selection', [['缺失'], ['文献'], ['../剪辑'], [' 剪辑 '], [23], '剪辑', ['剪辑'] * 101])
def test_invalid_selection_fails_before_target_creation(source, tmp_path, selection):
    out = tmp_path / 'invalid'
    with pytest.raises(ValueError):
        new_project.make(out, source, business_modules=selection)
    assert not out.exists()


def test_profile_build_does_not_take_optional_selection(source, tmp_path):
    out = tmp_path / 'release'
    with pytest.raises(ValueError, match='发行模板'):
        new_project.make(out, source, profile='general', business_modules=[])
    assert not out.exists()


def test_old_api_omission_and_explicit_extra_remain_compatible(source, tmp_path):
    with TestClient(create_app(project.Project(source), tasks=False, global_keys=False)) as c:
        initial = c.get('/api/settings/builtin')
        assert initial.status_code == 200
        default = initial.json()
        assert default['fixed_modules'] == FIXED
        assert {r['name'] for r in default['business_options'] if r['selected']} == {'PPT', '天气', '剪辑'}
        browse = c.get('/api/settings/builtin/browse', params={'path': '资料'}).json()
        rows = {r['name']: r for r in browse['items']}
        assert rows['测试']['required'] and rows['文献']['required'] and rows['论文']['required']
        assert rows['剪辑']['business_module'] == '剪辑' and not rows['剪辑']['required']
        old = c.post('/api/settings/new-project', json={'name': 'old', 'where': str(tmp_path)})
        assert old.status_code == 200
        assert (tmp_path / 'old/资料/天气/内置/模板.md').is_file()
        assert not (tmp_path / 'old/资料/天气/用户材料.md').exists()
        chosen = c.post('/api/settings/new-project', json={'name': 'chosen', 'where': str(tmp_path),
                'business_modules': [], 'extra': ['资料/天气/用户材料.md']})
        assert chosen.status_code == 200  # 老 extra 是用户明确选择的文件，业务复选框不生成它。
        assert (tmp_path / 'chosen/资料/天气/用户材料.md').is_file()


def test_api_preview_and_creation_use_the_same_selection_and_refuse_unknown(source, tmp_path):
    before = (source / '模板配置.json').read_bytes()
    with TestClient(create_app(project.Project(source), tasks=False, global_keys=False)) as c:
        preview = c.post('/api/settings/builtin/preview', json={'business_modules': ['PPT', '写小说']})
        assert preview.status_code == 200
        paths = preview.json()['copied_paths']
        assert '资料/写小说/内置/模板.md' in paths and '资料/天气/内置/模板.md' not in paths
        result = c.post('/api/settings/new-project', json={'name': 'same', 'where': str(tmp_path),
                                                         'business_modules': ['PPT', '写小说']})
        assert result.status_code == 200
        copied = {r['path'] for r in json.loads((tmp_path / 'same/新项目复制清单.json').read_text(encoding='utf-8'))['files']}
        assert set(paths) <= copied
        assert not any('用户材料' in p for p in copied)
        assert c.post('/api/settings/new-project', json={'name': 'bad', 'where': str(tmp_path),
                                                       'business_modules': ['不存在']}).status_code == 400
        assert not (tmp_path / 'bad').exists()
    assert (source / '模板配置.json').read_bytes() == before


def test_production_profiles_keep_93_default_method_ids_and_ppt_declarations():
    data = json.loads((Path(__file__).parent.parent / 'template_profiles.json').read_text(encoding='utf-8'))
    for cfg in data['profiles'].values():
        assert len(cfg['builtin_skill_ids']) == 93
        assert 'PPT' in cfg['modules']
        assert '资料/PPT/技能' in cfg['module_skills']
        assert '资料/PPT/内置/通用' in cfg['template_roots']
