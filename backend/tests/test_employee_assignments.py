"""用非科研临时项目核对真实派活授权在等待、退出和空索引之后仍能安全接续。"""
import json
import sys

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation
from conftest import BACKEND

import agents
import autolaunch
import blueprint
import claims
import construction_plans as cp
import dispatch
import employee_assignments as assignments
import governance
import store
import automation_mcp


def _finalize_fixture(goal):
    goal.write_text(goal.read_text(encoding='utf-8') + '\n规划：定稿 · 2026-10-03 · 临时测试\n', encoding='utf-8')


def _other_task(proj):
    f = proj.root / '治理/目标/S1-2 另一件.md'
    f.write_text('# S1-2 另一件\n\n**独立的合法任务。**\n\n规划：定稿 · 2026-10-03 · 临时测试\n\n'
                 '| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n'
                 '| S2-1 | 〔程序〕写另一份说明 | 能阅读全文 | 没做 |\n', encoding='utf-8')


@pytest.mark.parametrize('changed', ['source', 'task'])
@pytest.mark.parametrize('route', ['auto', 'workorder', 'elsewhere'])
def test_invalid_assignment_cannot_return_through_finalized_candidates(proj, setup, monkeypatch, changed, route):
    conn, worker, source, _, goal = setup
    _finalize_fixture(goal)
    point(proj, setup)
    claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    f = proj.root / source if changed == 'source' else goal
    f.write_text(f.read_text(encoding='utf-8').replace('整理', '修改'), encoding='utf-8')
    _other_task(proj)
    if route == 'auto':
        assert dispatch.auto_target(proj, worker) == ['S1-2 S2-1']
    elif route == 'elsewhere':
        g, x = dispatch._elsewhere(conn, proj, 'agent:worker', set(), worker)
        assert (g['code'], x['code']) == ('S1-2', 'S2-1')
    else:
        monkeypatch.setattr(dispatch, 'start_work', lambda *args, **kwargs: {
            'wo': {'code': 'Kfixture', 'target': ['S1-1 S2-1', 'S1-2 S2-1']}, 'joined': True})
        action = dispatch.next_task(conn, proj, 'agent:worker')
        assert (action['task']['goal'], action['task']['sub']) == ('S1-2', 'S2-1')
        assert '重新派活' in action['reason']
    assert not any(r['goal'] == 'S1-1' for r in claims.of(conn, 'agent:worker'))


@pytest.mark.parametrize('state', ['等你定', '以后', '等 S2-2', '待你验收（Jfixture）'])
def test_held_task_waiting_state_cannot_execute(proj, setup, state):
    point(proj, setup)
    goal = setup[4]
    goal.write_text(goal.read_text(encoding='utf-8').replace('没做', state), encoding='utf-8')
    assert dispatch.next_task(setup[0], proj, 'agent:worker')['task'] is None


@pytest.mark.parametrize('state', ['待你验收', '等验收', '验收通过'])
def test_new_delivery_blocks_even_when_claim_and_blueprint_are_stale(proj, setup, state):
    point(proj, setup)
    f = proj.root / '自动化/交付/J1 S1-1 S2-1.md'
    f.parent.mkdir(parents=True)
    f.write_text('---\n编号: J1\n目标: S1-1\n小目标: S2-1\n做什么: 整理资料\n'
                 f'状态: {state}\n时间: 2026-10-03 00:00\n谁: agent:worker\n自查全过: 是\n---\n'
                 '# 临时交付记录\n\n## 怎么验的\n\n- 过了 · 临时检查\n', encoding='utf-8')
    assert dispatch.next_task(setup[0], proj, 'agent:worker')['task'] is None


def _configuration_tools(proj, conn, source):
    class Tools:
        def __init__(self): self.funcs = {}
        def tool(self):
            def decorate(f): self.funcs[f.__name__] = f; return f
            return decorate
    class BorrowedConnection:
        def __getattr__(self, key): return getattr(conn, key)
        def close(self): pass
    registry = Tools()
    automation_mcp.attach(registry, proj, lambda: BorrowedConnection(), lambda ctx, name: 'agent:boss',
                          configuration_authorization=source)
    return registry.funcs


