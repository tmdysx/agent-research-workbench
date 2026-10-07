"""本地双版本发行：合成源、真实复制和ZIP内容指纹，不上传或读取私人资料。"""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import zipfile

import pytest

import new_project
import release
import release_clean


COMMON_SKILLS = ["自动化科研交互界面", "网页前端", "交付自查"]
SCIENCE_SKILLS = ["科研-总入口", "科研-选题", "科研-文献", "科研-数据设计", "科研-复现", "科研-图表", "科研-论文", "科研-投稿", "科研-返修"]
GENERAL_MODULES = ["想法", "蓝图", "戒律", "源代码", "测试", "文献", "论文"]
RESEARCH_MODULES = GENERAL_MODULES + ["实验", "汇报", "素材", "数据与分析", "投稿与返修"]


def write(root, rel, text="公共占位模板"):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


def synthetic_source(tmp_path):
    src = tmp_path / "合成发行源"
    write(src, "backend/main.py", "# 通用后台\n")
    write(src, "backend/tests/test_sample.py", "# 通用测试\n")
    write(src, "backend/builtin_resources.json", json.dumps({"version": 1, "paths": []}))
    write(src, "模板.html", "<html>通用界面</html>")
    write(src, "README.md", "# MiracleHarness2\n本地安装示例\n")
    write(src, "品牌/miracleharness2-hero.png", "合成品牌图片路径检查")
    write(src, "工具库/安装指南/从这里开始.md", "# 公开指南\n")
    write(src, "LICENSE", "合成测试许可占位，不代表产品许可")
    write(src, "NOTICE", "Required Notice: Synthetic author; contact not yet specified")
    write(src, "AGENTS.md", "# 接手说明\n\n## 核心\n通用程序和规矩\n")
    for name in COMMON_SKILLS + SCIENCE_SKILLS + ["未授权私人技能"]:
        write(src, f"技能库/{name}/SKILL.md", f"---\nname: {name}\ndescription: 中文测试技能\n---\n# {name}\n请先读目标再行动。\n")
    for name in SCIENCE_SKILLS:
        write(src, f"技能库/{name}/LICENSE-MIT.txt", "MIT License\nSynthetic upstream attribution fixture.\n")
    # 10-07 统一内置：各模块的 方法/ 靠清单勾上；插件/ 是核心，本来就带
    common_roots = [f"资料/{name}/方法" for name in GENERAL_MODULES]
    science_roots = [f"资料/{name}/方法" for name in RESEARCH_MODULES if name not in GENERAL_MODULES]
    for rel in common_roots + science_roots:
        write(src, rel + "/示例.md")
    write(src, "插件/安装说明.md", "# 安装说明\n按需安装，不自动启用。\n")
    write(src, "资料/文献/技能/SKILL.md", "---\nname: 文献模块\ndescription: 关联科研文献技能\n---\n读取正式技能库/科研-文献/SKILL.md。\n")
    profiles = {"version": 1, "profiles": {
        "general": {"label": "纯通用", "modules": GENERAL_MODULES, "skills": COMMON_SKILLS,
                    "template_roots": common_roots, "module_skills": []},
        "research": {"label": "科研内置", "modules": RESEARCH_MODULES, "skills": COMMON_SKILLS + SCIENCE_SKILLS,
                     "template_roots": common_roots + science_roots, "module_skills": ["资料/文献/技能"],
                     "module_labels": {"数据与分析": "Data & Analysis", "投稿与返修": "Submission & Revision"}}}}
    write(src, "backend/template_profiles.json", json.dumps(profiles, ensure_ascii=False))
    for rel in ("资料/论文/私人论文.md", "资料/测试/建模/私人模型.blend", "笔记/总览.md", "自动化/交付/J1 历史.md",
                "治理/计划/项目/P1 历史.md", "工具库/下载/Blender/blender.exe", "索引/state.db", "存档/C1/原件.txt", "回收站/X1/原件.txt"):
        write(src, rel, "不能默认带入的合成私人标记")
    write(src, "资料/天气/方法/天气模板.md", "普通新项目仍应继承的DIY内置")
    write(src, "资料/天气/本次材料.md", "只有当次选中才复制")
    write(src, "内置标记.json", json.dumps({"version": 1, "paths": common_roots + science_roots + ["资料/天气/方法"]}, ensure_ascii=False))
    return src


