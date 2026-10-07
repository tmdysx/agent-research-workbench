"""员工配置、施工计划和外层运行器的 MCP 入口。"""
import json
import os
import re
import agents, board, claims, construction_plans as cp, dispatch, governance, journal, plugins, runs, store, workorders, work_packages
from mcp.server.fastmcp import Context


def authority(project, path, caller, key=''):
    doc = governance.read_document(project, path)
    text = doc['text']
    owners = re.search(r'^> 授权操作者：(.+)$', text, re.M)
    targets = re.search(r'^> 授权对象：(.+)$', text, re.M)
    if not path.startswith('治理/计划/') or '授权：作者本次' not in text or not owners or agents.short(caller) not in agents._split(owners.group(1)):
        raise store.Refused('需要保存的人的明确授权，且授权操作者必须匹配当前身份')
    if key and (not targets or agents.get(project, key)['code'] not in agents._split(targets.group(1))):
        raise store.Refused('这份授权不包括这个员工')
    return path + ' · ' + doc['revision'] + ' · 作者在对话中批准'


def _runner_pid_alive(value) -> bool:
    """只读进程存活；权限不足保守认作仍活着，Windows不用os.kill。"""
    try:
        pid = int(value or 0)
    except (TypeError, ValueError):
        return True
    if pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k.OpenProcess(0x00100000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # INVALID_PARAMETER：进程已不存在。
        try:
            return k.WaitForSingleObject(handle, 0) != 0
        finally:
            k.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def resume_inactive_runners(project, *, restoring: bool, by: str, reason: str, explicit_resume: bool = False) -> list[str]:
    """恢复已退出员工；空闲失败限制需明确恢复，配置更新和活员工不清零。"""
    import autolaunch
    if not restoring:
        return []
    resumed = []
    # 与自动开窗共用短锁，避免筛选之后又被调度器启动的窗口遭到清零。
    with autolaunch._file_lock(project, '自动开工'):
        candidates = [a for a in agents.list_all(project) if a.get('auto') and not a.get('paused')
                      and autolaunch.resumable_state(autolaunch.runner_state(project, a['code']), explicit_resume=explicit_resume)]
        if not candidates:
            return resumed
        try:
            windows = autolaunch.windows(project, require_known=True)
        except Exception:
            return resumed  # 查询失败不能证明窗口已退出，保留全部预算与失败限制。
        alive = {m.group(1) for w in windows if w.get('alive')
                 and (m := re.match(r'^(G\d+)(?:\s|$)', w.get('title', '')))}
        for a in candidates:
            state = autolaunch.runner_state(project, a['code'])
            if a['code'] in alive or not autolaunch.resumable_state(state, explicit_resume=explicit_resume) or _runner_pid_alive(state.get('pid')):
                continue
            autolaunch.resume_runner(project, a['code'], by=by, reason=reason)
            resumed.append(a['code'])
    return resumed


def attach(mcp, project, conn, me, *, configuration_authorization='', runner_control=False):
    # 配置能力在启动连接时授予，普通模型连接不能靠自写授权文字取得权限。
    trusted_revision = governance.read_document(project, configuration_authorization)['revision'] if configuration_authorization else ''
    def authorized(path, caller, key=''):
        if not configuration_authorization or path != configuration_authorization:
            raise store.Refused('本员工连接没有配置授权；需要人的授权配置连接')
        if governance.read_document(project,path)['revision'] != trusted_revision:
            raise store.Refused('授权记录已变化，请核对后重新建立授权配置连接')
        return authority(project,path,caller,key)
    def pack(out):
        return json.dumps(out, ensure_ascii=False)

    @mcp.tool()
    def get_work_package(goal: str, sub: str, plan_code: str = '', skill_ids: list[str] | None = None, lang: str = 'zh') -> str:
        """只读当前项目的编程工作包；明确来源和有效批准范围，不领活、派活或运行工具。"""
        with work_packages.open_read_connection(project) as c:
            return pack(work_packages.build(c, project, goal, sub, plan_code=plan_code, skill_ids=skill_ids, lang=lang))

    @mcp.tool()
    def configure_workflow_graph(code: str, action: str, revision: str, authorization_path: str,
                                 agent: str = '', ctx: Context | None = None) -> str:
        """仅可信人的授权连接能启用/停用流程快照；普通模型只能保存草稿，不能自行启用。"""
        import workflow_graph
        caller = me(ctx, agent)
        source = authorized(authorization_path, caller)
        authorization = governance.read_document(project, authorization_path)['text']
        control_word = '启用' if action == 'enable' else '停用' if action == 'stop' else ''
        if not control_word or '工作流' not in authorization or not re.search(r'(?<![A-Za-z0-9])' + re.escape(code) + r'(?!\d)', authorization) or control_word not in authorization:
            raise store.Refused('授权记录须明确该工作流编号及启用或停用；员工配置授权不能被扩成任意流程启动')
        c = conn()
        try:
            out = workflow_graph.control(c, project, code, action, revision, by=caller)
            journal.add(c, project, f'{action} 工作流 {code}；{source}', by=caller, kind='工作流配置', scope='自动化')
            return pack(out)
        finally:
            c.close()

    @mcp.tool()
    def configure_agent(key: str, fields: dict, authorization_path: str, agent: str = '', ctx: Context | None = None) -> str:
        """按人的已保存授权配置指定员工，记录真实操作者；不得自行提权。"""
        caller = me(ctx, agent)
        source = authorized(authorization_path, caller, key)
        old = agents.get(project, key)
        if old['name'] == agents.short(caller) and (fields.get('core') == '能' and old['core'] != '能' or set(fields.get('roles', [])) - set(agents.jobs(old)) or fields.get('level', old['level']) != old['level']):
            raise store.Refused('员工不能给自己提高核心、岗位或等级权限')
        c = conn()
        try:
            return pack(agents.configure(c, project, key, fields, by=caller, authorization=source))
        finally:
            c.close()

    @mcp.tool()
    def configure_automation(on: bool, max_windows: int, authorization_path: str, round_limit: int = 12, agent: str = '', resume: bool = False, ctx: Context | None = None) -> str:
        """按人的明确授权更新开关、并发和圈数；resume恢复已退出的终态或空闲受限员工，活员工预算不清零。"""
        import autolaunch
        caller = me(ctx, agent)
        source = authorized(authorization_path, caller)
        if not 1 <= round_limit <= 50:
            raise store.Refused('圈数上限 1～50')
        c = conn()
        try:
            restoring = on and (resume or not autolaunch.settings(c)['on'] or bool(workorders.paused(c)))
            if on:
                plugins.set_enabled(c, '网页终端', True)
                workorders.resume(c, by=caller)
                runs.set_settings(c, runs.settings(c)['level'], round_limit)
                wo = workorders.running(project)
                if wo:
                    workorders.update(c, project, wo['code'], {'rounds': round_limit}, by=caller)
                resume_inactive_runners(project, restoring=restoring, by=caller, reason=source, explicit_resume=resume)
            else:
                with store.tx(c):
                    store._set_meta(c, workorders.PAUSE, '按作者授权关闭自动化 · ' + caller)
            out = autolaunch.set_settings(c, on=on, max_=max_windows)
            journal.add(c, project, f'自动开工 {on}，最多 {max_windows} 个；{source}', by=caller, kind='自动化配置', scope='自动化')
            return pack(out)
        finally:
            c.close()

    @mcp.tool()
    def open_employee_window(key: str, authorization_path: str, agent: str = '', ctx: Context | None = None) -> str:
        """启动网页终端中的员工，已经运行的不重复开。"""
        import autolaunch
        caller = me(ctx, agent)
        authorized(authorization_path, caller, key)
        a = agents.get(project, key)
        c = conn()
        try:
            if workorders.paused(c) or a.get('paused'):
                raise store.Refused('项目或员工已暂停')
            plugins.open_page(c, project, '网页终端')
            title = f"{a['code']} {a['name']}"
            old = next((w for w in autolaunch.windows(project) if w['title'] == title and w['alive']), None)
            if old:
                return pack(old)
            launch = agents.launcher(project, key)
            out = autolaunch._call(project, 'POST', '/api/terms', {'title': title, 'cmd': launch['cmd']}
                                  | autolaunch.window_metadata(c, project, a))
            journal.add(c, project, '网页终端启动 ' + title, by=caller, kind='启动员工', scope='自动化')
            return pack(out)
        finally:
            c.close()

    @mcp.tool()
    def next_action(agent: str = '', ctx: Context | None = None) -> str:
        """结构化下一步，与next_task同源；等待时退出模型轮次，由外层运行器接续。"""
        c = conn()
        caller = me(ctx, agent)
        try:
            got = dispatch.next_task(c, project, caller)
            if got.get('task'):
                t = got['task']
                got['why'] = board.why_text(project, t['goal'], t['sub'])
            got['profile'] = agents.brief_text(agents.require(project, caller))
            import autolaunch
            got['limits'] = {'rounds': (got.get('wo') or {}).get('rounds', runs.settings(c)['rounds']), 'failures': (got.get('wo') or {}).get('fails', 2)}
            got['holding'] = claims.of(c, caller)
            got['runtime'] = autolaunch.runner_state(project, agents.require(project, caller)['code'])
            return pack(got)
        finally:
            c.close()

    @mcp.tool()
    def report_employee_runtime(state: dict, agent: str = '', ctx: Context | None = None) -> str:
        """记录本窗口自己的轮次、等待原因和结果；网页、运行器读同一普通文件。"""
        import autolaunch
        if not runner_control:
            raise store.Refused('运行预算和停止状态只由外层运行器记录；模型员工使用add_log记录结果')
        caller = me(ctx, agent)
        a = agents.require(project, caller)
        allowed = {'pid', 'session', 'rounds', 'cycles', 'failure_counts', 'blocked', 'current', 'last_result', 'status', 'reason', 'action'}
        if set(state) - allowed:
            raise store.Refused('只能写本窗口的运行状态字段')
        old = autolaunch.runner_state(project,a['code'])
        if any(int(state.get(k,old.get(k,0))) < int(old.get(k,0)) for k in ('rounds','cycles')):
            raise store.Refused('不能降低已用轮次；恢复需要人的授权入口')
        if not set(old.get('blocked',[])).issubset(state.get('blocked',old.get('blocked',[]))):
            raise store.Refused('不能清除失败限制；恢复需要人的授权入口')
        if old.get('status') in ('stopped','limit','failed') and state.get('status',old['status']) != old['status']:
            raise store.Refused('当前已停止或达到上限，需人明确恢复')
        out = autolaunch.write_runner_state(project,a['code'],**state,by=caller)
        c = conn()
        try:
            claims.beat(c, caller)
            if state.get('last_result') or state.get('status') in ('stopped', 'limit', 'failed'):
                journal.add(c, project, f"{a['code']} {state.get('status','')} · {state.get('last_result') or state.get('reason','')}", by=caller, kind='员工运行', scope='自动化')
        finally:
            c.close()
        return pack(out)

    @mcp.tool()
    def assign_employee_task(key: str, goal: str, sub: str, authorization_path: str, reason: str, agent: str = '', ctx: Context | None = None) -> str:
        """按人的点名施工授权派给员工，仍检查岗位、工种、负责范围和互斥。"""
        import blueprint
        caller=me(ctx,agent)
        source=authorized(authorization_path,caller,key)
        a=agents.get(project,key)
        g=blueprint.find(blueprint.pyramid(project),goal)
        x=next((s for s in (g or {}).get('subs',[]) if s['code']==sub),None)
        if not x or x['status']=='ok' or not x['how'].strip():
            raise store.Refused('点名任务必须存在、未完成且有验收标准')
        why=agents.allows_reason(a,g,x)
        import workflow_graph
        why = why or workflow_graph.worker_reason(project, a, g, x)
        if why or '干活' not in agents.jobs(a):
            raise store.Refused(why or '该员工不承担施工')
        c=conn()
        try:
            if workorders.paused(c):
                raise store.Refused('人已叫停，不再派活')
            actor = agents.actor(a['name'])
            already_held = any(r['goal'] == goal and r['sub'] == sub for r in claims.of(c, actor))
            out=claims.claim(c,goal,sub,agents.actor(a['name']),claims.lanes_of(g,x),x['what'])
            import employee_assignments
            try:
                employee_assignments.record(project, a, goal, sub, by=caller,
                    authorization_path=authorization_path, authorization_revision=trusted_revision, reason=reason)
            except Exception as e:
                if not already_held:
                    claims.release(c, goal, sub, actor, note='派活来源保存失败，撤回本次新认领')
                raise store.Refused('派活来源保存失败；' + ('原有认领保留' if already_held else '本次新认领已撤回') + '：' + str(e)) from e
            journal.add(c,project,f"派 {a['code']} {goal} {sub}：{reason}；{source}",by=caller,kind='派活',scope='自动化')
            return pack(out)
        finally:
            c.close()

    @mcp.tool()
    def reassign_employee_work(key: str, authorization_path: str, reason: str, agent: str = '', ctx: Context | None = None) -> str:
        """按人的明确授权接手旧员工：留认领清单与来源，再释放供符合岗位的员工领取。"""
        caller = me(ctx, agent)
        source = authorized(authorization_path, caller, key)
        old = agents.get(project, key)
        c = conn()
        try:
            held = claims.of(c, agents.actor(old['name']))
            import employee_assignments
            revoked = employee_assignments.revoke(project, old, by=caller,
                authorization_path=authorization_path, authorization_revision=trusted_revision, reason=reason)
            detail = {'from': old['code'], 'claims': held, 'revoked_assignments': revoked,
                      'reason': reason, 'authorization': source, 'by': caller}
            journal.add(c, project, '接手旧员工 ' + pack(detail), by=caller, kind='员工接手', scope='自动化')
            for row in held:
                claims.release(c, row['goal'], row['sub'], row['agent'], reason + '；操作者 ' + caller + '；' + source)
            return pack(detail)
        finally:
            c.close()

    @mcp.tool()
    def submit_execution_plan(goal: str, sub: str, text: str, files: list[str], revision: str = '', agent: str = '', ctx: Context | None = None) -> str:
        """提交或修订施工计划，修订带原revision；待审时不施工。"""
        c = conn()
        try:
            return pack(cp.submit(c, project, goal, sub, me(ctx, agent), text, files, revision))
        finally:
            c.close()

    @mcp.tool()
    def get_execution_plan(code: str = '') -> str:
        """读施工计划全文、版本、允许修改范围及审核记录。"""
        return pack(cp.get(project, code) if code else cp.listing(project))

    @mcp.tool()
    def review_execution_plan(code: str, ok: bool, why: str, revision: str, agent: str = '', ctx: Context | None = None) -> str:
        """审核别人的施工计划，带原revision；不审自己的。"""
        c = conn()
        try:
            return pack(cp.review(c, project, code, me(ctx, agent), ok, why, revision))
        finally:
            c.close()

    @mcp.tool()
    def write_handover(text: str, agent: str = '', ctx: Context | None = None) -> str:
        """写七项接手摘要，普通文件保存，机器日志与人的笔记分开。"""
        from datetime import datetime
        caller = me(ctx, agent)
        d = project.root / '自动化' / '交接'
        d.mkdir(parents=True, exist_ok=True)
        nums = [int(m.group(1)) for f in d.glob('H*.md') if (m := re.match(r'H(\d+)', f.name))]
        code = 'H' + str(max(nums, default=0) + 1)
        safe = re.sub(r'[\\/:*?"<>|]', '-', agents.short(caller))
        f = d / f'{code} · {datetime.now():%Y-%m-%d} · {safe}.md'
        with f.open('x', encoding='utf-8') as out:
            out.write(f'# {code} · {datetime.now():%Y-%m-%d} · {safe}\n\n{text}\n')
        c = conn()
        try:
            journal.add(c, project, f'写了 {f.relative_to(project.root).as_posix()}', by=caller, kind='交接', scope='自动化')
        finally:
            c.close()
        return f.relative_to(project.root).as_posix()
