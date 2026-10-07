"""文件内置小锁与存档关联；只在临时项目中存取，不碰作者存档。"""
import hashlib
import json

import pytest

import builtin
import snapshot
import store


A = '资料/论文/a.md'
B = '资料/论文/b.md'
C = '资料/实验/c.md'


def write(root, rel, text):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding='utf-8')


def marks(root, paths):
    return builtin.replace_marks(root, paths, builtin.marks_revision(root))


def setup(proj):
    write(proj.root, 'backend/a.py', 'old core')
    for rel in (A, B, C):
        write(proj.root, rel, 'old ' + rel)
    conn = store.connect(proj.db_path)
    store.migrate(conn)
    return conn


def test_full_save_keeps_unlocked_files_and_uses_archived_marks_bytes(proj, monkeypatch):
    conn = setup(proj)
    marks(proj.root, [A])
    original = (proj.root / builtin.MARKS_FILE).read_bytes()
    put = snapshot._put

    def changing_put(project, src, sha=None):
        got = put(project, src, sha)
        if src.name == builtin.MARKS_FILE:
            marks(proj.root, [B])
        return got

    monkeypatch.setattr(snapshot, '_put', changing_put)
    saved = snapshot.save(conn, proj, name='bytes', mode='全量', by='人')
    assert saved['builtin_marks_version'] == 1 and saved['builtin_marks'] == [A]
    assert saved['builtin_marks_revision'] == hashlib.sha256(original).hexdigest()
    assert A in saved['builtin_scope'] and B not in saved['builtin_scope']
    assert snapshot.old_file(proj, saved['code'], B)[0].read_text(encoding='utf-8') == 'old ' + B
    assert builtin.read_marks(proj.root)['paths'] == [B]
    assert snapshot.old_file(proj, saved['code'], builtin.MARKS_FILE)[0].read_bytes() == original
    conn.close()


def test_ignore_does_not_pretend_marked_content_or_marks_were_saved(proj):
    conn = setup(proj)
    marks(proj.root, [A])
    write(proj.root, snapshot.IGNORE, A + '\n')
    one = snapshot.save(conn, proj, name='ignore content', mode='全量', by='人')
    assert one['builtin_marks'] == [A] and one['builtin_marks_missing'] == [A]
    assert A not in one['builtin_scope']
    # 历史中未保存的标记原件不因后来取消忽略就被“恢复”误删。
    write(proj.root, snapshot.IGNORE, '')
    write(proj.root, A, 'ignored content kept')
    snapshot.restore(conn, proj, one['code'], by='人', confirm=True, whole=True)
    assert (proj.root / A).read_text(encoding='utf-8') == 'ignored content kept'
    write(proj.root, snapshot.IGNORE, builtin.MARKS_FILE + '\n')
    two = snapshot.save(conn, proj, name='ignore marks', mode='全量', by='人')
    assert two['builtin_marks_status'] == 'not_saved' and 'builtin_marks_version' not in two
    marks(proj.root, [B])
    snapshot.restore(conn, proj, two['code'], by='人', confirm=True, whole=True)
    assert builtin.read_marks(proj.root)['paths'] == [B]
    conn.close()


def test_default_restore_recovers_history_marks_and_locked_content_only(proj):
    conn = setup(proj)
    marks(proj.root, [A])
    saved = snapshot.save(conn, proj, name='default', mode='全量', by='人')
    marks(proj.root, [B])
    write(proj.root, A, 'new A')
    write(proj.root, B, 'new B')
    with pytest.raises(store.NeedConfirm) as preview:
        snapshot.restore(conn, proj, saved['code'], by='人', whole=False)
    info = preview.value.info
    assert info['builtin_marks']['added'] == [A] and info['builtin_marks']['removed'] == [B]
    assert '内置标记：开启 1 个、解除 1 个' in str(preview.value)
    snapshot.restore(conn, proj, saved['code'], by='人', whole=False, confirm=True,
                     builtin_revision=info['builtin_marks']['revision'])
    assert builtin.read_marks(proj.root)['paths'] == [A]
    assert (proj.root / A).read_text(encoding='utf-8') == 'old ' + A
    assert (proj.root / B).read_text(encoding='utf-8') == 'new B'
    conn.close()


