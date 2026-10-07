"""只在本机构建所选干净模板。没有远程发布、GitHub、员工启动或凭据操作。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path

import new_project
import release_clean
from project import CODE_DIR, check_name


def inventory(root: Path) -> list[dict]:
    # 发行已选好的全部文件都要进 ZIP，包括内置、空占位和 .mcp 配置。
    # 不复用复制核心的筛选器：它会排除内置以免默认复制阶段重复扫描。
    out = []
    for base, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            f = Path(base) / name
            if f.is_symlink() or f.is_junction():
                raise ValueError('发行目录不能有链接：' + str(f))
        for name in names:
            f = Path(base) / name
            out.append({'path': f.relative_to(root).as_posix(), 'bytes': f.stat().st_size,
                        'sha256': hashlib.sha256(f.read_bytes()).hexdigest()})
    return sorted(out, key=lambda f: f['path'])


def build(output: Path, src: Path = CODE_DIR, *, notice_override: str | None = None,
          third_party_override: str | None = None, demo_overrides: dict[str, Path] | None = None,
          profiles: tuple[str, ...] = ('general', 'research'), package_name: str | None = None,
          public_payload_roots: tuple[str, ...] = (), public_module_labels: dict | None = None) -> dict:
    src, output = src.resolve(), output.resolve()
    if (not isinstance(profiles, (tuple, list)) or not profiles
            or any(not isinstance(n, str) or n not in {'general', 'research'} for n in profiles)
            or len(set(profiles)) != len(profiles)):
        raise ValueError('发行模板须是 general、research 的非空不重复列表')
    profiles = tuple(profiles)
    if package_name is not None:
        if not isinstance(package_name, str) or len(profiles) != 1 or check_name(package_name) != package_name:
            raise ValueError('发行包名称须是合法的单个文件夹名称，且只能用于单包发行')
        check_name(package_name.split('.')[0])  # Windows 设备名加扩展名也仍是设备别名。
    if output.exists():
        raise FileExistsError('本地发行目录已存在，请换一个新目录：' + str(output))
    if output == src or output.is_relative_to(src):
        raise ValueError('发行目录不能放进源项目')
    # 所选声明和路径全部通过，才创建输出。失败保留可检查的半成品，不覆盖旧发行。
    configs = [new_project.profile_config(src, name) for name in profiles]
    with release_clean.staged_source(src, configs, demo_overrides, public_payload_roots,
                                     public_module_labels, profiles) as (stage, source_report):
        for profile in profiles:
            new_project._copy_plan(stage, profile=profile)
        return _build_packages(output, stage, source_report, notice_override, third_party_override,
                               profiles, package_name)


def _build_packages(output: Path, src: Path, source_report: dict,
                    notice_override: str | None, third_party_override: str | None,
                    profiles: tuple[str, ...], package_name: str | None) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    packages, records = [], []
    for profile in profiles:
        target = output / (package_name or ('MiracleHarness2-' + profile))
        new_project.make(target, src, profile=profile)
        cleanup = release_clean.sanitize(target, public_payload_roots=tuple(source_report['public_payload_roots']))
        cleanup['public_demo_replacements'] = source_report['public_demo_replacements']
        cleanup['public_payload_roots'] = source_report['public_payload_roots']
        created_examples = json.loads((target / '新项目复制清单.json').read_text(encoding='utf-8')).get('onboarding_examples', {})
        cleanup['public_demo_counts'] = {'library': len(created_examples.get('library', [])),
                                         'downloads': len(created_examples.get('downloads', [])),
                                         'created_files': len(created_examples.get('created', []))}
        if notice_override is not None:
            (target / 'NOTICE').write_text(notice_override, encoding='utf-8')
        if third_party_override is not None:
            (target / '第三方许可证.md').write_text(third_party_override, encoding='utf-8')
        cfg = new_project.profile_config(src, profile)
        readme = ('# MiracleHarness2 · ' + cfg.get('label', profile) + '\n\n'
                  '![MiracleHarness](品牌/miracleharness2-hero.png)\n\n'
                  '人定方向，agent 做事。目标、需求、计划、规则和交付保存在本地普通文件。\n\n'
                  '## 开始使用\n\n'
                  '1. 安装 Python 3.12。打开此文件夹的 PowerShell，运行 `python -m pip install -r backend/requirements.txt`。\n'
                  '2. 双击 `启动.bat`，网页默认进入蓝图。填入自己的目标、需求和验收标准。\n'
                  '3. 让你已有的 agent 先读 `AGENTS.md`；MCP 可选，配置见 `.mcp.json`。平台无需模型 API key，agent 的账号与使用费用由你自行选择。\n'
                  '4. 到设置选择外观；笔记按 N 打开。默认不启动员工、不启用插件。\n\n'
                  '## 这一版带什么\n\n')
        if profile == 'general':
            readme += ('通用治理、想法与蓝图、戒律、源代码、测试、笔记、存档、自动化、工具、插件和通用技能。起步模块为：'
                       + '、'.join(cfg['modules'])
                       + '。保留公开展示案例，可自行建立业务模块。声明的内置在新项目时继承，额外资料在设置的自定义弹窗本次选择。\n\n')
        else:
            readme += ('包含完整通用核心，以及文献、实验、论文、数据与分析、投稿与返修、汇报和素材的科研模板、九份中文阶段技能。先读 `'
                       + cfg.get('guide', '资料/文献/方法/科研/科研入门.md') + '` 和 `'
                       + cfg.get('entry', '技能库/research-route/SKILL.md')
                       + '`。按任务所需跳过不适用阶段并说明理由；模板不是科研结果。\n\n')
        if source_report['public_payload_roots']:
            readme += ('另外保留本次明确选中的业务示例：'
                       + '、'.join(dict.fromkeys(rel.split('/')[1] for rel in source_report['public_payload_roots']))
                       + '。示例供了解界面与使用方法，不是使用者自己的研究或业务成果；新项目继续继承这些示例。\n\n')
        if '资料/宣传片/成果' in source_report['public_payload_roots']:
            readme += release_clean.VIDEO_DEMO_NOTE + '\n\n'
        readme += ('## 工具与插件\n\n'
                   '安装图解在 `工具库/安装指南/`；三个插件各有 `安装指南.md`。网页终端和PPT原版预览按需检查后由人启用；剪辑当前是协议与命令卡，网页剪辑器尚未完成。不随包携带 Office、LibreOffice、Git、FFmpeg、Blender 或其他外部安装。\n\n'
                   '本包保留原创示意图与官网文字入口，第三方官网截图和原样图标未随包分发。展示案例使用公开信息副本，并带仅由这些案例新建的演示索引，首次打开即可查看。源项目运行数据库未复制。\n\n'
                   '## 验证与许可\n\n'
                   '`python -m pytest backend/tests -q` 可运行通用回归。真实任务、真实科研完成与跨电脑安装需要另行验证。\n\n'
                   '本项目原创部分采用 PolyForm Noncommercial 1.0.0：个人及非商业研究可依条款使用，商业使用（包括商业研究）需作者另行书面授权，联系见 `NOTICE`。见 `LICENSE` 与 `NOTICE`；第三方部分保持其自身许可。公开源码含非商用限制，不是 OSI 开源许可证。\n')
        (target / 'README.md').write_text(readme, encoding='utf-8')
        # make 的清单是建项目时生成的；发行修改说明后同步实际大小。
        release_clean.refresh_copy_manifest(target, cleanup)
        files = inventory(target)
        manifest = {'version': 1, 'profile': profile, 'files': files,
                    'file_count': len(files), 'bytes': sum(f['bytes'] for f in files)}
        (target / '发行清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        files = inventory(target)
        archive = output / (target.name + '.zip')
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for file in files:
                z.write(target / file['path'], target.name + '/' + file['path'])
        summary = {'profile': profile, 'path': str(target), 'archive': str(archive),
                   'files': len(files), 'bytes': sum(f['bytes'] for f in files), 'cleanup': cleanup}
        packages.append(summary)
        records.append({'profile': profile, 'directory': target.name, 'archive': archive.name,
                        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                        'version': 1, 'files': files, 'file_count': len(files), 'bytes': summary['bytes']})
    package_text = ('发行包为 ' + Path(packages[0]['path']).name + '。同名 ZIP 和发布清单记录实际内容与 SHA256。'
                    if len(packages) == 1 else
                    '通用版是 MiracleHarness2-general；科研版是 MiracleHarness2-research。同名 ZIP 和发布清单记录实际内容与 SHA256。')
    handover = ('# 本地发行交接\n\n'
                '此目录是可供审阅的独立发行副本与 ZIP；未上传、未推送、未建立 PR。\n\n'
                + package_text + '仅选择这里的发行包，不要上传使用中的源项目、个人笔记或运行记录。\n\n'
                '第三方官网截图与原样图标未分发，保留原创图与官网文字入口。展示案例由公开信息副本生成，未继承源项目数据库、机器设置或历史记录。\n\n'
                '公开时须保留 LICENSE、NOTICE 和随带第三方原许可。本项目原创许可是 PolyForm Noncommercial 1.0.0；商业使用（包括商业研究）须取得作者书面授权，联系见 NOTICE。\n\n'
                '尚未在另一台电脑安装验证，也未宣称完成真实科研任务。发布前可照 README 检查本机环境；此构建不会自动安装外部软件或启动员工。\n')
    (output / '本地发行交接.md').write_text(handover, encoding='utf-8')
    path = output / '发布清单.json'
    path.write_text(json.dumps({'version': 1, 'local_only': True,
                                'packages': records}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'root': str(output), 'packages': packages, 'manifest': str(path), 'source_cleanup': source_report}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='构建本地通用版和科研版，不发布')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--notice-file', type=Path, help='只覆盖发行副本的作者许可通知')
    parser.add_argument('--third-party-file', type=Path, help='只覆盖发行副本的第三方通知')
    parser.add_argument('--demo-overrides-file', type=Path, help='公开展示案例JSON：工作台相对路径到替代文件绝对路径')
    parser.add_argument('--profile', action='append', choices=('general', 'research'), help='仅构建所选模板；可重复选择')
    parser.add_argument('--package-name', help='单包发行的文件夹与 ZIP 名称')
    parser.add_argument('--public-payload-root', action='append', help='明确选中的公开业务示例资料相对路径')
    args = parser.parse_args()
    overrides = (json.loads(args.demo_overrides_file.read_text(encoding='utf-8-sig'))
                 if args.demo_overrides_file else {})
    print(json.dumps(build(args.output,
                           notice_override=args.notice_file.read_text(encoding='utf-8') if args.notice_file else None,
                           third_party_override=args.third_party_file.read_text(encoding='utf-8') if args.third_party_file else None,
                           demo_overrides={k: Path(v) for k, v in overrides.items()},
                           profiles=tuple(args.profile) if args.profile else ('general', 'research'),
                           package_name=args.package_name,
                           public_payload_roots=tuple(args.public_payload_root or [])), ensure_ascii=False, indent=2))
