"""在临时目录真读来源、版本、迁移冲突和 Windows 联接，不改项目正本。"""
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import record_refs as refs


def write(root, source, text):
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def ref(source="", scope="项目", code="需-1", kind="requirement", revision=""):
    return {"kind": kind, "scope": scope, "source": source, "code": code, "revision": revision}


def test_identity_is_source_scoped_and_revision_independent(proj):
    a = refs.normalize(ref("治理/需求/甲.md"))
    b = refs.normalize(ref("治理/需求/乙.md"))
    assert a["identity"] != b["identity"]
    assert a["identity"] == refs.normalize(dict(a, revision="b" * 64))["identity"]
    first = refs.normalize(ref("治理/目标/S1-1 甲.md", "S1-1", "S2-1", "task"))
    second = refs.normalize(ref("治理/目标/S1-2 乙.md", "S1-2", "S2-1", "task"))
    assert first["identity"] != second["identity"] and first["code"] == second["code"] == "S2-1"
    plans = [refs.normalize(ref(f"治理/计划/{scope}/P1 · 历史.md", scope, "P1", "formal_plan")) for scope in ("S1-1", "S1-2")]
    assert plans[0]["identity"] != plans[1]["identity"]


def test_missing_and_ambiguous_are_explicit_without_latest_guess(proj):
    a, b = ref("治理/需求/甲.md"), ref("治理/需求/乙.md")
    write(proj.root, a["source"], "甲原文")
    write(proj.root, b["source"], "乙原文")
    resolved = refs.resolve(proj, ref(), [a, b])
    assert resolved["state"] == "ambiguous" and len(resolved["candidates"]) == 2
    assert resolved["document"] is None
    assert refs.resolve(proj, ref("治理/需求/不存在.md"))["state"] == "missing"
    assert refs.resolve(proj, ref(), [])["state"] == "missing"
    assert refs.resolve(proj, ref(), [a])["document"]["text"] == "甲原文"


def test_real_byte_revision_utf8_and_stale(proj):
    f = write(proj.root, "治理/需求/项目.md", "原编号需-1\n多字节中文原文。")
    current = refs.resolve(proj, ref("治理/需求/项目.md"))
    assert current["ref"]["revision"] == hashlib.sha256(f.read_bytes()).hexdigest()
    assert current["document"]["complete"] and current["document"]["text"].endswith("原文。")
    stale = refs.resolve(proj, ref("治理/需求/项目.md", revision="old-version"))
    assert stale["state"] == "stale" and stale["requested_revision"] == "old-version"


def test_legacy_central_alias_keeps_original_number_and_identity(proj):
    old, new = "资料/模块甲/需求.md", "治理/需求/模块甲.md"
    write(proj.root, new, "# 原编号需-1\n完全相同原文")
    legacy = refs.resolve(proj, ref(old, "模块甲"))
    central = refs.resolve(proj, ref(new, "模块甲"))
    assert legacy["original_source"] == old and legacy["resolved_source"] == new
    assert legacy["ref"]["identity"] == central["ref"]["identity"]
    assert legacy["ref"]["code"] == "需-1" and old in legacy["aliases"]
    write(proj.root, old, "# 原编号需-1\n完全相同原文")
    assert refs.resolve(proj, ref(old, "模块甲"))["state"] == "ok"


def test_conflicting_aliases_report_both_real_versions_even_central_read(proj):
    old, new = "资料/甲/需求.md", "治理/需求/甲.md"
    write(proj.root, old, "旧正本原话")
    write(proj.root, new, "集中正本原话")
    for source in (old, new):
        result = refs.resolve(proj, ref(source, "甲"))
        assert result["state"] == "conflict"
        assert {d["text"] for d in result["conflicts"]} == {"旧正本原话", "集中正本原话"}
        assert len({d["revision"] for d in result["conflicts"]}) == 2


def test_existing_oversize_alias_is_unverifiable_even_when_central_body_is_complete(proj):
    old, new = "资料/甲/需求.md", "治理/需求/甲.md"
    canonical = write(proj.root, new, "集中正本原话")
    legacy = write(proj.root, old, "")
    with legacy.open("wb") as stream:
        stream.truncate(refs.MAX_HASH_BYTES + 1)
    for source in (old, new):
        result = refs.resolve(proj, ref(source, "甲"))
        assert result["state"] == "conflict_unverifiable" and not result["complete"]
        assert result["resolved_source"] == new and old in result["aliases"]
        assert result["ref"]["revision"] == hashlib.sha256(canonical.read_bytes()).hexdigest()
        assert result["document"]["text"] == "集中正本原话"
        assert result["document"]["body_complete"] and not result["document"]["complete"]
        assert result["document"]["resolution_incomplete"]
        assert len(result["unverified_sources"]) == 1
        failure = result["unverified_sources"][0]
        assert failure["source"] == old and failure["state"] == "oversize"
        assert failure["bytes"] == refs.MAX_HASH_BYTES + 1 and "oversize" in failure["reason"]


