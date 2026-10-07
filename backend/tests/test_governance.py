"""集中治理的迁移、共享需求、并发编辑、旧链接与跨版本恢复。"""
import json
import anyio
import pytest
from fastapi.testclient import TestClient
import blueprint
import governance as gov
import governance_paths as gp
import requirements
import snapshot
import store
import trash
from main import create_app
from test_mcp import _call


def put(p, path, text):
    f = p.root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding='utf-8')
    return f


def setup(p):
    put(p, '资料/蓝图/S0 终极目标.md', '# S0\n**办好社区活动。**\n')
    put(p, '资料/蓝图/S1-1 招募.md', '# S1-1\n**报名清楚。**\n动到的模块：报名\n| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n| S2-1 | 名单 | 能导出 | 没做 |\n')
    put(p, '资料/报名/需求.md', '# 报名\n为了：S1-1\n| | 要什么功能 | 要什么效果 | 来自 |\n|---|---|---|---|\n| 需-1 | 名单 | 能查姓名 | 人 |\n')
    put(p, '资料/报名/蓝图.md', '# 任务\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n| S2-1 | 旧任务 | 需-1 | 查姓名 | 没做 |\n')
    put(p, '资料/报名/戒律.md', '| 报-1 | 不公开名单 | 人 |\n')
    put(p, '资料/戒律/1 通用戒律.md', '| 通-1 | 原文不丢 | 人 |\n')
    put(p, '资料/戒律/2 项目戒律.md', '| 项-1 | 只用本地 | 人 |\n')
    put(p, '资料/报名/名单.txt', '业务材料')
    put(p, '计划/S1-1 招募/P1 · 2026-09-29 · 名单.md', '# 计划\n目标：S1-1 · 动到的模块：报名 · 状态：在做\n')
    put(p, '笔记/总览.md', '# 人的笔记\n原话')
    put(p, '自动化/日志/示例.md', '运行记录')
    c = store.connect(p.db_path)
    store.migrate(c)
    return c


def test_migration_preserves_sources_and_old_web_links(proj):
    c = setup(proj)
    original = {gp.relative(proj, a): (a.read_bytes(), a.stat().st_mtime_ns) for a, b in gp.migration_pairs(proj)}
    r = gp.migrate(c, proj, by='agent:test', request='集中治理')
    assert r['moved'] == len(original) and r['backup']['code'].startswith('X')
    for old, (content, stamp) in original.items():
        f = gp.resolve(proj, old)
        assert f.read_bytes() == content and f.stat().st_mtime_ns == stamp
        assert not (proj.root / old).exists()
    assert gp.migrate(c, proj, by='agent:test', request='重跑')['moved'] == 0
    with TestClient(create_app(proj)) as web:
        for m, path in [('报名', '需求.md'), ('报名', '戒律.md'), ('蓝图', 'S0 终极目标.md'), ('蓝图', '@/资料/报名/需求.md')]:
            assert web.get(f'/api/modules/{m}/preview', params={'path': path}).status_code == 200
        assert web.get('/api/project/preview', params={'path': '计划/S1-1 招募/P1 · 2026-09-29 · 名单.md'}).status_code == 200
        state = web.get('/api/state').json()
        assert state['panorama']['s0']['one_line'] == '办好社区活动'
        detail = web.get('/api/governance', params={'kind': 'module', 'key': '报名'}).json()
        assert any('不公开名单' in r['text'] for r in detail['rules'])
        assert detail['plans'][0]['path'].startswith('治理/计划/')
    assert (proj.root / '笔记/总览.md').read_text(encoding='utf-8').endswith('原话')
    assert (proj.root / '自动化/日志/示例.md').read_text(encoding='utf-8') == '运行记录'
    c.close()


