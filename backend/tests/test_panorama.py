"""临时活动项目验证蓝图：明确多对多、缺项、真实验收状态、计划来源与 MCP 共用。"""
import anyio
from fastapi.testclient import TestClient

import deliveries
import store
from main import create_app
from test_mcp import _call


def put(p, path, text):
    f = p.root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")


def setup(p):
    put(p, "资料/蓝图/S0 终极目标.md", "# S0\n**办一场社区活动。**\n")
    put(p, "资料/蓝图/S1-1 场地.md", "# S1-1\n**备好场地。**\n动到的模块：场地、报名\n"
        "| | 做什么 | 状态 |\n|---|---|---|\n| S2-1 | 联系场地 | 做完（人验收） |\n| S2-2 | 核对设备 | 待你验收（J1） |\n")
    put(p, "资料/蓝图/S1-2 招募.md", "# S1-2\n**招募参加者。**\n| S2-1 | 准备名单 | 在做 |\n")
    put(p, "资料/报名/需求.md", "# 报名\n**报名清楚。**\n为了：S1-2、S1-1\n")
    put(p, "资料/报名/蓝图.md", "# 报名\n| S2-1 | 名单表 | 待你验收 |\n")
    put(p, "资料/场地/说明.md", "只是提到 S1-2 和报名，不是关联记录。")
    put(p, "资料/餐饮/说明.md", "没有需求和蓝图")
    put(p, "计划/S1-2 招募/P1 · 2026-09-28 · 联系.md", "# 计划\n目标：S1-2 · 动到的模块：报名 · 状态：在做\n\n正文里提及场地。")
    put(p, "计划/S1-2 招募/P2 · 2026-09-30 · 名单.md", "> 目标：S1-2 · 动到的模块：报名 · 状态：在做\n")
    put(p, "自动化/交付/J1 S1-1 S2-2.md", "---\n编号: J1\n目标: S1-1\n小目标: S2-2\n状态: 待你验收\n---\n# J1\n")


def test_many_to_many_missing_records_and_chronological_plans(proj):
    setup(proj)
    with TestClient(create_app(proj)) as c:
        state = c.get('/api/state').json()
        v = state['panorama']
        goals = {g['code']: g for g in v['goals']}
        mods = {m['name']: m for m in v['modules']}
        assert goals['S1-1']['related_modules'] == ['场地', '报名']
        assert set(mods['报名']['goals']) == {'S1-1', 'S1-2'}
        assert mods['餐饮']['missing'] == ['缺需求', '缺蓝图', '未关联']
        assert mods['场地']['goals'] == ['S1-1']  # 正文出现的目标不算关系
        assert [x['code'] for x in mods['报名']['plans']] == ['P2', 'P1']
        assert mods['场地']['plans'] == []  # 正文出现模块名不算计划范围
        assert v['counts'] == dict(done=1, pending=1, doing=1, partial=0, todo=0)
        assert mods['报名']['tasks'][0]['text'] == '待你验收'
        assert len(v['status']['deliveries']) == 1
        assert v['s0']['one_line'] == '办一场社区活动'
        assert {'测试', '文献', '论文'} <= set(mods)  # 10-06 起这三个也是固定模块（通用工作台，不带科研专属负载）
        rel = next(x for x in v['relations'] if x['goal'] == 'S1-1' and x['module'] == '报名')
        assert {x['field'] for x in rel['sources']} == {'动到的模块', '为了'}
        assert state['blueprint'][0]['modules'] == ['场地', '报名']  # 原有接口字段不变
        assert c.get('/api/modules/蓝图/tree').json()['default'] == '#项目全景'
        assert c.get('/api/modules/蓝图/preview', params={'path': 'S0 终极目标.md'}).status_code == 200
        assert c.get('/api/plans').status_code == 200


def test_unconfirmed_unknown_and_template_links_are_not_invented(proj):
    setup(proj)
    put(proj, '资料/餐饮/需求.md', '为了：S1-1（我猜的，等你定）\n')
    put(proj, '资料/未定/需求.md', '为了：（总蓝图里的哪几件，写 S1 编号，比如 S1-1、S1-4）\n')
    put(proj, '资料/场地/需求.md', '为了：S1-99\n')
    with TestClient(create_app(proj)) as c:
        v = c.get('/api/state').json()['panorama']
    mods = {m['name']: m for m in v['modules']}
    assert mods['餐饮']['goals'] == [] and mods['餐饮']['relation_notes']
    assert mods['未定']['goals'] == []
    assert any('S1-99' in x for x in v['problems'])


