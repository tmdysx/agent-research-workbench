"""外部资料入口 Intake：外面的材料从这里进项目（缓存区 / 熔炉）。

流程：
1. 拖进网页（或直接丢进 资料/_外部资料入口/）→ 先落在 _外部资料入口/，同名不覆盖，sha256 去重
2. 规则先给一个候选（.py → 源代码 …），agent 再用 MCP 写回最多 3 个候选：模块 · 高/中/低 · 一句理由
3. 人在网页上点一个，或 agent 调 sort_inbox_item（记下是谁、为什么），挪进 资料/<模块>/ 或模块里的某个文件夹
   资料/<模块>/<文件夹>/（10-07：「资料入口可以分配到具体模块的具体文件夹」）。只挪外部资料入口里的文件
4. 放错地方的普通材料可以挪回来重新分拣（网页阅读页「移到入口」/ MCP move_to_inbox，10-08）：
   原来在哪记成一个「原位置」候选，在入口点「放回原处」就按原名放回去
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path, PurePosixPath

import downloads
import governance_paths
import journal
import library
import project as proj
import store
from project import Project

CONF = ("高", "中", "低")
ORIGIN = "原位置"            # 移到入口的文件：原来在哪记成一个候选，by 写这个（10-08）
OSS = "工具/开源项目"          # 不在 资料/ 里的去向：压缩包收进工具页「开源项目」（工具 S2-3；作者 10-01：「为啥外部资料入口的东西不能直接分配到工具？」）

# 规则：只看扩展名给第一候选。看不出来的就等 agent
RULES = [
    ({".py", ".ipynb", ".r", ".m", ".jl", ".js", ".ts", ".cpp", ".c", ".java", ".sh"}, "源代码", "高", "是代码文件"),
    ({".bib", ".ris", ".enw"}, "文献", "高", "是文献引用格式"),
    ({".pdf"}, "文献", "中", "PDF 多半是论文或资料；也可能是你自己的稿子"),
    ({".tex", ".docx", ".doc"}, "论文", "中", "是写作用的文档"),
    ({".csv", ".tsv", ".json", ".xlsx", ".npy", ".pkl"}, "实验", "低", "像数据或结果文件，但只看了扩展名"),
]


def inbox_dir(p: Project) -> Path:
    return p.materials / proj.INBOX


# 模块里能放进去的文件夹：历史、工作台（模板和设置）、缓存这些不算
_NOT_A_PLACE = {"历史", "工作台", "预览缓存", "原件", "__pycache__", "node_modules", "venv", ".git"}
CASELESS = os.name == "nt"           # Windows 上文件名不分大小写：VENV/、Node_Modules/ 也是缓存（10-08）


def name_key(name: str) -> str:
    """比文件名用的样子：Windows 上折叠大小写，别的系统原样。"""
    return name.casefold() if CASELESS else name


def not_a_place(name: str) -> bool:
    return name_key(name) in {name_key(x) for x in _NOT_A_PLACE}


def governed(module: str, folder: str = "", name: str = "") -> str:
    """去向是不是只有人能定的地方（10-08）：治理模块、模块根上程序维护的文件、模块技能、文献解读、内置和程序管的文件夹、隐藏文件。
    是就返回为什么（agent 分拣不过去，监管也不替这种挪动开脱）；普通材料的位置返回空。"""
    parts = [x for x in (folder or "").split("/") if x]
    if module in proj.TOOL_NAMES:
        return f"「{module}」是固定的治理模块（想法 · 蓝图 · 戒律 · 源代码）"
    if parts and name_key(parts[0]) == name_key("技能"):
        return "模块技能（技能/）是写给 agent 的做法，由人定"
    if parts and name_key(parts[0]) == name_key(library.READ):
        return "文献解读（解读/）跟着原文走，由文献库管理"
    if any(name_key(x) == name_key("内置") or not_a_place(x) for x in parts):
        return "内置、历史、工作台和缓存这些文件夹由程序管理"
    if name.startswith("."):
        return "点开头的隐藏文件（比如 .链接.txt）由程序读"
    if name and not parts:
        rel = f"资料/{module}/{name_key(name)}"
        if governance_paths.central(rel) != rel or name_key(name) in {name_key(downloads.FILE), name_key("想法.md")}:
            return "模块根上的需求、任务、戒律、下载清单和想法由程序维护"
    return ""


def _agent_may_place(module: str, folder: str, name: str = "") -> None:
    why = governed(module, folder, name)
    if why:
        where = "/".join(x for x in (module, folder, name) if x)
        raise store.Refused(f"{why}：agent 不能直接分拣到「{where}」。要放这类位置请让人在网页上点")


def _put_back(now: Path, back: Path) -> None:
    """文件已经挪了、库却没记上（提交失败）：挪回原处（原处空着才挪），免得文件和记录对不上。"""
    try:
        if not os.path.lexists(back):
            os.replace(now, back)
    except OSError:
        pass


def module_folders(p: Project, module: str, depth: int = 4) -> list[str]:
    """模块里有哪些文件夹（从模块根算，比如「原文」「正文/引言」），给人和 agent 挑去向。"""
    base = p.materials / module
    out = []

    def walk(d: Path, rel: str, n: int):
        if n > depth:
            return
        try:
            kids = sorted((x for x in d.iterdir() if x.is_dir()), key=lambda x: x.name)
        except OSError:
            return
        for x in kids:
            if x.name.startswith((".", "_")) or not_a_place(x.name) or x.is_symlink() or x.is_junction():
                continue
            r = f"{rel}/{x.name}" if rel else x.name
            out.append(r)
            walk(x, r, n + 1)

    if base.is_dir():
        walk(base, "", 1)
    return out


def _folder(p: Project, module: str, folder: str) -> str:
    """检查去向文件夹：只能是这个模块里面、不往上跳、不碰历史和模板；空 = 模块根。"""
    folder = (folder or "").strip().replace("\\", "/").strip("/")
    if not folder:
        return ""
    parts = folder.split("/")
    if any(x in ("", ".", "..") or x.startswith((".", "_")) or not_a_place(x) or x.endswith((" ", ".")) for x in parts):
        raise store.Refused(f"「{folder}」不能当去向：要写模块里的文件夹（比如 原文、正文/引言），不能往上跳、不能放进历史和工作台")
    for x in parts:
        try:
            proj.check_name(x)
        except ValueError as e:
            raise store.Refused(f"文件夹名「{x}」不行：{e}") from None
    here = p.materials / module
    for x in parts:                          # 已经有的那几层不能是链接：链接文件夹指去哪看不出来（可能是技能/、解读/）
        here = here / x
        if here.is_symlink() or here.is_junction():
            raise store.Refused(f"「{folder}」里的「{x}」是链接文件夹，不能当去向")
    base = (p.materials / module).resolve()
    if not (base / folder).resolve().is_relative_to(base):
        raise store.Refused(f"「{folder}」跑出了模块「{module}」")
    return "/".join(parts)


def _real_folder(p: Project, module: str, dest_dir: Path) -> str:
    """去向文件夹在磁盘上的真名（从模块根算）：已经有的那几层按 realpath 认，还没建的照写的。"""
    base = os.path.realpath(p.materials / module)
    have, rest = dest_dir, []
    while not os.path.lexists(have) and have != p.materials / module:
        rest.insert(0, have.name)
        have = have.parent
    real = os.path.relpath(os.path.realpath(have), base).replace("\\", "/")
    return "/".join([x for x in real.split("/") if x not in ("", ".")] + rest)


def _row(r) -> dict:
    d = dict(r)
    d["candidates"] = json.loads(d["candidates"])
    d.pop("user_id", None)
    return d


def _rule_candidates(conn, name: str) -> list[dict]:
    ext = Path(name).suffix.lower()
    if ext == ".zip":
        return [{"module": OSS, "conf": "中", "reason": "是压缩包，多半是从 GitHub 下载的开源项目", "by": "规则"}]
    for exts, module, conf, why in RULES:
        if ext in exts and store.find_module(conn, module):
            return [{"module": module, "conf": conf, "reason": why, "by": "规则"}]
    return []


def origin(item: dict) -> dict | None:
    """移到入口的文件记着的原位置候选；没有就 None。"""
    return next((c for c in item.get("candidates") or [] if c.get("by") == ORIGIN), None)


def _free_name(folder: Path, name: str, sha: str, taken=frozenset()) -> str:
    """同名不覆盖：已有同名文件（或 taken 里的名字）就在后面加一段指纹；指纹名也占了就再加 -2、-3……"""
    used = {x.casefold() for x in taken}
    stem, ext = os.path.splitext(name)
    for n in range(1, 1000):
        x = name if n == 1 else f"{stem}（{sha[:6]}）{ext}" if n == 2 else f"{stem}（{sha[:6]}-{n - 1}）{ext}"
        if not os.path.lexists(folder / x) and x.casefold() not in used:
            return x
    raise store.Refused(f"「{name}」重名太多，换个名字再试")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def receive(conn, p: Project, tmp: Path, orig: str, *, by: str = "人") -> dict:
    """收一个已经写到临时文件 tmp 里的文件。重复的丢掉临时文件、不存第二份。"""
    sha = _sha(tmp)
    dup = conn.execute("SELECT * FROM intake WHERE sha256 = ? ORDER BY id LIMIT 1", (sha,)).fetchone()
    if dup:
        tmp.unlink()
        return {"dup": True, "item": _row(dup)}
    folder = inbox_dir(p)
    folder.mkdir(parents=True, exist_ok=True)
    base = Path(orig.replace("\\", "/")).name or "未命名"
    try:
        with store.tx(conn):                 # 先记库、最后挪文件：挪不成就整个回滚
            name = _free_name(folder, base, sha)
            iid = conn.execute(
                "INSERT INTO intake(name, orig, sha256, size, candidates, created_by, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (name, orig, sha, tmp.stat().st_size,
                 json.dumps(_rule_candidates(conn, name), ensure_ascii=False), by, store.now()),
            ).lastrowid
            store.log(conn, by, "放进外部资料入口", f"#{iid}", name)
            os.replace(tmp, folder / name)
    finally:
        tmp.unlink(missing_ok=True)
    return {"dup": False, "item": get(conn, iid)}


def take_from_module(conn, p: Project, src: Path, *, orig: str, sha: str, size: int, module: str, folder: str,
                     by: str, check=None) -> dict:
    """移到入口：模块里放错的一个文件挪回 _外部资料入口/ 重新分拣，原位置记成第一个候选。
    检查（能不能挪、版本对不对）由 file_actions 做完；这里只管登记和挪。先记库、最后挪：挪不成就整个回滚。"""
    box = inbox_dir(p)
    box.mkdir(parents=True, exist_ok=True)
    cand = {"module": module, "conf": "高", "reason": "原来在这里", "by": ORIGIN, **({"folder": folder} if folder else {})}
    done = []                             # 挪成了记一笔：提交没成就挪回原处再报错
    try:
        with store.tx(conn):
            if not os.path.lexists(src):
                raise store.Refused("文件已经移走或不存在，请重新打开目录")
            twin = conn.execute("SELECT id, name FROM intake WHERE sha256 = ? AND status = 'waiting' ORDER BY id LIMIT 1", (sha,)).fetchone()
            if twin:
                raise store.Refused(f"外部资料入口里已经有一份内容一模一样的「{twin['name']}」（#{twin['id']}）在等分拣："
                                    "先去入口处理那一份，或把这一份删掉")
            taken = {r[0] for r in conn.execute("SELECT name FROM intake WHERE status = 'waiting'")}
            name = _free_name(box, src.name, sha, taken)
            if check:
                check(box / name)
            iid = conn.execute(
                "INSERT INTO intake(name, orig, sha256, size, candidates, created_by, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (name, orig, sha, size, json.dumps([cand], ensure_ascii=False), by, store.now()),
            ).lastrowid
            store.log(conn, by, "移到外部资料入口", f"#{iid}", f"{orig} → 资料/{proj.INBOX}/{name}")
            os.replace(src, box / name)       # 最后挪：挪不成就回滚
            done.append(box / name)
    except BaseException:
        if done:
            _undo(conn, done[0], src)
        raise
    return get(conn, iid)


def _undo(conn, moved: Path, back: Path) -> None:
    if conn.in_transaction:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
    _put_back(moved, back)


def get(conn, iid: int) -> dict | None:
    r = conn.execute("SELECT * FROM intake WHERE id = ?", (iid,)).fetchone()
    return _row(r) if r else None


def sync(conn, p: Project) -> None:
    """资料/_外部资料入口/ 跟库对账：你直接丢进文件夹的也登记上；文件不见了的标 gone。没变化不拿写锁。"""
    folder = inbox_dir(p)

    def plan():
        on_disk = {e.name for e in os.scandir(folder) if e.is_file() and not e.name.startswith(".")} if folder.is_dir() else set()
        rows = {r["name"]: r for r in conn.execute("SELECT * FROM intake WHERE status = 'waiting'")}
        return sorted(on_disk - set(rows)), [r for n, r in rows.items() if n not in on_disk]

    if not any(plan()):
        return
    with store.tx(conn):
        new, gone = plan()                  # 锁里再看一次：网页正在收的文件已经登记了，别重复登记
        for n in new:
            sha = _sha(folder / n)
            same = conn.execute("SELECT name FROM intake WHERE sha256 = ? ORDER BY id LIMIT 1", (sha,)).fetchone()
            cands = _rule_candidates(conn, n)
            if same:
                cands = [{"module": c["module"], "conf": c["conf"], "reason": f"（跟之前放进来的「{same[0]}」内容一模一样）{c['reason']}", "by": c["by"]} for c in cands]
            iid = conn.execute(
                "INSERT INTO intake(name, orig, sha256, size, candidates, created_by, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (n, n, sha, (folder / n).stat().st_size, json.dumps(cands, ensure_ascii=False), "文件夹里发现的", store.now()),
            ).lastrowid
            store.log(conn, "资料/", "放进外部资料入口（直接丢进文件夹的）", f"#{iid}", n)
        for r in gone:
            conn.execute("UPDATE intake SET status = 'gone' WHERE id = ?", (r["id"],))
            store.log(conn, "资料/", "外部资料入口里的文件不见了", f"#{r['id']}", r["name"])


def waiting(conn) -> list[dict]:
    return [_row(r) for r in conn.execute("SELECT * FROM intake WHERE status = 'waiting' ORDER BY id DESC")]


def suggest(conn, iid: int, candidates: list[dict], *, by: str, p: Project | None = None) -> dict:
    """agent 写回候选：1~3 个，每个 = 已有模块（可再带模块里的一个文件夹 folder）+ 高/中/低 + 一句理由。
    移到入口的文件记着的「原位置」候选留在最前面，不算在这 3 个里。"""
    if by == ORIGIN:
        raise store.Refused(f"「{ORIGIN}」留给记录原来位置的候选，不能当署名")
    if not 1 <= len(candidates) <= 3:
        raise store.Refused("候选要 1 到 3 个")
    clean = []
    for c in candidates:
        m, conf, why = str(c.get("module", "")).strip(), str(c.get("confidence", c.get("conf", ""))).strip(), str(c.get("reason", "")).strip()
        folder = str(c.get("folder", "") or "").strip()
        if m != OSS and not store.find_module(conn, m):
            raise store.Refused(f"没有「{m}」这个模块；候选只能是已有模块，或「{OSS}」（GitHub 压缩包）（要新模块先 add_module）")
        if conf not in CONF:
            raise store.Refused(f"把握只能是 高 / 中 / 低，不是「{conf}」")
        if not why:
            raise store.Refused("每个候选都要写一句理由")
        folder = _folder(p, m, folder) if folder and m != OSS and p is not None else ""
        clean.append({"module": m, "conf": conf, "reason": why[:120], "by": by, **({"folder": folder} if folder else {})})
    with store.tx(conn):
        it = get(conn, iid)
        if not it or it["status"] != "waiting":
            raise store.Refused(f"外部资料入口里没有 #{iid}（可能已经分拣过了）")
        back = origin(it)
        conn.execute("UPDATE intake SET candidates = ? WHERE id = ?", (json.dumps(([back] if back else []) + clean, ensure_ascii=False), iid))
        store.log(conn, by, "给分拣建议", f"#{iid}", " / ".join(f"{c['module']}{'/' + c['folder'] if c.get('folder') else ''}（{c['conf']}）" for c in clean))
    return get(conn, iid)


def sort(conn, p: Project, iid: int, module: str, *, by: str = "人", folder: str = "") -> dict:
    """人点了「放这里」（或 agent 调了 sort_inbox_item）：把文件从 _外部资料入口/ 挪进 资料/<模块>/（或模块里的 folder，没有就建）。
    只挪这一个，同名不覆盖；移到入口的文件按原来的名字放（入口里为了不重名加的指纹去掉）。
    agent（by 不是「人」）只能放普通材料的位置：治理模块、模块根上程序维护的文件、技能/、解读/、内置/ 要人在网页上点（10-08）。"""
    done = []                                # 挪成了记一笔：提交没成就挪回入口再报错
    try:
        with store.tx(conn):
            it = get(conn, iid)
            if not it or it["status"] != "waiting":
                raise store.Refused(f"外部资料入口里没有 #{iid}（可能已经分拣过了）")
            m = store.find_module(conn, module)
            if not m:
                raise store.Refused(f"没有「{module}」这个模块")
            src = inbox_dir(p) / it["name"]
            if not src.is_file():
                raise store.Refused(f"「{it['name']}」不在 资料/{proj.INBOX}/ 里了")
            folder = _folder(p, m["name"], folder)
            dest_dir = p.materials / m["name"] / folder if folder else p.materials / m["name"]
            if by != "人":                   # agent 只放普通材料的位置；治理、技能、程序管的地方要人点（10-08）
                _agent_may_place(m["name"], folder)
                real = _real_folder(p, m["name"], dest_dir)
                if real != folder:           # 磁盘上真名不一样（大小写、短文件名）：按真名再看一遍
                    _agent_may_place(m["name"], real)
            dest_dir.mkdir(parents=True, exist_ok=True)
            want = PurePosixPath(it["orig"]).name if origin(it) else it["name"]
            name = _free_name(dest_dir, want, it["sha256"])
            if by != "人":
                _agent_may_place(m["name"], folder, name)
            where = f"{m['name']}/{folder}/{name}" if folder else f"{m['name']}/{name}"
            conn.execute("UPDATE intake SET status = 'sorted', sorted_to = ?, sorted_by = ?, sorted_at = ? WHERE id = ?",
                         (where, by, store.now(), iid))
            store.log(conn, by, "分拣", f"#{iid}", f"{it['name']} → 资料/{where}")
            os.replace(src, dest_dir / name)     # 最后挪：挪不成就回滚，库里不会记一笔假的
            done.append((dest_dir / name, src))
    except BaseException:
        if done:
            _undo(conn, *done[0])
        raise
    return get(conn, iid)


def place(conn, p: Project, iid: int, module: str, *, folder: str = "", by: str = "人", reason: str = "") -> dict:
    """分拣一件并记日志：网页「放这里 / 放回原处」和 MCP sort_inbox_item 共用。agent 分拣要写一句为什么。"""
    reason = " / ".join(x.strip() for x in (reason or "").splitlines() if x.strip())
    if by != "人" and not reason:
        raise store.Refused("agent 分拣要写一句为什么放这里")
    if len(reason) > 2000:
        raise store.Refused("原因太长了（最多 2000 字）")
    before = get(conn, iid)
    try:
        it = sort(conn, p, iid, module, by=by, folder=folder)
    except OSError as exc:                   # 建不了文件夹、文件被别的程序占着：没挪成（挪了一半的 sort 已挪回）
        raise store.Refused(f"没放成，文件还在入口：{exc}") from None
    picked = next((c for c in (before or {}).get("candidates", []) if c["module"] == module
                   and (c.get("folder") or "") == (folder or "").strip().strip("/")), None)
    if picked and picked.get("by") == ORIGIN:
        why = "（放回原处）"
    elif picked:
        why = f"（选的是 {picked['by']} 给的候选：把握 {picked['conf']}，{picked['reason']}）"
    else:
        why = "（候选里没有，自己选的）"
    out = {"item": it, "log_id": None}
    try:
        e = journal.add(conn, p, f"从外部资料入口放进来：{it['sorted_to']}{why}" + (f"\n原因：{reason}" if reason else ""),
                        kind="放进来", by=by, scope=it["sorted_to"].split("/")[0])
        out["log_id"] = e["id"]
    except (OSError, sqlite3.Error):
        out["warning"] = "已经放进去了，日志写入失败"
    return out
