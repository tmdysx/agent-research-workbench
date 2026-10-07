"""File marks, safe inheritance and real inter-process CAS; all writes are temporary."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import builtin
import new_project
import store
from project import Project


def put(root, rel, content='example'):
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return target


def test_absent_read_and_missing_history_are_read_only(tmp_path):
    first = builtin.read_marks(tmp_path)
    assert first['paths'] == [] and not first['exists']
    assert first['revision'] == hashlib.sha256(b'').hexdigest()
    assert not list(tmp_path.iterdir())
    data = builtin.parse_marks(b'{"version":1,"paths":["materials/missing.pdf"]}')
    assert data['paths'] == ['materials/missing.pdf']


def test_guard_reentrant_and_raw_cas_repairs_broken_json(tmp_path):
    put(tmp_path, builtin.MARKS_FILE, 'broken json')
    revision = builtin.marks_revision(tmp_path)
    with pytest.raises(builtin.Invalid):
        builtin.read_marks(tmp_path)
    with builtin.marks_guard(tmp_path):
        result = builtin.replace_marks(tmp_path, ['materials/missing.pdf'], revision)
    assert result['paths'] == ['materials/missing.pdf']
    assert builtin.mark_state(tmp_path, 'materials/missing.pdf')['state'] == 'missing'
    with pytest.raises(builtin.Conflict):
        builtin.replace_marks(tmp_path, [], revision)


@pytest.mark.parametrize('path', ['../outside', 'C:/outside', 'a\\b', '索引/state.db',
                                 '资料/PPT/CON.pdf', 'a/x.pdf ', '自动化/交付/J1.md',
                                 '归档/历史包/demo.pdf', '资料/PPT/预览缓存/1.png',
                                 'materials/Node_Modules/pkg/file.js', '自动化/Agent/G1.md'])
def test_history_parser_rejects_unsafe_paths(tmp_path, path):
    raw = json.dumps({'version': 1, 'paths': [path]}, ensure_ascii=False).encode()
    with pytest.raises(builtin.Invalid):
        builtin.parse_marks(raw)


def test_explicit_set_records_plain_log_and_preserves_original(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    rel = '资料/PPT/导出/example.txt'
    original = put(tmp_path, rel)
    conn = store.connect(tmp_path / '索引/state.db')
    try:
        before = builtin.mark_state(tmp_path, rel)
        result = builtin.set_mark(conn, Project(tmp_path), rel, True, before['project'], before['revision'])
        assert result['state'] == 'marked' and result['changed'] and result['log_id']
        assert original.read_text(encoding='utf-8') == 'example'
        assert list((tmp_path / '笔记/日志').glob('*.md'))
        with pytest.raises(builtin.Conflict):
            builtin.set_mark(conn, Project(tmp_path), rel, False, before['project'], before['revision'])
        result = builtin.set_mark(conn, Project(tmp_path), rel, False, result['project'], result['revision'])
        assert result['state'] == 'unmarked'
    finally:
        conn.close()


def test_make_filters_marked_business_and_projects_each_generation(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    source = tmp_path / 'source'
    ppt, notes = '资料/PPT/导出/example.txt', '资料/文献/示例.txt'
    put(source, ppt)
    put(source, notes)
    put(source, '资料/PPT/私有.txt', 'private')
    original = builtin.read_marks(source)
    builtin.replace_marks(source, [ppt, notes], original['revision'])
    first, second, excluded = [tmp_path / x for x in ('child', 'grandchild', 'without-ppt')]
    new_project.make(first, source, business_modules=['PPT'])
    new_project.make(second, first)
    new_project.make(excluded, source, business_modules=[])
    for target in (first, second):
        assert builtin.read_marks(target)['paths'] == sorted([ppt, notes], key=str.casefold)
        assert (target / ppt).is_file() and (target / notes).is_file()
        assert not (target / '资料/PPT/私有.txt').exists()
    assert not (excluded / '资料/PPT').exists()
    assert builtin.read_marks(excluded)['paths'] == [notes]
    assert builtin.read_marks(source)['paths'] == sorted([ppt, notes], key=str.casefold)


def test_cross_process_compare_and_swap_has_one_winner(tmp_path):
    revision = builtin.read_marks(tmp_path)['revision']
    script = '''import json, sys
from pathlib import Path
import builtin
root, rel, revision = sys.argv[1:]
print('ready', flush=True)
sys.stdin.readline()
try:
    out = builtin.replace_marks(Path(root), [rel], revision)
    print(json.dumps({'status':'saved','paths':out['paths']}), flush=True)
except builtin.Conflict:
    print(json.dumps({'status':'conflict'}), flush=True)
'''
    env = {**os.environ, 'PYTHONPATH': str(Path(builtin.__file__).parent), 'PYTHONIOENCODING': 'utf-8'}
    children = []
    try:
        for rel in ('materials/alpha.txt', 'materials/beta.txt'):
            proc = subprocess.Popen([sys.executable, '-X', 'utf8', '-c', script, str(tmp_path), rel, revision],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding='utf-8', env=env,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            children.append(proc)
        for proc in children:
            assert proc.stdout.readline().strip() == 'ready'
        for proc in children:
            proc.stdin.write('go\n')
            proc.stdin.flush()
        results = []
        for proc in children:
            stdout, stderr = proc.communicate(timeout=20)
            assert proc.returncode == 0, stderr
            results.append(json.loads(stdout))
        assert sorted(r['status'] for r in results) == ['conflict', 'saved']
        winner = next(r for r in results if r['status'] == 'saved')
        assert builtin.read_marks(tmp_path)['paths'] == winner['paths']
    finally:
        for proc in children:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)


def test_current_project_custom_database_allowed_and_outside_database_rejected(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    rel = 'materials/example.txt'
    put(root, rel)
    inside_db = root / 'index-custom/runtime.sqlite'
    monkeypatch.setenv('RC_DB', str(inside_db))
    conn = store.connect(inside_db)
    try:
        state = builtin.mark_state(root, rel)
        result = builtin.set_mark(conn, Project(root), rel, True, state['project'], state['revision'])
        assert result['state'] == 'marked' and result['log_id']
        db_state = builtin.mark_state(root, 'index-custom/runtime.sqlite')
        with pytest.raises(builtin.Invalid, match='数据库'):
            builtin.set_mark(conn, Project(root), 'index-custom/runtime.sqlite', True,
                             db_state['project'], db_state['revision'])
    finally:
        conn.close()
    outside_db = tmp_path / 'outside/state.db'
    monkeypatch.setenv('RC_DB', str(outside_db))
    conn = store.connect(outside_db)
    try:
        with pytest.raises(builtin.Invalid):
            builtin.set_mark(conn, Project(root), rel, False, result['project'], result['revision'])
        assert builtin.read_marks(root)['paths'] == [rel]
    finally:
        conn.close()


def test_wrong_database_and_project_identity_leave_marks_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    root = tmp_path / 'project'
    rel = 'materials/example.txt'
    put(root, rel)
    conn = store.connect(tmp_path / 'other/state.db')
    try:
        state = builtin.mark_state(root, rel)
        with pytest.raises(builtin.Conflict, match='项目'):
            builtin.set_mark(conn, Project(root), rel, True, 'wrong-project', state['revision'])
        with pytest.raises(builtin.Invalid):
            builtin.set_mark(conn, Project(root), rel, True, state['project'], state['revision'])
        assert not (root / builtin.MARKS_FILE).exists()
    finally:
        conn.close()


def test_missing_file_mark_can_be_cleared_but_not_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    rel = 'materials/missing.pdf'
    state = builtin.replace_marks(tmp_path, [rel], builtin.marks_revision(tmp_path))
    conn = store.connect(tmp_path / '索引/state.db')
    try:
        action = builtin.mark_state(tmp_path, rel)
        assert action['state'] == 'missing' and action['toggle_allowed'] and action['enabled']
        with pytest.raises(builtin.Invalid, match='不存在'):
            builtin.set_mark(conn, Project(tmp_path), rel, True, state['project'], state['revision'])
        cleared = builtin.set_mark(conn, Project(tmp_path), rel, False, state['project'], state['revision'])
        assert cleared['state'] == 'missing' and not cleared['enabled'] and not cleared['toggle_allowed']
        assert cleared['log_id']
        assert builtin.read_marks(tmp_path)['paths'] == []
    finally:
        conn.close()


def test_required_states_are_fast_read_only_and_cannot_be_switched_off(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    for rel in ('backend/main.py', '.mcp.json', 'AGENTS.md', '资料/PPT/内置/sample.txt', '归档/内置/example.txt'):
        put(tmp_path, rel)
    monkeypatch.setattr(builtin, 'files', lambda *a, **kw: pytest.fail('single-file state must not scan files'))
    conn = store.connect(tmp_path / '索引/state.db')
    try:
        for rel in ('backend/main.py', '.mcp.json', 'AGENTS.md', '资料/PPT/内置/sample.txt', '归档/内置/example.txt'):
            state = builtin.mark_state(tmp_path, rel)
            assert state['state'] == 'required' and not state['toggle_allowed']
            with pytest.raises(builtin.Invalid):
                builtin.set_mark(conn, Project(tmp_path), rel, False, state['project'], state['revision'])
        if os.name == 'nt':
            assert builtin.mark_state(tmp_path, 'BACKEND/MAIN.PY')['state'] == 'required'
            assert builtin.mark_state(tmp_path, '.MCP.JSON')['state'] == 'required'
        assert not (tmp_path / builtin.MARKS_FILE).exists()
        assert not (tmp_path / '笔记').exists()
    finally:
        conn.close()


def test_case_alias_duplicates_rejected_and_unmark_matches_existing_spelling(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    raw = json.dumps({'version': 1, 'paths': ['materials/A.txt', 'materials/a.txt']}).encode()
    with pytest.raises(builtin.Invalid, match='大小写'):
        builtin.parse_marks(raw)
    put(tmp_path, 'materials/A.txt')
    state = builtin.replace_marks(tmp_path, ['materials/A.txt'], builtin.marks_revision(tmp_path))
    conn = store.connect(tmp_path / '索引/state.db')
    try:
        result = builtin.set_mark(conn, Project(tmp_path), 'materials/a.txt', False, state['project'], state['revision'])
        assert not result['enabled'] and builtin.read_marks(tmp_path)['paths'] == []
    finally:
        conn.close()


@pytest.mark.skipif(os.name != 'nt', reason='Windows case-insensitive path lookup')
def test_case_alias_uses_real_module_spelling_through_two_generations(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    root = tmp_path / 'source'
    rel = '资料/PPT/导出/Example.txt'
    put(root, rel)
    conn = store.connect(root / '索引/state.db')
    try:
        state = builtin.mark_state(root, rel.lower())
        result = builtin.set_mark(conn, Project(root), rel.lower(), True, state['project'], state['revision'])
        assert result['path'] == rel
        assert builtin.read_marks(root)['paths'] == [rel]
    finally:
        conn.close()
    # Handwritten historical aliases are accepted, then projected to the actual
    # filename instead of creating a different module spelling in the child.
    builtin.replace_marks(root, [rel.lower()], builtin.marks_revision(root))
    assert builtin.project_marks(root, [rel])['paths'] == [rel]
    child, grandchild = tmp_path / 'child', tmp_path / 'grandchild'
    new_project.make(child, root, business_modules=['PPT'])
    new_project.make(grandchild, child)
    for target in (child, grandchild):
        assert builtin.read_marks(target)['paths'] == [rel]
        assert (target / rel).exists()


def test_real_junction_rejected_for_files_and_manifest_and_alias(tmp_path):
    if os.name != 'nt':
        pytest.skip('Windows junction check')
    root = tmp_path / 'project'
    outside = tmp_path / 'outside'
    root.mkdir()
    put(outside, 'example.txt', 'outside bytes')
    link = root / 'linked'
    env = {**os.environ, 'MARK_TEST_LINK': str(link), 'MARK_TEST_TARGET': str(outside)}
    result = subprocess.run(['powershell', '-NoProfile', '-Command',
                             'New-Item -ItemType Junction -Path $env:MARK_TEST_LINK -Target $env:MARK_TEST_TARGET | Out-Null'],
                            capture_output=True, text=True, env=env,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert result.returncode == 0, result.stderr
    try:
        state = builtin.mark_state(root, 'linked/example.txt')
        assert state['state'] == 'ineligible' and not state['toggle_allowed']
        put(root, 'normal.txt')
        assert builtin.mark_state(root, 'normal.txt', original=link / 'example.txt')['state'] == 'ineligible'
        builtin.replace_marks(root, ['linked/example.txt'], builtin.marks_revision(root))
        with pytest.raises(ValueError, match='无法复制'):
            new_project.make(tmp_path / 'blocked', root, business_modules=[])
        assert not (tmp_path / 'blocked').exists()
        assert (outside / 'example.txt').read_text() == 'outside bytes'
    finally:
        os.rmdir(link)  # Remove only the verified temporary junction, never its target.


def test_profile_keeps_marks_without_reintroducing_filtered_core_and_extra_is_once(tmp_path, monkeypatch):
    monkeypatch.delenv('RC_DB', raising=False)
    source = tmp_path / 'source'
    manual = '资料/PPT/导出/example.txt'
    unselected = '资料/小说/private.txt'
    filtered_core = '技能库/unused/SKILL.md'
    for rel in (manual, unselected, filtered_core, 'backend/cache.pyc', '资料/PPT/内置/通用/template.txt',
                '资料/小说/内置/通用/template.txt', 'materials/once.txt'):
        put(source, rel)
    profile = {'modules': ['PPT'], 'skills': [], 'template_roots': ['资料/PPT/内置/通用'],
               'module_skills': [], 'builtin_skill_ids': [], 'module_labels': {}}
    put(source, 'backend/template_profiles.json', json.dumps({'version': 1, 'profiles': {'general': profile}}))
    builtin.replace_marks(source, [manual, unselected, filtered_core, 'backend/cache.pyc'], builtin.marks_revision(source))
    first, second = tmp_path / 'first', tmp_path / 'second'
    new_project.make(first, source, profile='general')
    new_project.make(second, first, extra=['资料/PPT/导出/example.txt'])
    for target in (first, second):
        assert (target / manual).is_file()
        assert builtin.read_marks(target)['paths'] == [manual]
        assert not (target / filtered_core).exists()
        assert not (target / 'backend/cache.pyc').exists()
        assert not (target / unselected).exists()
    third = tmp_path / 'third'
    new_project.make(third, source, business_modules=['PPT'], extra=['materials/once.txt'])
    fourth = tmp_path / 'fourth'
    new_project.make(fourth, third)
    assert (third / 'materials/once.txt').exists()
    assert not (fourth / 'materials/once.txt').exists()
    assert (fourth / manual).exists()


def test_missing_mark_in_unselected_business_is_ignored_but_selected_blocks_before_creation(tmp_path):
    source = tmp_path / 'source'
    missing = '资料/PPT/missing.pdf'
    put(source, '资料/PPT/内置/template.txt')
    builtin.replace_marks(source, [missing], builtin.marks_revision(source))
    skipped = tmp_path / 'skipped'
    new_project.make(skipped, source, business_modules=[])
    assert builtin.read_marks(skipped)['paths'] == []
    with pytest.raises(ValueError, match='无法复制'):
        new_project.make(tmp_path / 'blocked', source, business_modules=['PPT'])
    assert not (tmp_path / 'blocked').exists()


def test_generated_marks_are_not_offered_as_one_time_extra(tmp_path):
    source = tmp_path / 'source'
    put(source, '资料/测试/example.txt')
    builtin.replace_marks(source, ['资料/测试/example.txt'], builtin.marks_revision(source))
    assert builtin.MARKS_FILE not in {r['path'] for r in builtin.browse(source)['items']}
    child = tmp_path / 'child'
    new_project.make(child, source)
    assert builtin.read_marks(child)['paths'] == ['资料/测试/example.txt']
