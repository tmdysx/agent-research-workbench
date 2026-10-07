"""技能库：应用自带几份好用的技能。正本就留在项目里，哪家 agent 都看得到、调得到（AGENTS.md 里的技能目录 · MCP read_skill）；
另外可以装一份到 Claude Code 自动发现的地方（本项目，或本机），人点了才装。

- 技能库在当前项目 `技能库/<名>/SKILL.md`；业务清单在 `技能库/业务/manifest.json`，不借用别的项目
- 「装到本项目」→ 项目/.claude/skills/<名>/（只有这个项目里的 agent 用）
- 「装到本机」  → ~/.claude/skills/<名>/（这台电脑所有项目都能用）
- **已经有不一样的同名技能：先问人；人同意覆盖，旧的先挪进 索引/技能备份/**——绝不静默覆盖，也不删
- 模块专属技能放在模块里：资料/<模块>/技能/SKILL.md（作者 09-28：「这个模块要有自己的skill」「模块专属技能就放模块里吧」）。
  技能页一起列（编号「模块:文献」），装过去叫模块名；就在模块里改，不「复制一份改」
"""
from __future__ import annotations

import hashlib
import atomic
import json
import os
import re
import shutil
import stat
from contextvars import ContextVar
from functools import wraps
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import project as proj
from project import CODE_DIR, Project, SKIP_DIRS

LIB = CODE_DIR / "技能库"
MODULE_DIR = "技能"                                   # 资料/<模块>/技能/SKILL.md
MOD = "模块:"
_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
MANIFEST = "业务/manifest.json"
_BIZ_ID = re.compile(r"biz:([a-z][a-z0-9-]*):([a-z][a-z0-9-]*):([a-z][a-z0-9-]*)\Z")
_DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.I)

# 一次读取内复用已经检查的父链、目录和字节；返回后全部丢弃。
# 没有进程级或跨请求缓存，下次读取仍重新核文件、联接和来源指纹。
_READ = ContextVar("skill_read_snapshot", default=None)


def _reading(function):
    @wraps(function)
    def call(*args, **kwargs):
        if _READ.get() is not None:
            return function(*args, **kwargs)
        snapshot = {"ordinary": set(), "observed": {}, "trees": {}, "bytes": {}, "digests": {}}
        token = _READ.set(snapshot)
        try:
            result = function(*args, **kwargs)
            if function.__name__ in {"inventory", "read", "catalog", "find"}:
                _verify_read(snapshot)
            return result
        finally:
            _READ.reset(token)
    return call


def _stamp(info) -> tuple:
    return tuple(getattr(info, field, None) for field in (
        "st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns", "st_reparse_tag"))


