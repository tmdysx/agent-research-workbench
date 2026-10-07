"""模块方法的安全路径、唯一编号和独立安装闭包，不把可读说明称为已装依赖。"""
import hashlib
import json
import os
from pathlib import Path

import pytest

import skills
import mcp_server
from fastapi.testclient import TestClient
from main import create_app
from project import Project


def put(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


@pytest.fixture
def module_package(tmp_path, monkeypatch):
    monkeypatch.setenv('RC_HOME', str(tmp_path / 'fake-machine'))
    p = Project(tmp_path / 'project')
    base = '资料/论文/技能/ARIS/合成方法'
    name = 'mh-paper-aris-module-synthetic'
    zh = put(p.root, base + '/SKILL.md', f'---\nname: {name}\ndescription: 合成中文方法\n---\n输入 → 产物 → 检查。\n')
    put(p.root, base + '/SKILL.en.md', f'---\nname: {name}\ndescription: Synthetic English method\n---\nInput → artifact → checks.\n')
    source = put(p.root, base + '/references/upstream.md', '# Synthetic full upstream\n')
    put(p.root, base + '/references/support/检查.md', '# 合成检查说明\n')
    put(p.root, base + '/LICENSE.txt', 'Synthetic MIT proof fixture\n')
    row = {'id': 'biz:paper:aris-module:synthetic', 'kind': 'skill', 'business': 'paper', 'stages': ['write'],
           'install_name': name, 'path': base + '/SKILL.md', 'languages': {'zh-CN': base + '/SKILL.md', 'en': base + '/SKILL.en.md'},
           'license': {'id': 'MIT', 'files': [base + '/LICENSE.txt']}, 'redistribution': {'status': 'verified'},
           'support_files': [base + '/references/support/检查.md'],
           'source': {'files': [{'local_path': base + '/references/upstream.md', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}]},
           'dependencies': [{'name': 'Optional TeX', 'required': False}], 'runtime_status': 'not_verified'}
    data = {'schema': 1, 'groups': [{'id': 'paper', 'stages': [{'id': 'write'}]}], 'items': [row]}
    manifest = put(p.root, '技能库/业务/manifest.json', json.dumps(data, ensure_ascii=False))
    return p, data, manifest, base


def test_module_method_has_one_id_correct_owner_and_same_bilingual_reader(module_package):
    p, _, _, base = module_package
    rows = skills.inventory(p)['items']
    assert len(rows) == 1 and rows[0]['module'] == '论文' and rows[0]['available']
    assert rows[0]['runtime_status'] == 'not_verified'
    for language, name in [('zh-CN', 'SKILL.md'), ('en', 'SKILL.en.md')]:
        r = skills.read(p, rows[0]['id'], language)
        assert r['path'] == base + '/' + name and not r['fallback']
        assert r['text'] == (p.root / r['path']).read_bytes().decode('utf-8')


def test_new_module_method_is_same_in_web_and_mcp_without_installing(module_package):
    p, _, _, _ = module_package
    c = TestClient(create_app(p))
    server = mcp_server.build(p)
    native = server._tool_manager.get_tool('list_skill_catalog').fn()
    assert (json.loads(native) if isinstance(native, str) else native) == c.get('/api/skills/catalog').json()
    sid = 'biz:paper:aris-module:synthetic'
    document = server._tool_manager.get_tool('read_skill_entry').fn(id=sid, language='en')
    assert (json.loads(document) if isinstance(document, str) else document) == c.get('/api/skills/' + sid, params={'language': 'en'}).json()
    assert not (p.root / '.claude').exists() and not (skills.machine_home() / 'skills').exists()


@pytest.mark.parametrize('module', ['论文', 'PPT'])
def test_module_short_name_reads_its_top_level_index_not_owned_business_methods(module_package, module):
    p, _, _, _ = module_package
    put(p.root, f'资料/{module}/技能/SKILL.md', f'---\nname: module-index\ndescription: 合成模块入口\n---\n# {module}独立索引\n')
    exact = skills.read(p, '模块:' + module)
    assert skills.read(p, module) == exact and exact['id'] == '模块:' + module
    server = mcp_server.build(p)
    read = server._tool_manager.get_tool('read_skill').fn
    assert read(name=module) == read(name='模块:' + module)
    # 原完整业务 ID 仍先精确匹配，而非被模块索引代替。
    assert skills.read(p, 'biz:paper:aris-module:synthetic')['id'] == 'biz:paper:aris-module:synthetic'


def test_genuine_duplicate_titles_still_require_full_method_id(module_package):
    p, data, manifest, base = module_package
    original = data['items'][0]
    original['title'] = '相同名称'
    second = json.loads(json.dumps(original))
    other = '资料/论文/技能/ARIS/另一个方法'
    second.update({'id': 'biz:paper:aris-module:other', 'path': other + '/SKILL.md',
                   'install_name': 'mh-paper-aris-module-other',
                   'languages': {'zh-CN': other + '/SKILL.md', 'en': other + '/SKILL.en.md'}})
    put(p.root, other + '/SKILL.md', '---\nname: mh-paper-aris-module-other\n---\n# 独立方法\n')
    put(p.root, other + '/SKILL.en.md', '---\nname: mh-paper-aris-module-other\n---\n# Separate method\n')
    data['items'].append(second)
    manifest.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError, match='不唯一'):
        skills.read(p, '相同名称')
    assert skills.read(p, original['id'])['id'] == original['id']
    assert skills.read(p, second['id'])['id'] == second['id']


def test_installed_single_package_contains_support_and_original(module_package):
    p, _, _, base = module_package
    r = skills.install(p, 'biz:paper:aris-module:synthetic', 'project')
    target = Path(r['to'])
    for f in (p.root / base).rglob('*'):
        if f.is_file():
            assert (target / f.relative_to(p.root / base)).read_bytes() == f.read_bytes()
    assert not (skills.machine_home() / 'skills').exists()


@pytest.mark.parametrize('path', ['资料/论文/正文/SKILL.md', '资料/论文/技能/SKILL.md',
                                  '资料/论文/技能/ARIS/SKILL.md', '资料/论文/技能/ARIS/多/一/SKILL.md',
                                  '资料/论文/技能/.私有/一/SKILL.md', '资料/论文/技能/_系统/一/SKILL.md',
                                  '资料/ 论文/技能/ARIS/一/SKILL.md', '资料/论文/技能/ARIS/../SKILL.md'])
def test_manifest_does_not_turn_any_material_folder_into_installable_code(module_package, path):
    p, data, manifest, _ = module_package
    data['items'][0]['path'] = path
    data['items'][0]['languages'] = {}
    manifest.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError):
        skills.inventory(p)


def test_module_manifest_conflicting_owner_is_refused(module_package):
    p, data, manifest, _ = module_package
    data['items'][0]['module'] = '别的模块'
    manifest.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError, match='归属'):
        skills.inventory(p)


def test_module_directory_link_is_never_followed(module_package, tmp_path):
    p, data, manifest, base = module_package
    ordinary = p.root / base
    target = tmp_path / 'outside'
    target.mkdir()
    link = p.root / '资料/论文/技能/ARIS/linked'
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('Windows 未允许创建符号链接')
    data['items'][0]['path'] = '资料/论文/技能/ARIS/linked/SKILL.md'
    data['items'][0]['languages'] = {}
    manifest.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError, match='链接|联接'):
        skills.inventory(p)
