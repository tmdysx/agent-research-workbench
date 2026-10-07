"""插件：重活不进核心，玩家自己装、自己启用（总蓝图 S1-11 玩家自己组装）。

作者 2026-09-29：「重活需要自己安装插件……那个不放核心代码，但是提供一个安装脚本之类的，其他agent一看联网就能下载」
「就是不装插件就这样显示，装了之后能不能原版显示?」
- 一个插件一个文件夹：应用根目录 `插件/<名字>/插件.md`，开头 --- 之间写：名字 · 一句话 · 类别 · 版本 · 管哪些文件 · 转成 · 检查 · 转换；
  正文写给 agent 看的安装步骤（装外部程序之前先问人）
- 检查：在插件文件夹里跑卡上那条命令，退出码 0 = 这台电脑能用；查过的记一会儿
- **启用只由人点**（每个项目自己记，存库）；agent 能照 插件.md 装外部程序，不能替人启用
- 转换：{输入} {输出} 换成完整路径、在插件文件夹里跑；一次只转一份，有超时；
  转出来的放 `索引/预览缓存/`（能删能重建），同一份文件没改过就不重转。原文件一个字节不动
- 拿掉插件文件夹，核心照常，只是那个功能没了
"""
from __future__ import annotations

import hashlib
import json
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import store
from files import _decode
from project import CODE_DIR, Project
from skills import frontmatter

DIR = CODE_DIR / "插件"
CHECK_TIMEOUT = 20           # 秒。PowerShell 冷启动要一两秒
CONVERT_TIMEOUT = 180        # 秒。大的 PPT 第一次转要几十秒
KEEP = 50                    # 预览缓存最多留几份，多了删最早的（缓存能重建）
_ON = "插件启用:"             # 库里记「这个项目启用了哪个插件」的键
_LOCK = threading.Lock()     # 一次只转一份：PowerPoint 同时开好几份容易卡死
_CHECKED: dict[str, tuple[float, dict]] = {}


def list_plugins(d: Path | None = None) -> list[dict]:
    """插件/ 里每个有 插件.md 的文件夹一个，按名字排。"""
    d = d or DIR
    out = []
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*/插件.md")):
        if f.parent.name == "内置":
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        body = text[text.find("\n---", 3) + 4:].lstrip() if text.startswith("---") else text
        out.append({"name": fm.get("名字") or f.parent.name, "one_line": fm.get("一句话", ""),
                    "version": fm.get("版本", ""), "exts": [e.lower() for e in fm.get("管哪些文件", "").split()],
                    "to": fm.get("转成", "").lower(), "check": fm.get("检查", ""), "convert": fm.get("转换", ""),
                    "page": fm.get("页面", ""), "start": fm.get("启动", ""),          # 挂一页的插件（S1-11 S2-6）
                    "port": int(fm.get("端口") or 0) if str(fm.get("端口") or "").isdigit() else 0,
                    "dir": f.parent, "body": body})
    return out


def get(name: str, d: Path | None = None) -> dict:
    p = next((x for x in list_plugins(d) if x["name"] == name), None)
    if p is None:
        raise KeyError(name)
    return p


def _args(cmd: str, plugin_dir: Path, fill: dict[str, str] | None = None) -> list[str]:
    """不经过命令行解释器：按空格拆，去掉外层引号，{输入} {输出} 换成完整路径（整段替换，路径里有空格也不怕）。"""
    args = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a for a in shlex.split(cmd, posix=False)]
    for k, v in ({"python": sys.executable} | (fill or {})).items():   # {python}：跑应用的那个 Python（本机 PATH 里的 python 可能是乱码）
        args = [a.replace("{" + k + "}", v) for a in args]
    here = plugin_dir / args[0]
    args[0] = str(here) if here.is_file() else (shutil.which(args[0]) or args[0])
    return args


def _run(args: list[str], cwd: Path, timeout: int) -> tuple[int, str]:
    r = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    text, _ = _decode(r.stdout + b"\n" + r.stderr, True)
    return r.returncode, "\n".join(x.strip() for x in text.splitlines() if x.strip())