def test_explicit_all_modules_and_plan_headers_have_sources(proj):
    setup(proj)
    put(proj, '资料/蓝图/S1-3 协作.md', '动到的模块：所有模块（本项目）、场地\n')
    put(proj, '计划/S1-2 招募/P3 · 2026-09-30 · 布置.md', '> S1-2 · P3 · 目标：S1-2 · 动到的模块：场地 · 报名 · 状态：在做\n')
    with TestClient(create_app(proj)) as c:
        v = c.get('/api/state').json()['panorama']
    goals = {g['code']: g for g in v['goals']}
    assert set(goals['S1-3']['related_modules']) == {m['key'] for m in v['modules'] if m['kind'] == 'project'}
    rel = next(x for x in v['relations'] if x['goal'] == 'S1-2' and x['module'] == '场地')
    assert rel['sources'][0]['file'].endswith('布置.md')


def test_mcp_reads_the_same_relations_and_pending_state(proj):
    setup(proj)
    (overview,) = anyio.run(_call, proj, [('get_overview', {})])
    assert '办一场社区活动' in overview
    assert 'S1-1 → 场地、报名；做完 1，待你验收 1' in overview
    assert '模块 餐饮 → 未关联；缺需求、缺蓝图、未关联' in overview
    assert '资料/报名/需求.md · 为了' in overview
    assert 'P2 · 2026-09-30 · 名单.md' in overview


def test_delivery_cannot_attach_to_an_unrelated_running_order(proj, monkeypatch):
    setup(proj)
    import workorders
    monkeypatch.setattr(workorders, 'running', lambda p: {'code': 'K9', 'target': ['S1-2']})
    c = store.connect(proj.db_path)
    try:
        j = deliveries.deliver(c, proj, goal='S1-1', sub='S2-2', did='核对设备', checks=[{'name': '开机', 'ok': True}])
        assert j['workorder'] == ''
        monkeypatch.setattr(workorders, 'running', lambda p: {'code': 'K9', 'target': ['S1-1 S2-2']})
        j = deliveries.deliver(c, proj, goal='S1-1', sub='S2-2', did='核对设备', checks=[{'name': '开机', 'ok': True}])
        assert j['workorder'] == 'K9'
    finally:
        c.close()


def test_common_layer_sits_above_shared_and_business_without_fake_folders(proj):
    setup(proj)
    put(proj, '资料/计划/说明.md', '一个恰好也叫计划的 DIY 模块。')
    f = proj.materials / '蓝图/S1-2 招募.md'
    f.write_text(f.read_text(encoding='utf-8') + '\n动到的模块：通用/计划、笔记本、计划\n', encoding='utf-8')
    with TestClient(create_app(proj)) as c:
        s = c.get('/api/state').json()
        v = s['panorama']
        assert [l['key'] for l in v['layers']] == ['common', 'shared', 'business']
        layers = {l['key']: l['modules'] for l in v['layers']}
        assert 'common:plans' in layers['common'] and '计划' in layers['business']
        assert set(layers['shared']) == {'想法', '蓝图', '戒律', '源代码', '测试', '文献', '论文'}   # 固定七个（10-06 起）
        mods = {m['key']: m for m in v['modules']}
        assert mods['common:notes']['href'] == '#/notes'
        assert mods['common:notes']['goals'] == ['S1-2']
        assert mods['common:plans']['goals'] == ['S1-2']
        assert mods['计划']['goals'] == ['S1-2']
        assert mods['common:saves']['missing'] == ['未关联', '缺需求']
        assert all(not m['name'].startswith('common:') for m in s['modules'])
        assert not (proj.materials / '笔记本').exists()
    (overview,) = anyio.run(_call, proj, [('get_overview', {})])
    assert overview.index('通用操作层：') < overview.index('项目交集层：') < overview.index('DIY 业务层：')
    assert '笔记本' in overview and '餐饮' in overview
