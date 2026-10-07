"""按来源保留历史编号，安全读取项目普通文件并核对一次请求的真实版本。"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote

import governance_paths as gp

MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_HASH_BYTES = 32 * 1024 * 1024
MAX_ENTRIES = 20000
_DEVICE = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


class UnsafePath(ValueError):
    """引用不是当前项目内的普通路径。"""


class Changed(ValueError):
    """读取期间文件、目录或路径类型发生变化。"""


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def relative_source(value, *, directory=False):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise UnsafePath("来源应是项目内的相对路径文字")
    value = value.replace("\\", "/")
    if value.startswith("/") or PureWindowsPath(value).drive or any(c in value for c in ':*?"<>|'):
        raise UnsafePath("来源不能是绝对路径、盘符或通配路径")
    if directory and value.endswith("/"):
        value = value[:-1]
    if any(part in ("", ".", "..") or part.endswith((".", " ")) or _DEVICE.match(part)
           for part in value.split("/")):
        raise UnsafePath("来源不能包含空段、父级路径或 Windows 路径别名")
    return value


def _linked(info):
    # 普通云文件也有重解析属性；只拒绝真实链接与目录联接。
    return (stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", None)
            == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003))


def _stamp(info):
    return tuple(getattr(info, field, None) for field in
                 ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns", "st_reparse_tag"))


def _opened_stamp(info):
    # Windows 的 fstat/lstat 对 ctime 的语义不同；比较同一对象的身份、大小及修改时间。
    return tuple(getattr(info, field, None) for field in
                 ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_reparse_tag"))


def normalize(ref):
    if not isinstance(ref, dict):
        raise ValueError("记录引用应是 kind/scope/source/code/revision 对象")
    out = {}
    for key in ("kind", "scope", "source", "code", "revision"):
        value = ref.get(key, "")
        if key == "source" and value:
            out[key] = relative_source(value)
            continue
        if not isinstance(value, str) or any(ord(c) < 32 for c in value):
            raise ValueError("引用字段须是没有控制字符的文字")
        out[key] = relative_source(value) if key == "source" and value else value.strip()
    if not out["kind"]:
        raise ValueError("记录引用缺少 kind")
    stable = [out[k] for k in ("kind", "scope", "source", "code")]
    out["identity"] = _digest(json.dumps(stable, ensure_ascii=False, separators=(",", ":")).encode())
    return out


class Snapshot:
    """请求内缓存；返回前重核所有观察，绝不跨请求复用正文。"""

    def __init__(self, p):
        self.root = Path(os.path.abspath(p.root))
        self._observed = {}
        self._directories = {}
        self._files = {}
        self._identity_only = set()
        self._identity_files = {}
        self._aliases = None
        self._count = 0

    def path(self, source, *, directory=False):
        rel = relative_source(source, directory=directory)
        candidate = self.root.joinpath(*rel.split("/"))
        current = self.root
        for part in (None, *rel.split("/")):
            if part is not None:
                current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                self._observed.setdefault(current, None)
                continue
            if _linked(info):
                raise UnsafePath("来源路径不能是符号链接或目录联接：" + rel)
            if current != candidate and not stat.S_ISDIR(info.st_mode):
                raise UnsafePath("来源的父路径不是普通目录：" + rel)
            self._observed.setdefault(current, _stamp(info))
        return candidate

    def _relative(self, path):
        try:
            return Path(path).relative_to(self.root).as_posix()
        except ValueError as exc:
            raise UnsafePath("路径越出当前项目") from exc

    def children(self, source):
        rel = relative_source(source, directory=True)
        d = self.path(rel, directory=True)
        if rel in self._directories:
            return list(self._directories[rel])
        if not d.exists():
            self._directories[rel] = ()
            return []
        if not d.is_dir():
            raise UnsafePath("枚举来源不是普通目录：" + rel)
        names = tuple(sorted(e.name for e in os.scandir(d)))
        self._count += len(names)
        if self._count > MAX_ENTRIES:
            raise ValueError("工作包来源数量超过有界读取上限")
        self._directories[rel] = names
        return list(names)

    def walk(self, source):
        rel = relative_source(source, directory=True)
        stack = [rel]
        while stack:
            current = stack.pop()
            for name in self.children(current):
                child = current + "/" + name
                f = self.path(child)
                if f.is_dir():
                    yield child, "directory"
                    stack.append(child)
                elif f.is_file():
                    yield child, "file"
                else:
                    raise UnsafePath("来源不是普通文件或目录：" + child)

    def read(self, source, *, include_text=True, limit=MAX_DOCUMENT_BYTES):
        rel = relative_source(source, directory=True)
        if rel not in self._files:
            f = self.path(rel)
            if not f.exists():
                row = {"source": rel, "state": "missing", "revision": "", "bytes": 0}
                raw = b""
            elif f.is_dir():
                row = {"source": rel, "state": "directory", "revision": "", "bytes": 0}
                raw = b""
            elif not f.is_file():
                raise UnsafePath("来源不是普通文件：" + rel)
            else:
                before = f.lstat()
                if before.st_size > MAX_HASH_BYTES:
                    row = {"source": rel, "state": "oversize", "revision": "", "bytes": before.st_size}
                    raw = b""
                else:
                    with f.open("rb") as stream:
                        opened = os.fstat(stream.fileno())
                        if _opened_stamp(opened) != _opened_stamp(before):
                            raise Changed("文件在打开时变化：" + rel)
                        raw = stream.read(MAX_HASH_BYTES + 1)
                        after = os.fstat(stream.fileno())
                    self.path(rel)
                    if len(raw) > MAX_HASH_BYTES or _opened_stamp(before) != _opened_stamp(after) or _stamp(before) != _stamp(f.lstat()):
                        raise Changed("文件在读取时变化：" + rel)
                    row = {"source": rel, "state": "ok", "revision": _digest(raw), "bytes": len(raw)}
            self._files[rel] = (row, raw)
        row, raw = self._files[rel]
        out = dict(row, missing=row["state"] == "missing", text_loaded=bool(include_text),
                   truncated=False, encoding_error=False, text="")
        if include_text and row["state"] == "ok":
            out["truncated"] = len(raw) > limit
            part = raw[:limit]
            try:
                raw.decode("utf-8-sig")
                out["text"] = part.decode("utf-8-sig", errors="ignore" if out["truncated"] else "strict")
            except UnicodeDecodeError:
                out["text"] = part.decode("utf-8-sig", errors="replace")
                out["encoding_error"] = True
        out["complete"] = row["state"] == "ok" and not out["truncated"] and not out["encoding_error"]
        return out

    def observe_identity(self, source):
        """仅观察 SQLite 现有共享缓存路径；临时读标记不属于业务正文版本。"""
        rel = relative_source(source)
        f = self.path(rel)
        self._identity_only.add(f)
        state = "missing" if not f.exists() else ("ok" if f.is_file() else "directory")
        row = {"source": rel, "state": state, "revision": "", "bytes": 0,
               "role": "sqlite_shared_cache", "version_basis": "ordinary_path_identity_only",
               "content_fingerprint": False}
        self._identity_files[rel] = row
        return dict(row)

    def bytes(self, source):
        row = self.read(source)
        if not row["complete"]:
            raise ValueError("正本不能完整读取：" + source + "（" + row["state"] + "）")
        return self._files[row["source"]][1]

    def aliases(self):
        if self._aliases is not None:
            return self._aliases
        self._aliases = {}
        doc = self.read("治理/迁移记录.json")
        if doc["missing"]:
            return self._aliases
        if not doc["complete"]:
            raise ValueError("治理迁移记录不能完整读取")
        try:
            data = json.loads(doc["text"])
            if not isinstance(data, dict) or not isinstance(data.get("files"), list):
                raise ValueError("缺少 files 列表")
            for item in data["files"]:
                if not isinstance(item, dict):
                    raise ValueError("迁移记录不是对象")
                old, new = relative_source(item["old"]), relative_source(item["new"])
                self.path(old)
                self.path(new)
                if old in self._aliases and self._aliases[old] != new:
                    raise ValueError("同一旧路径有多个迁移目标")
                self._aliases[old] = new
        except (KeyError, TypeError, ValueError) as exc:
            self._aliases = None
            raise ValueError("治理迁移记录无效：" + str(exc)) from exc
        return self._aliases

    def validate(self):
        issues = []
        for path, expected in self._observed.items():
            try:
                info = path.lstat()
                actual = _stamp(info)
                linked = _linked(info)
            except FileNotFoundError:
                actual, linked = None, False
            if path in self._identity_only and actual is not None and expected is not None:
                different = tuple(actual[i] for i in (0, 1, 2, 6)) != tuple(expected[i] for i in (0, 1, 2, 6))
            else:
                different = actual != expected
            if linked or different:
                issues.append("来源路径或版本变化：" + self._relative(path))
        for rel, names in self._directories.items():
            try:
                d = self.path(rel)
                actual = tuple(sorted(e.name for e in os.scandir(d))) if d.is_dir() else ()
                if actual != names:
                    issues.append("来源目录变化：" + rel)
            except (OSError, ValueError):
                issues.append("来源目录不能重新核对：" + rel)
        for rel, (row, _) in self._files.items():
            if row["state"] != "ok":
                continue
            try:
                f = self.path(rel)
                with f.open("rb") as stream:
                    raw = stream.read(MAX_HASH_BYTES + 1)
                if _digest(raw) != row["revision"]:
                    issues.append("来源指纹变化：" + rel)
            except (OSError, ValueError):
                issues.append("来源文件不能重新核对：" + rel)
        return list(dict.fromkeys(issues))

    def report(self, *, selection=None, extra_sources=(), retries=0, issues=()):
        sources = [dict(row) for row, _ in self._files.values()] + list(self._identity_files.values()) + list(extra_sources)
        sources.sort(key=lambda r: (r["source"], r.get("revision", "")))
        stable = {"sources": sources, "selection": selection or {}}
        return {"generated_at": datetime.now().isoformat(timespec="seconds"), "sources": sources,
                "digest": _digest(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode()),
                "consistent": not issues, "retries": retries, "issues": list(issues)}


def resolve(p, ref, candidates=(), *, snapshot=None, include_text=True):
    snap = snapshot or Snapshot(p)
    original = normalize(ref)
    if not original["source"]:
        matches = {}
        for candidate in candidates:
            row = normalize(candidate)
            if all(not original[k] or row[k] == original[k] for k in ("kind", "scope", "code")):
                matches[row["identity"]] = row
        if len(matches) != 1:
            return {"state": "ambiguous" if matches else "missing", "ref": original,
                    "document": None, "candidates": list(matches.values()), "aliases": []}
        chosen = next(iter(matches.values()))
        chosen["revision"] = original["revision"] or chosen["revision"]
        return resolve(p, chosen, snapshot=snap, include_text=include_text)
    source = original["source"]
    mapping = snap.aliases()
    central = gp.central(source)
    if source == "资料/蓝图/蓝图.md" and snap.read("治理/任务/蓝图.md", include_text=False)["state"] == "ok":
        central = "治理/任务/蓝图.md"
    destinations = {mapping.get(source, central)}
    if central != source and mapping.get(source, central) != central:
        destinations.add(central)
    if len(destinations) != 1:
        return {"state": "ambiguous", "ref": original, "document": None,
                "candidates": [dict(original, source=s) for s in sorted(destinations)], "aliases": []}
    target = next(iter(destinations))
    new = snap.read(target, include_text=include_text)
    old = snap.read(source, include_text=include_text) if source != target else new
    doc = new if new["state"] != "missing" else old
    resolved = doc["source"]
    current = normalize(dict(original, source=resolved, revision=doc["revision"]))
    aliases = {s for s in (source, target) if s != resolved}
    aliases.update(old_source for old_source, new_source in mapping.items() if new_source == resolved and old_source != resolved)
    parts = resolved.split("/")
    if len(parts) == 3 and parts[:2] in (["治理", "需求"], ["治理", "任务"]):
        module = unquote(Path(parts[2]).stem)
        aliases.add("资料/" + module + ("/需求.md" if parts[1] == "需求" else "/蓝图.md"))
    elif len(parts) == 3 and parts[:2] == ["治理", "目标"]:
        aliases.add("资料/蓝图/" + parts[2])
    elif len(parts) == 3 and parts[:2] == ["治理", "戒律"]:
        aliases.add("资料/戒律/" + parts[2])
    elif len(parts) == 4 and parts[:3] == ["治理", "戒律", "模块"]:
        aliases.add("资料/" + unquote(Path(parts[3]).stem) + "/戒律.md")
    elif parts[:2] == ["治理", "计划"]:
        aliases.add("/".join(parts[1:]))
    counterparts = [snap.read(alias, include_text=include_text) for alias in sorted(aliases)]
    conflicts = [row for row in [old, *counterparts] if row["state"] == doc["state"] == "ok" and row["revision"] != doc["revision"]]
    conflict = bool(conflicts)
    unverified = list({row["source"]: dict(row, reason="别名来源无法完成字节指纹核对：" + row["state"])
                       for row in [old, *counterparts]
                       if row["source"] != resolved and row["state"] not in {"ok", "missing"}}.values())
    state = "conflict" if conflict else ("conflict_unverifiable" if unverified else doc["state"])
    if state == "ok" and not doc["complete"]:
        state = "incomplete"
    if not conflict and not unverified and original["revision"] and original["revision"] != doc["revision"]:
        state = "stale"
    if unverified:
        doc = dict(doc, body_complete=doc["complete"], complete=False, resolution_incomplete=True)
    return {"state": state, "ref": current, "document": doc, "original_source": source,
            "resolved_source": resolved, "aliases": sorted(aliases),
            "complete": state == "ok" and doc["complete"], "unverified_sources": unverified,
            "requested_revision": original["revision"], "candidates": [],
            "conflicts": list({row["source"]: row for row in [doc, *conflicts]}.values()) if conflict else []}


class ReadPath(type(Path())):
    """旧读取器的请求内路径视图；不改全局解析器，不触发本机 Git。"""

    def __new__(cls, *args, snapshot=None):
        self = super().__new__(cls, *args)
        self.snapshot = snapshot
        return self

    def __init__(self, *args, snapshot=None):
        super().__init__(*args)

    def with_segments(self, *args):
        return type(self)(*args, snapshot=self.snapshot)

    def _rel(self):
        return self.snapshot._relative(self)

    def _guard(self):
        rel = self._rel()
        if rel == ".":
            return self.snapshot.root
        return self.snapshot.path(rel)

    def exists(self, *, follow_symlinks=True):
        if self._rel().split("/", 1)[0] == ".git":
            return False
        return self._guard().exists()

    def is_file(self, *, follow_symlinks=True):
        return self._guard().is_file()

    def is_dir(self):
        return self._guard().is_dir()

    def resolve(self, strict=False):
        self._guard()
        return self.with_segments(os.path.abspath(self))

    def read_bytes(self):
        return self.snapshot.bytes(self._rel())

    def read_text(self, encoding=None, errors=None):
        return self.read_bytes().decode(encoding or "utf-8", errors=errors or "strict")

    def iterdir(self):
        for name in self.snapshot.children(self._rel()):
            child = self / name
            child._guard()
            yield child

    def glob(self, pattern, *, case_sensitive=None):
        parts = pattern.replace("\\", "/").split("/")
        paths = [self]
        for part in parts:
            paths = [d / name for d in paths if d.is_dir()
                     for name in self.snapshot.children(d._rel())
                     if fnmatch.fnmatchcase(name.casefold(), part.casefold())]
            for path in paths:
                path._guard()
        yield from paths

    def rglob(self, pattern, *, case_sensitive=None):
        for rel, _ in self.snapshot.walk(self._rel()):
            if fnmatch.fnmatchcase(Path(rel).name.casefold(), pattern.casefold()):
                yield self.with_segments(self.snapshot.root / rel)