def check(name: str, d: Path | None = None) -> dict:
    """这台电脑能不能用：跑插件自己的检查命令。查完记一会儿。"""
    p = get(name, d)
    if not p["check"]:
        r = {"ok": True, "msg": ""}
    else:
        try:
            code, text = _run(_args(p["check"], p["dir"]), p["dir"], CHECK_TIMEOUT)
            r = {"ok": code == 0, "msg": text.splitlines()[0][:200] if text else ("" if code == 0 else f"退出码 {code}")}
        except subprocess.TimeoutExpired:
            r = {"ok": False, "msg": f"检查 {CHECK_TIMEOUT} 秒没反应"}
        except OSError as e:
            r = {"ok": False, "msg": f"检查跑不起来：{e.strerror or e}"}
    _CHECKED[name] = (time.time(), r)
    return r


def check_cached(name: str, max_age: float = 600, d: Path | None = None) -> dict:
    hit = _CHECKED.get(name)
    if hit and time.time() - hit[0] < max_age:
        return hit[1]
    return check(name, d)


def enabled(conn, name: str) -> bool:
    return store._meta(conn, _ON + name) == "1"


def set_enabled(conn, name: str, on: bool, d: Path | None = None) -> None:
    get(name, d)                                    # 没有这个插件就报 KeyError
    store._set_meta(conn, _ON + name, "1" if on else "0")


def converter_for(target: Path, d: Path | None = None) -> dict | None:
    """管这种文件、能转成 PDF 的插件（有好几个就用名字排第一的）。"""
    ext = target.suffix.lower()
    return next((x for x in list_plugins(d) if ext in x["exts"] and x["to"] == "pdf" and x["convert"]), None)


def info_for(conn, p: Project, target: Path, d: Path | None = None) -> dict | None:
    """给预览用：这份文件有没有插件能照原样显示、这台电脑能不能用、这个项目启用了没有。"""
    c = converter_for(target, d)
    if c is None:
        return None
    ck = check_cached(c["name"], d=d)
    return {"name": c["name"], "one_line": c["one_line"], "ok": ck["ok"], "msg": ck["msg"],
            "enabled": enabled(conn, c["name"]), "ready": cached(p, c, target) is not None}


def _key(c: dict, target: Path) -> str:
    st = target.stat()
    raw = f"{target.resolve()}|{st.st_size}|{st.st_mtime_ns}|{c['name']}|{c['version']}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def cache_dir(p: Project) -> Path:
    return p.index_dir / "预览缓存"


def _good(f: Path) -> bool:
    try:
        with open(f, "rb") as h:
            return h.read(5) == b"%PDF-"
    except OSError:
        return False


def cached(p: Project, c: dict, target: Path) -> Path | None:
    f = cache_dir(p) / (_key(c, target) + ".pdf")
    return f if f.is_file() and _good(f) else None


def convert(p: Project, name: str, target: Path, d: Path | None = None) -> Path:
    """转成 PDF 放进预览缓存，返回那个 PDF。转过、原文件没改过就直接给。失败抛 RuntimeError（写人话）。"""
    c = get(name, d)
    if target.suffix.lower() not in c["exts"]:
        raise RuntimeError(f"「{name}」不管 {target.suffix} 文件")
    hit = cached(p, c, target)
    if hit:
        return hit
    out_dir = cache_dir(p)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / (_key(c, target) + ".pdf")
    part = out_dir / (final.stem + ".正在转.pdf")
    with _LOCK:
        if final.is_file() and _good(final):          # 等锁的时候别人已经转好了
            return final
        part.unlink(missing_ok=True)
        args = _args(c["convert"], c["dir"], {"输入": str(target.resolve()), "输出": str(part.resolve())})
        try:
            code, text = _run(args, c["dir"], CONVERT_TIMEOUT)
        except subprocess.TimeoutExpired:
            part.unlink(missing_ok=True)
            raise RuntimeError(f"转了 {CONVERT_TIMEOUT} 秒还没转完，先点「只看字」或者用本机软件打开")
        except OSError as e:
            raise RuntimeError(f"「{name}」跑不起来：{e.strerror or e}")
        if code != 0 or not _good(part):
            part.unlink(missing_ok=True)
            tail = " / ".join(text.splitlines()[-3:])[:300]
            raise RuntimeError(f"没转出来（退出码 {code}）" + (f"：{tail}" if tail else ""))
        part.replace(final)
        _trim(out_dir)
    return final