@pytest.mark.parametrize('existing', [False, True])
def test_failed_assignment_persistence_only_rolls_back_new_claim(proj, setup, monkeypatch, existing):
    conn, worker, source = setup[:3]
    if existing:
        claims.claim(conn, 'S1-1', 'S2-1', 'agent:worker', ['S1-1 S2-1'])
    def broken(*args, **kwargs): raise OSError('临时模拟持久化失败')
    monkeypatch.setattr(assignments, 'record', broken)
    tools = _configuration_tools(proj, conn, source)
    with pytest.raises(store.Refused, match='派活来源.*失败'):
        tools['assign_employee_task'](worker['code'], 'S1-1', 'S2-1', source, '临时测试')
    assert bool(claims.of(conn, 'agent:worker')) is existing
    assert assignments.listing(proj, worker) == []


@pytest.mark.parametrize('released', [False, True])
def test_reassign_revokes_only_target_employee_sources_and_keeps_history(proj, setup, released):
    conn, worker, source, revision = setup[:4]
    point(proj, setup)
    if released:
        claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    other = agents.create(conn, proj, 'other', program='Codex')
    f = proj.root / '治理/计划/S1-1 整理档案/P2 · 另一员工.md'
    f.write_text('> 授权：作者本次临时测试\n> 授权操作者：boss\n'
                 f"> 授权对象：{other['code']}\n", encoding='utf-8')
    other_source = f.relative_to(proj.root).as_posix()
    assignments.record(proj, other, 'S1-1', 'S2-1', by='agent:boss', authorization_path=other_source,
                       authorization_revision=governance.read_document(proj, other_source)['revision'], reason='另一员工')
    before = (proj.root / assignments.DIR / (other['code'] + '.json')).read_bytes()
    tools = _configuration_tools(proj, conn, source)
    tools['reassign_employee_work'](worker['code'], source, '移交施工')
    assert claims.of(conn, 'agent:worker') == []
    assert dispatch.next_task(conn, proj, 'agent:worker')['task'] is None
    saved = assignments.listing(proj, worker)[0]
    assert saved['authorization_path'] == source
    assert saved['revoked']['by'] == 'agent:boss' and saved['revoked']['at']
    assert saved['revoked']['authorization_path'] == source and saved['revoked']['reason'] == '移交施工'
    assert (proj.root / assignments.DIR / (other['code'] + '.json')).read_bytes() == before
    tools['assign_employee_task'](worker['code'], 'S1-1', 'S2-1', source, '新的明确派活')
    saved = assignments.listing(proj, worker)[0]
    assert not saved.get('revoked') and saved['history'][-1]['revoked']['reason'] == '移交施工'
    assert dispatch.next_task(conn, proj, 'agent:worker')['task']['sub'] == 'S2-1'


def test_failed_revocation_keeps_existing_claim(proj, setup, monkeypatch):
    conn, worker, source = setup[:3]
    point(proj, setup)
    def broken(*args, **kwargs): raise OSError('撤销记录写入失败')
    monkeypatch.setattr(assignments, 'revoke', broken)
    tools = _configuration_tools(proj, conn, source)
    with pytest.raises(OSError, match='撤销记录写入失败'):
        tools['reassign_employee_work'](worker['code'], source, '临时测试')
    assert len(claims.of(conn, 'agent:worker')) == 1
    assert not assignments.listing(proj, worker)[0].get('revoked')


def test_assignment_never_adopts_authority_changed_during_claim(proj, setup, monkeypatch):
    conn, worker, source = setup[:3]
    tools = _configuration_tools(proj, conn, source)
    claim = claims.claim
    def changed(*args, **kwargs):
        result = claim(*args, **kwargs)
        f = proj.root / source
        f.write_text(f.read_text(encoding='utf-8') + '\n人的新范围\n', encoding='utf-8')
        return result
    monkeypatch.setattr(claims, 'claim', changed)
    with pytest.raises(store.Refused, match='授权已变更'):
        tools['assign_employee_task'](worker['code'], 'S1-1', 'S2-1', source, '旧连接不能采纳新授权')
    assert claims.of(conn, 'agent:worker') == [] and assignments.listing(proj, worker) == []


