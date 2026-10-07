"""宣传片复用真实工作台：两区、只读观看、同源接口及原有保存保护。"""
import hashlib
import json
import subprocess

import pytest
from fastapi.testclient import TestClient

import content_modules as cm
import mcp_server
import outline
import store
from main import create_app
from project import Project, CODE_DIR, FIXED_NAMES


@pytest.fixture
def promo(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    p = Project(tmp_path)
    config = p.materials / '宣传片' / cm.CONFIG
    config.parent.mkdir(parents=True)
    config.write_bytes((CODE_DIR / '资料/宣传片' / cm.CONFIG).read_bytes())
    for name in ('素材', '成果'):
        (p.materials / '宣传片' / name).mkdir()
    return p


def fingerprints(p):
    return {str(f.relative_to(p.root)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in p.root.rglob('*') if f.is_file() and '索引' not in f.relative_to(p.root).parts}


def test_promo_web_mcp_and_outline_read_same_two_sections_without_writes(promo, monkeypatch):
    before = fingerprints(promo)
    def forbidden(*args, **kwargs):
        pytest.fail('读取宣传片工作台不能写索引或执行外部工具')
    monkeypatch.setattr(store, 'connect', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    response = TestClient(create_app(promo)).get('/api/content/宣传片')
    assert response.status_code == 200
    data = response.json()
    native = json.loads(mcp_server.build(promo)._tool_manager.get_tool('get_content_workspace').fn(module='宣传片'))
    assert data == native
    assert [(s['id'], s['title'], s['folder']) for s in data['sections']] == [
        ('materials', '素材', '素材'), ('results', '成果', '成果')]
    assert not data['problems'] and all(not s['files'] for s in data['sections'])
    nav = outline.sections(promo, '宣传片', [])
    assert nav['default'] == '#工作区:all'
    assert [n['path'] for n in nav['sections'][0]['items']] == [
        '#工作区:all', '#工作区:materials', '#工作区:results']
    assert '宣传片' not in FIXED_NAMES
    assert fingerprints(promo) == before and not promo.index_dir.exists()


@pytest.mark.parametrize('folder', ['素材', '成果'])
def test_promo_text_save_keeps_history_and_rejects_stale_revision(promo, folder):
    with store.connect(promo.db_path) as conn:
        path = folder + '/任务.md'
        first = cm.write_document(conn, promo, '宣传片', path, '合成初稿', '', str(promo.root), by='人', source='http')
        cm.write_document(conn, promo, '宣传片', path, '合成修订', first['revision'], str(promo.root), by='G11', source='mcp')
        before = fingerprints(promo)
        with pytest.raises(cm.Conflict):
            cm.write_document(conn, promo, '宣传片', path, '陈旧稿', first['revision'], str(promo.root), by='人', source='http')
        assert fingerprints(promo) == before
        assert cm.read_document(promo, '宣传片', path)['text'] == '合成修订'
        assert any(f.read_text(encoding='utf-8') == '合成初稿'
                   for f in (promo.materials / '宣传片/历史/内容工作台').rglob('*.md'))


@pytest.mark.parametrize('path', ['../PPT/导出/坏.md', '内置/方法/方法.md', '素材/CON.md',
                                  '成果/成片.mp4', '工作/旧.md', '成果/../../旁边.md'])
def test_promo_editor_does_not_expand_writable_scope(promo, path):
    with store.connect(promo.db_path) as conn:
        before = fingerprints(promo)
        with pytest.raises(cm.Invalid):
            cm.write_document(conn, promo, '宣传片', path, '不得写入', '', str(promo.root), by='人', source='http')
        assert fingerprints(promo) == before


def test_promo_binary_is_viewable_metadata_and_config_cannot_escape(promo):
    path = promo.materials / '宣传片/成果/合成.mp4'
    path.write_bytes(b'SYNTHETIC_METADATA_ONLY_NOT_A_VIDEO')
    result = cm.workspace(promo, '宣传片')['sections'][1]['files'][0]
    assert result['path'] == '成果/合成.mp4' and not result['editable']
    with pytest.raises(cm.Invalid):
        cm.read_document(promo, '宣传片', result['path'])
    config = json.loads((promo.materials / '宣传片' / cm.CONFIG).read_text(encoding='utf-8'))
    config['sections'][0]['folder'] = '内置'
    with pytest.raises(cm.Invalid):
        cm.validate_config('宣传片', config)