def test_shared_cache_identity_observation_ignores_read_marks_but_detects_replacement(proj):
    cache = write(proj.root, "索引/state.db-shm", "SQLite 临时读标记")
    snap = refs.Snapshot(proj)
    row = snap.observe_identity("索引/state.db-shm")
    first = snap.report()
    cache.write_bytes(b"another temporary mark")
    assert not snap.validate() and snap.report()["digest"] == first["digest"]
    assert not row["content_fingerprint"] and row["version_basis"] == "ordinary_path_identity_only"
    # 保留旧对象，再由新对象占同一路径，确保核验真正比较文件身份。
    cache.rename(cache.with_name("old-shared-cache"))
    cache.write_bytes(b"replacement")
    assert any("state.db-shm" in issue for issue in snap.validate())


def test_explicit_migration_mapping_and_malicious_or_corrupt_manifest(proj):
    write(proj.root, "治理/需求/甲.md", "原文")
    manifest = write(proj.root, "治理/迁移记录.json", json.dumps({"version": 2, "files": [{"old": "旧位置/甲.md", "new": "治理/需求/甲.md"}]}))
    assert refs.resolve(proj, ref("旧位置/甲.md"))["resolved_source"] == "治理/需求/甲.md"
    manifest.write_text(json.dumps({"files": [{"old": "旧位置/甲.md", "new": "../泄漏.md"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="迁移"):
        refs.resolve(proj, ref("旧位置/甲.md"))
    manifest.write_text("{bad-json", encoding="utf-8")
    with pytest.raises(ValueError, match="迁移"):
        refs.resolve(proj, ref("治理/需求/甲.md"))


@pytest.mark.parametrize("source", ["../a.md", "/a.md", "C:/a.md", "C:a.md", "//server/a.md", "a//b.md", "a/./b.md", "a/../b.md", "a\x00b", "a/NUL.md", "a./b", "a /b", "a.md:stream"])
def test_path_escapes_and_windows_aliases_refused(proj, source):
    with pytest.raises(refs.UnsafePath):
        refs.resolve(proj, ref(source))


def test_real_windows_junction_cannot_read_outside_project(proj, tmp_path):
    if os.name != "nt":
        pytest.skip("Windows 联接专项")
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    write(outside, "秘密.md", "不能泄漏")
    link = proj.root / "联接"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
    assert result.returncode == 0, result.stderr
    with pytest.raises(refs.UnsafePath, match="联接"):
        refs.resolve(proj, ref("联接/秘密.md"))
    # 不用递归删除联接；临时目录的测试清理由 pytest 负责。


def test_real_symlink_refused_when_os_allows_it(proj, tmp_path):
    target = write(proj.root, "普通.md", "原文")
    link = proj.root / "符号.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("本机 Windows 未授予创建符号链接权限；目录联接另有实际测试")
    with pytest.raises(refs.UnsafePath):
        refs.resolve(proj, ref("符号.md"))


def test_cloud_reparse_tag_is_not_a_directory_junction():
    info = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_reparse_tag=0x9000001A)
    assert not refs._linked(info)
    assert refs._linked(SimpleNamespace(st_mode=stat.S_IFDIR, st_reparse_tag=0xA0000003))


def test_large_invalid_utf8_and_metadata_reads_do_not_claim_full_text(proj):
    f = write(proj.root, "大文件.md", "正文" * 80)
    snap = refs.Snapshot(proj)
    row = snap.read("大文件.md", limit=11)
    assert row["truncated"] and not row["complete"]
    assert row["revision"] == hashlib.sha256(f.read_bytes()).hexdigest()
    metadata = snap.read("大文件.md", include_text=False)
    assert metadata["text"] == "" and not metadata["text_loaded"]
    f = proj.root / "坏编码.md"
    f.write_bytes(b"text\xff")
    row = snap.read("坏编码.md")
    assert row["encoding_error"] and not row["complete"]


def test_snapshot_tracks_byte_edits_new_records_and_digest_ignores_clock(proj):
    f = write(proj.root, "治理/需求/项目.md", "初版")
    snap = refs.Snapshot(proj)
    snap.children("治理/需求")
    snap.read("治理/需求/项目.md")
    a, b = snap.report(selection={"goal": "S1-1"}), snap.report(selection={"goal": "S1-1"})
    assert a["digest"] == b["digest"] and not snap.validate()
    f.write_text("新版", encoding="utf-8")
    assert snap.validate()
    fresh = refs.Snapshot(proj)
    fresh.children("治理/需求")
    write(proj.root, "治理/需求/新增.md", "新记录")
    assert any("目录" in issue for issue in fresh.validate())


def test_read_view_caches_bytes_and_explicitly_omits_git(proj):
    f = write(proj.root, "治理/需求/项目.md", "初版")
    (proj.root / ".git").mkdir()
    snap = refs.Snapshot(proj)
    root = refs.ReadPath(proj.root, snapshot=snap)
    assert not (root / ".git").exists() and (proj.root / ".git").exists()
    assert (root / "治理/需求/项目.md").read_text(encoding="utf-8") == "初版"
    f.write_text("变化后", encoding="utf-8")
    assert (root / "治理/需求/项目.md").read_text(encoding="utf-8") == "初版"
    assert snap.validate()