def test_unassigned_final_task_is_not_permanently_blocked(proj, setup):
    _finalize_fixture(setup[4])
    assert assignments.listing(proj, setup[1]) == []
    assert dispatch.auto_target(proj, setup[1]) == ['S1-1 S2-1']


def test_rejected_delivery_can_return_for_rework(proj, setup):
    import deliveries
    point(proj, setup)
    claims.release(setup[0], 'S1-1', 'S2-1', 'agent:worker')
    f = proj.root / '自动化/交付/J1 S1-1 S2-1.md'
    f.parent.mkdir(parents=True)
    f.write_text('---\n编号: J1\n目标: S1-1\n小目标: S2-1\n做什么: 整理资料\n'
                 '状态: 打回\n时间: 2026-10-03 00:00\n谁: agent:worker\n---\n'
                 f'# 临时交付记录\n\n## 你的意见\n\n- {deliveries.AGENT_NO}：缺少检查\n', encoding='utf-8')
    action = dispatch.next_task(setup[0], proj, 'agent:worker')
    assert action['task']['sub'] == 'S2-1' and '先改它' in action['reason']


def _shared_lane_pair(proj, setup, *, recorded=True):
    conn, worker, source, revision, goal = setup
    text = goal.read_text(encoding='utf-8').replace('**建立通用档案工具。**', '**建立通用档案工具。**\n\n动到的模块：档案模块')
    goal.write_text(text + '| S2-2 | 〔网页〕准备网页模板 | 网页模板可读 | 没做 |\n', encoding='utf-8')
    web = agents.create(conn, proj, 'webworker', program='Codex', plan_required=True, crafts=['网页'])
    other_source = '治理/计划/S1-1 整理档案/P2 · 网页工派活.md'
    (proj.root / other_source).write_text('> 授权：作者本次临时测试\n> 授权操作者：boss\n'
                                        f"> 授权对象：{web['code']}\n", encoding='utf-8')
    for who, sub, path in [(web, 'S2-2', other_source), (worker, 'S2-1', source)]:
        g = blueprint.find(blueprint.pyramid(proj), 'S1-1')
        x = next(row for row in g['subs'] if row['code'] == sub)
        claims.claim(conn, 'S1-1', sub, agents.actor(who['name']), claims.lanes_of(g, x))
        if who == web or recorded:
            assignments.record(proj, who, 'S1-1', sub, by='agent:boss', authorization_path=path,
                               authorization_revision=governance.read_document(proj, path)['revision'], reason='临时测试派活')
        if who == web:
            claims.release(conn, 'S1-1', sub, agents.actor(who['name']))
    return web


def test_dependency_wait_releases_shared_lane_and_resumes_original_grant(proj, setup):
    conn, worker = setup[:2]
    _shared_lane_pair(proj, setup)
    saved = proj.root / assignments.DIR / (worker['code'] + '.json')
    original = saved.read_bytes()
    blueprint.set_status(proj, 'S1-1', 'S2-1', '等 S2-2')
    assert dispatch.next_task(conn, proj, 'agent:worker')['task'] is None
    assert claims.of(conn, 'agent:worker') == []
    next_dependency = dispatch.next_task(conn, proj, 'agent:webworker')
    assert next_dependency['task']['sub'] == 'S2-2' and next_dependency['action'] == 'submit_plan'
    assert claims.of(conn, 'agent:webworker')[0]['lanes'] == ['档案模块']
    assert saved.read_bytes() == original
    # 设置临时夹具的前置条件，不调用交付或模拟实际验收。
    blueprint.set_status(proj, 'S1-1', 'S2-2', '做完（临时测试前置条件）')
    claims.release(conn, 'S1-1', 'S2-2', 'agent:webworker')
    resumed = dispatch.next_task(conn, proj, 'agent:worker')
    assert resumed['task']['sub'] == 'S2-1' and '按人的明确派活记录接续' in resumed['reason']
    assert saved.read_bytes() == original


