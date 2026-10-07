"""本机 git 记账：多个 agent 一起干时，每交一件记一次——谁、改了哪些文件。只在本机，不推送、不上网。

作者 2026-09-30 选了「要」：「多个 agent（我开的几个 + Codex）同时干的时候，用本机 git 记下每个人改了哪些文件」。
- 项目里有 .git 才记，没有就不记（这里不替人建仓库）
- 只提交这个 agent 该管的：它领的模块、交付单列的文件、它拿着核心锁时的核心文件、记录（交付单、日志、计划、交接单）——
  别人手上还没交的改动不带进来
- 作者写那个 agent，提交人是这个工具；用户名、邮箱只设在项目的仓库里，不动电脑的全局设置
- git 出错不挡交付：记不上就在交付单里写一句
"""
from __future__ import annotations

import re
import subprocess

import tools
from project import Project

CORE_PATHS = ["backend", "模板.html", "界面英文.js", "治理界面.js", "启动.bat", "新项目.bat", ".mcp.json", "DESIGN.md", "外观"]
RECORD_PATHS = ["自动化/交付", "自动化/日志", "自动化/交接", "自动化/开工单", "笔记/日志", "治理/计划"]


def _git() -> str | None:
    card = next((t for t in tools.list_tools() if t["code"] == "T3"), None)
    return tools.find_exe("git", card["where"] if card else "", "T3")


def _run(p: Project, *args: str, timeout: int = 120) -> tuple[int, str]:
    exe = _git()
    if not exe:
        return 127, "没找到 git"
    r = subprocess.run([exe, "-C", str(p.root), *args], capture_output=True, timeout=timeout,
                       stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace").strip()


def enabled(p: Project) -> bool:
    return (p.root / ".git").exists() and _git() is not None


def _identity(p: Project) -> None:
    """提交人只设在这个项目的仓库里（不动全局）；中文文件名照原样显示。"""
    if _run(p, "config", "--local", "user.name")[0] != 0:
        _run(p, "config", "--local", "user.name", "自动化科研交互界面")
        _run(p, "config", "--local", "user.email", "console@localhost")
    _run(p, "config", "--local", "core.quotepath", "false")


def _author(agent: str) -> str:
    name = re.sub(r"[<>\n]", "", agent or "agent").strip() or "agent"
    mail = re.sub(r"[^A-Za-z0-9._-]", "-", name.split(":")[-1]) or "agent"
    return f"{name} <{mail}@agent.local>"


def commit(p: Project, paths: list[str], *, agent: str, message: str) -> str:
    """把这些路径（文件或文件夹，从项目根算）的改动提交一次。→ 短哈希；没东西可记返回空；记不上抛 RuntimeError。"""
    if not enabled(p):
        return ""
    keep = []
    for x in dict.fromkeys(x.strip().strip("/") for x in paths if x and x.strip()):
        if (p.root / x).exists() or _run(p, "ls-files", "--error-unmatch", "--", x)[0] == 0:
            keep.append(x)
    if not keep:
        return ""
    _identity(p)
    code, out = _run(p, "add", "-A", "--", *keep)
    if code != 0:
        raise RuntimeError(f"git add 没过：{out[-200:]}")
    # git 不认识的路径（空文件夹：领活时连带的模块里还没有文件）不能写进 commit，不然整次被拒（10-01 交 J29 时撞上：资料/素材 是空的）
    keep = [x for x in keep if _run(p, "ls-files", "--error-unmatch", "--", x)[0] == 0
            or _run(p, "ls-tree", "-r", "--name-only", "HEAD", "--", x)[1].strip()]
    if not keep:
        return ""
    if _run(p, "diff", "--cached", "--quiet", "--", *keep)[0] == 0:
        return ""                                          # 这些路径没变
    code, out = _run(p, "commit", "-m", message, f"--author={_author(agent)}", "--", *keep)
    if code != 0:
        raise RuntimeError(f"git commit 没过：{out[-200:]}")
    return _run(p, "rev-parse", "--short", "HEAD")[1]


def log(p: Project, limit: int = 20) -> list[dict]:
    """最近几次记账：哈希、谁、什么时候、写的什么。"""
    if not enabled(p):
        return []
    code, out = _run(p, "log", f"-{limit}", "--pretty=format:%h%x1f%an%x1f%ad%x1f%s", "--date=format:%m-%d %H:%M")
    if code != 0 or not out:
        return []
    return [dict(zip(("hash", "who", "at", "msg"), line.split("\x1f"))) for line in out.splitlines() if line.count("\x1f") == 3]
