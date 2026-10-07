"""开新项目：复制一份干净的应用（新项目.bat 跑的就是它）。

一份应用只管一个项目。要开下一个项目，就复制程序和所选内置内容，
不带本项目自己的东西（想法 / 文献 / 蓝图 / 戒律 / 心得、数据库）。
所选模块明确声明的入门示例在新项目中重新初始化，不复制旧索引和个人记录。
新项目第一次启动时自己建好七个固定模块（想法 · 蓝图 · 戒律 · 源代码 · 测试 · 文献 · 论文）和可选起步业务模块，项目名就是文件夹名。

给 agent 的进门文件也带上（作者 2026-09-30：「每一个agent接手这个项目都可以看到并且调用，这样我这个平台才能服务更多的人」）：
AGENTS.md（从这份应用的 AGENTS.md 里取哪个项目都用得上的：东西在哪、技能目录、做事的流程、通用戒律、核心；
这个项目自己的介绍和项目戒律换成空的样子）· CLAUDE.md（让 Claude Code 自动读 AGENTS.md）· 通用戒律全文。技能本来就在 技能库/ 里。
"""
from __future__ import annotations

import os
import json
import re
import shutil
import sys
from pathlib import Path

from project import CODE_DIR, Project, check_name, ensure_skeleton
from skills import INDEX_END, INDEX_START
import skills
import builtin

# 程序本身：这些跟着走
APP_FILES = builtin.CORE_FILES
APP_DIRS = builtin.CORE_DIRS