def test_partial_restore_only_updates_actual_selected_files_marks(proj):
    conn = setup(proj)
    marks(proj.root, [A, B])
    saved = snapshot.save(conn, proj, name='partial', mode='全量', by='人')
    marks(proj.root, [B, C])
    write(proj.root, A, 'new A')
    with pytest.raises(store.NeedConfirm) as preview:
        snapshot.restore(conn, proj, saved['code'], by='人', paths=[A])
    assert '仅恢复所选文件的内置标记' in str(preview.value)
    snapshot.restore(conn, proj, saved['code'], by='人', paths=[A], confirm=True)
    assert builtin.read_marks(proj.root)['paths'] == sorted([A, B, C])
    # 标记本身是唯一变化时也可恢复：文件不必为了更新锁强制重写。
    marks(proj.root, [B, C])
    result = snapshot.restore(conn, proj, saved['code'], by='人', paths=[A], confirm=True)
    assert result['replaced'] == 1 and builtin.read_marks(proj.root)['paths'] == sorted([A, B, C])
    conn.close()


def test_marks_only_restore_does_not_restore_material_contents(proj):
    conn = setup(proj)
    marks(proj.root, [A])
    saved = snapshot.save(conn, proj, name='marks only', mode='全量', by='人')
    marks(proj.root, [B])
    write(proj.root, A, 'new A')
    snapshot.restore(conn, proj, saved['code'], by='人', paths=[builtin.MARKS_FILE], confirm=True)
    assert builtin.read_marks(proj.root)['paths'] == [A]
    assert (proj.root / A).read_text(encoding='utf-8') == 'new A'
    conn.close()


def test_old_unknown_and_explicit_empty_are_distinct(proj):
    conn = setup(proj)
    empty = snapshot.save(conn, proj, name='new empty', mode='全量', by='人')
    folder = snapshot._folder(proj, empty['code'])
    old = dict(empty)
    for key in list(old):
        if key.startswith('builtin_marks'):
            old.pop(key)
    snapshot._rewrite_meta(folder, old)
    marks(proj.root, [A])
    write(proj.root, A, 'later')
    with pytest.raises(store.NeedConfirm) as preview:
        snapshot.restore(conn, proj, empty['code'], by='人', whole=True)
    assert '旧档未记录内置标记，保留现在的名单' in str(preview.value)
    snapshot.restore(conn, proj, empty['code'], by='人', confirm=True, whole=True)
    assert builtin.read_marks(proj.root)['paths'] == [A]
    snapshot._rewrite_meta(folder, empty)
    snapshot.restore(conn, proj, empty['code'], by='人', confirm=True, whole=True)
    assert builtin.read_marks(proj.root)['paths'] == []
    conn.close()


def test_restore_stale_confirmation_refuses_before_content_changes(proj):
    conn = setup(proj)
    marks(proj.root, [A])
    saved = snapshot.save(conn, proj, name='race', mode='全量', by='人')
    marks(proj.root, [B])
    write(proj.root, A, 'later')
    with pytest.raises(store.NeedConfirm) as preview:
        snapshot.restore(conn, proj, saved['code'], by='人', whole=True)
    marks(proj.root, [C])
    with pytest.raises(store.Refused, match='确认期间已变化'):
        snapshot.restore(conn, proj, saved['code'], by='人', whole=True, confirm=True,
                         builtin_revision=preview.value.info['builtin_marks']['revision'])
    assert (proj.root / A).read_text(encoding='utf-8') == 'later'
    assert builtin.read_marks(proj.root)['paths'] == [C]
    conn.close()


def test_restore_failure_rolls_back_contents_and_marks(proj, monkeypatch):
    conn = setup(proj)
    marks(proj.root, [A])
    saved = snapshot.save(conn, proj, name='rollback', mode='全量', by='人')
    marks(proj.root, [B])
    write(proj.root, A, 'later')
    current = (proj.root / builtin.MARKS_FILE).read_bytes()
    def fail(*args, **kwargs):
        raise OSError('forced mark failure')
    monkeypatch.setattr(builtin, 'replace_marks', fail)
    with pytest.raises(OSError, match='forced mark failure'):
        snapshot.restore(conn, proj, saved['code'], by='人', whole=True, confirm=True)
    assert (proj.root / A).read_text(encoding='utf-8') == 'later'
    assert (proj.root / builtin.MARKS_FILE).read_bytes() == current
    conn.close()


