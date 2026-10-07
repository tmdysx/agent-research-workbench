"""工具库：外部工具一个一张卡，编号 T1、T2…（号不回收），把「怎么调」写死，agent 照抄就能用。

- 卡片在应用根目录 `工具库/T<号> <名字>.md`，开头 --- 之间写：编号 · 名字 · 类别 · 一句话 · 检查 · 在哪 · 配套技能
- 类别两种：技术栈（项目拿什么做的：语言、框架、库、数据库）· 外部工具（做的时候要调的程序）；不写就算外部工具
  技术栈是每个项目自己的，新项目.bat 只带外部工具卡
- 网页只做一件事：跑卡上那条「检查」命令看装没装（只读，有超时）。**不替人跑工具**——调工具是 agent 的活
- 本机 PATH 可能有乱码（新开的窗口找不到程序），所以卡上写「在哪」：PATH 里找不到就去那找
- agent 缺工具时自己上网找、写一张新卡（propose），卡上「状态：待你装」；**装是人的事**
  （作者 2026-09-27 选的：「它找、写卡、给命令，你点头装」）。人装好了在工具页点「装好了」，查一遍通过就去掉那一行
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from files import _decode
from project import CODE_DIR
from skills import frontmatter

LIB = CODE_DIR / "工具库"
CHECK_TIMEOUT = 10          # 秒。draw.io 这类桌面程序冷启动要几秒
_CODE = re.compile(r"T(\d+)")
_VERSION = re.compile(r"\d+\.\d+")


def list_tools(lib: Path | None = None) -> list[dict]:
    """全部卡片，按编号排。"""
    lib = lib or LIB
    out = []
    if not lib.is_dir():
        return out
    for f in lib.glob("*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        code = fm.get("编号") or f.stem.split(" ")[0]
        m = _CODE.fullmatch(code)
        if not m:
            continue
        body = text[text.find("\n---", 3) + 4:].lstrip() if text.startswith("---") else text
        out.append({"code": code, "n": int(m.group(1)), "name": fm.get("名字", f.stem), "one_line": fm.get("一句话", ""),
                    "kind": fm.get("类别") or "外部工具",
                    "check": fm.get("检查", ""), "where": fm.get("在哪", ""), "skill": fm.get("配套技能", ""),
                    "state": fm.get("状态", ""), "file": f.name, "body": body,
                    "url": fm.get("官网", ""), "source": fm.get("来源", ""),
                    "manual": fm.get("来源") == "手工添加", "by": fm.get("作者", ""),
                    "created_at": fm.get("创建时间", "")})
    out.sort(key=lambda t: t["n"])
    for t in out:
        del t["n"]
    return out


def _in(d: Path, name: str) -> str | None:
    for cand in (d / name, *(d / (name + ext) for ext in (".exe", ".cmd", ".bat"))):
        if cand.is_file():
            return str(cand)
    return None


def find_exe(name: str, where: str = "", code: str = "") -> str | None:
    """找程序：PATH → 本机设置（这台电脑上找到过的）→ 卡上写的「在哪」（只当提示，可以写 %LOCALAPPDATA% 这种）→
    几个常见的安装位置看一两层。本机设置之外找到的，记进本机设置（作者 10-01：「用户的文件目录跟我的可不一样」）。"""
    hit = shutil.which(name)
    if hit:
        return hit
    import machine
    if code and machine.get("tools", code):
        hit = _in(Path(machine.get("tools", code)), name)
        if hit:
            return hit
    hit = _in(Path(os.path.expandvars(where)), name) if where else None
    if not hit:
        for base in machine.common_dirs():
            for pat in ("*", "*/bin", "*/cmd"):
                try:
                    dirs = [d for d in base.glob(pat) if d.is_dir()]
                except OSError:
                    continue
                hit = next((h for d in dirs if (h := _in(d, name))), None)
                if hit:
                    break
            if hit:
                break
    if hit and code:
        machine.put("tools", code, str(Path(hit).parent))
    return hit


def check(code: str, lib: Path | None = None) -> dict:
    """跑卡上的「检查」命令：装了吗、在哪、什么版本。只跑卡上写的那一条，不经过命令行解释器。查完记一会儿（开工单的灯用）。"""
    r = _check(code, lib)
    _CACHE[_cache_key(code, lib)] = (time.time(), r)
    return r


def _check(code: str, lib: Path | None = None) -> dict:
    t = next((x for x in list_tools(lib) if x["code"] == code), None)
    if t is None:
        raise KeyError(code)
    if not t["check"]:
        return {"ok": None, "msg": "未检查" if t["manual"] else "不用装（内置）"}
    if t["check"].startswith("文件 "):                 # 放进应用里的库（pdf.js 这类）：看文件在不在，不用跑程序
        rel = t["check"][3:].strip()
        f = (Path(lib).parent if lib is not None else CODE_DIR) / rel
        return ({"ok": True, "path": str(f), "version": "", "msg": ""} if f.is_file()
                else {"ok": False, "msg": f"应用里没有 {rel}"})
    # 不经过命令行解释器，只按空格拆；带引号的参数去掉外层引号再传
    args = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a for a in shlex.split(t["check"], posix=False)]
    exe = find_exe(args[0], t["where"], t["code"])
    if not exe and args[0].lower() in ("python", "python.exe"):   # 本机 PATH 里的 Python 路径可能是乱码：就用跑后台的这个 Python
        exe = sys.executable
    if not exe:
        return {"ok": False, "msg": f"没找到 {args[0]}：PATH 里没有，本机设置、卡上写的「在哪」、常见的安装位置里也没有（设置 → 本机 能填它在哪）"}
    try:
        r = subprocess.run([exe, *args[1:]], capture_output=True, timeout=CHECK_TIMEOUT, stdin=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return {"ok": False, "path": exe, "msg": f"{CHECK_TIMEOUT} 秒没反应"}
    except OSError as e:
        return {"ok": False, "path": exe, "msg": str(e)}
    text, _ = _decode(r.stdout + b"\n" + r.stderr, True)
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    ver = next((x for x in lines if _VERSION.search(x)), lines[0] if lines else "")
    return {"ok": r.returncode == 0, "path": exe, "version": ver[:120],
            "msg": "" if r.returncode == 0 else f"退出码 {r.returncode}"}


# ---------------------------------------------------------------- 查过的记一会儿：开工单的灯不用每次都把工具全跑一遍

_CACHE: dict[tuple[str, str], tuple[float, dict]] = {}


def _cache_key(code: str, lib: Path | None = None) -> tuple[str, str]:
    return os.path.normcase(str(Path(lib or LIB).resolve())), code


def check_cached(code: str, max_age: float = 600, lib: Path | None = None) -> dict:
    hit = _CACHE.get(_cache_key(code, lib))
    if hit and time.time() - hit[0] < max_age:
        return hit[1]
    return check(code, lib)


def forget(code: str | None = None, lib: Path | None = None) -> None:
    if code is None:
        _CACHE.clear()
    else:
        _CACHE.pop(_cache_key(code, lib), None)


# ---------------------------------------------------------------- agent 找到的新工具：写一张「待你装」的卡

_BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class Duplicate(ValueError):
    """重名时保留原卡供网页定位，不能覆盖它。"""

    def __init__(self, card: dict):
        self.card = card
        super().__init__(f"已经有这张卡了：{card['code']} {card['name']}")


@contextmanager
def _creation_lock(lib: Path):
    """Web/MCP 的短文件锁；进程退出由系统释放，不用数据库分配编号。"""
    lib.mkdir(parents=True, exist_ok=True)
    with (lib / ".工具卡创建.lock").open("a+b") as stream:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"\x00")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            lock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            unlock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            lock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            unlock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        deadline = time.monotonic() + 5
        while True:
            try:
                lock()
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError("工具卡正在保存，请稍后再试") from None
                time.sleep(0.01)
        try:
            yield
        finally:
            stream.seek(0)
            unlock()


def _write_new(lib: Path, name: str, build) -> dict:
    """锁内检查重名、分配编号，独占创建以免覆盖旧卡。"""
    with _creation_lock(lib):
        have = list_tools(lib)
        same = next((t for t in have if t["name"].lower() == name.lower()), None)
        if same:
            raise Duplicate(same)
        numbers = [int(_CODE.fullmatch(t["code"]).group(1)) for t in have]
        for f in lib.glob("*.md"):
            m = re.match(r"^T(\d+)(?:\s|$)", f.stem)
            if m:
                numbers.append(int(m.group(1)))
        n = max(numbers, default=0) + 1
        while True:
            code = f"T{n}"
            f = lib / f"{code} {name}.md"
            text = build(code)
            draft = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=lib,
                                                 prefix=".工具卡-", suffix=".tmp", delete=False) as stream:
                    draft = Path(stream.name)
                    stream.write(text)
                    stream.flush()
                    os.fsync(stream.fileno())
                # 原子发布完整文件，hard link 已存在就失败；读者不会看到空卡，也不覆盖旧卡。
                os.link(draft, f)
                break
            except FileExistsError:
                n += 1
            finally:
                if draft is not None:
                    draft.unlink(missing_ok=True)
        return next(t for t in list_tools(lib) if t["file"] == f.name)


def _manual_text(value: str, label: str, limit: int, *, required: bool = False, multiline: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label}要填写文字")
    controls = (r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]" if multiline
                else r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")
    if re.search(controls, value):
        raise ValueError(f"{label}不能含控制字符")
    value = value.strip()
    if required and not value:
        raise ValueError(f"要填写{label}")
    if len(value) > limit:
        raise ValueError(f"{label}不能超过 {limit} 字")
    return value


def create(name: str, *, one_line: str, kind: str = "外部工具", url: str = "", install: str = "", how: str = "",
           by: str = "人", lib: Path) -> dict:
    """人的手工工具卡：只保存说明，不配置或执行检查，不声称已经安装。"""
    if lib is None:
        raise ValueError("需要明确工具库位置")
    name = " ".join(_manual_text(name, "工具名", 40, required=True).split())
    if _BAD_NAME.search(name):
        raise ValueError("工具名不能有 \\ / : * ? \" < > | 这些符号")
    one_line = _manual_text(one_line, "一句话用途", 200, required=True)
    if kind not in ("技术栈", "外部工具"):
        raise ValueError("类别只有「技术栈」「外部工具」")
    url = _manual_text(url, "官网", 2048)
    if url:
        try:
            parsed = urlsplit(url)
            valid = (parsed.scheme in ("http", "https") and parsed.hostname and parsed.username is None
                     and parsed.password is None and not re.search(r'[\s\\<>\"]', url))
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("官网只能填写不含账号密码的 http/https 网址")
    install = _manual_text(install, "安装说明", 20000, multiline=True)
    how = _manual_text(how, "调用说明", 20000, multiline=True)
    by = _manual_text(by, "作者", 100, required=True)
    created_at = datetime.now().isoformat(timespec="seconds")

    def build(code):
        return (f"---\n编号: {code}\n名字: {name}\n类别: {kind}\n一句话: {one_line}\n检查:\n在哪:\n配套技能:\n"
                f"状态: 未检查\n官网: {url}\n来源: 手工添加\n作者: {by}\n创建时间: {created_at}\n---\n"
                f"# {code} {name}\n\n## 用途\n\n{one_line}\n\n## 官网\n\n{url or '（未填写）'}\n\n"
                f"## 下载与安装说明\n\n{install or '（未填写）'}\n\n## 怎么调\n\n{how or '（未填写）'}\n")

    return _write_new(Path(lib), name, build)


def propose(name: str, *, one_line: str, why: str, install: str, check_cmd: str = "", how: str = "",
            kind: str = "外部工具", by: str = "agent", lib: Path | None = None) -> dict:
    """写一张新卡（下一个 T 号），状态「待你装」。同名的已经有了就不写，告诉是哪张。"""
    lib = lib or LIB
    name = " ".join((name or "").split())
    if not name or len(name) > 40 or _BAD_NAME.search(name):
        raise ValueError("工具名要有、40 字以内、不能有 \\ / : * ? \" < > | 这些符号")
    if kind not in ("技术栈", "外部工具"):
        raise ValueError("类别只有「技术栈」「外部工具」")
    if not install.strip():
        raise ValueError("要写清怎么装（人照着装）")
    flat = lambda s: " ".join((s or "").split())

    def build(code):
        return (f"---\n编号: {code}\n名字: {name}\n类别: {kind}\n一句话: {flat(one_line)}\n检查: {flat(check_cmd)}\n"
                f"在哪:\n配套技能:\n状态: 待你装\n---\n# {code} {name}\n\n## 为什么要\n\n{why.strip()}\n\n"
                f"## 怎么装（你来装）\n\n```\n{install.strip()}\n```\n\n## 怎么调\n\n{how.strip() or '（装好以后 agent 补上）'}\n\n"
                f"> {by} 找的、写的卡，{datetime.now():%Y-%m-%d %H:%M}。装好了在网页「工具」页点「装好了」：跑一遍检查，通过就去掉「待你装」。\n")

    card = _write_new(Path(lib), name, build)
    return {key: card[key] for key in ("code", "name", "file")}


def set_state(code: str, state: str, lib: Path | None = None) -> None:
    """改卡上的「状态」那一行（空 = 去掉那一行）。"""
    t = next((x for x in list_tools(lib) if x["code"] == code), None)
    if t is None:
        raise KeyError(code)
    if t["manual"] and not t["check"] and state != "未检查":
        raise ValueError("尚未配置检查，不能标为装好了；请保留未检查状态")
    f = (lib or LIB) / t["file"]
    text = f.read_text(encoding="utf-8")
    end = text.find("\n---", 3)
    head, rest = text[:end], text[end:]
    lines = [x for x in head.split("\n") if not x.startswith("状态:")]
    if state:
        lines.append(f"状态: {state}")
    f.write_text("\n".join(lines) + rest, encoding="utf-8")
    forget(code, lib)