def test_unrecorded_legacy_dependency_claim_is_not_lost(proj, setup):
    _shared_lane_pair(proj, setup, recorded=False)
    conn, worker = setup[:2]
    blueprint.set_status(proj, 'S1-1', 'S2-1', '等 S2-2')
    assert assignments.listing(proj, worker) == []
    assert dispatch.next_task(conn, proj, 'agent:worker')['task'] is None
    assert claims.of(conn, 'agent:worker')[0]['sub'] == 'S2-1'


def test_plan_review_wait_keeps_shared_lane_but_reviewer_can_proceed(proj, setup):
    _shared_lane_pair(proj, setup)
    conn, worker = setup[:2]
    agents.create(conn, proj, 'reviewer', program='Codex', roles=['审核'])
    plan = cp.submit(conn, proj, 'S1-1', 'S2-1', 'agent:worker', '整理资料并检查结果', ['result.py'])
    waiting = dispatch.next_task(conn, proj, 'agent:worker')
    assert waiting['action'] == 'waiting' and '计划待审' in waiting['reason']
    assert claims.of(conn, 'agent:worker')[0]['lanes'] == ['档案模块']
    reviewing = dispatch.next_task(conn, proj, 'agent:reviewer')
    assert reviewing['action'] == 'review_plan' and reviewing['construction_plan']['code'] == plan['code']


@pytest.fixture
def setup(proj):
    goal = proj.root / '治理/目标/S1-1 整理档案.md'
    goal.parent.mkdir(parents=True)
    goal.write_text('# S1-1 整理档案\n\n**建立通用档案工具。**\n\n'
                    '| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n'
                    '| S2-1 | 〔程序〕整理资料 | 搜索到自己的记录 | 没做 |\n', encoding='utf-8')
    conn = store.connect(proj.db_path)
    store.migrate(conn)
    worker = agents.create(conn, proj, 'worker', program='Codex', plan_required=True, crafts=['程序'])
    source = '治理/计划/S1-1 整理档案/P1 · 派活授权.md'
    file = proj.root / source
    file.parent.mkdir(parents=True)
    file.write_text('> 授权：作者本次要求完成整理档案。\n> 授权操作者：boss\n'
                    f"> 授权对象：{worker['code']}\n", encoding='utf-8')
    revision = governance.read_document(proj, source)['revision']
    yield conn, worker, source, revision, goal
    conn.close()


def point(proj, setup):
    conn, worker, source, revision, _ = setup
    claims.claim(conn, 'S1-1', 'S2-1', 'agent:worker', ['S1-1 S2-1'], '整理资料')
    return assignments.record(proj, worker, 'S1-1', 'S2-1', by='agent:boss',
                              authorization_path=source, authorization_revision=revision, reason='作者已点名')


def test_existing_claim_resumes_without_any_workorder_or_final_goal(proj, setup):
    conn = setup[0]
    claims.claim(conn, 'S1-1', 'S2-1', 'agent:worker', ['S1-1 S2-1'])
    action = dispatch.next_task(conn, proj, 'agent:worker')
    assert action['action'] == 'submit_plan' and action['task']['sub'] == 'S2-1'
    assert action['wo']['code'] == ''


def test_explicit_assignment_survives_released_claim_and_empty_index(proj, setup, tmp_path):
    record = point(proj, setup)
    claims.release(setup[0], 'S1-1', 'S2-1', 'agent:worker')
    fresh = store.connect(tmp_path / 'fresh-index.sqlite3')
    store.migrate(fresh)
    try:
        action = dispatch.next_task(fresh, proj, 'agent:worker')
        assert action['task']['sub'] == 'S2-1' and action['action'] == 'submit_plan'
        assert record['authorization_path'] in action['reason']
        assert claims.of(fresh, 'agent:worker')[0]['sub'] == 'S2-1'
    finally:
        fresh.close()
    saved = json.loads((proj.root / assignments.DIR / (setup[1]['code'] + '.json')).read_text(encoding='utf-8'))
    assert saved['items'][0]['by'] == 'agent:boss'


