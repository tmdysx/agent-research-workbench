"""PPT 复用内容工作台，文件安全与网页/MCP 同源都用合成材料验。"""
import hashlib
import json
import subprocess

import pytest
from fastapi.testclient import TestClient

import content_modules as cm
import journal
import mcp_server
import outline
import store
from main import create_app
from project import Project, FIXED_NAMES, GOVERNANCE_NAMES


def put(p, rel, text):
    path = p.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


@pytest.fixture
def ppt(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    p = Project(tmp_path)
    sections = [{'id': str(i), 'title': name, 'en': en, 'kind': 'documents', 'folder': name,
                 'templates': ['工作台/模板/空卡.md']}
                for i, (name, en) in enumerate(zip(cm.ROOTS['PPT'], ['Materials', 'Outline', 'Slides', 'Export', 'Checks']))]
    put(p, '资料/PPT/' + cm.CONFIG, json.dumps({'version': 1, 'sections': sections}, ensure_ascii=False))
    put(p, '资料/PPT/工作台/模板/空卡.md', '# 合成空卡\n')
    return p


def snapshot(p):
    return {f.relative_to(p.root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in p.root.rglob('*') if f.is_file() and '索引' not in f.relative_to(p.root).parts}


def test_ppt_get_and_mcp_share_five_sections_without_writes(ppt, monkeypatch):
    old = snapshot(ppt)
    def forbidden(*args, **kwargs):
        pytest.fail('观看工作台不能扫描资料、开数据库或执行工具')
    monkeypatch.setattr(store, 'connect', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    c = TestClient(create_app(ppt))
    response = c.get('/api/content/PPT')
    assert response.status_code == 200
    data = response.json()
    native = json.loads(mcp_server.build(ppt)._tool_manager.get_tool('get_content_workspace').fn(module='PPT'))
    assert native == data
    assert [s['folder'] for s in data['sections']] == list(cm.ROOTS['PPT'])
    assert all(not s['files'] for s in data['sections'])
    assert not data['problems']
    assert data['skill_entry']['path'] == '技能/SKILL.md' and not data['skill_entry']['available']
    assert snapshot(ppt) == old and not ppt.index_dir.exists()
    assert 'PPT' not in FIXED_NAMES and 'PPT' not in GOVERNANCE_NAMES


@pytest.mark.parametrize('folder', ['材料', '大纲', '幻灯片', '导出', '检查'])
def test_each_ppt_text_folder_uses_version_history_and_real_operator(ppt, folder):
    conn = store.connect(ppt.db_path)
    try:
        rel = folder + '/记录.md'
        first = cm.write_document(conn, ppt, 'PPT', rel, '一稿', '', str(ppt.root), by='G11', source='mcp')
        second = cm.write_document(conn, ppt, 'PPT', rel, '二稿', first['revision'], str(ppt.root), by='人', source='http')
        assert second['revision'] != first['revision']
        assert cm.read_document(ppt, 'PPT', rel)['text'] == '二稿'
        saved = snapshot(ppt)
        with pytest.raises(cm.Conflict):
            cm.write_document(conn, ppt, 'PPT', rel, '陈旧稿', first['revision'], str(ppt.root), by='G11', source='mcp')
        assert snapshot(ppt) == saved
        historical = list((ppt.materials / 'PPT/历史/内容工作台').rglob('*.md'))
        assert any(f.read_text(encoding='utf-8') == '一稿' for f in historical)
        logs = [f.read_text(encoding='utf-8') for f in (ppt.root / '笔记/日志').rglob('*.md')]
        assert any('G11' in text for text in logs)
    finally:
        conn.close()


@pytest.mark.parametrize('path', ['../论文/正文/盗写.md', '技能/SKILL.md', '笔记/记录.md',
                                  '工作台/模板/空卡.md', '材料/CON.md', '材料/假.docx', '检查/运行.exe'])
def test_ppt_cannot_expand_editor_into_protected_or_binary_content(ppt, path):
    conn = store.connect(ppt.db_path)
    try:
        before = snapshot(ppt)
        with pytest.raises(cm.Invalid):
            cm.write_document(conn, ppt, 'PPT', path, '不可写', '', str(ppt.root), by='人', source='http')
        assert snapshot(ppt) == before
    finally:
        conn.close()


def test_ppt_binary_preview_is_metadata_only_and_template_is_readonly(ppt):
    put(ppt, '资料/PPT/导出/合成.pptx', '不是真正的演示二进制')
    data = cm.workspace(ppt, 'PPT')
    export = next(s for s in data['sections'] if s['folder'] == '导出')
    assert export['files'][0]['path'] == '导出/合成.pptx' and not export['files'][0]['editable']
    assert not cm.read_document(ppt, 'PPT', '工作台/模板/空卡.md')['editable']
    with pytest.raises(cm.Invalid):
        cm.read_document(ppt, 'PPT', '导出/合成.pptx')


def test_ppt_config_cannot_write_outside_fixed_five_roots(ppt):
    data = json.loads((ppt.materials / 'PPT' / cm.CONFIG).read_text(encoding='utf-8'))
    data['sections'][0]['folder'] = '论文/正文'
    with pytest.raises(cm.Invalid, match='范围'):
        cm.validate_config('PPT', data)


def test_skill_entry_is_explicit_readonly_and_missing_get_never_creates_it(ppt):
    data = cm.workspace(ppt, 'PPT')
    assert data['skill_entry']['readonly'] and not data['skill_entry']['available']
    assert not (ppt.materials / 'PPT/技能').exists()
    put(ppt, '资料/PPT/技能/SKILL.md', '# 合成方法索引\n')
    entry = cm.workspace(ppt, 'PPT')['skill_entry']
    assert entry == {'path': '技能/SKILL.md', 'name': 'PPT技能', 'en': 'PPT skills', 'readonly': True, 'available': True}
    with pytest.raises(cm.Invalid):
        cm.read_document(ppt, 'PPT', entry['path'])