def test_requirement_exists_before_modules_then_shared_without_id_collisions(proj):
    c = setup(proj)
    gp.migrate(c, proj, by='agent:test', request='集中')
    import ideas
    idea = ideas.add(c, proj, '需要统一搜索', about='整个项目', source='人', by='人')
    ideas.suggest(c, proj, idea['code'], [{'to':'需求','func':'搜索','effect':'一次找到全部材料','goals':['S1-1'],'modules':[],'reason':'作者要求'}], by='agent:test')
    ideas.adopt(c, proj, idea['code'], 0)
    key = requirements.key('项目', '需-1')
    q = next(q for q in gov.catalog(proj) if q['key'] == key)
    assert q['modules'] == [] and q['tasks'] == []
    with TestClient(create_app(proj)) as web:
        response = web.post('/api/governance/assign', json={'key':key,'goals':['S1-1'],'modules':['报名','common:search']})
        assert response.status_code == 200
        left = web.get('/api/governance', params={'kind':'module','key':'报名'}).json()
        right = web.get('/api/governance', params={'kind':'module','key':'common:search'}).json()
        assert next(q for q in left['requirements'] if q['key'] == key) == right['requirements'][0]
    f = proj.root / '治理/任务/报名.md'
    f.write_text(f.read_text(encoding='utf-8') + f'| S2-2 | 新任务 | {key} | 搜索结果 | 待你验收 |\n', encoding='utf-8')
    shared = next(q for q in gov.catalog(proj) if q['key'] == key)
    old = next(q for q in gov.catalog(proj) if q['scope'] == '报名')
    assert [x['code'] for x in shared['tasks']] == ['S2-2'] and shared['state'] == '待你验收'
    assert [x['code'] for x in old['tasks']] == ['S2-1']
    trash.move(c, proj, '资料/报名', by='人', reason='移除业务模块')
    assert next(q for q in gov.catalog(proj) if q['key'] == key)['missing_modules'] == ['报名']
    assert requirements.read(proj, '报名') is not None
    c.close()


def test_editor_conflicts_are_rejected_and_web_mcp_share_text(proj):
    c = setup(proj)
    gp.migrate(c, proj, by='agent:test', request='集中')
    path = '治理/需求/报名.md'
    original = gov.read_document(proj, path)
    edited = original['text'].replace('能查姓名', '能查姓名和报名时间')
    with TestClient(create_app(proj)) as web:
        first = web.put('/api/governance/document', json={'path':path,'text':edited,'revision':original['revision']})
        assert first.status_code == 200
        stale = web.put('/api/governance/document', json={'path':path,'text':'过时版本','revision':original['revision']})
        assert stale.status_code == 409
        assert web.put('/api/governance/document', json={'path':'笔记/总览.md','text':'x','revision':''}).status_code == 400
        assert web.put('/api/governance/document', json={'path':'治理/需求/../../backend/x.md','text':'x','revision':''}).status_code == 400
    got = anyio.run(_call, proj, [('read_governance_document', {'path':path}), ('get_governance', {'kind':'module','key':'报名'}),
                                ('write_governance_document', {'path':path,'text':edited+'\nagent 补充说明\n','revision':first.json()['revision'],'reason':'作者授权测试'})])
    assert json.loads(got[0])['text'] == edited and '能查姓名和报名时间' in got[1]
    assert 'agent 补充说明' in json.loads(got[2])['text']
    d = gov.read_document(proj, '治理/任务/报名.md')
    with pytest.raises(store.Refused):
        gov.save_document(c, proj, d['file'], d['text'].replace('没做','做完'), d['revision'], by='agent:test')
    c.close()


def test_conflict_migration_does_not_overwrite_either_version(proj):
    c = setup(proj)
    put(proj, '治理/需求/报名.md', '已有新版本')
    r = gp.migrate(c, proj, by='agent:test', request='集中')
    assert r['conflicts'] == [{'old':'资料/报名/需求.md','new':'治理/需求/报名.md'}]
    assert '能查姓名' in (proj.root / '资料/报名/需求.md').read_text(encoding='utf-8')
    assert (proj.root / '治理/需求/报名.md').read_text(encoding='utf-8') == '已有新版本'
    assert gp.problems(proj)
    c.close()


def test_old_checkpoint_restores_central_sources_without_rewinding_history(proj):
    c = setup(proj)
    before = snapshot.save(c, proj, name='旧目录', mode='全量', by='人')
    gp.migrate(c, proj, by='agent:test', request='集中')
    f = proj.root / '治理/需求/报名.md'
    f.write_text('改过的需求', encoding='utf-8')
    plan = proj.root / '治理/计划/S1-1 招募/P1 · 2026-09-29 · 名单.md'
    plan.write_text('新计划不能倒退', encoding='utf-8')
    snapshot.restore(c, proj, before['code'], by='人', confirm=True)
    assert '能查姓名' in f.read_text(encoding='utf-8')
    assert plan.read_text(encoding='utf-8') == '新计划不能倒退'
    assert not (proj.root / '资料/报名/需求.md').exists()
    assert (proj.root / '治理/迁移记录.json').exists()
    c.close()


