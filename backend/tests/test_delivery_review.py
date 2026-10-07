"""独立验收的旧调用兼容、认领边界与等写锁期间的真实状态变化。"""
from contextlib import contextmanager

import pytest

import agents
import blueprint
import claims
import deliveries
import store
import workorders


CHECKS = [{"name": "实际复跑", "ok": True, "detail": "文件内容符合验收要求"}]


@pytest.fixture
def setup(proj, monkeypatch):
    goal = proj.root / "治理/目标/S1-1 样板.md"
    goal.parent.mkdir(parents=True)
    goal.write_text("# S1-1 样板\n\n**样板目标。**\n\n"
                    "| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n"
                    "| S2-1 | 〔程序〕修改文件 | 内容符合验收要求 | 没做 |\n", encoding="utf-8")
    conn = store.connect(proj.db_path)
    agents.create(conn, proj, "writer", roles=["干活"])
    agents.create(conn, proj, "reviewer", roles=["验收"])
    agents.create(conn, proj, "other", roles=["验收"])
    monkeypatch.setattr(deliveries, "_book", lambda *a, **kw: None)
    j = deliveries.deliver(conn, proj, goal="S1-1", sub="S2-1", did="完成样板文件", checks=CHECKS, by="agent:writer")
    assert j["state"] == "等验收"
    yield conn, j
    conn.close()


def _claim(conn, code, name="reviewer"):
    return claims.claim(conn, "验收", code, "agent:" + name, ["验收 " + code])


def _raw(proj, j):
    return (proj.root / deliveries.DIR / j["file"]).read_bytes()


def _review(conn, proj, j, ok=True, checks=None):
    return deliveries.review(conn, proj, j["code"], ok, "实际看到了结果" if ok else "发现结果不符", by="agent:reviewer", checks=checks)


def _before_write_lock(monkeypatch, change):
    """模拟初读以后、取得写锁以前发生的操作，用真实文件和员工更新。"""
    original = store.tx
    pending = True

    @contextmanager
    def tx(conn):
        nonlocal pending
        if pending:
            pending = False
            change()
        with original(conn):
            yield conn

    monkeypatch.setattr(store, "tx", tx)


@pytest.mark.parametrize("ok, expected", [(True, "验收通过"), (False, "打回")])
def test_legacy_reviewer_can_review_without_checks_or_claim(proj, setup, ok, expected):
    conn, j = setup
    result = _review(conn, proj, j, ok=ok)
    assert result["state"] == expected
    assert "## 验收复跑" not in result["body"]
    assert claims.active(conn) == []


@pytest.mark.parametrize("ok", [True, False])
def test_other_reviewer_claim_blocks_writes_and_is_not_released(proj, setup, ok):
    conn, j = setup
    _claim(conn, j["code"], "other")
    before = _raw(proj, j)
    with pytest.raises(store.Refused, match="其他员工"):
        _review(conn, proj, j, ok=ok, checks=CHECKS)
    assert _raw(proj, j) == before
    assert claims.of(conn, "agent:other")[0]["sub"] == j["code"]


@pytest.mark.parametrize("key, fields", [("reviewer", {"auto": True}), ("reviewer", {"plan_required": True}), ("writer", {"plan_required": True})])
def test_managed_acceptance_requires_own_claim_and_actual_passing_checks(proj, setup, key, fields):
    conn, j = setup
    agents.update(conn, proj, key, fields, by="人")
    before = _raw(proj, j)
    with pytest.raises(store.Refused, match="先认领"):
        _review(conn, proj, j, checks=CHECKS)
    _claim(conn, j["code"])
    with pytest.raises(store.Refused, match="实际复跑"):
        _review(conn, proj, j)
    with pytest.raises(store.Refused, match="复跑有失败"):
        _review(conn, proj, j, checks=[{"name": "实际复跑", "ok": False}])
    assert _raw(proj, j) == before
    assert _review(conn, proj, j, checks=CHECKS)["state"] == "验收通过"
    assert claims.of(conn, "agent:reviewer") == []


