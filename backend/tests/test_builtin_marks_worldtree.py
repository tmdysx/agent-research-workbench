"""内置名单在独立分枝与合并中保持历史范围、有效JSON和冲突证据。"""
from pathlib import Path

import builtin
import snapshot
import store
import worldtree


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
    write(proj.root, 'backend/a.py', 'core')
    for rel in (A, B, C):
        write(proj.root, rel, rel)
    marks(proj.root, [A])
    conn = store.connect(proj.db_path)
    store.migrate(conn)
    return conn


def test_grow_uses_archived_marks_and_copies_unlocked_material(proj):
    conn = setup(proj)
    saved = snapshot.save(conn, proj, name='base', mode='全量', by='人')
    marks(proj.root, [B])
    branch = worldtree.grow(conn, proj, name='history', base=saved['code'], by='人')
    root = Path(branch['path'])
    assert builtin.read_marks(root)['paths'] == [A]
    assert (root / C).read_text(encoding='utf-8') == C
    conn.close()


def test_disjoint_mark_changes_merge_as_valid_path_set(proj):
    conn = setup(proj)
    branch = worldtree.grow(conn, proj, name='disjoint', by='人')
    root = Path(branch['path'])
    marks(root, [A, B])
    marks(proj.root, [A, C])
    result = worldtree.merge(conn, proj, branch['code'], by='人')
    assert builtin.read_marks(proj.root)['paths'] == sorted([A, B, C])
    assert builtin.MARKS_FILE in result['merged'] and result['conflicts'] == []
    conn.close()


def test_invalid_branch_marks_remain_conflict_without_overwriting_trunk(proj):
    conn = setup(proj)
    branch = worldtree.grow(conn, proj, name='invalid', by='人')
    root = Path(branch['path'])
    raw = (proj.root / builtin.MARKS_FILE).read_bytes()
    write(root, builtin.MARKS_FILE, '{invalid')
    result = worldtree.merge(conn, proj, branch['code'], by='人')
    assert (proj.root / builtin.MARKS_FILE).read_bytes() == raw
    assert result['conflicts'][0]['path'] == builtin.MARKS_FILE
    conflict = proj.root / worldtree.REG / branch['code'] / '冲突'
    assert (conflict / builtin.MARKS_FILE).read_text(encoding='utf-8') == '{invalid'
    assert (conflict / (builtin.MARKS_FILE + '.主干')).read_bytes() == raw
    conn.close()


def test_new_mark_of_trunk_deleted_file_conflicts_without_resurrection(proj):
    conn = setup(proj)
    branch = worldtree.grow(conn, proj, name='deleted', by='人')
    root = Path(branch['path'])
    marks(root, [A, B])
    (proj.root / B).unlink()
    result = worldtree.merge(conn, proj, branch['code'], by='人')
    assert not (proj.root / B).exists()
    assert builtin.read_marks(proj.root)['paths'] == [A]
    assert result['conflicts'][0]['path'] == builtin.MARKS_FILE
    conn.close()


def test_new_trunk_mark_of_branch_deleted_file_is_not_silently_accepted(proj):
    conn = setup(proj)
    branch = worldtree.grow(conn, proj, name='branch deletion', by='人')
    root = Path(branch['path'])
    (root / B).unlink()
    marks(root, [A, C])
    marks(proj.root, [A, B])
    result = worldtree.merge(conn, proj, branch['code'], by='人')
    assert not (proj.root / B).exists()
    assert builtin.read_marks(proj.root)['paths'] == sorted([A, B])
    assert result['conflicts'][0]['path'] == builtin.MARKS_FILE
    conn.close()
