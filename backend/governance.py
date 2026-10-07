"""目标、共享需求、适用戒律和执行记录的统一只读视图。"""
from __future__ import annotations

import re
import hashlib
import atomic
import os
import blueprint
import files
import governance_paths as gp
import project
import requirements


def module_catalog(p):
    from panorama import COMMON
    return [{'key': n, 'name': n, 'available': True} for n in sorted(project.module_dirs(p))] + [
        {'key': 'common:' + ident, 'name': '通用/' + name, 'available': True} for ident, name, en, href in COMMON]


def normalize_module(p, name):
    options = module_catalog(p)
    return next((x['key'] for x in options if x['key'] == name), next((x['key'] for x in options if x['name'] == name), name))


def validate_links(p, goals, modules):
    import store
    known_goals = {g['code'] for g in blueprint.pyramid(p)['goals']}
    known_modules = {m['key'] for m in module_catalog(p)}
    for g in goals:
        if g not in known_goals:
            raise store.Refused(f'找不到目标 {g}')
    for m in modules:
        if normalize_module(p, m) not in known_modules:
            raise store.Refused(f'找不到承接模块 {m}；可以先留空')


def catalog(p, bp=None):
    out = requirements.catalog(p, bp)
    available = {m['key'] for m in module_catalog(p)}
    known_goals = {g['code'] for g in (bp or blueprint.pyramid(p))['goals']}
    for q in out:
        q['modules'] = list(dict.fromkeys(normalize_module(p, m) for m in q['modules']))
        q['missing_modules'] = [m for m in q['modules'] if m not in available]
        q['missing_goals'] = [g for g in q['goals'] if g not in known_goals]
    return out


def doc(p, rel, title='', layer=''):
    f = gp.resolve(p, rel)
    try:
        text = f.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return {'file': rel, 'title': title or rel, 'layer': layer, 'text': '', 'missing': True}
    return {'file': gp.relative(p, f), 'title': title or f.stem, 'layer': layer, 'text': text, 'missing': False,
            'revision': hashlib.sha256(f.read_bytes()).hexdigest()}


def edit_path(p, path):
    """只允许治理正文；日志、笔记、代码和迁移清单不能经此入口改写。"""
    rel = gp.central(path)
    f = gp.safe(p, rel)
    parts = f.relative_to(p.root.resolve()).parts
    if len(parts) < 3 or parts[0] != gp.ROOT or parts[1] not in ('目标', '需求', '戒律', '任务', '计划') or f.suffix.lower() != '.md':
        raise ValueError('这里只能编辑治理区的目标、需求、戒律、任务和计划 Markdown 文件')
    if any(x.startswith('.') for x in parts):
        raise ValueError('不支持隐藏路径')
    return f


def read_document(p, path):
    f = edit_path(p, path)
    found = gp.resolve(p, path)
    d = doc(p, gp.relative(p, found)) if found.is_file() else doc(p, gp.relative(p, f))
    d['revision'] = d.get('revision', '')
    d['editable'] = True
    d['save_path'] = gp.relative(p, f)
    return d