@pytest.fixture
def source(tmp_path):
    return synthetic_source(tmp_path)


def test_build_creates_two_local_packages_zips_and_checkable_fingerprints(source, tmp_path):
    output = tmp_path / "本地发行"
    result = release.build(output, src=source)
    assert Path(result["root"]).resolve() == output.resolve()
    assert {p["profile"] for p in result["packages"]} == {"general", "research"}
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    recorded = {p["profile"]: p for p in manifest["packages"]}
    forbidden = ("私人", "Blender", "索引/", "存档/", "回收站/", "自动化/交付/J1", "治理/计划/项目/P1", "笔记/总览.md")
    for package in result["packages"]:
        profile = package["profile"]
        root = Path(package["path"])
        archive = Path(package["archive"])
        assert root == output / f"MiracleHarness2-{profile}"
        assert archive == output / f"MiracleHarness2-{profile}.zip"
        readme = (root / "README.md").read_text(encoding="utf-8")
        assert "![MiracleHarness](品牌/miracleharness2-hero.png)" in readme
        assert (root / "品牌/miracleharness2-hero.png").is_file()
        assert "`工具库/安装指南/`" in readme and (root / "工具库/安装指南").is_dir()
        assert "品牌/内置/" not in readme and "工具库/内置/" not in readme
        records = recorded[profile]["files"]
        actual = {f.relative_to(root).as_posix(): f for f in root.rglob("*") if f.is_file()}
        assert {r["path"] for r in records} == set(actual)
        assert len(records) == len(actual) == package["files"]
        assert sum(f.stat().st_size for f in actual.values()) == package["bytes"]
        for row in records:
            raw = actual[row["path"]].read_bytes()
            assert row["bytes"] == len(raw)
            assert row["sha256"] == hashlib.sha256(raw).hexdigest()
        assert recorded[profile]["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
        assert not any(any(marker in rel for marker in forbidden) for rel in actual)
        with zipfile.ZipFile(archive) as zipped:
            normalized = [name.removeprefix(root.name + "/") for name in zipped.namelist() if not name.endswith("/")]
            assert len(normalized) == len(actual) and set(normalized) == set(actual)
            for rel, f in actual.items():
                options = [p for p in (rel, root.name + "/" + rel) if p in zipped.namelist()]
                assert len(options) == 1, rel
                assert zipped.read(options[0]) == f.read_bytes()
            assert not any(".." in Path(name).parts or name.startswith("/") for name in zipped.namelist())


def test_build_never_overwrites_an_existing_output(source, tmp_path):
    output = tmp_path / "以前的发行"
    output.mkdir()
    sentinel = write(output, "原版本.txt", "必须保留")
    with pytest.raises(FileExistsError):
        release.build(output, src=source)
    assert sentinel.read_text(encoding="utf-8") == "必须保留"
    assert list(output.iterdir()) == [sentinel]


def test_single_complete_package_has_one_archive_and_no_other_edition_promises(source, tmp_path):
    output = tmp_path / '单份完整发行'
    result = release.build(output, src=source, profiles=('research',), package_name='MiracleHarness2')
    assert len(result['packages']) == 1
    package = result['packages'][0]
    root = Path(package['path'])
    assert root.name == 'MiracleHarness2' and package['profile'] == 'research'
    assert Path(package['archive']).name == 'MiracleHarness2.zip'
    assert [p.name for p in output.glob('*.zip')] == ['MiracleHarness2.zip']
    assert [p.name for p in output.iterdir() if p.is_dir()] == ['MiracleHarness2']
    assert (root / '技能库/科研-返修/SKILL.md').is_file()
    assert (root / '资料/数据与分析/方法/示例.md').is_file()
    handover = (output / '本地发行交接.md').read_text(encoding='utf-8')
    readme = (root / 'README.md').read_text(encoding='utf-8')
    assert '发行包为 MiracleHarness2。' in handover
    assert '完整通用核心' in readme
    assert '通用版' not in handover and '科研版' not in handover
    assert 'MiracleHarness2-general' not in readme and 'MiracleHarness2-research' not in readme
    manifest = json.loads(Path(result['manifest']).read_text(encoding='utf-8'))
    assert len(manifest['packages']) == 1 and manifest['packages'][0]['directory'] == 'MiracleHarness2'
    with zipfile.ZipFile(package['archive']) as archive:
        assert all(name.startswith('MiracleHarness2/') for name in archive.namelist())


@pytest.mark.parametrize('profiles, name', [
    ((), None), (('unknown',), None), (('research', 'research'), None), ('research', None),
    (('research',), '../outside'), (('research',), '..\\outside'), (('research',), 'C:/outside'),
    (('research',), 'CON'), (('research',), 'CON.txt'), (('research',), 'name.'),
    (('research',), ' name'), (('general', 'research'), 'MiracleHarness2')
])
def test_release_selection_and_package_name_reject_invalid_values_before_output(source, tmp_path, profiles, name):
    output = tmp_path / '错误名称不会创建发行'
    with pytest.raises(ValueError):
        release.build(output, src=source, profiles=profiles, package_name=name)
    assert not output.exists()


def test_explicit_public_business_examples_and_labels_survive_release_and_new_project(source, tmp_path):
    payload = ('资料/写小说/方法', '资料/宣传片/成果', '资料/宣传片/工作台')
    write(source, payload[0] + '/开始这里.md', '# 公开小说示例方法\n使用者填自己的目标。\n')
    write(source, payload[1] + '/demo.mp4', '合成自制视频展示示例')
    write(source, payload[2] + '/README.md', '# 宣传片工作台\n公开案例入口。\n')
    labels = {'写小说': 'Novel Writing', '宣传片': 'Promo Video'}
    original_config = (source / 'backend/template_profiles.json').read_bytes()
    result = release.build(tmp_path / '业务示例单包', src=source, profiles=('research',),
                           package_name='MiracleHarness2', public_payload_roots=payload,
                           public_module_labels=labels)
    root = Path(result['packages'][0]['path'])
    config = json.loads((root / '模板配置.json').read_text(encoding='utf-8'))
    profile = json.loads((root / 'backend/template_profiles.json').read_text(encoding='utf-8'))['profiles']['research']
    marks = json.loads((root / '内置标记.json').read_text(encoding='utf-8'))
    assert {'写小说', '宣传片'}.issubset(config['modules'])
    assert all(config['module_labels'][name] == label for name, label in labels.items())
    assert set(payload).issubset(profile['template_roots']) and set(payload).issubset(marks['paths'])
    assert (root / payload[1] / 'demo.mp4').read_text(encoding='utf-8') == '合成自制视频展示示例'
    assert result['packages'][0]['cleanup']['public_payload_roots'] == list(payload)
    assert '业务示例：写小说、宣传片' in (root / 'README.md').read_text(encoding='utf-8')
    assert release_clean.VIDEO_DEMO_NOTE in (root / 'README.md').read_text(encoding='utf-8')
    (root / 'README.md').write_text('# 已建发行副本\n', encoding='utf-8')
    release_clean.sanitize(root)
    assert release_clean.VIDEO_DEMO_NOTE in (root / 'README.md').read_text(encoding='utf-8')
    child = tmp_path / '公开示例新项目'
    new_project.make(child, root)
    for rel in ('资料/写小说/方法/开始这里.md', '资料/宣传片/成果/demo.mp4', '资料/宣传片/工作台/README.md'):
        assert (child / rel).read_bytes() == (root / rel).read_bytes()
    assert (source / 'backend/template_profiles.json').read_bytes() == original_config


@pytest.mark.parametrize('payload, labels', [
    (('笔记',), None), (('索引/state.db',), None), (('资料',), None),
    (('资料/文献/../../笔记',), None), (('资料/不存在/方法',), None),
    ((), {'未选择': 'Unselected'})
])
def test_public_payload_rejects_history_traversal_missing_paths_and_unselected_labels(source, tmp_path, payload, labels):
    output = tmp_path / '无效业务示例'
    with pytest.raises(ValueError):
        release.build(output, src=source, profiles=('research',), public_payload_roots=payload,
                      public_module_labels=labels)
    assert not output.exists()


def test_selected_public_methods_explain_missing_optional_skills_and_keep_available_links(source, tmp_path):
    entry = '资料/写小说/方法/开始这里.md'
    write(source, entry, '# 开始这里\n\n3. 让它读路线技能及阶段路线，先确认实际阶段，再做一件有验收的任务。\n\n'
          '[路线技能](<../../../技能库/业务/novel/missing/SKILL.md>)\n'
          '[通用方法](<../../../技能库/自动化科研交互界面/SKILL.md>)\n')
    write(source, '资料/写小说/方法/阶段路线.md',
          '可选方法：[小说方法 [biz:novel:missing]](<../../../技能库/业务/novel/missing/SKILL.md>)\n')
    write(source, '资料/写小说/方法/阶段路线.en.md',
          'Optional: [Novel Method [biz:novel:missing]](<../../../技能库/业务/novel/missing/SKILL.en.md>)\n')
    result = release.build(tmp_path / '可选方法清楚声明', src=source, profiles=('research',),
                           public_payload_roots=('资料/写小说/方法',))
    root = Path(result['packages'][0]['path'])
    body = (root / entry).read_text(encoding='utf-8')
    assert '先让它读阶段路线' in body and '如选择额外方法，再准备对应技能' in body
    assert '路线技能（可选方法，本发行包未内置）' in body
    assert '[通用方法](<../../../技能库/自动化科研交互界面/SKILL.md>)' in body
    route = (root / '资料/写小说/方法/阶段路线.md').read_text(encoding='utf-8')
    assert '小说方法 [biz:novel:missing]（可选方法，本发行包未内置）' in route
    english = (root / '资料/写小说/方法/阶段路线.en.md').read_text(encoding='utf-8')
    assert 'Novel Method [biz:novel:missing] (optional method; not bundled in this release)' in english
    assert '业务/novel/missing/SKILL' not in body + route + english
    assert result['packages'][0]['cleanup']['optional_skill_links_removed'] == 3
    assert '路线技能及阶段路线' in (source / entry).read_text(encoding='utf-8')


def test_invalid_unused_business_profile_and_stale_filename_assets_are_cleaned_idempotently(source, tmp_path):
    config = source / 'backend/template_profiles.json'
    data = json.loads(config.read_text(encoding='utf-8'))
    data['profiles']['business'] = {'modules': ['宣传片'], 'skills': [],
                                   'template_roots': ['资料/宣传片/不存在的方法'], 'module_skills': []}
    config.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    write(source, '工具库/安装指南/应用截图/来源.json',
          json.dumps({'assets': [{'file': 'already-removed.png', 'source': 'https://example.org'}]}))
    write(source, '工具库/安装指南/应用截图/来源.md', '# 原官网来源\n')
    write(source, '工具库/安装指南/catalog.json', json.dumps({'version': 1, 'items': [{
        'id': 'document', 'notice': '程序不随包，图片是官方文档示例。保留安装说明。',
        'notice_en': 'Program not included, image is an official documentation example. Setup unchecked.'
    }]}, ensure_ascii=False))
    result = release.build(tmp_path / '准确元数据清理', src=source, profiles=('research',))
    root = Path(result['packages'][0]['path'])
    profiles = json.loads((root / 'backend/template_profiles.json').read_text(encoding='utf-8'))['profiles']
    assert set(profiles) == {'general', 'research'}
    assert result['packages'][0]['cleanup']['excluded_invalid_profiles'] == ['business']
    records = json.loads((root / '工具库/安装指南/应用截图/来源.json').read_text(encoding='utf-8'))
    assert records['assets'] == []
    catalog = json.loads((root / '工具库/安装指南/catalog.json').read_text(encoding='utf-8'))['items'][0]
    assert '图片是官方文档示例' not in catalog['notice'] and '官方文字链接' in catalog['notice']
    assert 'image is an official' not in catalog['notice_en'] and 'official text links' in catalog['notice_en']
    public_docs = root / '工具库/安装指南/应用截图/来源.md'
    note = public_docs.read_bytes()
    release_clean.sanitize(root)
    assert public_docs.read_bytes() == note
    assert 'business' in json.loads(config.read_text(encoding='utf-8'))['profiles']


def test_release_copy_manifest_still_describes_the_final_readme(source, tmp_path):
    result = release.build(tmp_path / "检查包内复制记录", src=source)
    for package in result["packages"]:
        target = Path(package["path"])
        manifest = json.loads((target / "新项目复制清单.json").read_text(encoding="utf-8"))
        records = {row["path"]: row for row in manifest["files"]}
        assert "README.md" in records
        for rel, row in records.items():
            assert row["bytes"] == (target / rel).stat().st_size, rel
        assert manifest["file_count"] == len(manifest["files"])
        assert manifest["bytes"] == sum(row["bytes"] for row in manifest["files"])


def test_clean_build_removes_unverified_images_but_keeps_originals_links_and_licenses(source, tmp_path):
    third_party = '工具库/安装指南/应用截图/official.png'
    logo = '工具库/安装指南/应用图片/official.svg'
    own = '工具库/安装指南/应用图片/miracleharness-links.png'
    for rel in (third_party, logo, own):
        write(source, rel, '合成图片字节')
    write(source, '工具库/安装指南/catalog.json', json.dumps({'version': 1, 'items': [
        {'id': 'foreign', 'image': third_party, 'image_kind': 'screenshot', 'logo': logo,
         'official': 'https://example.org', 'guide': '工具库/安装指南/从这里开始.md'},
        {'id': 'own', 'image': own, 'image_kind': 'original', 'official': 'https://example.org/own'}
    ]}, ensure_ascii=False))
    guide = '# 官方入口\n\n![第三方截图](应用截图/official.png)\n\n[官网](https://example.org)\n\n![原创](应用图片/miracleharness-links.png)\n'
    write(source, '工具库/安装指南/从这里开始.md', guide)
    write(source, '工具库/安装指南/参考/网页链接.md', '| 项目 | 图片 | 类型 |\n|---|---|---|\n| [官网](https://example.org) | ![截图](../应用截图/official.png) | 官网截图 |\n')
    write(source, '工具库/安装指南/应用截图/来源.json', json.dumps({'assets': [{'path': third_party, 'source': 'https://example.org'}]}))
    write(source, '工具库/安装指南/应用截图/来源.md', f'# 图源\n\n`{third_party}`\n\n[官网](https://example.org)\n')
    write(source, 'backend/tests/evidence/private-browser.png', '不得进入发行的本机证据')
    original = {f.relative_to(source).as_posix(): f.read_bytes() for f in source.rglob('*') if f.is_file()}
    notice = 'Required Notice: Synthetic author; contact: public@example.org\n'
    result = release.build(tmp_path / '图片清理发行', src=source, notice_override=notice)
    for package in result['packages']:
        root = Path(package['path'])
        assert not (root / third_party).exists() and not (root / logo).exists()
        assert not (root / 'backend/tests/evidence').exists()
        assert (root / own).is_file()
        assert (root / 'LICENSE').read_bytes() == original['LICENSE']
        assert (root / 'NOTICE').read_text(encoding='utf-8') == notice
        catalog = json.loads((root / '工具库/安装指南/catalog.json').read_text(encoding='utf-8'))
        assert 'image' not in catalog['items'][0] and 'logo' not in catalog['items'][0]
        assert catalog['items'][0]['official'] == 'https://example.org'
        assert catalog['items'][1]['image'] == own
        body = (root / '工具库/安装指南/从这里开始.md').read_text(encoding='utf-8')
        assert '应用截图/official.png' not in body and 'https://example.org' in body
        assert '![原创](应用图片/miracleharness-links.png)' in body
        table = (root / '工具库/安装指南/参考/网页链接.md').read_text(encoding='utf-8')
        assert '| - | 官网入口 |' in table
        records = json.loads((root / '工具库/安装指南/应用截图/来源.json').read_text(encoding='utf-8'))
        assert records['assets'] == []
        assert package['cleanup']['removed_file_count'] >= 2
    assert {f.relative_to(source).as_posix(): f.read_bytes() for f in source.rglob('*') if f.is_file()} == original
    handover = (Path(result['root']) / '本地发行交接.md').read_text(encoding='utf-8')
    assert '商业研究' in handover and '未上传' in handover
    assert 'tmdysx' not in handover and 'Claude' not in handover


def test_source_lock_projection_preserves_and_verifies_only_bundled_originals(source, tmp_path):
    rel = '技能库/自动化科研交互界面/source/LICENSE.txt'
    blob = write(source, rel, 'MIT License\nSynthetic original.\n').read_bytes()
    lock = {'schema': 1, 'audit_sha256': 'original-audit', 'files': [
        {'local_path': rel, 'sha256': hashlib.sha256(blob).hexdigest(), 'license': 'MIT'},
        {'local_path': '技能库/未授权私人技能/source/missing.txt', 'sha256': 'f' * 64, 'license': 'MIT'}
    ]}
    lock_rel = '技能库/自动化科研交互界面/sources.lock.json'
    write(source, lock_rel, json.dumps(lock, ensure_ascii=False))
    result = release.build(tmp_path / '来源投影发行', src=source)
    for package in result['packages']:
        root = Path(package['path'])
        projected = json.loads((root / lock_rel).read_text(encoding='utf-8'))
        assert projected['files'] == lock['files'][:1]
        assert projected['upstream_audit_sha256'] == 'original-audit'
        assert projected['release_projection']['excluded_records'] == 1
        assert (root / rel).read_bytes() == blob
    assert json.loads((source / lock_rel).read_text(encoding='utf-8')) == lock


def test_reference_cards_replace_removed_screenshot_with_explicit_original_artwork(source, tmp_path):
    foreign = '工具库/安装指南/应用截图/repo.jpg'
    own = '工具库/安装指南/应用图片/miracleharness-repo-links.png'
    write(source, foreign, '合成官网图片')
    write(source, own, '合成自有示意图')
    write(source, '工具库/安装指南/参考/开源项目.md',
          '| 项目 | 用途 | 许可 | 怎么用 | 图片 | 类型 | 来源 |\n|---|---|---|---|---|---|---|\n'
          '| [项目](https://example.org) | 示例 | MIT | 读文档 | ![官网](../应用截图/repo.jpg) | 官网截图 | [实际截图页](https://example.org) |\n')
    result = release.build(tmp_path / '原创参考卡发行', src=source)
    for package in result['packages']:
        root = Path(package['path'])
        body = (root / '工具库/安装指南/参考/开源项目.md').read_text(encoding='utf-8')
        assert '![MiracleHarness 原创示意](../应用图片/miracleharness-repo-links.png)' in body
        assert '| 原创示意图 | MiracleHarness 原创；[官网入口](https://example.org) |' in body
        assert '官网截图' not in body and '应用截图/repo.jpg' not in body
        assert (root / own).is_file() and not (root / foreign).exists()


def test_source_lock_hash_mismatch_blocks_clean_release(source, tmp_path):
    rel = '技能库/自动化科研交互界面/source/LICENSE.txt'
    write(source, rel, 'MIT License\nSynthetic original.')
    write(source, '技能库/自动化科研交互界面/sources.lock.json', json.dumps({'files': [{'local_path': rel, 'sha256': '0' * 64}]}))
    with pytest.raises(ValueError, match='来源指纹不符'):
        release.build(tmp_path / '不应放行篡改来源', src=source)


def test_release_examples_require_explicit_public_copy_and_staging_never_changes_source(source, tmp_path):
    manifest_rel = '资料/文献/工作台/入门示例.json'
    example_rel = '资料/文献/工作台/示例/example.pdf'
    original = write(source, example_rel, '原示例不可被覆盖')
    write(source, manifest_rel, json.dumps({'version': 1, 'library': [{'source': '工作台/示例/example.pdf'}]}))
    cfg = new_project.profile_config(source, 'general')
    cfg['template_roots'].append('资料/文献/工作台')
    with pytest.raises(ValueError, match='公开信息检查'):
        with release_clean.staged_source(source, [cfg]):
            pass
    public = write(tmp_path, '公开案例.pdf', '公开示例')
    with release_clean.staged_source(source, [cfg], {example_rel: public}) as (stage, report):
        assert (stage / example_rel).read_text(encoding='utf-8') == '公开示例'
        assert json.loads((stage / manifest_rel).read_text(encoding='utf-8'))['library']
        assert report['public_demo_replacements'] == [example_rel]
        stage_path = stage
    assert not stage_path.exists()
    assert original.read_text(encoding='utf-8') == '原示例不可被覆盖'


def test_release_keeps_only_the_new_database_of_public_onboarding_examples(source, tmp_path):
    config = source / 'backend/template_profiles.json'
    profiles = json.loads(config.read_text(encoding='utf-8'))
    for profile in profiles['profiles'].values():
        profile['template_roots'].append('资料/文献/工作台')
    config.write_text(json.dumps(profiles, ensure_ascii=False), encoding='utf-8')
    sample = {'version': 1, 'downloads': [{
        'title': 'Attention Is All You Need', 'url': 'https://arxiv.org/pdf/1706.03762',
        'authors': 'Ashish Vaswani et al.', 'year': '2017', 'venue': 'NeurIPS',
        'why': 'Public demonstration only', 'note': 'Official link; full paper not bundled'
    }]}
    write(source, '资料/文献/工作台/入门示例.json', json.dumps(sample, ensure_ascii=False))
    source_db = (source / '索引/state.db').read_bytes()  # 源库故意是私人标记，不能被复制或连上。
    result = release.build(tmp_path / '公开示例索引发行', src=source)
    for package in result['packages']:
        root = Path(package['path'])
        db = root / '索引/state.db'
        assert db.is_file() and db.read_bytes() != source_db
        assert package['cleanup']['fresh_public_demo_db'] is True
        assert package['cleanup']['public_demo_counts']['downloads'] == 1
        connection = sqlite3.connect('file:' + db.as_posix() + '?mode=ro', uri=True)
        try:
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            texts = []
            for (name,) in tables:
                rows = connection.execute('SELECT * FROM "' + name.replace('"', '""') + '"').fetchall()
                texts.extend(value for row in rows for value in row if isinstance(value, str))
            body = '\n'.join(texts)
            assert 'Attention Is All You Need' in body
            # 下载正文保存为公开 Markdown，库中保留计数与操作记录。
            documents = '\n'.join(f.read_text(encoding='utf-8') for f in (root / '资料/文献').rglob('*.md'))
            assert 'https://arxiv.org/pdf/1706.03762' in documents
            assert '不能默认带入的合成私人标记' not in body
            assert str(source) not in body and str(root) not in body and 'miracle-release-' not in body
        finally:
            connection.close()
    assert (source / '索引/state.db').read_bytes() == source_db


def test_missing_research_resources_prevents_half_a_release(source, tmp_path):
    (source / "技能库/科研-返修").rename(source / "技能库/暂移返修技能")
    output = tmp_path / "不允许仅成功一半"
    with pytest.raises(ValueError):
        release.build(output, src=source)
    assert not output.exists()


@pytest.mark.parametrize("problem", ["unknown_profile", "missing_skill", "missing_template"])
def test_invalid_profile_resources_fail_before_creating_a_project(source, tmp_path, problem):
    profile = "general"
    if problem == "unknown_profile":
        profile = "不存在的版本"
    elif problem == "missing_skill":
        (source / "技能库/交付自查").rename(source / "技能库/移动后的技能")
    else:
        (source / "资料/文献/方法").rename(source / "资料/文献/移动后的模板")
    target = tmp_path / "不完整不能创建"
    with pytest.raises(ValueError):
        new_project.make(target, source, profile=profile)
    assert not target.exists()


def test_release_profile_refuses_extra_private_selection(source, tmp_path):
    target = tmp_path / "不扩大发行范围"
    with pytest.raises(ValueError):
        new_project.make(target, source, profile="general", extra=["资料/天气/本次材料.md"])
    assert not target.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows目录联接拒绝")
def test_release_selected_template_rejects_a_directory_junction(source, tmp_path):
    from test_builtin import _make_junction

    old = source / "资料/文献/方法"
    old.rename(source / "资料/文献/原模板")
    external = tmp_path / "外部资料"
    external.mkdir()
    write(external, "外部文件.md", "不能穿出项目")
    _make_junction(old, external)
    target = tmp_path / "不允许的发行模板"
    with pytest.raises(ValueError):
        new_project.make(target, source, profile="general")
    assert not target.exists()
