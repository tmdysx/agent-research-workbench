"""治理文件的统一位置、旧路径兼容及可核对、可重跑的迁移。"""
from __future__ import annotations

import hashlib
import json
import atomic
import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = "治理"
MANIFEST = "迁移记录.json"


def file_name(name):
    return re.sub(r'[\\/:*?"<>|%]', lambda m: quote(m.group(0), safe=''), name)


def active(p):
    return (p.root / ROOT).is_dir()


def central(rel: str) -> str:
    rel = rel.replace('\\', '/')
    parts = rel.split('/')
    if parts[0] == '计划':
        return ROOT + '/' + rel
    if len(parts) == 3 and parts[0] == '资料':
        module, name = parts[1:]
        if name == '需求.md':
            return f'{ROOT}/需求/{file_name(module)}.md'
        if name == '蓝图.md' and module != '蓝图':
            return f'{ROOT}/任务/{file_name(module)}.md'
        if name == '戒律.md':
            return f'{ROOT}/戒律/模块/{file_name(module)}.md'
        if module == '戒律' and re.match(r'^[123] ', name):
            return f'{ROOT}/戒律/{name}'
        if module == '蓝图' and (re.match(r'^S\d+(?:-\d+)* ', name) or name.endswith('方向承接.md')):
            return f'{ROOT}/目标/{name}'
    return rel


def safe(p, rel):
    root = p.root.resolve()
    f = (root / rel).resolve()
    if f == root or not f.is_relative_to(root):
        raise ValueError('治理路径必须在项目内')
    return f


def resolve(p, rel: str, *, write=False) -> Path:
    old = safe(p, rel)
    if rel.replace('\\', '/') == '资料/蓝图/蓝图.md':          # 「蓝图」模块自己的任务：治理/任务/蓝图.md 有了才认（旧的 资料/蓝图/ 里放的是总蓝图）
        own = safe(p, f'{ROOT}/任务/蓝图.md')
        if own.is_file():
            return own
    new = safe(p, central(rel))
    if new.is_file() or (write and active(p)):
        return new
    return old


def relative(p, f):
    return f.resolve().relative_to(p.root.resolve()).as_posix()


def plans_dir(p):
    return p.root / (ROOT + '/计划' if active(p) else '计划')


def plan_files(p, html=False):
    """部分迁移时两处都读；同路径优先集中记录，不隐藏尚未搬入的历史。
    html=True 连 .html 样图（R2、R3 这种）一起列——只给计划页用；答疑、计划覆盖这些只读 .md（S1-1 S2-20）。"""
    found = {}
    for d in (p.root / '计划', p.root / ROOT / '计划'):
        for pat in ('*.md', '*.html') if html else ('*.md',):
            for f in sorted(d.rglob(pat)):
                if '内置' in f.relative_to(d).parts:
                    continue
                found[f.relative_to(d).as_posix()] = f
    return found


def goal_files(p):
    found = {}
    for d in (p.materials / '蓝图', p.root / ROOT / '目标'):
        for f in sorted(d.glob('S*.md')):
            found[f.name] = f
    return list(found.values())


def records(p, kind):
    """返回来源名和实际文件；来源名是历史编号的限定范围，不代表模块拥有记录。"""
    oldname = {'需求': '需求.md', '任务': '蓝图.md', '模块戒律': '戒律.md'}[kind]
    found = {f.parent.name: f for f in p.materials.glob('*/' + oldname)}
    folder = '戒律/模块' if kind == '模块戒律' else kind
    for f in sorted((p.root / ROOT / folder).glob('*.md')):
        found[unquote(f.stem)] = f
    return found


def rule_files(p):
    found = {f.name: f for f in (p.materials / '戒律').glob('[123] *.md')}
    found.update({f.name: f for f in (p.root / ROOT / '戒律').glob('[123] *.md')})
    return list(found.values())


def module_rule(p, name):
    return resolve(p, f'资料/{name}/戒律.md')


def manifest(p):
    try:
        return json.loads((p.root / ROOT / MANIFEST).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'version': 2, 'files': [], 'conflicts': []}


def problems(p):
    out = []
    for old, new in migration_pairs(p):
        if new.exists() and old.read_bytes() != new.read_bytes():
            out.append(f'治理迁移冲突：{relative(p, old)} 与 {relative(p, new)} 均保留；当前读取治理版本')
    return out


def migration_pairs(p):
    candidates = list(p.materials.glob('*/*.md'))
    if (p.root / '计划').is_dir():
        candidates += [f for f in (p.root / '计划').rglob('*') if f.is_file()]
    pairs = []
    for f in candidates:
        old = relative(p, f)
        new = central(old)
        if new != old and not f.is_symlink():
            pairs.append((safe(p, old), safe(p, new)))
    return sorted(pairs)


def migrate(conn, p, *, by, request):
    """先复制并逐字节校验，再把原件集中保存在回收站；不改正文与时间。"""
    import trash
    data = manifest(p)
    known = {x['old']: x for x in data['files']}
    moves, conflicts = [], []
    for old, new in migration_pairs(p):
        a, b = relative(p, old), relative(p, new)
        if new.exists() and old.read_bytes() != new.read_bytes():
            conflicts.append({'old': a, 'new': b})
            continue
        new.parent.mkdir(parents=True, exist_ok=True)
        if not new.exists():
            shutil.copy2(old, new)
        if old.read_bytes() != new.read_bytes():
            raise ValueError(f'迁移校验失败：{a}')
        known[a] = {'old': a, 'new': b, 'sha256': hashlib.sha256(old.read_bytes()).hexdigest(), 'mtime_ns': old.stat().st_mtime_ns}
        moves.append(a)
    box = trash.move_many(conn, p, moves, by=by, reason='蓝图 v2 集中治理：已校验原文和时间，原件留底', request=request, origin='治理迁移') if moves else None
    data.update(files=list(known.values()), conflicts=conflicts)
    if box:
        data.setdefault('backups', []).append(box['code'])
    root = p.root / ROOT
    for folder in ('目标', '需求', '戒律/模块', '任务', '计划'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    temp = root / (MANIFEST + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    atomic.replace(temp, root / MANIFEST)
    lines = ['# 集中治理迁移清单', '', '原文、编号和修改时间保留；原件在回收站留底。日志、人的笔记和业务材料未迁移。', '', '| 原路径 | 现路径 | SHA256 |', '|---|---|---|']
    lines += [f"| {x['old']} | {x['new']} | {x['sha256']} |" for x in data['files']]
    lines += ['', '冲突：' + ('；'.join(x['old'] for x in conflicts) or '无'), '留底：' + '、'.join(data.get('backups', []))]
    (root / '迁移清单.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'moved': len(moves), 'conflicts': conflicts, 'backup': box, 'total': len(known)}