def agents_md(src: Path = CODE_DIR) -> str:
    """新项目的 AGENTS.md：照这份应用的 AGENTS.md，留下哪个项目都用得上的，把这个项目自己的换成空的样子。"""
    text = (src / "AGENTS.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    head, *secs = re.split(r"(?m)^(?=## )", text)
    first = [l for l in head.splitlines() if l.startswith(("# ", "> "))]
    out = "\n\n".join(first) + "\n\n" + (
        "**这是什么**：用「自动化科研交互界面」管的一个长程项目。这个项目要做成什么、要解决什么问题，写在 `治理/目标/S0 终极目标.md`（人写）。\n"
        "干活的是 agent，这个工具不替它干活，只管：人看得懂项目、想法记下来变成准确的指令、项目走多久都不失控。\n\n")
    for sec in secs:
        title = sec.splitlines()[0]
        if title.startswith("## 项目戒律"):
            sec = ("## 项目戒律（家规：只管这个项目；写在 `治理/戒律/2 项目戒律.md`）\n\n"
                   "- （还没有。这个项目自己的规矩一行一条，写清从哪来；只有人能定）\n\n")
        elif title.startswith("## 戒律"):              # 改-1（10-03）以后通用、项目合成一节：项目那一行换成空的
            sec = re.sub(r"(?m)^- \*\*项目\*\*：.*$", "- **项目**：（还没有。这个项目自己的规矩写在 `治理/戒律/2 项目戒律.md`，"
                         "一行一条，写清从哪来；只有人能定）", sec)
        elif title.startswith("## 核心"):
            sec = "\n".join(l for l in sec.splitlines() if not l.startswith("已经否决过的提议")).rstrip() + "\n\n"
        out += sec
    i, j = out.find(INDEX_START), out.find(INDEX_END)
    if 0 <= i < j:                                   # 技能目录留空：新项目第一次启动时按它自己的技能库现生成
        out = out[:i] + INDEX_START + "\n" + out[j:]
    return out.rstrip() + "\n"


def profile_config(src: Path, name: str, business_modules: list[str] | None = None) -> dict:
    """发行负载由声明文件选择，核心不猜测业务名称。"""
    f = src / 'backend/template_profiles.json'
    if not f.is_file():
        raise ValueError('找不到发行模板清单')
    builtin.files(src, f, core=True)
    data = json.loads(f.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('profiles'), dict) or name not in data['profiles']:
        raise ValueError('没有这个发行模板：' + str(name))
    cfg = data['profiles'][name]
    if not isinstance(cfg, dict):
        raise ValueError('发行模板清单读不了')
    for key in ('modules', 'skills', 'template_roots', 'module_skills', 'builtin_skill_ids'):
        values = cfg.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError('发行模板清单读不了：' + key)
        cfg[key] = list(dict.fromkeys(values))
    if business_modules is not None:
        import project
        def keep(rel):
            parts = rel.split('/')
            return parts[0] != '资料' or len(parts) < 2 or parts[1] in project.FIXED_NAMES + business_modules
        cfg['modules'] = [n for n in cfg['modules'] if n in project.FIXED_NAMES + business_modules]
        cfg['template_roots'] = [r for r in cfg['template_roots'] if keep(r)]
        cfg['module_skills'] = [r for r in cfg['module_skills'] if keep(r)]
    for n in cfg['modules']:
        check_name(n)
    for n in cfg['skills']:
        check_name(n)
        builtin.path(src, '技能库/' + n)
    if '业务' in cfg['skills']:
        import skills
        skills._manifest(Project(src), src / '技能库')  # 坏清单在创建目标之前报告，缺件仍由目录明确列出。
    for rel in cfg['template_roots']:
        builtin.path(src, rel)
    cfg['module_skills'] = _module_skill_paths(src, cfg['module_skills'])
    _builtin_skill_files(src, cfg['builtin_skill_ids'])
    import project
    cfg['module_labels'] = project.check_module_labels(cfg.get('module_labels', {}))
    return cfg


def _module_skill_paths(src: Path, paths: object) -> list[str]:
    """模块技能只能声明独立技能目录，不能借这个入口复制整个资料模块。"""
    if not isinstance(paths, list):
        raise ValueError('模板的 module_skills 必须是相对目录列表')
    for rel in paths:
        if not isinstance(rel, str):
            raise ValueError('模块技能路径应是资料/模块名/技能')
        parts = rel.split('/')
        if len(parts) != 3 or parts[0] != '资料' or parts[-1] != '技能':
            raise ValueError('模块技能路径应是资料/模块名/技能')
        if check_name(parts[1]) != parts[1]:
            raise ValueError('模块技能路径中的模块名不合法')
        candidate = builtin.path(src, rel)
        if not candidate.is_dir():
            raise ValueError('模块技能路径须是资料/模块名/技能目录')
    return list(dict.fromkeys(paths))


def inherited_module_skills(src: Path) -> list[str]:
    f = src / '模板配置.json'
    if not f.is_file():
        return []
    builtin.files(src, f, core=True)
    data = json.loads(f.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('模板配置须是对象')
    return _module_skill_paths(src, data.get('module_skills', []))


def inherited_profile(src: Path, business_modules: list[str] | None = None) -> tuple[str | None, dict | None]:
    """新项目继续遵守其已声明的模板负载，不借用安装目录的业务。"""
    f = src / '模板配置.json'
    if not f.is_file():
        return None, None
    builtin.files(src, f, core=True)
    data = json.loads(f.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('模板配置须是对象')
    name = data.get('profile')
    if name is None:
        return None, None  # 未声明发行版的老项目仍按其内置内容复制。
    if data.get('version') != 1 or not isinstance(name, str):
        raise ValueError('模板配置的发行版声明读不了')
    cfg = dict(profile_config(src, name, business_modules))
    modules = data.get('modules', cfg['modules'])
    if not isinstance(modules, list) or any(not isinstance(n, str) for n in modules):
        raise ValueError('模板配置的模块须是名称列表')
    for n in modules:
        check_name(n)
    # 只在复制新后代时补通用起步模块；不修改源项目配置，也不在普通读取时迁移。
    cfg['modules'] = list(dict.fromkeys(modules + (cfg['modules'] if name == 'general' else [])))
    cfg['module_skills'] = inherited_module_skills(src)
    # 默认内容技能在新后代继承；旧模块声明仍保留，不在读取时写回源项目。
    cfg['module_skills'] = list(dict.fromkeys(cfg['module_skills'] + profile_config(src, name, business_modules)['module_skills']))
    declared = data.get('builtin_skill_ids', cfg['builtin_skill_ids'])
    if not isinstance(declared, list) or any(not isinstance(s, str) for s in declared):
        raise ValueError('模板配置的 builtin_skill_ids 须是完整技能编号列表')
    cfg['builtin_skill_ids'] = list(dict.fromkeys(declared))
    _builtin_skill_files(src, cfg['builtin_skill_ids'])
    import project
    cfg['module_labels'] = project.check_module_labels(data.get('module_labels', cfg['module_labels']))
    cfg['label'] = data.get('label', cfg.get('label', name))
    return name, cfg


_SKILL_FILES: dict = {}                              # 同一次预览里核了好几遍（每遍十几秒）：一分钟内同样的请求用上一遍的结果（10-07）


def _builtin_skill_files(src: Path, ids: list[str]) -> tuple[list[str], dict | None]:
    """只复制显式方法及其许可/来源闭包，不从未核资料或本机技能借一份。"""
    import copy
    import time
    if not ids:
        return [], None
    manifest = Path(src) / '技能库/业务/manifest.json'
    key = (str(Path(src).resolve()), tuple(ids), manifest.stat().st_mtime_ns if manifest.is_file() else 0)
    hit = _SKILL_FILES.get(key)
    if hit and time.monotonic() - hit[0] < 60:
        return list(hit[1]), copy.deepcopy(hit[2])
    files, projected = _builtin_skill_files_now(src, ids)
    _SKILL_FILES.clear()
    _SKILL_FILES[key] = (time.monotonic(), files, projected)
    return list(files), copy.deepcopy(projected)


@skills._reading
def _builtin_skill_files_now(src: Path, ids: list[str]) -> tuple[list[str], dict | None]:
    import skills
    p = Project(src)
    groups, rows = skills._manifest(p, src / '技能库')
    by_id = {r['id']: r for r in rows}
    selected, files = [], set()
    for sid in ids:
        row = by_id.get(sid)
        if row is None or row.get('kind') != 'skill' or not row.get('path'):
            raise ValueError('声明的内置方法不存在或只是一条网址：' + sid)
        package = row['path'].rsplit('/', 1)[0]
        # manifest 指向哪个包就核整个普通包；目录不足不冒充可用方法。
        document = builtin.path(src, row['path'])
        if not document.is_file():
            raise ValueError('声明的内置方法缺少正文：' + sid)
        files.update(builtin.files(src, document.parent))
        references = list(row.get('languages', {}).values()) + row.get('support_files', [])
        references += row.get('license', {}).get('files', [])
        references += [s['local_path'] for s in row.get('source', {}).get('files', []) if s.get('local_path')]
        references += [row['info_path']] if row.get('info_path') else []
        for rel in references:
            # 随包来源只能是本包或全局的公开技能来源；不借许可字段复制人的笔记/论文。
            if not (rel.startswith(package + '/') or rel.startswith('技能库/业务/')):
                raise ValueError('方法配套文件须在本包或技能来源库中：' + rel)
            path = builtin.path(src, rel)
            if not path.is_file():
                raise ValueError('声明的内置方法缺少配套文件：' + rel)
            files.update(builtin.files(src, path))
        for source in row.get('source', {}).get('files', []):
            if source.get('local_path'):
                import hashlib
                raw = builtin.path(src, source['local_path']).read_bytes()
                if hashlib.sha256(raw).hexdigest() != source['sha256'].lower():
                    raise ValueError('声明的内置方法来源指纹不符：' + source['local_path'])
        selected.append(row)
    rel = '技能库/业务/manifest.json'
    raw = json.loads(builtin.path(src, rel).read_text(encoding='utf-8-sig'))
    # 元数据照实投影；旧编号、来源与指纹保留，不留下未复制的可安装条目。
    used = {r['business'] for r in selected}
    projected = {**raw, 'groups': [g for g in groups if g['id'] in used], 'items': selected,
                 'issues': [i for i in raw.get('issues', []) if isinstance(i, dict) and i.get('id') in ids]}
    files.add(rel)
    lock = raw.get('source_lock')
    if lock:
        path = builtin.path(src, lock)
        if not path.is_file():
            raise ValueError('技能来源锁缺失：' + lock)
        files.add(lock)  # 纯来源锁保留原指纹，不把其中未选方法当作已复制正文。
    skills._verify_read(skills._READ.get())
    return sorted(files), projected


def _project_skill_manifest(src: Path, copied: list[str], selected: dict | None) -> dict | None:
    """按实际复制的包投影；保留明确仅链接的条目，不给缺包制造 ready。"""
    rel = '技能库/业务/manifest.json'
    if rel not in copied:
        return None
    raw = json.loads(builtin.path(src, rel).read_text(encoding='utf-8-sig'))
    existing = set(copied)
    rows = [r for r in raw['items'] if (r.get('path') in existing
            and all(p in existing for p in r.get('languages', {}).values())) or r.get('kind') == 'link']
    # 窄模板只继承显式条目；旧广业务模板仍保留其实际带走的可读方法和链接。
    if selected is not None:
        selected_ids = {r['id'] for r in selected['items']}
        rows = [r for r in rows if r['id'] in selected_ids or r.get('path') in existing]
    groups = {r['business'] for r in rows}
    return {**raw, 'groups': [g for g in raw['groups'] if g['id'] in groups], 'items': rows,
            'issues': [i for i in raw.get('issues', []) if not isinstance(i, dict) or i.get('id') in {r['id'] for r in rows}],
            'projection': {'version': 1, 'rule': 'only copied packages and explicit reference links'}}


def _windows_path_preflight(target: Path, copied: list[str], folders: list[dict],
                            names: list[str], *, entry: bool, configured: bool,
                            work_folders: list[str] | None = None) -> None:
    """复制和骨架将用普通 Windows 路径读取；创建前核完整路径，不能留下半份项目。"""
    if os.name != 'nt':
        return
    files, directories = set(copied), {''}

    def directory(rel):
        parts = rel.split('/') if rel else []
        directories.update('/'.join(parts[:i]) for i in range(1, len(parts) + 1))

    for rel in files:
        directory(rel.rsplit('/', 1)[0] if '/' in rel else '')
    for name in names:
        directory('资料/' + name)
    for rel in work_folders or []:
        directory(rel)
    directory('笔记')
    for folder in folders:
        directory(folder['path'])
    for rel in ('治理/目标', '治理/需求', '治理/戒律/模块', '治理/任务', '治理/计划', '自动化/agent'):
        directory(rel)
    files.update({'治理/戒律/2 项目戒律.md', '新项目复制清单.json'})
    if entry:
        files.add('AGENTS.md')
    if configured:
        files.add('模板配置.json')
    for rel in files:
        directory(rel.rsplit('/', 1)[0] if '/' in rel else '')
    for kind, paths, limit in (('文件夹', directories, 248), ('文件', files, 260)):
        for rel in sorted(paths):
            absolute = target.joinpath(*rel.split('/')) if rel else target
            length = len(str(absolute).encode('utf-16-le')) // 2
            if length >= limit:
                raise ValueError(f'新项目路径太长：{kind}完整路径为 {length} 个字符（须少于 {limit}）。'
                                 f'请换更短的目标目录后重试；尚未创建项目。路径：{absolute}')


def _content_folders(src: Path, copied: list[str]) -> list[str]:
    """只在明确开新项目时，根据将带走的合法配置建立空正文目录。"""
    import content_modules
    out = []
    for module in content_modules.ROOTS:
        rel = f'资料/{module}/{content_modules.CONFIG}'
        if rel not in copied:
            continue  # 没有内容配置的旧模板继续保持原样。
        raw, _ = content_modules._snapshot(Project(src), src / rel, content_modules.MAX_CONFIG)
        cfg = content_modules.validate_config(module, json.loads(raw.decode('utf-8-sig')))
        out.extend(f'资料/{module}/{s["folder"]}' for s in cfg['sections'])
    return list(dict.fromkeys(out))


def available_business_modules(src: Path) -> list[str]:
    """仅列普通模块目录；不读用户材料，不将模块目录当复制来源。"""
    import project
    return sorted(n for n in project.module_dirs(Project(src)) if n not in project.FIXED_NAMES
                  and not (src / '资料' / n).is_junction())


def _business_selection(src: Path, values: object) -> list[str]:
    if not isinstance(values, list) or len(values) > 100 or any(not isinstance(n, str) for n in values):
        raise ValueError('业务模块应是最多100个名称的列表')
    available = set(available_business_modules(src))
    for n in values:
        if check_name(n) != n or n not in available:
            raise ValueError('没有这个可选业务模块：' + n)
        builtin.path(src, '资料/' + n)  # 目标创建前拒绝新换入的链接。
    return list(dict.fromkeys(values))


def _copy_plan(src: Path, extra: list[str] | None = None, profile: str | None = None,
               business_modules: list[str] | None = None) -> dict:
    if profile is not None and (extra or business_modules is not None):
        raise ValueError('发行模板负载由声明选择；新项目自定义仍可按次选择')
    if business_modules is None and profile is None:
        config = src / '模板配置.json'
        if config.is_file():
            saved = json.loads(config.read_text(encoding='utf-8-sig'))
            if 'business_modules' in saved:
                business_modules = saved['business_modules']
    selected = _business_selection(src, business_modules) if business_modules is not None else None
    choice = builtin.preview(src, {'extra': extra or []})
    all_folders = list(choice['folders'])
    effective_profile, cfg = (profile, profile_config(src, profile)) if profile is not None else inherited_profile(src, selected)
    module_skills = cfg.get('module_skills', []) if cfg is not None else inherited_module_skills(src)
    import project
    names = cfg['modules'] if cfg is not None else project.template_start_names(src)
    # 加了锁、勾了东西的业务模块默认就带上（作者 10-07：「我发现加锁之后的模块也无法复制到新文件夹」）；
    # 没指定选哪些业务模块时，把这些模块并进默认选择，照「明确勾选」那条路走；人在弹窗里明确取消的才不带
    if selected is None and profile is None:
        available = available_business_modules(src)
        marked_mods = [n for n in dict.fromkeys(r.split('/')[1] for r in choice['marks']['paths']
                                                if r.startswith('资料/') and len(r.split('/')) > 2) if n in available]
        missing = [n for n in marked_mods if n not in names]
        if missing:
            return _copy_plan(src, extra, None, [n for n in names if n in available] + missing)
    if cfg is not None:
        roots = cfg['template_roots'] + cfg.get('module_skills', [])
        def allowed(rel):
            if rel.startswith('技能库/') and not builtin.is_template(rel):
                return rel.split('/')[1] in cfg['skills']
            if rel.startswith('资料/') or builtin.is_template(rel):
                return any(rel == p or rel.startswith(p + '/') for p in roots)
            return True
        choice['copied_paths'] = [r for r in choice['copied_paths'] if allowed(r)]
        choice['folders'] = [r for r in choice['folders'] if allowed(r['path'] + '/.gitkeep')]
    # A manual file mark extends selected module templates, not the set of
    # selected modules. Keep it separate from one-time legacy extra choices.
    mark_modules = set(project.FIXED_NAMES)
    if selected is not None:
        mark_modules.update(selected)
    elif cfg is not None:
        mark_modules.update(names)
        mark_modules.update(r.split('/')[1] for r in cfg['template_roots']
                            if r.startswith('资料/') and len(r.split('/')) > 2)
    def selected_mark(rel):
        parts = rel.split('/')
        return (parts[0] != '资料' or len(parts) < 3 or
                (selected is None and cfg is None) or parts[1].casefold() in {n.casefold() for n in mark_modules})
    marked = [r for r in choice['marked_paths'] if selected_mark(r)]
    for rel in marked:
        if profile is not None and (src / rel).is_dir() and not allowed(rel + '/.'):
            continue                                 # 打发行版时勾的文件夹照发行版的范围挑（跟原来的 内置/ 文件夹一样），不把科研方法带进通用版；小锁标的单个文件照旧带
        action = builtin.mark_state(src, rel)
        if action['state'] in {'ineligible', 'missing'}:
            raise ValueError('所选模块的内置标记无法复制：' + rel + '；' + action['reason'])
        if action.get('kind') == 'folder':           # 勾的是整个文件夹：里面的都带（10-07 统一内置）
            choice['copied_paths'] += builtin.files(src, builtin.path(src, rel))
        elif action['state'] != 'required':
            choice['copied_paths'].append((src / rel).resolve().relative_to(src).as_posix())
    if selected is not None:
        def keep(rel):
            parts = rel.split('/')
            return parts[0] != '资料' or len(parts) < 2 or parts[1] in project.FIXED_NAMES + selected
        choice['copied_paths'] = [r for r in choice['copied_paths'] if keep(r)]
        choice['folders'] = [r for r in choice['folders'] if keep(r['path'])]
        module_skills = [r for r in module_skills if keep(r)]
        # 明确勾选仅扩展内置目录，不读取或复制模块的用户材料。
        for folder in all_folders:
            parts = folder['path'].split('/')
            if len(parts) > 2 and parts[0] == '资料' and parts[1] in selected:
                choice['copied_paths'] += builtin.files(src, builtin.path(src, folder['path']))
                if folder not in choice['folders']:
                    choice['folders'].append(folder)
        names = list(dict.fromkeys([n for n in names if n in project.FIXED_NAMES] + selected))
        if cfg is not None:
            cfg = {**cfg, 'modules': names, 'module_skills': module_skills}
        choice['config']['business_modules'] = selected
    # 旧 extra 接口仍表示明确的文件/资料选择；不会被业务复选框自动生成。
    for rel in extra or []:
        choice['copied_paths'] += builtin.files(src, builtin.path(src, rel))
    for rel in module_skills:
        choice['copied_paths'] += builtin.files(src, builtin.path(src, rel))
    declared_files, selected_manifest = _builtin_skill_files(src, cfg.get('builtin_skill_ids', [])) if cfg is not None else ([], None)
    choice['copied_paths'] = sorted(set(choice['copied_paths'] + declared_files))
    choice['copied_paths'] = [r for r in choice['copied_paths'] if r != builtin.MARKS_FILE]
    # Copy membership and its manifest are one fixed plan. Do not reread the
    # parent's changing manifest midway through the physical copy.
    copied_keys = {r.casefold(): r for r in choice['copied_paths']}
    choice['marked_paths'] = builtin.copied_marks(choice['marks']['paths'], choice['copied_paths'])   # 勾的文件夹带走了里面的就留着
    choice['mark_issues'] = [x for x in choice['mark_issues'] if selected_mark(x['path'])]
    marks_projection = {'version': 1, 'paths': choice['marked_paths']}
    skill_manifest = _project_skill_manifest(src, choice['copied_paths'],
                      selected_manifest if cfg is not None and '业务' not in cfg['skills'] else None)
    chosen = set(names)
    for rel in choice['copied_paths'] + [r['path'] for r in choice['folders']]:
        parts = rel.split('/')
        if len(parts) > 2 and parts[0] == '资料':
            chosen.add(parts[1])
    labels = cfg['module_labels'] if cfg is not None else project.template_module_labels(src)
    options = [{'name': n, 'en': labels.get(n, project.KNOWN_EN.get(n, '')),
                'selected': n in (selected if selected is not None else chosen)}
               for n in available_business_modules(src)]
    choice.update(files=len(choice['copied_paths']),
                  bytes=sum((src / r).stat().st_size for r in choice['copied_paths']),
                  fixed_modules=project.FIXED_NAMES, business_options=options,
                  module_skills=list(module_skills))          # 设置 → 内置 的勾选树把这些显示成「随模块带」
    return {'choice': choice, 'profile': effective_profile, 'cfg': cfg,
            'module_skills': module_skills, 'skill_manifest': skill_manifest,
            'names': names, 'business_modules': selected, 'marks_projection': marks_projection}


def preview(src: Path, extra: list[str] | None = None,
            business_modules: list[str] | None = None) -> dict:
    """新建弹窗与实际复制共用负载规划；只读，不保存选择。"""
    return _copy_plan(src.resolve(), extra, business_modules=business_modules)['choice']


def make(target: Path, src: Path = CODE_DIR, extra: list[str] | None = None,
         profile: str | None = None, business_modules: list[str] | None = None) -> list[str]:
    """把应用复制到 target（必须还不存在）。返回复制了哪些，给人看。"""
    src = src.resolve()
    target = target.resolve()
    if target == src or target.is_relative_to(src):
        raise ValueError('新项目要放在当前项目之外，不能套在原项目里面')
    if target.exists():
        raise FileExistsError(f"{target} 已经有了，换个名字")
    plan = _copy_plan(src, extra, profile, business_modules)
    choice, effective_profile, cfg = plan['choice'], plan['profile'], plan['cfg']
    module_skills, skill_manifest, names = plan['module_skills'], plan['skill_manifest'], plan['names']
    entry = agents_md(src) if (src / 'AGENTS.md').is_file() else ''
    import project
    content_folders = _content_folders(src, choice['copied_paths'])
    import onboarding_examples
    example_plan = onboarding_examples.validate(src, choice['copied_paths'])
    # 生成文件也先检查路径，但不混入真正的源文件复制清单。
    preflight_paths = sorted(set(choice['copied_paths'] + onboarding_examples.planned_paths(example_plan)))
    if choice['marks']['exists']:
        preflight_paths.append(builtin.MARKS_FILE)
    _windows_path_preflight(target, preflight_paths, choice['folders'],
                            list(dict.fromkeys(project.FIXED_NAMES + names)),
                            entry=bool(entry), configured=cfg is not None or plan['business_modules'] is not None, work_folders=content_folders)
    target.mkdir(parents=True, exist_ok=False)
    done = [d + '/' for d in APP_DIRS if (src / d).is_dir()]
    done += [f for f in APP_FILES if (src / f).is_file()]
    for rel in choice['copied_paths']:
        f = src / rel
        builtin.files(src, f)                      # 复制前再检查，不沿新换入的链接取资料
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target / rel)
    if choice['marks']['exists']:
        (target / builtin.MARKS_FILE).write_text(
            json.dumps(plan['marks_projection'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if skill_manifest is not None:
        (target / '技能库/业务/manifest.json').write_text(json.dumps(skill_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # 先补完整骨架：源内置目录可能已使资料存在，不能拿资料是否存在判定初始化。
    for name in project.FIXED_NAMES + names:
        (target / '资料' / name).mkdir(parents=True, exist_ok=True)
    (target / '笔记').mkdir(parents=True, exist_ok=True)
    ensure_skeleton(Project(target))
    import content_modules
    for rel in content_folders:
        path = target / rel
        content_modules._ordinary(Project(target), path, missing=True)
        path.mkdir(parents=True, exist_ok=True)
        content_modules._ordinary(Project(target), path)
    if cfg is not None or plan['business_modules'] is not None:
        config = {'version': 1, 'profile': effective_profile,
            'modules': names, 'module_skills': module_skills,
            'builtin_skill_ids': cfg.get('builtin_skill_ids', []) if cfg is not None else [],
            'module_labels': cfg['module_labels'] if cfg is not None else project.template_module_labels(src),
            'label': cfg.get('label', effective_profile) if cfg is not None else '自选业务'}
        if effective_profile is None:
            config.pop('profile')
        if plan['business_modules'] is not None:
            config['business_modules'] = plan['business_modules']
        (target / '模板配置.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for folder in choice['folders']:
        d = target / folder['path']
        d.mkdir(parents=True, exist_ok=True)
        done.append(folder['path'] + '/')
    for part in ('目标', '需求', '戒律/模块', '任务', '计划'):
        (target / '治理' / part).mkdir(parents=True, exist_ok=True)
    (target / '自动化' / 'agent').mkdir(parents=True, exist_ok=True)   # agent 档案是每个项目自己的：空着，来了先报到
    if entry:
        (target / "AGENTS.md").write_text(entry, encoding="utf-8")
        done.append("AGENTS.md")
    rules = target / "治理" / "戒律" / "2 项目戒律.md"
    if not rules.exists():
        rules.write_text("# 2 项目戒律（家规：只管这个项目）\n\n| | 规矩 | 从哪来 |\n|---|---|---|\n", encoding="utf-8")
    settings = target / '.claude/settings.json'
    if settings.is_file():
        cfg = json.loads(settings.read_text(encoding='utf-8'))
        cfg['plansDirectory'] = './治理/计划'
        settings.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Git 不保存空目录；只加空占位，不改已有模板内容。
    for rel in builtin.folders(target):
        d = target / rel
        if not any(d.iterdir()):
            (d / '.gitkeep').write_bytes(b'')
    example_result = None
    if example_plan['modules']:
        import store
        # RC_DB 可能仍指着父项目；新项目只能连接自己新建的索引。
        connection = store.connect(target / '索引' / 'state.db')
        try:
            example_result = onboarding_examples.initialize(connection, Project(target), example_plan)
        finally:
            connection.close()
    copied = [{'path': f.relative_to(target).as_posix(), 'bytes': f.stat().st_size}
              for f in sorted(target.rglob('*')) if f.is_file()]
    manifest = {'version': 1, 'files': copied, 'file_count': len(copied),
                'bytes': sum(f['bytes'] for f in copied), 'config': choice['config'],
                'profile': effective_profile or ('inherited' if (src / '模板配置.json').is_file() else 'all-builtin')}
    if example_result is not None:
        manifest['onboarding_examples'] = example_result
    if choice['marks']['exists']:
        manifest['builtin_marks'] = {'paths': plan['marks_projection']['paths'],
                                    'source_revision': choice['marks']['revision']}
    (target / '新项目复制清单.json').write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    done += ['新项目复制清单.json']
    return done


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    print("开一个新项目：复制一份干净的应用（只带程序，不带这个项目自己的东西）\n")
    while True:
        try:
            name = check_name(input("新项目叫什么（也是文件夹名）："))
            break
        except ValueError as e:
            print(f"  {e}")
    default_dir = CODE_DIR.parent
    where = input(f"放在哪（直接回车 = {default_dir}）：").strip().strip('"')
    target = (Path(where) if where else default_dir) / name
    try:
        done = make(target)
    except (OSError, ValueError) as e:
        print(f"\n没建成：{e}")
        return
    print(f"\n建好了：{target}")
    print("复制了：" + "、".join(done))
    print("\n下一步：进这个文件夹，双击「启动.bat」。外面的材料拖进网页上的「外部资料入口 Intake」，让 agent 分拣。")
    try:
        os.startfile(target)                          # 顺手打开新文件夹
    except (AttributeError, OSError):
        pass


if __name__ == "__main__":
    main()