def test_partial_copy_failure_does_not_leave_a_new_file_or_clear_current_marks(proj, monkeypatch):
    conn = setup(proj)
    marks(proj.root, [A])
    saved = snapshot.save(conn, proj, name='partial copy failure', mode='全量', by='人')
    (proj.root / A).unlink()
    marks(proj.root, [B])
    current = (proj.root / builtin.MARKS_FILE).read_bytes()
    copy = snapshot.shutil.copy2
    def partial_copy(src, dst, *args, **kwargs):
        if dst == proj.root / A:
            dst.write_text('partial', encoding='utf-8')
            raise OSError('forced partial copy')
        return copy(src, dst, *args, **kwargs)
    monkeypatch.setattr(snapshot.shutil, 'copy2', partial_copy)
    with pytest.raises(OSError, match='forced partial copy'):
        snapshot.restore(conn, proj, saved['code'], by='人', paths=[A], confirm=True)
    assert not (proj.root / A).exists()
    assert (proj.root / builtin.MARKS_FILE).read_bytes() == current
    conn.close()


def test_full_restore_can_repair_invalid_marks_but_partial_refuses(proj):
    conn = setup(proj)
    marks(proj.root, [A])
    saved = snapshot.save(conn, proj, name='invalid current', mode='全量', by='人')
    write(proj.root, builtin.MARKS_FILE, '{broken')
    with pytest.raises(store.Refused, match='不能局部恢复'):
        snapshot.restore(conn, proj, saved['code'], by='人', paths=[A], confirm=True)
    snapshot.restore(conn, proj, saved['code'], by='人', whole=True, confirm=True)
    assert builtin.read_marks(proj.root)['paths'] == [A]
    conn.close()


def test_slim_uses_saved_scope_and_preserves_history_rules(proj):
    conn = setup(proj)
    write(proj.root, '笔记/总览.md', 'old note')
    write(proj.root, '治理/计划/P1.md', 'old plan')
    marks(proj.root, [A])
    saved = snapshot.save(conn, proj, name='slim', mode='全量', by='人')
    marks(proj.root, [B])
    snapshot.slim(conn, proj, saved['code'], by='人')
    meta = snapshot._meta(snapshot._folder(proj, saved['code']))
    assert A in meta['picks'] and B not in meta['picks']
    assert snapshot.old_file(proj, saved['code'], A)[0].is_file()
    assert snapshot.old_file(proj, saved['code'], builtin.MARKS_FILE)[0].is_file()
    write(proj.root, '笔记/总览.md', 'new note')
    write(proj.root, '治理/计划/P1.md', 'new plan')
    snapshot.restore(conn, proj, saved['code'], by='人', confirm=True)
    assert (proj.root / '笔记/总览.md').read_text(encoding='utf-8') == 'new note'
    assert (proj.root / '治理/计划/P1.md').read_text(encoding='utf-8') == 'new plan'
    assert builtin.read_marks(proj.root)['paths'] == [A]
    conn.close()


def test_marked_notes_and_plans_do_not_override_history_protection(proj):
    conn = setup(proj)
    note, plan = '笔记/总览.md', '治理/计划/P1.md'
    write(proj.root, note, 'old note')
    write(proj.root, plan, 'old plan')
    marks(proj.root, [A, note, plan])
    saved = snapshot.save(conn, proj, name='protected history', mode='全量', by='人')
    marks(proj.root, [B])
    write(proj.root, note, 'new note')
    write(proj.root, plan, 'new plan')
    result = snapshot.restore(conn, proj, saved['code'], by='人', paths=[note, plan], confirm=True)
    assert result['nothing'] is True and builtin.read_marks(proj.root)['paths'] == [B]
    snapshot.restore(conn, proj, saved['code'], by='人', whole=False, confirm=True)
    assert (proj.root / note).read_text(encoding='utf-8') == 'new note'
    assert (proj.root / plan).read_text(encoding='utf-8') == 'new plan'
    assert set(builtin.read_marks(proj.root)['paths']) == {A, note, plan}
    conn.close()