def test_employee_submitted_plan_does_not_grant_unfinalized_task(proj, setup):
    conn = setup[0]
    cp.submit(conn, proj, 'S1-1', 'S2-1', 'agent:worker', '自己起草的施工办法', ['backend/a.py'])
    assert assignments.listing(proj, setup[1]) == []
    assert dispatch.next_task(conn, proj, 'agent:worker')['task'] is None


@pytest.mark.parametrize('change', ['source', 'task'])
@pytest.mark.parametrize('release', [False, True])
def test_changed_authority_or_task_requires_new_explicit_assignment(proj, setup, change, release):
    point(proj, setup)
    if release:
        claims.release(setup[0], 'S1-1', 'S2-1', 'agent:worker')
    target = proj.root / setup[2] if change == 'source' else setup[4]
    target.write_text(target.read_text(encoding='utf-8').replace('整理', '修改'), encoding='utf-8')
    action = dispatch.next_task(setup[0], proj, 'agent:worker')
    assert action['task'] is None and '重新派活' in action['reason']
    assert claims.of(setup[0], 'agent:worker') == []


def test_completed_assigned_task_is_not_executed_again(proj, setup):
    point(proj, setup)
    claims.release(setup[0], 'S1-1', 'S2-1', 'agent:worker')
    setup[4].write_text(setup[4].read_text(encoding='utf-8').replace('没做', '做完（J1）'), encoding='utf-8')
    assert dispatch.next_task(setup[0], proj, 'agent:worker')['task'] is None


@pytest.mark.parametrize('restricted', ['paused', 'craft', 'scope', 'blocked'])
def test_recovery_still_obeys_current_employee_permissions(proj, setup, restricted):
    point(proj, setup)
    conn, worker = setup[:2]
    claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    if restricted == 'blocked':
        autolaunch.write_runner_state(proj, worker['code'], 'idle', blocked=['submit_plan:S1-1:S2-1'])
    else:
        field = {'paused': {'paused': True}, 'craft': {'crafts': ['网页']}, 'scope': {'scope': ['其他模块']}}[restricted]
        agents.configure(conn, proj, worker['code'], field, by='人', authorization='临时测试人的授权')
    assert dispatch.next_task(conn, proj, 'agent:worker')['task'] is None
    assert claims.of(conn, 'agent:worker') == []


def test_other_employee_keeps_mutex_during_recovery(proj, setup):
    point(proj, setup)
    conn = setup[0]
    claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    claims.claim(conn, 'S1-1', 'S2-1', 'agent:other', ['S1-1 S2-1'])
    assert dispatch.next_task(conn, proj, 'agent:worker')['task'] is None
    assert claims.active(conn)[0]['agent'] == 'agent:other'


def test_corrupt_assignment_is_reported_instead_of_treated_as_no_authority(proj, setup):
    point(proj, setup)
    claims.release(setup[0], 'S1-1', 'S2-1', 'agent:worker')
    f = proj.root / assignments.DIR / (setup[1]['code'] + '.json')
    f.write_text('{broken', encoding='utf-8')
    action = dispatch.next_task(setup[0], proj, 'agent:worker')
    assert action['task'] is None and '接续记录读不了' in action['reason']


def test_source_cannot_authorize_another_employee_or_operator(proj, setup):
    conn, worker, source, revision, _ = setup
    with pytest.raises(store.Refused, match='匹配'):
        assignments.record(proj, worker, 'S1-1', 'S2-1', by='agent:worker',
                           authorization_path=source, authorization_revision=revision, reason='自说自话')
    assert assignments.listing(proj, worker) == []