def test_managed_rejection_also_requires_own_claim(proj, setup):
    conn, j = setup
    agents.update(conn, proj, "reviewer", {"auto": True}, by="人")
    with pytest.raises(store.Refused, match="先认领"):
        _review(conn, proj, j, ok=False)
    _claim(conn, j["code"])
    assert _review(conn, proj, j, ok=False)["state"] == "打回"
    assert claims.of(conn, "agent:reviewer") == []


@pytest.mark.parametrize("fields, reason", [({"paused": True}, "暂停"), ({"roles": ["干活"]}, "岗位"), ({"scope": ["S1-2"]}, "范围"), ({"crafts": ["网页"]}, "工种")])
def test_employee_changes_while_waiting_for_write_lock_are_rechecked(proj, setup, monkeypatch, fields, reason):
    conn, j = setup
    _claim(conn, j["code"])
    before = _raw(proj, j)
    _before_write_lock(monkeypatch, lambda: agents.update(conn, proj, "reviewer", fields, by="人"))
    with pytest.raises(store.Refused, match=reason):
        _review(conn, proj, j, checks=CHECKS)
    assert _raw(proj, j) == before
    assert claims.of(conn, "agent:reviewer")[0]["sub"] == j["code"]


def test_project_pause_while_waiting_for_write_lock_blocks_result(proj, setup, monkeypatch):
    conn, j = setup
    before = _raw(proj, j)
    _before_write_lock(monkeypatch, lambda: store._set_meta(conn, workorders.PAUSE, "人刚叫停"))
    with pytest.raises(store.Refused, match="暂停"):
        _review(conn, proj, j, checks=CHECKS)
    assert _raw(proj, j) == before


def test_claim_taken_while_waiting_for_write_lock_cannot_be_overwritten(proj, setup, monkeypatch):
    conn, j = setup
    before = _raw(proj, j)
    _before_write_lock(monkeypatch, lambda: _claim(conn, j["code"], "other"))
    with pytest.raises(store.Refused, match="其他员工"):
        _review(conn, proj, j, checks=CHECKS)
    assert _raw(proj, j) == before
    assert claims.of(conn, "agent:other")[0]["sub"] == j["code"]


def test_delivery_accepted_while_waiting_for_write_lock_is_not_reviewed_twice(proj, setup, monkeypatch):
    conn, j = setup
    accepted = {}

    def accept():
        deliveries.accept(conn, proj, j["code"])
        accepted["raw"] = _raw(proj, j)

    _before_write_lock(monkeypatch, accept)
    with pytest.raises(store.Refused, match="不用验"):
        _review(conn, proj, j, checks=CHECKS)
    assert _raw(proj, j) == accepted["raw"]
    assert deliveries.get(proj, j["code"])["body"].count("验收通过") == 1
    assert blueprint.find(blueprint.pyramid(proj), "S1-1")["subs"][0]["status"] == "ok"


def test_release_after_review_only_releases_own_claim(proj, setup, monkeypatch):
    conn, j = setup
    _claim(conn, j["code"])
    original = claims.release

    def release(c, goal, sub, agent="", note=""):
        if goal == "验收" and sub == j["code"]:
            assert agent == "agent:reviewer"
            original(c, goal, sub, "agent:reviewer", "模拟提交后的锁交接")
            _claim(c, sub, "other")
        return original(c, goal, sub, agent, note)

    monkeypatch.setattr(claims, "release", release)
    assert _review(conn, proj, j, checks=CHECKS)["state"] == "验收通过"
    assert claims.of(conn, "agent:other")[0]["sub"] == j["code"]


def _legacy_failed(proj, j):
    f = proj.root / deliveries.DIR / j['file']
    text = f.read_text(encoding='utf-8').replace('状态: 等验收', '状态: 待你验收').replace('自查全过: 是\n', '')
    text = text.replace('- 过了 · 实际复跑：文件内容符合验收要求', '- 没过 · 安装检查：没有实际跑安装')
    f.write_text(text + '\n## 验收复跑（别的旧记录）\n\n- 过了 · 安装检查：不能代替原失败\n', encoding='utf-8')
    return deliveries.get(proj, j['code'])