def save_document(conn, p, path, text, revision, *, by, reason=''):
    import store
    import journal
    f = edit_path(p, path)
    if not isinstance(text, str) or len(text.encode('utf-8')) > 1024 * 1024:
        raise ValueError('正文须为文字，且不超过 1 MB')
    f.parent.mkdir(parents=True, exist_ok=True)
    lock = f.with_suffix('.md.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise store.Refused('文件正在保存，请重新读取后重试')
    os.close(fd)
    try:
        current = read_document(p, path)
        if current['revision'] != revision:
            raise store.Refused('内容已被别人修改；你的输入保留，请重新读取对照后再保存')
        if by.startswith('agent'):
            old = {x['code']: x['status'] for x in blueprint._subs(current['text'].splitlines())}
            if any(x['status'] == 'ok' and old.get(x['code']) != 'ok' for x in blueprint._subs(text.splitlines())):
                raise store.Refused('agent 不能自行标做完；请用 deliver 交付，等人验收')
        tmp = f.with_suffix('.md.tmp')
        tmp.write_text(text, encoding='utf-8')
        atomic.replace(tmp, f)
        if f.parent == (p.root / gp.ROOT / '戒律').resolve() and f.name.startswith(('1 ', '2 ')):
            agents = p.root / 'AGENTS.md'
            if agents.is_file():
                summary = agents.read_text(encoding='utf-8')
                for line in text.splitlines():
                    cells = [c.strip() for c in line.strip().strip('|').split('|')]
                    if len(cells) >= 2 and re.fullmatch(r'(通|项)-\d+', cells[0]):
                        summary = re.sub(r'^- ' + re.escape(cells[0]) + r' .*$', lambda m: '- ' + cells[0] + ' ' + cells[1], summary, flags=re.M)
                agents.write_text(summary, encoding='utf-8')
        journal.add(conn, p, (reason + '；' if reason else '') + gp.relative(p, f), by=by, kind='修改了治理正文', scope='蓝图')
    finally:
        lock.unlink(missing_ok=True)
    return read_document(p, gp.relative(p, f))


def draft(p, kind, module='', goal=''):
    """点击新建只生成草稿，保存才落盘。"""
    from datetime import date
    from panorama import COMMON
    scope = module or '项目'
    module = normalize_module(p, module) if module else ''
    if module and module not in {m['key'] for m in module_catalog(p)}:
        raise ValueError('找不到模块')
    if goal and goal not in {g['code'] for g in blueprint.pyramid(p)['goals']}:
        raise ValueError('找不到目标')
    if kind == '需求':
        path = f'治理/需求/{gp.file_name(scope)}.md'
        text = f'# {scope} · 需求\n\n为了：{goal}\n承接模块：{module}\n\n| | 要什么功能 | 要什么效果（验收标准） | 来自 |\n|---|---|---|---|\n| 需-1 |  |  | 网页手写 |\n'
    elif kind == '戒律':
        path = f'治理/戒律/模块/{gp.file_name(scope)}.md'
        text = f'# {scope} · 适用戒律\n\n| | 规矩 | 从哪来 |\n|---|---|---|\n'
    elif kind == '任务':
        path = f'治理/任务/{gp.file_name(scope)}.md'
        text = f'# {scope} · 任务\n\n动到的模块：{module}\n怎么算装好：\n\n| | 做什么 | 为了 | 怎么验 | 状态 |\n|---|---|---|---|---|\n| S2-1 |  |  |  | 没做 |\n'
    elif kind == '计划':
        scope = goal or module or 'S0 总体'
        existing = [x for x in plan_records(p) if x['goal'].split(' ')[0] == scope]
        num = max([int(x['code'][1:]) for x in existing if re.fullmatch(r'P\d+', x['code'])], default=0) + 1
        folder = next((x['goal'] for x in existing), scope)
        path = f'治理/计划/{gp.file_name(folder)}/P{num} · {date.today().isoformat()} · 新计划.md'
        text = f'# P{num} · 新计划\n\n目标：{goal} · 守的戒律： · 动到的模块：{module} · 状态：草稿\n\n## 要做什么\n\n## 怎样验收\n'
    else:
        raise ValueError('新建类型写需求、戒律、任务或计划')
    d = read_document(p, path)
    if d['missing']:
        d['text'] = text
    return d


def rule_docs(p, modules):
    out = [doc(p, 'AGENTS.md', '接手规则', '接手')]
    for layer, pre in (('通用', '1 '), ('项目', '2 ')):
        fs = [f for f in gp.rule_files(p) if f.name.startswith(pre)]
        out += [doc(p, gp.relative(p, f), layer + '戒律', layer) for f in fs] or [
            {'file': '', 'title': layer + '戒律', 'layer': layer, 'text': '', 'missing': True}]
    out += [doc(p, gp.relative(p, gp.module_rule(p, m)), m + ' · 适用戒律', '模块') for m in modules]
    return out


def plan_records(p):
    from panorama import _field, _names, _text, _TENTATIVE
    out = []
    for group in files.plans(p):
        for item in group.get('children', [group]):
            text = _text(p, item['path'])
            goals = re.findall(r'\bS1-\d+\b', _field(text, '目标'))
            match = re.match(r'S1-\d+', item['goal'])
            if match:
                goals.append(match.group())
            raw = _field(text, '动到的模块')
            mods = [] if _TENTATIVE.search(raw) else [normalize_module(p, m) for m in _names(raw)]
            if '所有模块' in mods:
                mods = [m for m in mods if m != '所有模块'] + list(project.module_dirs(p))
            if item['goal'] in project.module_dirs(p):
                mods.append(item['goal'])
            out.append(dict(item, goals=list(dict.fromkeys(goals)), modules=list(dict.fromkeys(mods))))
    return sorted(out, key=lambda x: (x['date'], x['mtime']), reverse=True)


def detail(p, kind='module', key=''):
    import deliveries
    import journal
    import workorders
    bp = blueprint.pyramid(p)
    all_req = catalog(p, bp)
    all_plans = plan_records(p)
    selected_goals, mods, selected = [], [], []
    if kind == 'module':
        key = normalize_module(p, key)
        mods = [key]
        selected = [q for q in all_req if key in q['modules']]
        selected_goals = [g for g in bp['goals'] if key in [normalize_module(p, m) for m in g['modules']]]
        linked = {g for x in all_plans if key in x['modules'] and x['code'].startswith('P') for g in x['goals']}
        selected_goals += [g for g in bp['goals'] if g['code'] in linked and g not in selected_goals]
    elif kind == 'goal':
        selected_goals = [g for g in bp['goals'] if g['code'] == key]
        selected = [q for q in all_req if key in q['goals']]
        mods = [normalize_module(p, m) for g in selected_goals for m in g['modules']]
        mods += [m for x in all_plans if key in x['goals'] and x['code'].startswith('P') for m in x['modules']]
    elif kind == 'requirement':
        selected = [q for q in all_req if q['key'] == key]
        if not selected:
            raise ValueError('找不到这条需求')
    elif kind == 'all':
        selected = all_req
    else:
        raise ValueError('kind 写 module、goal、requirement 或 all')
    goal_codes = {g['code'] for g in selected_goals} | {c for q in selected for c in q['goals']}
    selected_goals = [g for g in bp['goals'] if g['code'] in goal_codes]
    if kind != 'module':
        mods += [m for q in selected for m in q['modules']]
    mods = list(dict.fromkeys(mods))
    req_keys = {q['key'] for q in selected}
    tasks = []
    for g in bp['goals'] + bp['modules']:
        for s in g['subs']:
            related = bool(req_keys.intersection(requirements.task_refs(g, s)))
            own = (kind == 'goal' and g['code'] == key) or (kind == 'module' and g['code'] == key)
            if related or own:
                tasks.append(dict(s, goal=g['code'], file=g['file'], key=g['code'] + '::' + s['code'], requirements=requirements.task_refs(g, s)))
    task_goals = {x['goal'] for x in tasks}
    plans = [x for x in all_plans if set(x['goals']) & goal_codes or set(x['modules']) & set(mods) or x['goal'] in task_goals]
    js = [x for x in deliveries.list_all(p) if x['goal'] in task_goals | goal_codes or x['goal'] in mods]
    orders = [x for x in workorders.list_all(p) if set(x['modules']) & set(mods) or any(t.split(' ')[0] in task_goals | goal_codes for t in x['target'])]
    logs = [x for x in journal.recent(p, 300) if x['scope'] in set(mods) | goal_codes]
    material = []
    for m in mods:
        d = project.module_dir(p, m)
        if d:
            material += [{'name': f.name, 'file': gp.relative(p, f), 'module': m} for f in project.walk(d)
                         if f.name not in ('需求.md', '蓝图.md', '戒律.md')]
    source_files = list(dict.fromkeys([q['file'] for q in selected] + [g['file'] for g in selected_goals] + [t['file'] for t in tasks]))
    return {'kind': kind, 'key': key, 'goals': selected_goals, 'requirements': selected, 'modules': mods,
            'tasks': tasks, 'rules': rule_docs(p, mods), 'plans': plans, 'deliveries': js, 'workorders': orders,
            'logs': logs, 'materials': material, 'documents': [doc(p, f) for f in source_files],
            'options': {'goals': [{'key': g['code'], 'name': g['name']} for g in bp['goals']], 'modules': module_catalog(p)},
            'problems': gp.problems(p)}
