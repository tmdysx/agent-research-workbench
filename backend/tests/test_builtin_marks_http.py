"""文件小锁的真实HTTP、预览、MCP和恢复确认；只操作临时项目。"""
import json

import pytest
from fastapi.testclient import TestClient

import builtin
import file_actions
import mcp_server
import project
import snapshot
import store
from main import create_app


@pytest.fixture
def case(tmp_path, monkeypatch):
    p = project.Project(tmp_path / '内置联动样板')
    monkeypatch.setenv('RC_DB', str(p.root / '索引/state.db'))
    project.ensure_skeleton(p)
    ordinary = p.materials / '测试/示例.txt'
    ordinary.write_text('属于这个文件的内容', encoding='utf-8')
    with TestClient(create_app(p)) as client:
        yield p, client, ordinary


def toggle(client, action, enabled, **changes):
    data = {k: action[k] for k in ('path', 'project', 'revision')}
    data.update(enabled=enabled, **changes)
    return client.put('/api/builtin/files', json=data)


def test_read_only_then_round_trip_and_shared_preview(case):
    p, client, f = case
    rel = f.relative_to(p.root).as_posix()
    a = client.get('/api/builtin/files', params={'path': rel}).json()
    assert a['state'] == 'unmarked' and a['toggle_allowed']
    assert not (p.root / builtin.MARKS_FILE).exists()
    assert client.get('/api/builtin/files').json()['items'] == []
    original = f.read_bytes()
    enabled = toggle(client, a, True)
    assert enabled.status_code == 200
    current = enabled.json()
    assert current['state'] == 'marked' and current['enabled']
    assert f.read_bytes() == original
    assert json.loads((p.root / builtin.MARKS_FILE).read_text('utf-8'))['paths'] == [rel]
    for url, path in [('/api/project/preview',rel),('/api/modules/测试/preview','示例.txt')]:
        result = client.get(url, params={'path': path})
        assert result.status_code == 200
        assert result.json()['builtin_action']['revision'] == current['revision']
        assert result.json()['builtin_action']['path'] == rel
    disabled = toggle(client, current, False)
    assert disabled.status_code == 200 and disabled.json()['enabled'] is False
    assert f.read_bytes() == original
    log = '\n'.join(x.read_text('utf-8') for x in (p.root/'笔记/日志').glob('*.md'))
    assert rel in log and '开启' in log and '关闭' in log


def test_stale_revision_wrong_project_and_nonboolean_fail(case):
    p, client, f = case
    a = client.get('/api/builtin/files', params={'path': '资料/测试/示例.txt'}).json()
    assert toggle(client, a, True, project='another-project').status_code == 409
    for invalid in ('true', 1, None):
        assert toggle(client, a, invalid).status_code == 422
    assert not (p.root/builtin.MARKS_FILE).exists()
    assert toggle(client, a, True).status_code == 200
    assert toggle(client, a, False).status_code == 409
    assert builtin.read_marks(p.root)['paths'] == ['资料/测试/示例.txt']


def test_required_file_has_no_switch_and_legacy_governance_alias(case):
    p, client, _ = case
    required = p.materials / '测试/内置/样例.md'
    required.write_text('默认内置', encoding='utf-8')
    a = client.get('/api/builtin/files', params={'path': required.relative_to(p.root).as_posix()}).json()
    assert a['enabled'] and not a['toggle_allowed']
    assert toggle(client, a, False).status_code == 400
    doc = p.root/'治理/需求/测试.md'
    doc.parent.mkdir(parents=True,exist_ok=True)
    doc.write_text('真实需求',encoding='utf-8')
    old = client.get('/api/builtin/files',params={'path':'资料/测试/需求.md'}).json()
    assert old['path'] == '治理/需求/测试.md'
    assert toggle(client, old, True).status_code == 200
    assert builtin.read_marks(p.root)['paths'] == ['治理/需求/测试.md']


def test_deleted_mark_is_clearable_without_destroying_recycle_history(case):
    p, client, f = case
    a = client.get('/api/builtin/files',params={'path':'资料/测试/示例.txt'}).json()
    assert toggle(client,a,True).status_code == 200
    preview = client.get('/api/project/preview',params={'path':a['path']}).json()['delete_action']
    result = client.post('/api/files/trash',json={k:preview[k] for k in ('path','project','revision')})
    assert result.status_code == 200 and not f.exists()
    missing = client.get('/api/builtin/files',params={'path':a['path']}).json()
    assert missing['state']=='missing' and missing['toggle_allowed']
    assert client.get('/api/builtin/files').json()['items'][0]['state']=='missing'
    assert toggle(client,missing,False).status_code == 200
    assert (p.root/'回收站/清单.md').is_file()


def test_restore_confirmation_transmits_mark_revision(case):
    p, client, _ = case
    a = client.get('/api/builtin/files',params={'path':'资料/测试/示例.txt'}).json()
    current=toggle(client,a,True).json()
    conn=store.connect(p.db_path)
    try: saved=snapshot.save(conn,p,name='已锁样例',mode='全量',by='agent:test')
    finally: conn.close()
    unlocked=toggle(client,current,False).json()
    url='/api/checkpoints/'+saved['code']+'/restore'
    preview=client.post(url,json={'paths':[a['path']],'confirm':False})
    assert preview.status_code==409
    marks=preview.json()['confirm']['builtin_marks']
    assert marks['added']==[a['path']] and marks['revision']==unlocked['revision']
    assert '内置标记' in preview.json()['detail']
    other=p.materials/'测试/另一个.txt';other.write_text('另一个',encoding='utf-8')
    other_a=client.get('/api/builtin/files',params={'path':'资料/测试/另一个.txt'}).json()
    assert toggle(client,other_a,True).status_code==200
    stale=client.post(url,json={'paths':[a['path']],'confirm':True,'builtin_revision':marks['revision']})
    assert stale.status_code==400 and '变化' in stale.json()['detail']
    assert builtin.read_marks(p.root)['paths']==['资料/测试/另一个.txt']


@pytest.mark.anyio
async def test_mcp_status_matches_http_without_writing(case):
    p, client, _ = case
    expected=client.get('/api/builtin/files',params={'path':'资料/测试/示例.txt'}).json()
    server=mcp_server.build(p)
    tool=server._tool_manager.get_tool('get_builtin_files')
    result=await tool.run({'path':'资料/测试/示例.txt'})
    assert json.loads(result)==expected
    assert not (p.root/builtin.MARKS_FILE).exists()