def _linked(info) -> bool:
    return (stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_reparse_tag", None) == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003))


def _verify_read(snapshot) -> None:
    """输出前再直接检查一次，读取途中换路径或改文件就丢弃本次结果。"""
    for path, expected in snapshot["observed"].items():
        try:
            info = path.lstat()
        except OSError as exc:
            raise ValueError("技能文件在读取期间发生变化，请重新读取：" + str(path)) from exc
        if _linked(info):
            raise ValueError("技能路径不能是符号链接或目录联接：" + str(path))
        if _stamp(info) != expected:
            raise ValueError("技能文件在读取期间发生变化，请重新读取：" + str(path))


def _file_bytes(path: Path) -> bytes:
    current = _READ.get()
    if current is None:
        return path.read_bytes()
    if path not in current["bytes"]:
        current["bytes"][path] = path.read_bytes()
    return current["bytes"][path]


class Conflict(Exception):
    """那边已经有一份不一样的——要人点了「覆盖」才行。消息给人看。"""


def machine_home() -> Path:
    """「本机」= 用户目录下的 .claude。测试时用 RC_HOME 指到临时文件夹，不碰真的。"""
    return Path(os.environ.get("RC_HOME") or Path.home()) / ".claude"


def target_base(p: Project, where: str) -> Path:
    if where == "project":
        return p.root / ".claude"
    if where == "machine":
        return machine_home()
    raise ValueError(where)


def _library(p: Project, lib: Path | None = None) -> Path:
    """正本属于当前项目；显式 lib 仅供兼容调用，不向应用根目录回退。"""
    return Path(lib) if lib is not None else p.root / "技能库"


def _ordinary(root: Path, path: Path) -> Path:
    """只读项目内普通路径，拒绝目录链接与 Windows 联接。"""
    current = _READ.get()
    checked = current["ordinary"] if current is not None else set()
    if (root, path) in checked:
        return path
    root, path = Path(os.path.abspath(root)), Path(os.path.abspath(path))
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        raise ValueError("技能路径越出当前项目")
    if (root, path) in checked:
        return path
    parent = root
    for part in (None, *parts):
        if part is not None:
            parent /= part
        if (root, parent) in checked:
            continue
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        # OneDrive 等普通文件的重解析标记不是目录联接，不一概拒绝。
        if _linked(info):
            raise ValueError("技能路径不能是符号链接或目录联接：" + str(parent))
        if current is not None:
            current["observed"].setdefault(parent, _stamp(info))
        checked.add((root, parent))
    return path


def _tree(path: Path, root: Path | None = None) -> list[Path]:
    root = root or path
    _ordinary(root, path)
    snapshot = _READ.get()
    key = (root, path)
    if snapshot is not None and key in snapshot["trees"]:
        return snapshot["trees"][key]
    if not path.exists():
        return []
    out = []
    for current, dirs, files in os.walk(path, followlinks=False):
        current = Path(current)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in dirs + sorted(files):
            f = _ordinary(root, current / name)
            if f.is_file() and not (set(f.parts) & SKIP_DIRS):
                out.append(f)
    out.sort()
    if snapshot is not None:
        snapshot["trees"][key] = out
    return out


def _ref(p: Project, rel: str) -> Path:
    if (not isinstance(rel, str) or not rel or "\\" in rel or rel.startswith("/")
            or any(x in {"", ".", ".."} or x.endswith((".", " ")) or _BAD.search(x) or _DEVICE.fullmatch(x)
                   for x in rel.split("/"))):
        raise ValueError("技能清单路径必须是项目根相对路径：" + str(rel))
    return _ordinary(p.root, p.root.joinpath(*rel.split("/")))


def _translated(value, language="zh-CN") -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get(language) or value.get("zh-CN") or value.get("en") or next(iter(value.values()), "")
    return ""


def _url(value):
    if not isinstance(value, str):
        raise ValueError("技能来源网址必须是文字")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("技能来源只接受不含账号密码的 HTTP(S) 网址")


def _manifest(p: Project, lib: Path) -> tuple[list[dict], list[dict]]:
    f = _ordinary(lib, lib / MANIFEST)
    if not f.exists():
        if (lib / "业务").exists():
            raise ValueError("业务技能目录缺少 manifest.json，不能把未知内容当成已内置技能")
        return [], []
    try:
        data = json.loads(f.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("业务技能清单读不了：" + str(exc)) from exc
    if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("groups"), list) or not isinstance(data.get("items"), list):
        raise ValueError("业务技能清单须是 schema 1 的 groups/items")
    groups, seen_groups = data["groups"], set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("id"), str) or not re.fullmatch(r"[a-z][a-z0-9-]*", group["id"]) or group["id"] in seen_groups:
            raise ValueError("业务技能分组编号缺失或重复")
        seen_groups.add(group["id"])
        stages = group.get("stages", [])
        if not isinstance(stages, list) or any(not isinstance(s, dict) or not isinstance(s.get("id"), str) for s in stages):
            raise ValueError("业务技能阶段清单读不了")
        if len({s["id"] for s in stages}) != len(stages):
            raise ValueError("业务技能阶段编号重复")
    seen_ids, seen_paths, seen_install, seen_alias = set(), set(), set(), set()
    for row in data["items"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("业务技能条目缺少编号")
        sid = row["id"]
        match = _BIZ_ID.fullmatch(sid)
        if not match and (not sid.startswith("research-") or _BAD.search(sid)):
            raise ValueError("业务技能编号应是 biz:业务:来源:名称；已有 research 编号继续保留")
        if sid in seen_ids:
            raise ValueError("业务技能编号重复：" + sid)
        seen_ids.add(sid)
        business = row.get("business")
        if business not in seen_groups or (match and business != match[1]):
            raise ValueError("业务技能条目的分组不一致：" + sid)
        if row.get("kind") not in {"skill", "link"}:
            raise ValueError("业务技能 kind 只能是 skill 或 link")
        stages = row.get("stages", [])
        group_stages = {s["id"] for g in groups if g["id"] == business for s in g.get("stages", [])}
        if not isinstance(stages, list) or any(not isinstance(s, str) or s not in group_stages for s in stages):
            raise ValueError("业务技能引用了未定义阶段：" + sid)
        for key in ("title", "summary"):
            if key in row and not isinstance(row[key], (str, dict)):
                raise ValueError("业务技能标题和简介须是文字或语言映射")
            if isinstance(row.get(key), dict) and any(not isinstance(v, str) for v in row[key].values()):
                raise ValueError("业务技能多语言说明须是文字")
        for key in ("source", "license", "redistribution", "languages"):
            if key in row and not isinstance(row[key], dict):
                raise ValueError("业务技能 " + key + " 须是对象")
        for key in ("dependencies", "support_files", "aliases"):
            if key in row and not isinstance(row[key], list):
                raise ValueError("业务技能 " + key + " 须是列表")
        for alias in row.get("aliases", []):
            if not isinstance(alias, str) or not alias.strip() or alias != alias.strip() or alias.casefold() in seen_alias or alias in seen_ids:
                raise ValueError("业务技能别名缺失或重复")
            seen_alias.add(alias.casefold())
        source = row.get("source", {})
        for key in ("url", "repository_url", "license_url"):
            if source.get(key):
                _url(source[key])
        source_files = source.get("files", [])
        if not isinstance(source_files, list):
            raise ValueError("业务技能来源 files 须是列表")
        for source_file in source_files:
            if not isinstance(source_file, dict):
                raise ValueError("业务技能来源文件须是对象")
            if source_file.get("url"):
                _url(source_file["url"])
            if source_file.get("local_path"):
                _ref(p, source_file["local_path"])
                if not isinstance(source_file.get("sha256"), str) or not re.fullmatch(r"[a-fA-F0-9]{64}", source_file["sha256"]):
                    raise ValueError("随包来源文件须有 SHA256 指纹")
        path = row.get("path")
        languages = row.get("languages", {})
        if row["kind"] == "link" and (path or languages):
            raise ValueError("网址条目不能伪装成已内置的技能")
        if path:
            _ref(p, path)
            parts = path.split("/")
            module_package = (len(parts) == 6 and parts[0] == "资料" and parts[2] == MODULE_DIR
                              and parts[-1] == "SKILL.md")
            if module_package and proj.check_name(parts[1]) != parts[1]:
                raise ValueError("模块技能须使用完整普通模块名称")
            if module_package:
                here = p.root
                for part in parts:
                    if part.startswith((".", "_")):
                        raise ValueError("模块技能不能藏在系统或隐藏目录")
                    candidate = here / part
                    if os.name == 'nt' and candidate.exists() and not any(
                            e.name.casefold() == part.casefold() for e in os.scandir(here)):
                        raise ValueError("模块技能须使用完整路径，不能使用短名称别名")
                    here = candidate
            if not ((path.startswith("技能库/") and path.endswith("/SKILL.md")) or module_package):
                raise ValueError("业务技能正文须在技能库或资料/模块/技能/分类/名称/SKILL.md")
            if module_package and not match:
                raise ValueError("模块技能包须使用唯一的 biz 编号；旧科研编号留在原位")
            if module_package and row.get("module", parts[1]) != parts[1]:
                raise ValueError("模块技能的归属与路径不一致")
            if path.casefold() in seen_paths:
                raise ValueError("同一技能正文被清单重复引用：" + path)
            seen_paths.add(path.casefold())
            if not match and path != "技能库/" + sid + "/SKILL.md":
                raise ValueError("旧科研编号必须指向原技能正本")
        for lang, rel in languages.items():
            if not isinstance(lang, str):
                raise ValueError("技能语言编号必须是文字")
            _ref(p, rel)
            if lang not in {"zh-CN", "zh", "en", "en-US", "en-GB"} or _ref(p, rel).name not in {"SKILL.md", "SKILL.en.md"}:
                raise ValueError("技能语言只能引用本包的 SKILL.md 或 SKILL.en.md")
            if _ref(p, rel).name != ("SKILL.en.md" if lang.startswith("en") else "SKILL.md"):
                raise ValueError("中文与英文须分别引用 SKILL.md 和 SKILL.en.md")
            if path and _ref(p, rel).parent != _ref(p, path).parent:
                raise ValueError("技能翻译须放在同一技能包")
        license_files = row.get("license", {}).get("files", [])
        if not isinstance(license_files, list):
            raise ValueError("业务技能许可证 files 须是列表")
        for rel in row.get("support_files", []) + license_files:
            _ref(p, rel)
        if row.get("info_path"):
            _ref(p, row["info_path"])
        name = row.get("install_name", sid if not match else "mh-" + "-".join(match.groups()))
        if (not isinstance(name, str) or not name or _BAD.search(name) or name.startswith(".")
                or name.endswith((".", " ")) or _DEVICE.fullmatch(name)):
            raise ValueError("业务技能安装名不合法")
        if row["kind"] == "skill":
            if name.casefold() in seen_install:
                raise ValueError("业务技能安装名重复：" + name)
            seen_install.add(name.casefold())
        row["install_name"] = name
    if seen_alias & {sid.casefold() for sid in seen_ids}:
        raise ValueError("业务技能别名与编号冲突")
    return groups, data["items"]


def frontmatter(text: str) -> dict:
    """读开头 --- 之间的 key: value。够用就行，不引 YAML 库。"""
    out = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        for line in text[3:end if end > 0 else 0].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                v = v.strip()
                if (k.strip() in {'name', 'description', 'display_name', 'version', 'license', 'language'}
                        and len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'")):
                    if v[0] == '"':
                        import json
                        try:
                            v = json.loads(v)
                        except ValueError:
                            v = v[1:-1]
                    else:
                        v = v[1:-1].replace("''", "'")
                out[k.strip()] = v
    return out


def _digest(path: Path) -> str:
    """一个文件或文件夹的内容指纹：用来判断装过去的那份跟库里这份一不一样。"""
    current = _READ.get()
    if current is not None and path in current["digests"]:
        return current["digests"][path]
    h = hashlib.sha1()
    single = path.is_file()
    files = [path] if single else _tree(path)
    _ordinary(path.parent if single else path, path)
    for f in files:
        h.update((f.name if single else f.relative_to(path).as_posix()).encode())
        h.update(_file_bytes(f))
    result = h.hexdigest()
    if current is not None:
        current["digests"][path] = result
    return result


def status_of(src: Path, dst: Path) -> str | None:
    """None = 没装；same = 装了且一样；different = 装了但不一样（被改过，或库里更新了）。"""
    if not dst.exists():
        return None
    try:
        return "same" if _digest(src) == _digest(dst) else "different"
    except OSError:
        return "different"


def place(src: Path, dst: Path, backup_root: Path, *, overwrite: bool) -> dict:
    """把 src（文件或文件夹）放到 dst。已有不一样的：没说覆盖就抛 Conflict；说了就先把旧的挪去备份。"""
    st = status_of(src, dst)
    if st == "same":
        return {"already": True, "to": str(dst), "backup": None}
    backup = None
    if st == "different":
        if not overwrite:
            raise Conflict(f"那边已经有一份不一样的「{dst.name}」。要覆盖的话，旧的会先备份。")
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / f"{dst.stem}-{datetime.now():%Y%m%d-%H%M%S}{dst.suffix}"
        shutil.move(str(dst), str(backup))              # 挪走，不删
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"))
    else:
        shutil.copy2(src, dst)
    return {"already": False, "to": str(dst), "backup": str(backup) if backup else None}


def _skill_dir(sid: str, lib: Path) -> Path:
    if not sid or _BAD.search(sid) or sid.startswith("."):
        raise KeyError(sid)
    d = lib / sid
    if not (d / "SKILL.md").is_file():
        raise KeyError(sid)
    return d


def module_skill(p: Project, module: str) -> Path | None:
    """这个模块的专属技能文件夹（资料/<模块>/技能/），没有就是 None。"""
    if not module or _BAD.search(module) or module.startswith("."):
        return None
    d = _ordinary(p.root, p.materials / module / MODULE_DIR)
    return d if (d / "SKILL.md").is_file() else None


def _source(p: Project, sid: str, lib: Path) -> tuple[Path, str]:
    row = _resolve(_records(p, lib)[1], sid)
    if not row or row["kind"] != "skill":
        if row:
            raise ValueError("这是一条网址参考，不能安装或复制成技能")
        raise KeyError(sid)
    if not row["installable"]:
        raise ValueError("这份技能还不能安装：" + "；".join(row["issues"]))
    if _READ.get() is not None:
        _verify_read(_READ.get())
    return row["_dir"], row["install_name"]


def _entry(p: Project, sid: str, d: Path, name: str, where: str, module: str = "") -> dict:
    meta = frontmatter((d / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
    return {
        "id": sid, "module": module, "where": where,
        "name": meta.get("display_name") or meta.get("name", name),
        "agent_name": meta.get("name", name),
        "description": meta.get("description", ""),
        "files": sum(1 for f in d.rglob("*") if f.is_file()),
        "project": status_of(d, target_base(p, "project") / "skills" / name),
        "machine": status_of(d, target_base(p, "machine") / "skills" / name),
    }


def _records(p: Project, lib: Path | None = None) -> tuple[list[dict], list[dict]]:
    lib = _library(p, lib)
    _ordinary(lib, lib)
    groups, manifest = _manifest(p, lib)
    rows, paths = [], {}
    def base(sid, d, where, module=""):
        files = _tree(d)
        meta = frontmatter(_file_bytes(d / "SKILL.md").decode("utf-8", errors="replace"))
        languages = {"zh-CN": where + "SKILL.md"}
        if (d / "SKILL.en.md").is_file():
            languages["en"] = where + "SKILL.en.md"
        row = {"id": sid, "kind": "skill", "module": module, "where": where,
               "name": meta.get("display_name") or meta.get("name") or d.name,
               "agent_name": meta.get("name") or d.name, "description": meta.get("description", ""),
               "path": where + "SKILL.md", "metadata": meta, "install_name": module or d.name,
               "languages": languages, "business": "", "stages": [], "source": {}, "license": {},
               "dependencies": [], "support_files": [where + f.relative_to(d).as_posix() for f in files
                    if f.name not in {"SKILL.md", "SKILL.en.md"}], "issues": [], "available": True,
               "installable": True, "_dir": d, "_document": d / "SKILL.md", "aliases": []}
        rows.append(row)
        paths[row["path"]] = row
    if lib.is_dir():
        for d in sorted(lib.iterdir()):
            _ordinary(lib, d)
            if d.name not in {"内置", "业务"} and (d / "SKILL.md").is_file():
                base(d.name, d, f"技能库/{d.name}/")
    for m in sorted(proj.module_dirs(p)):
        d = module_skill(p, m)
        if d:
            base(MOD + m, d, f"资料/{m}/{MODULE_DIR}/", m)
    for item in manifest:
        path = item.get("path")
        existing = paths.get(path)
        if existing and existing["id"] != item["id"]:
            raise ValueError("清单不得为已有正文另造编号：" + path)
        row = existing or {"id": item["id"], "module": "", "metadata": {}, "_dir": None, "_document": None}
        if existing is None:
            rows.append(row)
        row.update(item)
        if path and path.startswith("资料/"):
            row["module"] = path.split("/")[1]
        row.setdefault("source", {})
        row.setdefault("license", {})
        row.setdefault("dependencies", [])
        row.setdefault("support_files", [])
        row.setdefault("aliases", [])
        row.setdefault("stages", [])
        row.setdefault("languages", {})
        problems = []
        d = _ref(p, path).parent if path else None
        if d and d.is_dir():
            _tree(d, p.root)
        doc = _ref(p, path) if path else None
        meta = frontmatter(_file_bytes(doc).decode("utf-8", errors="replace")) if doc and doc.is_file() else {}
        row.update({"_dir": d, "_document": doc, "metadata": meta,
                    "where": path.rsplit("/", 1)[0] + "/" if path else "",
                    "name": _translated(item.get("title")) or meta.get("display_name") or meta.get("name") or item["id"],
                    "description": _translated(item.get("summary")) or meta.get("description", ""),
                    "agent_name": meta.get("name") or item["install_name"]})
        if row["kind"] == "skill":
            if not doc or not doc.is_file():
                problems.append("缺少技能正文")
            if doc and doc.is_file() and row["id"].startswith("biz:") and meta.get("name") != row["install_name"]:
                problems.append("正文技能名与唯一安装名不一致")
            if not row["languages"]:
                row["languages"] = {"zh-CN": path} if path else {}
            for lang, rel in row["languages"].items():
                if not _ref(p, rel).is_file():
                    problems.append("缺少语言文件：" + lang)
            if path and row["languages"].get("zh-CN", path) != path:
                raise ValueError("中文正文路径与 path 不一致：" + row["id"])
            if not row["license"].get("id") or not row["license"].get("files"):
                problems.append("缺少许可证记录")
            if row.get("redistribution", {}).get("status") != "verified":
                problems.append("来源许可或配套文件尚未核验")
        elif row.get("redistribution", {}).get("status") == "pending":
            problems.append(row.get("redistribution", {}).get("reason") or "仅提供外部网址，尚未内置")
        for rel in row["support_files"] + row["license"].get("files", []):
            if not _ref(p, rel).is_file():
                problems.append("缺少配套文件：" + rel)
        for source_file in row["source"].get("files", []):
            if source_file.get("local_path"):
                f = _ref(p, source_file["local_path"])
                if not f.is_file():
                    problems.append("缺少随包来源文件：" + source_file["local_path"])
                elif hashlib.sha256(_file_bytes(f)).hexdigest() != source_file["sha256"].lower():
                    problems.append("随包来源文件指纹不符：" + source_file["local_path"])
        row["issues"] = list(dict.fromkeys(problems))
        row["available"] = row["kind"] == "skill" and not problems
        row["installable"] = row["available"]
    ids, installs = set(), {}
    for row in rows:
        if row["id"] in ids:
            raise ValueError("技能编号重复：" + row["id"])
        ids.add(row["id"])
        if row["kind"] == "skill":
            name = row["install_name"]
            if name.casefold() in installs:
                raise ValueError("技能安装目录冲突：" + name)
            installs[name.casefold()] = row["id"]
    return groups, rows


def _resolve(rows: list[dict], name: str) -> dict | None:
    name = (name or "").strip()
    exact = next((row for row in rows if row["id"] == name), None)
    if exact:
        return exact
    if not name:
        return None
    module_index = next((row for row in rows if row["id"] == MOD + name), None)
    if module_index:
        return module_index
    matches = [row for row in rows if name in [row["name"], row.get("agent_name"), row.get("module"),
                    row["_dir"].name if row.get("_dir") else None, *row.get("aliases", [])]]
    if len(matches) > 1:
        raise ValueError("技能名称不唯一，请用完整编号：" + "、".join(row["id"] for row in matches))
    return matches[0] if matches else None


def _public(p: Project, row: dict) -> dict:
    out = {k: v for k, v in row.items() if not k.startswith("_")}
    d = row.get("_dir")
    out["files"] = len(_tree(d)) if d and d.is_dir() else 0
    out["package_revision"] = _digest(d) if d and d.is_dir() else None
    out["project"] = status_of(d, target_base(p, "project") / "skills" / row["install_name"]) if d and d.is_dir() else None
    out["machine"] = status_of(d, target_base(p, "machine") / "skills" / row["install_name"]) if d and d.is_dir() else None
    return out


@_reading
def inventory(p: Project, lib: Path | None = None) -> dict:
    """网页、MCP、接手索引共用的普通文件技能目录；不运行或下载任何依赖。"""
    groups, rows = _records(p, lib)
    return {"schema": 1, "groups": groups, "items": [_public(p, row) for row in rows],
            "issues": [{"id": row["id"], "path": row.get("path"), "message": message}
                       for row in rows for message in row["issues"]]}


def list_skills(p: Project, lib: Path | None = None) -> list[dict]:
    return inventory(p, lib)["items"]


@_reading
def read(p: Project, sid: str, language: str = "zh-CN", lib: Path | None = None) -> dict:
    if not isinstance(language, str) or language not in {"zh-CN", "zh", "en", "en-US", "en-GB"}:
        raise ValueError("技能语言只支持中文和英文")
    row = _resolve(_records(p, lib)[1], sid)
    if row is None:
        raise KeyError(sid)
    normalized = "en" if language.startswith("en") else "zh-CN"
    languages = row["languages"]
    choices = ["en", "en-US", "en-GB"] if normalized == "en" else ["zh-CN", "zh"]
    selected = next((lang for lang in choices if lang in languages), "zh-CN")
    fallback = ("en" if selected.startswith("en") else "zh-CN") != normalized
    path = languages.get(selected) if row["kind"] == "skill" else row.get("info_path")
    doc = _ref(p, path) if path else None
    # 显式 lib 的老调用也读它自己的正文，不借用另一个项目。
    if lib is not None and row["kind"] == "skill" and row.get("_document") and selected == "zh-CN":
        doc = row["_document"]
    if doc and doc.is_file():
        raw = _file_bytes(doc)
        text, revision = raw.decode("utf-8-sig", errors="replace"), hashlib.sha256(raw).hexdigest()
    else:
        text, revision = "", None
    return {**_public(p, row), "text": text, "path": path, "revision": revision,
            "requested_language": language, "language": selected if row["kind"] == "skill" else None,
            "fallback": row["kind"] == "skill" and fallback,
            "language_fallback": "未提供请求语言，显示已有中文正本" if row["kind"] == "skill" and fallback else ""}


# ---------------------------------------------------------------- 技能留在项目里：哪家 agent 进门都看得到、调得到
# 作者 2026-09-30：「能不能把技能留在我的这个项目里，这样每一个agent接手这个项目都可以看到并且调用，
# 这样我这个平台才能服务更多的人，因为不是每一个人都用得起codex和你的」
# - 正本就在项目里（技能库/<名>/ · 资料/<模块>/技能/），不用装；AGENTS.md 里有一张技能目录（下面现生成）——
#   几乎每家 agent 进门都读 AGENTS.md（Claude Code 经项目根 CLAUDE.md 读到它）
# - 有 MCP 的用 list_skills / read_skill；没有 MCP 的照目录里的路径直接读文件
# - 「装到本项目 / 本机」只是给 Claude Code 自动发现多备一份，可装可不装

INDEX_START = "<!-- 技能目录：程序按 技能库/ 和 资料/<模块>/技能/ 现生成，别手改 -->"
INDEX_END = "<!-- 技能目录完 -->"


@_reading
def catalog(p: Project, lib: Path | None = None) -> list[dict]:
    """项目里的每份技能：编号、名字、什么时候用、在哪（从项目根算）。不算装没装，轻，开着网页也能常跑。"""
    return [{"id": row["id"], "name": row["name"], "agent_name": row["agent_name"],
             "when": row["description"], "path": row["path"], "dir": row["_dir"],
             "module": row["module"], "business": row["business"], "kind": row["kind"]}
            for row in _records(p, lib)[1] if row["available"]]


@_reading
def find(p: Project, name: str, lib: Path | None = None) -> dict | None:
    """按编号、名字、文件夹名或模块名找一份技能（「自动化科研交互界面」「模块:文献」「文献」都行）。"""
    row = _resolve(_records(p, lib)[1], name)
    return {**row, "dir": row["_dir"], "when": row["description"]} if row else None


def index_text(p: Project, lib: Path | None = None) -> str:
    rows = ["| 技能 | 什么时候用 | 在哪 |", "|---|---|---|"]
    for s in catalog(p, lib):
        label = s["name"] + (f"（{s['module']} 模块专属）" if s["module"] else "")
        rows.append(f"| {label} | {s['when'].replace('|', '/')} | `{s['path']}` |")
    if len(rows) == 2:
        rows.append("| （还没有） | | |")
    return "\n".join(rows)


def write_index(p: Project, lib: Path | None = None) -> bool:
    """把技能目录写进项目根 AGENTS.md 两行标记之间（AGENTS.md 是作者的，只动标记中间这一段；没有标记就不动）。
    内容没变就不写。返回写了没有。"""
    f = p.root / "AGENTS.md"
    try:
        raw = f.read_bytes()
    except OSError:
        return False
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    i, j = text.find(INDEX_START), text.find(INDEX_END)
    if i < 0 or j < i:
        return False
    new = text[:i] + INDEX_START + "\n" + index_text(p, lib) + "\n" + text[j:]
    if new == text:
        return False
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
    atomic.replace(tmp, f)
    return True


@_reading
def install(p: Project, sid: str, where: str, *, overwrite: bool = False, lib: Path | None = None) -> dict:
    src, name = _source(p, sid, _library(p, lib))
    dst = target_base(p, where) / "skills" / name
    _ordinary(p.root if where == "project" else machine_home().parent, dst)
    return place(src, dst, p.index_dir / "技能备份", overwrite=overwrite)


@_reading
def fork(p: Project, sid: str, lib: Path | None = None) -> str:
    """复制一份改：库里多一个「<名>（我的）」，frontmatter 里的名字跟着改。内容怎么改交给 agent。"""
    if sid.startswith(MOD):
        raise KeyError(sid)  # 模块技能继续在模块里改，兼容原接口。
    lib = _library(p, lib)
    src, name = _source(p, sid, lib)
    new, n = f"{name}（我的）", 2
    while (lib / new).exists():
        new, n = f"{name}（我的{n}）", n + 1
    shutil.copytree(src, lib / new, ignore=shutil.ignore_patterns(*SKIP_DIRS))
    f = lib / new / "SKILL.md"
    text = f.read_text(encoding="utf-8")
    display = frontmatter(text).get('display_name')
    text = re.sub(r"^(name:\s*).*$", lambda m: m.group(1) + new, text, count=1, flags=re.M)
    if display:
        display += new[len(name):]
        text = re.sub(r"^([ \t]*display_name:[ \t]*).*$", lambda m: m.group(1) + display,
                      text, count=1, flags=re.M)
    f.write_text(text, encoding="utf-8")
    return new