def test_common_module_can_create_and_edit_its_own_documents(proj):
    c = setup(proj)
    gp.migrate(c, proj, by='agent:test', request='集中')
    with TestClient(create_app(proj)) as web:
        for kind in ('需求','戒律','任务','计划'):
            draft = web.get('/api/governance/draft', params={'kind':kind,'module':'common:notes'}).json()
            assert draft['missing'] and draft['revision'] == ''
            text = draft['text'].replace('| 需-1 |  |  |', '| 需-1 | 记笔记 | 能保存 |')
            assert web.put('/api/governance/document', json={'path':draft['save_path'],'text':text,'revision':''}).status_code == 200
        got = web.get('/api/governance', params={'kind':'module','key':'common:notes'}).json()
        assert got['requirements'][0]['func'] == '记笔记' and got['plans'] and got['tasks']
        assert not (proj.materials / 'common:notes').exists()
    c.close()


def test_restore_legacy_core_preserves_latest_plans_in_legacy_layout(proj):
    c = setup(proj)
    put(proj, 'backend/main.py', '# legacy application')
    before = snapshot.save(c, proj, name='旧程序全量', mode='全量', by='人')
    gp.migrate(c, proj, by='agent:test', request='集中')
    put(proj, 'backend/main.py', '# centralized application')
    put(proj, 'backend/governance_paths.py', '# path resolver')
    put(proj, '治理/计划/S1-1 招募/P1 · 2026-09-29 · 名单.md', '最新计划不可倒退')
    put(proj, '治理/计划/S1-1 招募/附件.txt', '新附件')
    with pytest.raises(store.Refused, match='整档复活'):
        snapshot.restore(c, proj, before['code'], by='人', paths=['backend'], confirm=True)
    restored = snapshot.restore(c, proj, before['code'], by='人', confirm=True)
    assert restored['legacy_layout'] and restored['trash_code']
    assert not gp.active(proj)
    assert (proj.root / '计划/S1-1 招募/P1 · 2026-09-29 · 名单.md').read_text(encoding='utf-8') == '最新计划不可倒退'
    assert (proj.root / '计划/S1-1 招募/附件.txt').read_text(encoding='utf-8') == '新附件'
    assert '能查姓名' in requirements.read(proj, '报名')['reqs'][0]['effect']
    assert (proj.root / '笔记/总览.md').read_text(encoding='utf-8').endswith('原话')
    c.close()


def test_partial_migration_keeps_old_plans_and_rule_summary_in_sync(proj):
    c = setup(proj)
    put(proj, '治理/需求/项目.md', '# 项目需求')
    put(proj, 'AGENTS.md', '# 接手\n- 通-1 原文不丢\n')
    assert gov.plan_records(proj)[0]['path'].startswith('计划/')
    d = gov.read_document(proj, '资料/戒律/1 通用戒律.md')
    gov.save_document(c, proj, d['file'], d['text'].replace('原文不丢','先存原文再编辑'), d['revision'], by='人')
    assert '先存原文再编辑' in (proj.root / 'AGENTS.md').read_text(encoding='utf-8')
    c.close()


def test_shared_requirement_completion_keeps_source_scope(proj):
    import workorders
    c = setup(proj)
    gp.migrate(c, proj, by='agent:test', request='集中')
    requirements.add_shared(proj, '搜索', '能搜索', goals=['S1-1'], modules=['报名'])
    key = requirements.key('项目', '需-1')
    f = proj.root / '治理/任务/报名.md'
    f.write_text(f.read_text(encoding='utf-8') + f'| S2-2 | 搜索 | {key} | 搜索结果 | 做完 |\n', encoding='utf-8')
    assert workorders._all_done(proj, {'target':['项目 需-1']})
    assert not workorders._all_done(proj, {'target':['报名 需-1']})
    c.close()