def _trim(out_dir: Path) -> None:
    """缓存多了删最早的（都是能重建的转换结果，不是谁的东西）。"""
    pdfs = sorted((f for f in out_dir.glob("*.pdf") if not f.stem.endswith(".正在转")), key=lambda f: f.stat().st_mtime)
    for f in pdfs[:-KEEP] if len(pdfs) > KEEP else []:
        f.unlink(missing_ok=True)


# ---------------------------------------------------------------- 挂一页的插件（S1-11 S2-6；为了网页终端，作者 10-02「就不能在网页端展示这个吗？」）
#
# 插件.md 写「页面: 窗口」「启动: {python} server.py --port {端口} --token {令牌} --cwd {项目}」「端口: 8790」：
# - 人在网页上点「打开」，核心才把它跑起来（只听 127.0.0.1），给它一个令牌；网页那页把 http://127.0.0.1:端口/?t=令牌 嵌进来
# - 跑起来以后它自己活着：核心重启、网页关了都不停（窗口里可能开着 agent）；端口和令牌记在 索引/插件页/<名字>.json，核心重启后照着接上
# - 没启用、检查不过的不给开；拿掉插件文件夹，那页就没了

PAGE_WAIT = 15                                    # 秒：起服务最多等这么久


def pages(d: Path | None = None) -> list[dict]:
    return [x for x in list_plugins(d) if x["page"] and x["start"]]


def _state_file(p: Project, name: str) -> Path:
    return p.index_dir / "插件页" / f"{name}.json"


def _ping(port: int, token: str) -> bool:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/ping?t={token}", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def _free_port(start: int) -> int:
    for port in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"{start}～{start + 29} 这些端口都被占了")


def _view(c: dict, st: dict) -> dict:
    return {"name": c["name"], "title": c["page"], "port": st["port"], "url": f"http://127.0.0.1:{st['port']}/?t={st['token']}"}


def page_status(p: Project, name: str, d: Path | None = None) -> dict:
    """这一页的服务在不在跑（在跑就给地址）。"""
    c = get(name, d)
    try:
        st = json.loads(_state_file(p, name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"name": name, "title": c["page"], "running": False}
    if not _ping(st["port"], st["token"]):
        return {"name": name, "title": c["page"], "running": False}
    return _view(c, st) | {"running": True}


def open_page(conn, p: Project, name: str, d: Path | None = None) -> dict:
    """人点「打开」：在跑就接上，不在跑就起一个。"""
    c = get(name, d)
    if not (c["page"] and c["start"]):
        raise RuntimeError(f"「{name}」不是挂一页的插件")
    if not enabled(conn, name):
        raise RuntimeError(f"插件「{name}」还没启用：在工具页点「启用」")
    now = page_status(p, name, d)
    if now["running"]:
        return now
    ck = check(name, d)
    if not ck["ok"]:
        raise RuntimeError(f"插件「{name}」这台电脑还用不了：{ck['msg']}")
    st = {"port": _free_port(c["port"] or 8790), "token": secrets.token_urlsafe(18), "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    args = _args(c["start"], c["dir"], {"端口": str(st["port"]), "令牌": st["token"], "项目": str(p.root)})
    f = _state_file(p, name)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f.with_suffix(".log"), "ab") as log:            # 它自己活着：不跟核心一起关（窗口里可能开着 agent）
        subprocess.Popen(args, cwd=c["dir"], stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    t0 = time.time()
    while time.time() - t0 < PAGE_WAIT:
        if _ping(st["port"], st["token"]):
            f.write_text(json.dumps(st), encoding="utf-8")
            return _view(c, st) | {"running": True}
        time.sleep(0.3)
    raise RuntimeError(f"「{name}」{PAGE_WAIT} 秒还没起来，看 索引/插件页/{name}.log")


def close_page(p: Project, name: str, d: Path | None = None) -> dict:
    """人点「关掉」：服务和它里面的窗口一起关。"""
    get(name, d)
    f = _state_file(p, name)
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        opener.open(urllib.request.Request(f"http://127.0.0.1:{st['port']}/quit?t={st['token']}", method="POST"), timeout=3)
    except Exception:
        pass
    f.unlink(missing_ok=True)
    return {"name": name, "running": False}
