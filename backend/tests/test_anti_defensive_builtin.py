"""实际内置写作方法的语言、许可、来源闭包；不运行模型或读取作者稿件。"""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

import mcp_server
import new_project
import skills
from main import create_app
from project import CODE_DIR, Project


SID = 'biz:paper:adkid-zephyr:anti-defensive-writing'


def source_row():
    manifest = json.loads((CODE_DIR / '技能库/业务/manifest.json').read_text(encoding='utf-8-sig'))
    return next(row for row in manifest['items'] if row['id'] == SID)


def test_default_profiles_inherit_the_complete_method_and_original_license():
    row = source_row()
    actual = next(r for r in skills.inventory(Project(CODE_DIR))['items'] if r['id'] == SID)
    assert actual['available'] and not actual['issues']
    for profile in ('general', 'research', 'business'):
        cfg = new_project.profile_config(CODE_DIR, profile)
        assert cfg['builtin_skill_ids'].count(SID) == 1
        files, projected = new_project._builtin_skill_files(CODE_DIR, [SID])
        assert {r['id'] for r in projected['items']} == {SID}
        required = {*row['languages'].values(), *row['support_files'], *row['license']['files']}
        assert required <= set(files)
        assert not any(part.startswith('.') for rel in required for part in rel.split('/'))
    assert row['license']['id'] == 'MIT'
    original = CODE_DIR / row['license']['source_file']
    assert (CODE_DIR / row['license']['files'][0]).read_bytes() == original.read_bytes()


def test_all_eight_originals_match_the_pinned_source_and_project_source_lock():
    row = source_row()
    manifest = json.loads((CODE_DIR / '技能库/业务/manifest.json').read_text(encoding='utf-8-sig'))
    lock = json.loads((CODE_DIR / manifest['source_lock']).read_text(encoding='utf-8-sig'))
    locked = {r['local_path']: r for r in lock['files']}
    assert len(row['source']['files']) == 8
    for record in row['source']['files']:
        raw = (CODE_DIR / record['local_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        assert locked[record['local_path']]['sha256'] == record['sha256']
    gitignore = next(r for r in row['source']['files'] if r['path'] == '.gitignore')
    assert gitignore['local_path'].endswith('/gitignore.txt')
    assert row['dependencies'] == [] and row['runtime_enabled'] is False


@pytest.mark.parametrize('language', ['zh-CN', 'en'])
def test_source_http_and_mcp_return_the_same_authoritative_language(language):
    project = Project(CODE_DIR)
    client = TestClient(create_app(project, tasks=False, global_keys=False))
    server = mcp_server.build(project)
    raw = server._tool_manager.get_tool('read_skill_entry').fn(id=SID, language=language)
    native = json.loads(raw) if isinstance(raw, str) else raw
    response = client.get('/api/skills/' + SID, params={'language': language})
    assert response.status_code == 200 and response.json() == native
    row = source_row()
    assert native['path'] == row['languages'][language]
    assert native['text'] == (CODE_DIR / native['path']).read_text(encoding='utf-8')
