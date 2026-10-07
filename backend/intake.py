"""外部资料入口 Intake：外面的材料从这里进项目（缓存区 / 熔炉）。

流程：
1. 拖进网页（或直接丢进 资料/_外部资料入口/）→ 先落在 _外部资料入口/，同名不覆盖，sha256 去重
2. 规则先给一个候选（.py → 源代码 …），agent 再用 MCP 写回最多 3 个候选：模块 · 高/中/低 · 一句理由
3. **人点一个，才挪**进 资料/<模块>/ 或模块里的某个文件夹 资料/<模块>/<文件夹>/（10-07：「资料入口可以分配到具体模块的具体文件夹」）。
   工具只挪【人点过的】【从外部资料入口进来的】文件，别的一概不碰
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import project as proj
import store
from project import Project

CONF = ("高", "中", "低")
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
            if x.name.startswith((".", "_")) or x.name in _NOT_A_PLACE or x.is_symlink() or x.is_junction():
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
    if any(x in ("", ".", "..") or x.startswith((".", "_")) or x in _NOT_A_PLACE or x.endswith((" ", ".")) for x in parts):
        raise store.Refused(f"「{folder}」不能当去向：要写模块里的文件夹（比如 原文、正文/引言），不能往上跳、不能放进历史和工作台")
    for x in parts:
        try:
            proj.check_name(x)
        except ValueError as e:
            raise store.Refused(f"文件夹名「{x}」不行：{e}") from None
    base = (p.materials / module).resolve()
    if not (base / folder).resolve().is_relative_to(base):
        raise store.Refused(f"「{folder}」跑出了模块「{module}」")
    return "/".join(parts)


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


def _free_name(folder: Path, name: str, sha: str) -> str:
    """同名不覆盖：已有同名文件就在后面加一段指纹。"""
    if not (folder / name).exists():
        return name
    stem, ext = os.path.splitext(name)
    return f"{stem}（{sha[:6]}）{ext}"


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
    """agent 写回候选：1~3 个，每个 = 已有模块（可再带模块里的一个文件夹 folder）+ 高/中/低 + 一句理由。"""
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
        conn.execute("UPDATE intake SET candidates = ? WHERE id = ?", (json.dumps(clean, ensure_ascii=False), iid))
        store.log(conn, by, "给分拣建议", f"#{iid}", " / ".join(f"{c['module']}{'/' + c['folder'] if c.get('folder') else ''}（{c['conf']}）" for c in clean))
    return get(conn, iid)


def sort(conn, p: Project, iid: int, module: str, *, by: str = "人", folder: str = "") -> dict:
    """人点了「放这里」：把文件从 _外部资料入口/ 挪进 资料/<模块>/（或模块里的 folder，没有就建）。只挪这一个，同名不覆盖。"""
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
        dest_dir.mkdir(parents=True, exist_ok=True)
        name = _free_name(dest_dir, it["name"], it["sha256"])
        where = f"{m['name']}/{folder}/{name}" if folder else f"{m['name']}/{name}"
        conn.execute("UPDATE intake SET status = 'sorted', sorted_to = ?, sorted_by = ?, sorted_at = ? WHERE id = ?",
                     (where, by, store.now(), iid))
        store.log(conn, by, "分拣", f"#{iid}", f"{it['name']} → 资料/{where}")
        os.replace(src, dest_dir / name)     # 最后挪：挪不成就回滚，库里不会记一笔假的
    return get(conn, iid)