@pytest.mark.parametrize('fields', [{'auto': True}, {'plan_required': True}])
def test_existing_managed_failed_record_can_only_be_independently_sent_back(proj, setup, fields):
    conn, j = setup
    agents.update(conn, proj, 'writer', fields, by='人')
    j = _legacy_failed(proj, j)
    assert j['self_checks_passed'] is False and j['self_checks'][0]['name'] == '安装检查'
    assert deliveries.independent_pending(proj, j)
    before = _raw(proj, j)
    with pytest.raises(store.Refused, match='先认领'):
        _review(conn, proj, j, ok=False)
    _claim(conn, j['code'])
    with pytest.raises(store.Refused, match='原交付自查有失败'):
        _review(conn, proj, j, checks=CHECKS)
    assert _raw(proj, j) == before
    result = _review(conn, proj, j, ok=False, checks=[{'name': '安装检查', 'ok': False, 'detail': '实查原检查未完成'}])
    assert result['state'] == '打回' and deliveries.AGENT_NO in result['body']
    assert '没过 · 安装检查：没有实际跑安装' in result['body']
    assert claims.of(conn, 'agent:reviewer') == []


def test_old_failed_record_still_waits_for_human(proj, setup):
    conn, j = setup
    j = _legacy_failed(proj, j)
    assert not deliveries.independent_pending(proj, j)
    with pytest.raises(store.Refused, match='不用验'):
        _review(conn, proj, j, ok=False)
    assert deliveries.get(proj, j['code'])['state'] == '待你验收'


def test_legacy_failed_delivery_keeps_human_gate_even_with_acceptor(proj, setup):
    conn, j = setup
    deliveries.reject(conn, proj, j['code'], '另一个旧流程场景')
    failed = deliveries.deliver(conn, proj, goal='S1-1', sub='S2-1', did='原流程失败', checks=[{'name': '命令', 'ok': False}], by='agent:writer')
    assert failed['state'] == '待你验收' and failed['self_checks_passed'] is False
    assert not deliveries.independent_pending(proj, failed)


def test_existing_managed_failed_record_cannot_be_bypassed_by_repeat_delivery(proj, setup):
    conn, j = setup
    agents.update(conn, proj, 'writer', {'auto': True}, by='人')
    j = _legacy_failed(proj, j)
    before = _raw(proj, j)
    with pytest.raises(store.Refused, match='重复交付'):
        deliveries.deliver(conn, proj, goal='S1-1', sub='S2-1', did='跳过原失败单', checks=CHECKS, by='agent:writer')
    assert _raw(proj, j) == before and len(deliveries.list_all(proj)) == 1


def test_managed_failed_delivery_reject_then_repaired_new_delivery_needs_independent_checks(proj, setup):
    conn, initial = setup
    deliveries.reject(conn, proj, initial['code'], '开始另一个临时场景')
    agents.update(conn, proj, 'writer', {'auto': True, 'roles': ['干活', '验收']}, by='人')
    j = deliveries.deliver(conn, proj, goal='S1-1', sub='S2-1', did='检查失败如实交付',
                           checks=[{'name': '安装检查', 'ok': False, 'detail': '命令失败'}], by='agent:writer')
    assert j['state'] == '等验收' and j['self_checks_passed'] is False
    assert '自查有失败，等独立员工复查并打回' in deliveries.last_note(j)
    assert '自查全过: 否' in _raw(proj, j).decode('utf-8')
    with pytest.raises(store.Refused, match='自己'):
        deliveries.review(conn, proj, j['code'], False, '不能自验', by='agent:writer')
    _claim(conn, j['code'])
    with pytest.raises(store.Refused, match='原交付自查有失败'):
        _review(conn, proj, j, checks=CHECKS)
    assert _review(conn, proj, j, ok=False)['state'] == '打回'
    old = _raw(proj, j)
    repaired = deliveries.deliver(conn, proj, goal='S1-1', sub='S2-1', did='修复后重新检查', checks=CHECKS, by='agent:writer')
    assert repaired['code'] != j['code'] and repaired['state'] == '等验收'
    _claim(conn, repaired['code'])
    with pytest.raises(store.Refused, match='实际复跑'):
        _review(conn, proj, repaired)
    assert _review(conn, proj, repaired, checks=CHECKS)['state'] == '验收通过'
    assert _raw(proj, j) == old