def test_actual_mcp_only_trusted_assignment_writes_recovery_source(proj, setup):
    conn, worker, source, _, _ = setup
    agents.create(conn, proj, 'boss', program='Codex')

    async def assign(trusted):
        args = [str(BACKEND / 'mcp_server.py'), '--project', str(proj.root), '--agent', 'boss']
        if trusted:
            args += ['--configuration-authorization', source]
        params = StdioServerParameters(command=sys.executable, args=args)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, client_info=Implementation(name='boss', version='test')) as session:
                await session.initialize()
                return await session.call_tool('assign_employee_task', {'key': worker['code'], 'goal': 'S1-1', 'sub': 'S2-1',
                    'authorization_path': source, 'reason': '经真实配置MCP保存人的派活来源'})

    refused = anyio.run(assign, False)
    assert refused.isError and assignments.listing(proj, worker) == []
    assert claims.of(conn, 'agent:worker') == []
    accepted = anyio.run(assign, True)
    assert not accepted.isError, accepted
    saved = assignments.listing(proj, worker)
    assert saved[0]['by'] == 'agent:boss' and saved[0]['authorization_path'] == source
    claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    assert dispatch.next_task(conn, proj, 'agent:worker')['task']['sub'] == 'S2-1'


@pytest.mark.parametrize('change', ['revoked', 'source', 'task'])
def test_actual_mcp_invalid_assignment_cannot_be_reclaimed_but_trusted_reassignment_recovers(proj, setup, change):
    from test_automation_mcp import call
    conn, worker, source, revision, goal = setup
    agents.create(conn, proj, 'boss', program='Codex')
    point(proj, setup)
    claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    if change == 'revoked':
        assignments.revoke(proj, worker, by='agent:boss', authorization_path=source,
                           authorization_revision=revision, reason='人已撤回旧派活')
    else:
        target = proj.root / source if change == 'source' else goal
        target.write_text(target.read_text(encoding='utf-8').replace('整理', '调整'), encoding='utf-8')
    saved = proj.root / assignments.DIR / (worker['code'] + '.json')
    before = saved.read_bytes()
    result = anyio.run(call, proj, 'worker', [('claim_task', {'goal': 'S1-1', 'sub': 'S2-1'})])
    assert '没领到' in result[0][1], result[0][1]
    assert '重新派活' in result[0][1] or '新授权' in result[0][1]
    assert claims.of(conn, 'agent:worker') == [] and saved.read_bytes() == before
    # 人可以以当前授权重新点名，旧拒绝不是永久禁止；未定稿目标也可以点名。
    renewed = anyio.run(call, proj, 'boss', [('assign_employee_task', {
        'key': worker['code'], 'goal': 'S1-1', 'sub': 'S2-1', 'authorization_path': source,
        'reason': '人的当前授权重新点名',
    })], source)
    assert not renewed[0][0], renewed
    assert not assignments.listing(proj, worker)[0].get('revoked')
    claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    accepted = anyio.run(call, proj, 'worker', [('claim_task', {'goal': 'S1-1', 'sub': 'S2-1'})])
    assert '领了 S1-1 S2-1' in accepted[0][1]
    assert claims.of(conn, 'agent:worker')[0]['sub'] == 'S2-1'


def test_actual_mcp_managed_manual_claim_without_assignment_record_stays_compatible(proj, setup):
    from test_automation_mcp import call
    conn, worker = setup[:2]
    assert assignments.listing(proj, worker) == []
    result = anyio.run(call, proj, 'worker', [('claim_task', {'goal': 'S1-1', 'sub': 'S2-1'})])
    assert '领了 S1-1 S2-1' in result[0][1]
    assert claims.of(conn, 'agent:worker')[0]['sub'] == 'S2-1'
    assert assignments.listing(proj, worker) == []


def test_actual_mcp_auto_only_employee_cannot_reclaim_revoked_assignment(proj, setup):
    from test_automation_mcp import call
    conn, worker, source, revision, _ = setup
    point(proj, setup)
    claims.release(conn, 'S1-1', 'S2-1', 'agent:worker')
    assignments.revoke(proj, worker, by='agent:boss', authorization_path=source,
                       authorization_revision=revision, reason='人已撤回旧派活')
    agents.update(conn, proj, worker['code'], {'auto': True, 'plan_required': False}, by='人')
    result = anyio.run(call, proj, 'worker', [('claim_task', {'goal': 'S1-1', 'sub': 'S2-1'})])
    assert '没领到' in result[0][1] and '已撤销' in result[0][1]
    assert claims.of(conn, 'agent:worker') == []