def test_failed_deliveries_after_three_independent_rejections_return_to_human(proj, setup):
    conn, initial = setup
    deliveries.reject(conn, proj, initial['code'], '开始失败次数场景')
    agents.update(conn, proj, 'writer', {'auto': True}, by='人')
    for _ in range(deliveries.MAX_ROUNDS):
        j = deliveries.deliver(conn, proj, goal='S1-1', sub='S2-1', did='真实失败', checks=[{'name': '命令', 'ok': False}], by='agent:writer')
        assert j['state'] == '等验收'
        _claim(conn, j['code'])
        _review(conn, proj, j, ok=False)
    j = deliveries.deliver(conn, proj, goal='S1-1', sub='S2-1', did='仍有失败', checks=[{'name': '命令', 'ok': False}], by='agent:writer')
    assert j['state'] == '待你验收' and not deliveries.independent_pending(proj, j)
    with pytest.raises(store.Refused, match='不用验'):
        _review(conn, proj, j, ok=False)


@pytest.mark.parametrize('change,reason', [('project', '暂停'), ('paused', '暂停'), ('roles', '岗位'), ('scope', '范围'), ('held', '其他员工')])
def test_existing_managed_failed_record_keeps_review_permissions(proj, setup, change, reason):
    conn, j = setup
    agents.update(conn, proj, 'writer', {'auto': True}, by='人')
    j = _legacy_failed(proj, j)
    if change == 'project':
        store._set_meta(conn, workorders.PAUSE, '人叫停')
    elif change == 'held':
        _claim(conn, j['code'], 'other')
    else:
        fields = {'paused': True} if change == 'paused' else {'roles': ['干活']} if change == 'roles' else {'scope': ['S1-2']}
        agents.update(conn, proj, 'reviewer', fields, by='人')
    before = _raw(proj, j)
    with pytest.raises(store.Refused, match=reason):
        _review(conn, proj, j, ok=False)
    assert _raw(proj, j) == before


@pytest.mark.parametrize('new_ok', [True, False])
def test_stale_failed_card_does_not_override_latest_repair_result(proj, setup, new_ok):
    import dispatch
    conn, old = setup
    old = _legacy_failed(proj, old)
    before = _raw(proj, old)
    # 旧接口以前允许重交；迁移后仍保留旧失败卡，不让网页排序重置新结果。
    new = deliveries.deliver(conn, proj, goal='S1-1', sub='S2-1', did='旧流程修复重交', checks=CHECKS, by='agent:writer')
    result = _review(conn, proj, new, ok=new_ok, checks=CHECKS)
    agents.update(conn, proj, 'writer', {'auto': True}, by='人')
    assert deliveries.list_all(proj)[0]['code'] == old['code']
    assert deliveries.latest_by_task(proj)[('S1-1', 'S2-1')]['code'] == result['code']
    assert not deliveries.independent_pending(proj, deliveries.get(proj, old['code']))
    assert dispatch.review_job(conn, proj, 'agent:reviewer') is None
    back = dispatch._sent_back(proj)
    assert bool(back) is not new_ok
    if not new_ok:
        assert back[('S1-1', 'S2-1')]['code'] == new['code']
    assert _raw(proj, old) == before
    with pytest.raises(store.Refused, match='不用验'):
        _review(conn, proj, old, ok=False)


@pytest.mark.parametrize('passed', [False, True])
def test_real_mcp_managed_delivery_receipt_matches_self_checks(proj, passed):
    import anyio
    from test_automation_mcp import call
    goal = proj.root / '治理/目标/S1-1 样板.md'
    goal.parent.mkdir(parents=True)
    goal.write_text('# S1-1 样板\n\n**样板目标。**\n\n'
                    '| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n'
                    '| S2-1 | 〔程序〕写结果 | 实际命令正常退出 | 没做 |\n', encoding='utf-8')
    conn = store.connect(proj.db_path)
    try:
        agents.create(conn, proj, 'worker', roles=['干活'], program='Codex', auto=True)
        agents.create(conn, proj, 'reviewer', roles=['验收'], program='Codex', auto=True)
    finally:
        conn.close()
    results = anyio.run(call, proj, 'worker', [('deliver', {
        'goal': 'S1-1', 'sub': 'S2-1', 'did': '如实记录命令结果',
        'checks': [{'name': '实际命令', 'ok': passed, 'detail': '正常退出' if passed else '命令失败'}],
    })])
    error, receipt = results[0]
    assert not error
    j = deliveries.get(proj, 'J1')
    assert j['state'] == '等验收'
    assert deliveries.self_checks_failed(j) is not passed
    if passed:
        assert '检查全过，等验收的 agent 复跑' in receipt
    else:
        assert '检查全过' not in receipt
        assert '自查有失败' in receipt and '打回' in receipt and '重新交付' in receipt
        assert '原失败检查不能直接判通过' in receipt


@pytest.mark.parametrize('caller, fields', [
    ('writer', {'auto': True}), ('writer', {'plan_required': True}),
    ('reviewer', {'auto': True}), ('reviewer', {'plan_required': True}),
])
@pytest.mark.parametrize('failed', [False, True])
def test_real_mcp_managed_employee_cannot_use_oral_acceptance(proj, setup, caller, fields, failed):
    import anyio
    from test_automation_mcp import call
    conn, j = setup
    agents.update(conn, proj, caller, fields, by='人')
    if failed:
        j = _legacy_failed(proj, j)
    before = _raw(proj, j)
    results = anyio.run(call, proj, caller, [('record_acceptance', {'code': j['code'], 'said': '一段非空文本不能证明人验收过'})])
    assert '没记上' in results[0][1] and '不能用口头验收' in results[0][1]
    assert 'review_delivery' in results[0][1] and '人仍可在网页直接验收' in results[0][1]
    assert _raw(proj, j) == before
    assert deliveries.get(proj, j['code'])['state'] == j['state']
    assert blueprint.find(blueprint.pyramid(proj), 'S1-1')['subs'][0]['status'] != 'ok'


def test_real_mcp_legacy_caller_cannot_orally_pass_managed_delivery(proj, setup):
    import anyio
    from test_automation_mcp import call
    conn, j = setup
    agents.update(conn, proj, 'writer', {'auto': True}, by='人')
    j = _legacy_failed(proj, j)
    before = _raw(proj, j)
    results = anyio.run(call, proj, 'reviewer', [('record_acceptance', {'code': j['code'], 'said': '未经可信来源核验的文本'})])
    assert '不能用口头验收' in results[0][1]
    assert _raw(proj, j) == before


def test_real_mcp_legacy_oral_acceptance_still_compatible(proj, setup):
    import anyio
    from test_automation_mcp import call
    conn, j = setup
    j = _legacy_failed(proj, j)
    results = anyio.run(call, proj, 'reviewer', [('record_acceptance', {'code': j['code'], 'said': 'J1 按旧接口验收'})])
    assert not results[0][0] and '记上了' in results[0][1]
    result = deliveries.get(proj, j['code'])
    assert result['state'] == '验收通过'
    assert '人（对话里说的：「J1 按旧接口验收」，agent:reviewer 记的）' in result['body']


def test_direct_human_acceptance_still_available_for_managed_failed_delivery(proj, setup):
    conn, j = setup
    agents.update(conn, proj, 'writer', {'auto': True}, by='人')
    j = _legacy_failed(proj, j)
    assert deliveries.accept(conn, proj, j['code'], by='人')['state'] == '验收通过'
