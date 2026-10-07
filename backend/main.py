"""网页的后台：把网页发给浏览器、接网页的请求、项目一有变化就推给网页。双击 启动.bat 跑的就是它。

它做四件事：
1. 托管网页（模板.html）
2. 给网页读写数据的接口 /api/...——打开 /docs 能看见全部、能点着试
3. WebSocket /ws：库一变就通知网页，网页不用刷新。agent 从 MCP 写进来的也算
4. 盯着项目文件夹：谁放了、改了文件（蓝图、计划也在里面），网页不用刷新就看见

端口不写死：默认 8770，占用了就往后找。数据库路径也可配（见 project.py）。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import shutil
import uuid
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from contextlib import asynccontextmanager
from typing import Iterator

from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field, StrictBool

import agents
import claims
import dispatch
import sessions
import supervise
import machine
import builtin
import new_project
import skins
import bplook
import drafts
import toolbox
import tool_guides
import repos
import zips
import links
import board
import work_packages
import freeze
import scanmap
import codemap
import autolaunch
import answers
import blueprint
import commands
import files
import file_actions
import content_modules
import intake
import journal
import notebook
import capture
import hotkeys
import outline
import skills
import snapshot
import project as proj
import deliveries
import downloads
import ideas
import library
import office
import plugins
import requirements
import workorders
import runs
import store
import tools
import trash
from project import CODE_DIR, Project, resolve

APP_ID = "research-console"
PAGE = CODE_DIR / "模板.html"
HERE = Path(__file__).resolve().parent                 # backend/：改了这里的程序，后台自己重启


def ui_version() -> str:
    """网页那两份文件（模板.html、界面英文.js）的版本：大小 + 改动时间。一变，开着的网页自己刷新
    （作者 2026-09-27：「自动更新网页」）。"""
    parts = []
    for f in (PAGE, PAGE.parent / "界面英文.js", PAGE.parent / "治理界面.js", PAGE.parent / "代码地图.js", PAGE.parent / "自动化面板.js", PAGE.parent / "员工分配图.js", PAGE.parent / "流程编辑器.js", PAGE.parent / "小窗.js", PAGE.parent / "内容工作台.js"):
        try:
            st = f.stat()
            parts.append(f"{st.st_size}:{st.st_mtime_ns}")
        except OSError:
            parts.append("-")
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]
DEFAULT_PORT = 8770
EMBED_JS = (b"<script>(function(){function s(){var d=document.documentElement,b=document.body;"
            b"parent.postMessage({rcHeight:Math.ceil(Math.max(d.scrollHeight,b?b.scrollHeight:0,d.getBoundingClientRect().height))},'*')}"
            b"addEventListener('load',s);setTimeout(s,300);setTimeout(s,1500);"
            b"if(window.ResizeObserver)new ResizeObserver(s).observe(document.documentElement)})()</script>")


class Hub:
    """连着的网页。库一变，挨个通知。
    走到哪扫到哪（S1-8 S2-43）：focus 每个网页在看哪页 · paths 系统通知来的、还没分的路径 · now 设置里点「现在扫」的片 · poke 叫醒 watch。"""

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.focus: dict = {}
        self.paths: set[str] = set()
        self.now: set[str] = set()
        self.poke = asyncio.Event()

    async def broadcast(self, msg: dict) -> None:
        for ws in list(self.clients):
            try:
                await ws.send_json(msg)
            except Exception:
                self.clients.discard(ws)


SCAN = {"live": False, "why": "", "files": 0, "took": 0.0, "at": "", "events": 0, "areas": []}   # 设置 →「扫描」那块看的：现在怎么扫、上一回扫了哪几片
BIG_SCAN = 0.3                                          # 一回扫超过这么久：先告诉网页「扫着…」（第一次走进几万个文件的地方），扫完再通知


async def _scan_walk(project: Project, hub: Hub, walk, areas) -> dict:
    """真正读文件时报告开始/结束；无变化和取消也收尾，不把文件变动事件当结束。"""
    st = scanmap.state(project)
    selected = sorted(areas)
    st["busy"] = selected
    job = None
    try:
        await hub.broadcast({"type": "scanning", "active": True, "areas": selected, "project": str(project.root)})
        job = asyncio.create_task(asyncio.to_thread(walk, selected))
        # 取消协程不能终止已经在读文件的线程；等真正读完，再撤回火苗状态。
        return await asyncio.shield(job)
    except asyncio.CancelledError:
        if job is not None:
            try:
                await job
            except Exception:
                pass
        raise
    finally:
        st["busy"] = []
        await hub.broadcast({"type": "scanning", "active": False, "areas": [], "project": str(project.root)})


async def _notify(project: Project, hub: Hub, stop: asyncio.Event) -> None:
    """系统通知（S1-8 S2-42）：Windows 一有文件变动就把路径交给 watch，watch 按片分——热的马上扫、冷的记一笔、不看的丢掉（S2-43）。
    用 watchfiles（MIT，uvicorn 带着装的）；没有它就直接返回，watch 照老办法隔一会儿扫热的那几片。"""
    try:
        import watchfiles
    except ImportError:
        SCAN.update(live=False, why="这台电脑没装 watchfiles")
        return
    SCAN.update(live=True, why="")
    root = str(project.root)

    def rel(path: str) -> str:
        try:
            return os.path.relpath(path, root).replace("\\", "/")
        except ValueError:                               # 别的盘：不是这个项目的
            return ".."

    def keep(_change, path: str) -> bool:              # 库、缓存、存档和回收站里面、.claude/worktrees：通知都不收
        r = rel(path)
        return r.split("/")[0] != ".." and not scanmap.builtin_skip(project, r)
    async for changes in watchfiles.awatch(root, watch_filter=keep, debounce=200, step=50, stop_event=stop,
                                           ignore_permission_denied=True):
        SCAN["events"] += 1
        hub.paths.update(rel(path) for _, path in changes)
        hub.poke.set()


async def watch(project: Project, hub: Hub, interval: float = 0.5, use_sessions: bool = False, realtime: bool = True) -> None:
    """后台盯着项目（作者 2026-09-25：「我都要实时的要活的东西」；10-02：「像我玩游戏一样，走到哪里就扫描到哪里」）。

    - 项目分成一片一片（scanmap）：资料/ 下每个模块 · 治理 · 自动化 · 核心 · 其余顶层文件夹 · 根目录散文件。启动时全走一遍
    - 系统通知来一批路径：热的片（你在看的、agent 在干的、一直盯着的）马上扫那一片——只换那一片的快照，监管比、网页通知带上哪几片；
      冷的只记一笔「有变动」（第二栏标签亮小点），不扫、不叫网页重画；不看的丢掉
    - 走进去（网页换到那页、agent 领了那里的活）：那片有账先扫；兜底每 N 分钟（自动化/扫描规则.md）扫有账的冷片，没账的不碰
    - 没有系统通知（没装 watchfiles、realtime=False）：热的几片隔一会儿扫（扫一回用的时间 × 10，最快 1.5 秒），冷的到兜底全扫，走进去就扫
    - 每半秒（有通知时马上）看一眼库的版本号涨了没：网页点的、agent 从另一个进程写的都会记一条 event，不管谁写的这里都看得见
    扫文件放在另一个线程里，扫的时候网页照样能点。"""
    conn = store.connect(project.db_path)
    last_v = store.version(conn)
    last_ui = ui_version()
    loop = asyncio.get_running_loop()
    st = scanmap.state(project)
    R = {"key": "-", "sweep": 30, "rules": []}

    def load_rules() -> set[str]:                      # 规则文件改了：读新的，返回规则变了的路径
        try:
            k = (project.root / scanmap.RULES_FILE).stat().st_mtime_ns
        except OSError:
            k = None
        if k == R["key"]:
            return set()
        old = {(x["path"], x["mode"]) for x in R["rules"]}
        R.update(scanmap.read_rules(project), key=k)
        st["next_sweep"] = time.time() + R["sweep"] * 60
        return {x[0] for x in old ^ {(x["path"], x["mode"]) for x in R["rules"]}}

    def walk(areas) -> dict:
        return {a: scanmap.walk_area(project, a, R["rules"]) for a in areas}

    def flat(parts: dict) -> dict:                     # 给监管的：只要文件、只要看的范围里的，合成一份
        return {k: v for part in parts.values() for k, v in part.items()
                if not k.endswith("/") and scanmap.visible(project, R["rules"], k)}

    def supervise_scan(old, new):                     # 监管（10-01）：两遍扫描比一比，照规矩记；用自己的连接，不跟这个循环抢
        c = store.connect(project.db_path)
        try:
            return supervise.on_scan(c, project, old, new, use_sessions=use_sessions)
        finally:
            c.close()

    def supervise_state():
        c = store.connect(project.db_path)
        try:
            return supervise.check_state(c, project, sessions.board() if use_sessions else None)
        finally:
            c.close()

    def launch_tick():                                 # 全自动开工（S1-8 S2-50）：领着件、没开窗口的，在网页终端里给它开一个
        c = store.connect(project.db_path)
        try:
            saved = snapshot.timed_save(c, project)    # 设置里开了定时存：到点、有改动就存一档（S1-8 S2-59）
            import tidy
            tidied = tidy.timed(c, project)            # 设置里「多久查一次乱」到点了：查一遍、记日志（S1-8 S2-61）
            return bool(autolaunch.tick(c, project)) or bool(saved) or bool(tidied)
        finally:
            c.close()
    scanmap.migrate(conn, project)                     # 以前在「模块」表设的扫描方式搬进 自动化/扫描规则.md（一次）
    load_rules()
    stop = asyncio.Event()
    live = asyncio.create_task(_notify(project, hub, stop)) if realtime else None   # 先挂上系统通知再全走一遍：中间改的不漏
    try:
        snap: dict = await _scan_walk(project, hub, walk, scanmap.all_areas(project))   # {片: {路径: (大小, 时间)}}
    except BaseException:
        stop.set()
        if live is not None:
            live.cancel()
        st.update(on=False, hot={}, busy=[])
        conn.close()
        raise
    st["on"] = True
    old = supervise.restore(project)
    await asyncio.to_thread(supervise_scan, None if old is None else {k: v for k, v in old.items() if scanmap.visible(project, R["rules"], k)},
                            flat(snap))               # 跟上回存的样子比：重启那一下、关着时的改动也看得到

    async def scan(areas: set, quiet: bool = False) -> bool:
        """扫这几片：只换这几片的快照；有变化就给监管比、通知网页（带上哪几片）。quiet：规则刚改，只当新起点不报。返回通知了网页没有。"""
        nonlocal snap
        t0 = loop.time()
        parts = await _scan_walk(project, hub, walk, areas)
        cleared = [a for a in areas if st["dirty"].pop(a, None)]
        changed = {a for a in areas if parts[a] != snap.get(a, {})}
        gone = set()
        if changed & {project.materials.name, scanmap.ROOT_AREA}:   # 整个模块 / 顶层文件夹没了：那一片马上扫空，监管看得到
            gone = {k.rstrip("/") for a in changed & {project.materials.name, scanmap.ROOT_AREA}
                    for k in set(snap.get(a, {})) - set(parts[a]) if k.endswith("/")}   # 「笔记/」→ 笔记那片；「资料/旧/」→ 资料/旧 那片
            gone = {g for g in gone if g in snap and g not in areas}
            if gone:
                parts.update(await _scan_walk(project, hub, walk, gone))
                changed |= {g for g in gone if parts[g] != snap[g]}
                cleared += [g for g in gone if st["dirty"].pop(g, None)]
        SCAN.update(took=round(loop.time() - t0, 3), at=datetime.now().strftime("%m-%d %H:%M:%S"), areas=sorted(areas | gone))
        if not changed:
            if cleared:
                await hub.broadcast({"type": "dirty", "dirty": dict(st["dirty"])})
            return bool(cleared)
        before = flat(snap)
        snap.update(parts)
        for a in [a for a in changed if not parts[a] and not (project.root / a).exists()]:
            snap.pop(a, None)
        SCAN["files"] = sum(1 for part in snap.values() for k in part if not k.endswith("/"))
        found = await asyncio.to_thread(supervise_scan, None if quiet else before, flat(snap))
        if found:
            await hub.broadcast({"type": "supervise"})
        scanmap.forget_stats(project, changed)
        if changed & {project.materials.name, scanmap.ROOT_AREA}:
            store.sync_folders(conn, project)          # 资料/ 下多了、少了文件夹：模块跟着变
        try:
            await asyncio.to_thread(skills.write_index, project)
        except ValueError as e:
            print(f"[skills] 目录未更新，请修正技能清单：{e}", file=sys.stderr)
        await hub.broadcast({"type": "files", "areas": sorted(changed), "dirty": dict(st["dirty"])})
        return True

    SCAN["files"] = sum(1 for part in snap.values() for k in part if not k.endswith("/"))
    last_hot: set = set()
    next_state = next_hot = 0.0
    next_launch = loop.time() + 20                   # 起来先等一会儿（网页终端、认领都安顿好）再看要不要自动开工
    catchup = loop.time() + 1.0                        # 系统通知挂上前那一下改的：一秒后热的几片和结构再扫一回
    try:
        while True:
            try:
                await asyncio.wait_for(hub.poke.wait(), interval)
            except asyncio.TimeoutError:
                pass
            hub.poke.clear()
            try:
                if live is not None and live.done():           # 系统通知停了（没装、出错）：退回老办法
                    if not live.cancelled() and live.exception():
                        print(f"[watch] 系统通知停了，改回每隔一会儿扫：{live.exception()}", file=sys.stderr)
                        SCAN["why"] = f"系统通知出错停了：{live.exception()}"
                    live = None
                    SCAN["live"] = False
                if not realtime:
                    SCAN["why"] = "这次启动没开系统通知"
                moved = load_rules()
                if moved:                                    # 规则改了（设置页、手改文件）：碰到的那几片照新规矩重扫当起点，不报监管
                    await scan({a for a in set(scanmap.all_areas(project)) | set(snap)
                                if any(a == x or a.startswith(x + "/") or x.startswith(a + "/") or a == scanmap.area_of(project, x) for x in moved)},
                               quiet=True)
                hot = scanmap.hot_areas(conn, project, list(hub.focus.values()), R["rules"])
                st["hot"] = hot
                todo = {a for a in hub.now if a in snap or a in st["dirty"] or (project.root / a).exists()}
                hub.now.clear()                              # 设置里点了「现在扫」
                entered = set(hot) - last_hot
                last_hot = set(hot)
                todo |= {a for a in entered if a in st["dirty"] or live is None}   # 走进去：有账的先扫（没有系统通知的，不知道有没有账，扫）
                bumped: dict[str, int] = {}
                paths, hub.paths = hub.paths, set()
                for rel in paths:                            # 系统通知来的：按片分
                    kind = scanmap.classify(project, rel, R["rules"], set(hot))
                    if kind == "hot":
                        todo.add(scanmap.area_of(project, rel))
                    elif kind == "cold":
                        a = scanmap.area_of(project, rel)
                        bumped[a] = bumped.get(a, 0) + 1
                for a, n in bumped.items():
                    if a not in todo:
                        st["dirty"][a] = st["dirty"].get(a, 0) + n
                if catchup and loop.time() >= catchup:
                    catchup = 0.0
                    todo |= set(hot) | {scanmap.ROOT_AREA, project.materials.name}
                fallback = live is None and loop.time() >= next_hot
                if fallback:                                 # 没有系统通知：热的几片（加上根目录、资料/ 这层）隔一会儿扫一遍
                    todo |= set(hot) | {scanmap.ROOT_AREA, project.materials.name}
                if time.time() >= st["next_sweep"]:          # 兜底：有账的冷片（没有系统通知：全部冷片）
                    st["next_sweep"] = time.time() + R["sweep"] * 60
                    todo |= set(st["dirty"]) if live is not None else set(scanmap.all_areas(project)) - set(hot)
                told = False
                if todo:
                    t0 = loop.time()
                    told = await scan(todo)
                    if fallback:
                        next_hot = loop.time() + max(3 * interval, 1.5, 10 * (loop.time() - t0))
                if bumped and not told:
                    await hub.broadcast({"type": "dirty", "dirty": dict(st["dirty"])})
                if use_sessions and loop.time() >= next_launch:   # 全自动开工：一分钟看一次（只在正式启动的后台里跑，测试不跑）
                    next_launch = loop.time() + 60
                    if await asyncio.to_thread(launch_tick):
                        await hub.broadcast({"type": "changed", "v": store.version(conn)})
                if loop.time() >= next_state:                # 监管：领着活不动、没报到、问答里定了的（半分钟看一次）
                    next_state = loop.time() + 30
                    if await asyncio.to_thread(supervise_state):
                        await hub.broadcast({"type": "supervise"})
                v = store.version(conn)
                if v != last_v:
                    last_v = v
                    await hub.broadcast({"type": "changed", "v": v})
                ui = ui_version()
                if ui != last_ui:                      # 网页改了：开着的网页自己刷新
                    last_ui = ui
                    await hub.broadcast({"type": "ui", "ui": ui})
            except Exception as e:              # 库一时忙、文件一时读不了：记下来，下一轮再试，别让这个循环停掉
                print(f"[watch] {e}", file=sys.stderr)
    finally:
        stop.set()
        if live is not None:
            live.cancel()
        st.update(on=False, hot={}, busy=[])
        st["stats"].clear()
        st["dirty"].clear()
        conn.close()


async def watch_tasks(hub: Hub, interval: float = 5.0) -> None:
    """后台任务表：每 5 秒读一遍各家 agent 的会话记录（读过的只读新增的那段），表变了就让开着的网页刷新那一块。
    作者 2026-10-01：「我希望，网页端能有这样的表」。只在正式启动时开（自动测试不读你电脑上的会话记录）。"""
    last = None
    while True:
        try:
            rows = await asyncio.to_thread(sessions.board)
            sig = [(r["id"], r["state"], r["tools"], r["tokens"], r["action"]) for r in rows]
            if sig != last:
                last = sig
                await hub.broadcast({"type": "tasks"})
        except Exception as e:              # 某份记录一时读不了：下一轮再试，别让这个循环停掉
            print(f"[tasks] {e}", file=sys.stderr)
        await asyncio.sleep(interval)


# ---------------------------------------------------------------- 请求体

class AddModuleIn(BaseModel):
    name: str = Field(..., description="模块名，40 字以内", examples=["检索页"])
    one_line: str = Field("", description="一句话说它是干什么的（可空）")
    en: str = Field("", description="英文名（可空）", examples=["Data"])


class TextIn(BaseModel):
    text: str = Field(..., description="文字内容")


class DraftIn(BaseModel):
    text: str = Field(..., description="草稿现在的样子")
    recorded: bool = Field(False, description="刚「记下」清空的：已经在笔记本里了，不用留底")


class NoteIn(BaseModel):
    text: str = Field(..., description="笔记内容")
    kind: str = Field("笔记", description="这条是什么：笔记 / 截图 / 录屏 / 删除请求（机器记的进日志，不进笔记）")
    attach: list[str] = Field(default_factory=list, description="一起记下的截图、录屏（草稿里的名字，见 /api/note/drafts）")
    idea: bool = Field(False, description="这条是想法：照旧记进笔记，同时在 资料/想法/想法.md 多一行（连回这条笔记）")


class IdeaIn(BaseModel):
    text: str = Field(..., description="想法（原话）")
    about: str = Field("整个项目", description="关于哪个模块；整个项目就写「整个项目」")
    source: str = Field("自己写", description="从哪来：笔记 总-012 / 对话 / 自己写")


class DownloadIn(BaseModel):
    title: str = Field("", description="标题（空着就用 DOI / 链接）")
    url: str = Field("", description="链接：PDF 地址、论文页面、arXiv（http / https）")
    doi: str = Field("", description="DOI（有就写，能去找合法的免费版）")
    why: str = Field("", description="为什么要这篇")
    authors: str = Field("", description="作者（知道就写，不知道 OpenAlex 会补）")
    year: str = Field("", description="年")
    venue: str = Field("", description="期刊 / 会议")
    note: str = Field("", description="备注（比如：是书、是软件手册，不必下 PDF）")


class LibInfoIn(BaseModel):
    标签: list[str] | str | None = Field(None, description="标签（列表，或用「、」隔开）")
    分组: list[str] | str | None = Field(None, description="分组（列表，或用「、」隔开）")
    阅读状态: str | None = Field(None, description="没读 / 在读 / 读完")


class PaperNoteIn(BaseModel):
    page: int = Field(..., description="第几页（从 1 数）")
    quote: str = Field("", description="选中的原句")
    text: str = Field("", description="你写的（可空）")
    color: str = Field("黄", description="黄 / 绿 / 红 / 蓝 / 黑")


class PaperMarkIn(BaseModel):
    page: int = Field(..., description="第几页（从 1 数）")
    kind: str = Field(..., description="高亮 / 便签 / 笔")
    color: str = Field("黄", description="黄 / 绿 / 红 / 蓝 / 黑")
    points: list[list[float]] | None = Field(None, description="笔：[[x, y], …]，PDF 自己的单位（左上角起、放大前）")
    rects: list[list[float]] | None = Field(None, description="高亮：[[x, y, 宽, 高], …]")
    at: list[float] | None = Field(None, description="便签贴在哪：[x, y]")
    text: str = Field("", description="便签写的字；高亮时是选中的原句")
    width: float = Field(1.5, description="笔的粗细")


class PaperNoteEditIn(BaseModel):
    at: str = Field(..., description="这条笔记的时间（对上是不是那一条）")
    text: str = Field("", description="改成什么（原句不动）")
    color: str = Field("黄", description="黄 / 绿 / 红 / 蓝 / 黑")


class PluginOnIn(BaseModel):
    on: bool = Field(True, description="true 启用 / false 停用")


class ConvertIn(BaseModel):
    path: str = Field(..., description="文件路径：给了 module 就从模块算，没给就从项目根算")
    module: str = Field("", description="模块名（可空）")


class OpenLocalIn(BaseModel):
    path: str = Field(..., description="文件路径：给了 module 就从模块算（跟模块页一样），没给就从项目根算")
    module: str = Field("", description="模块名（可空）")


class AskIn(BaseModel):
    text: str = Field(..., description="你想问 agent 的")
    where: str = Field("", description="出处：在看什么的时候问的（文献 L1 第 3 页、原句……）")


class PickIn(BaseModel):
    index: int = Field(..., description="点的是第几个候选（从 0 数）")


class DestIn(BaseModel):
    dest: str = Field(..., description="放一放 / 不要 / 空（重新整理）")


class CaptureIn(BaseModel):
    kind: str = Field(..., description="image = 截图（Win+Shift+S）；video = 录屏（Win+Shift+R）")


class CaptureSettingsIn(BaseModel):
    shot: str = Field("", description="截图的全局快捷键，比如 Ctrl+Alt+S；空 = 不用", examples=["Ctrl+Alt+S"])
    record: str = Field("", description="录屏的全局快捷键，比如 Ctrl+Alt+R；空 = 不用", examples=["Ctrl+Alt+R"])
    folder: str = Field("", description="系统截图工具把录屏存在哪；空 = 用它的默认（视频\\Screen Recordings）")


class SortIn(BaseModel):
    module: str = Field(..., description="放进哪个模块", examples=["文献"])
    folder: str = Field("", description="模块里的哪个文件夹（从模块根算，空 = 模块根）", examples=["原文"])


class ConfirmIn(BaseModel):
    confirm: bool = Field(False, description="人看过警告、点了确定")


class SaveIn(BaseModel):
    name: str = Field(..., description="这一档叫什么，比如「表1跑完」", examples=["表1跑完"])
    why: str = Field("", description="为什么存这一档")
    mode: str = Field("核心", description="核心（程序和规矩，不带资料、笔记、零碎文件）/ 只记指纹；全量、自定义按核心存")
    picks: list[str] = Field(default_factory=list, description="（不用了：核心存哪些是定好的）")


class EstimateIn(BaseModel):
    mode: str = Field("核心", description="核心 / 只记指纹")
    picks: list[str] = Field(default_factory=list)


class RestoreIn(BaseModel):
    paths: list[str] = Field(default_factory=list, description="只复活这些文件或文件夹；空着 = 整档")
    confirm: bool = Field(False, description="人看过警告、点了确定")
    whole: bool = Field(False, description="true＝整份回到那一档（资料、零碎文件也回去）；默认只换程序和规矩")
    builtin_revision: str | None = Field(None, description="恢复预览中的内置标记版本，确认时原样回传")


class GrowIn(BaseModel):
    name: str = Field(..., description="这根枝叫什么（当文件夹名）")
    why: str = Field("", description="为了什么")
    base: str = Field("现在", description="从哪一档长：C<n>，或「现在」（先存一档）")
    for_: str = Field("", alias="for", description="挂哪件 / 哪条需求，比如「S1-8 S2-55」")


class BranchActIn(BaseModel):
    confirm: bool = Field(False, description="人看过警告、点了确定")
    why: str = Field("", description="为什么（砍枝时写）")


class AssignIn(BaseModel):
    agent: str = Field(..., description="员工编号或名字，比如 G5")
    goal: str = Field("", description="派哪件：S1 编号")
    sub: str = Field("", description="派哪件：S2 编号")
    open: bool = Field(True, description="在网页终端里给它开窗口（进枝的文件夹）")


class ManualToolIn(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    one_line: str
    kind: str = "外部工具"
    url: str = ""
    install: str = ""
    how: str = ""


class KnobsIn(BaseModel):
    patch: dict = Field(..., description="要改的设置，比如 {\"level\": 4} 或 {\"keep\": 20}；带了 level 又没带 max_agents / per_item，照那一档填")


class IgnoreIn(BaseModel):
    rows: list[dict] = Field(default_factory=list, description="存档不存的：[{path, why}]，整张表")


class FruitPickIn(BaseModel):
    code: str = Field(..., description="比较单，比如 比-3")
    branch: str = Field("", description="挑哪根合（枝-5）；空 = 都不行，全打回")
    why: str = Field(..., description="为什么")


class ArchiveIn(BaseModel):
    rels: list[str] | None = Field(None, description="收哪些（从项目根写）；不写 = 现在能收的全收")
    confirm: bool = Field(False, description="人看过要收哪些、点了确定")


class BackIn(BaseModel):
    rels: list[str] = Field(..., description="拿回来哪些（原来的路径）")


class RewriteAskIn(BaseModel):
    path: str = Field(..., description="要重写的正本，从项目根写")
    note: str = Field("", description="想怎么改（可空）")


class BackupIn(BaseModel):
    with_saves: bool = Field(True, description="连存档（存档/）一起备份")
    confirm: bool = Field(False, description="人看过放哪、多大、磁盘剩多少，点了确定")


class FruitIn(BaseModel):
    demo: str = Field(..., description="怎么看、看什么")
    checks: list[dict] = Field(default_factory=list, description="检查：[{name, ok, detail}]")


class PurgeIn(BaseModel):
    codes: list[str] = Field(..., description="要彻底删掉的回收站编号，比如 X3")
    confirm: bool = Field(False, description="人看过警告、点了确定")


class FileTrashIn(BaseModel):
    path: str = Field(..., description="阅读响应中的真实项目相对路径")
    project: str = Field(..., description="阅读响应中的项目身份")
    revision: str = Field(..., description="阅读时文件版本；变化后必须重新读取")
    reason: str = Field("网页文件阅读页手动删除", max_length=2000)


class BuiltinFileIn(BaseModel):
    path: str = Field(..., max_length=2048)
    enabled: StrictBool
    project: str
    revision: str = Field(..., min_length=64, max_length=64)


class PaperIn(BaseModel):
    done: bool = Field(True, description="true = 跑完了（记下今天）；false = 取消")


class ScanRuleIn(BaseModel):
    path: str = Field(..., description="文件夹，从项目根写，比如 资料/实验/原始数据")
    mode: str = Field(..., description="一直盯着 / 走到才扫 / 不看")
    note: str = Field("", description="备注（为什么这么设）")


class ScanIn(BaseModel):
    sweep: int = Field(30, description="兜底：每几分钟把记了有变动的冷地方扫一遍（10 / 30 / 60）")
    rules: list[ScanRuleIn] = Field(default_factory=list, description="自定义规则，一行一个文件夹；写得越细的越算数")


class ScanSetIn(BaseModel):
    paths: list[str] = Field(..., description="勾上的文件夹或文件，从项目根写")
    mode: str = Field("", description="一直盯着 / 走到才扫 / 不看；空 = 去掉它们身上的自定义")
    note: str = Field("", description="备注（可空）")


class ScanNowIn(BaseModel):
    area: str = Field(..., description="哪一片，比如 资料/实验")


class ModuleInfoIn(BaseModel):
    en: str | None = Field(None, description="英文名（中英对照时跟在中文后面），不改就不传")
    one_line: str | None = Field(None, description="一句话说它是干什么的，不改就不传")


class OrderIn(BaseModel):
    names: list[str] = Field(..., description="第二栏从左到右的模块名；固定的三个永远在最前，不用列")


class SettingsIn(BaseModel):
    level: int = Field(..., description="档位：0 手动 / 1 半自动 / 2 自动", examples=[1])
    rounds: int = Field(..., description="每次最多几圈（1–50）", examples=[5])


class WorkOrderNewIn(BaseModel):
    name: str = Field("", description="这张单叫什么（给了 module 可空：默认「<模块>模块装修」）", examples=["文献模块装修"])
    module: str = Field("", description="装修哪个模块：给了就按这个模块的需求、蓝图、戒律配齐", examples=["文献"])
    target: list[str] = Field(default_factory=list, description="目标：「文献」整个模块、「文献 需-2」「文献 S2-3」；或总蓝图的「S1-10」「S1-10 S2-3」", examples=[["文献"]])
    product: str = Field("", description="要做成什么，一句话（空着就用蓝图里那个 S1 的一句话）")


class WorkOrderPatchIn(BaseModel):
    name: str | None = None
    product: str | None = Field(None, description="要做成什么")
    target: list[str] | None = Field(None, description="目标")
    rules: list[str] | None = Field(None, description="戒律文件，从项目根写，如 AGENTS.md、资料/文献/戒律.md")
    modules: list[str] | None = Field(None, description="模块名")
    tools: list[str] | None = Field(None, description="工具卡编号，如 T10")
    materials: list[str] | None = Field(None, description="材料文件，从项目根写")
    saves: list[str] | None = Field(None, description="存档编号，如 C1")
    notes: dict[str, str] | None = Field(None, description="交代：{要做到, 建议, 不许} 带哪格改哪格")
    level: int | None = Field(None, description="档位：1 半自动 / 2 自动")
    rounds: int | None = Field(None, description="每次最多几圈（1–50）")
    fails: int | None = Field(None, description="同一件失败几次停（1–5）")


class ReasonIn(BaseModel):
    reason: str = Field(..., description="打回的理由，一句话，agent 照着改")


class AgentNewIn(BaseModel):
    name: str = Field(..., description="它调接口时报的名字，如 codex、claude-code#2", examples=["codex"])
    template: str = Field("空白", description="从哪个样子开始：规划的 / 审核的 / 写代码的 / 写文档的 / 验收的 / 空白")
    program: str = Field("", description="用什么：哪家程序（Claude Code、Codex……）")
    line: str = Field("", description="一句话：它是干什么的（空着用样子里的）")


class AgentPatchIn(BaseModel):
    crafts: list[str] | None = None
    auto: bool | None = None
    paused: bool | None = None
    plan_required: bool | None = None
    program: str | None = None
    line: str | None = None
    scope: list[str] | None = Field(None, description="管哪些：模块名或目标编号；空 = 都能领")
    avoid: list[str] | None = Field(None, description="不碰：模块名或目标编号")
    core: str | None = Field(None, description="改核心：能 / 不能")
    roles: list[str] | None = Field(None, description="岗位：规划 · 审核 · 干活 · 验收 · 带队，能兼；空 = 干活")
    level: str | None = Field(None, description="等级：见习 / 正式 / 资深")
    boss: str | None = Field(None, description="上级：「人」或另一个 agent 的编号（G1）")
    skills: list[str] | None = None
    opener: str | None = Field(None, description="开工的话：给这家 agent 说的第一句")
    brief: str | None = Field(None, description="交代（正文）")
    why: str = Field("", description="为什么改（记进「变迁」）")


class AgentCopyIn(BaseModel):
    name: str = Field(..., description="新的那个叫什么")


class LaunchIn(BaseModel):
    on: bool | None = Field(None, description="全自动开工开 / 关（只有人点）")
    max: int | None = Field(None, description="同时最多开几个 agent 窗口（1～12，默认 3）")
    resume: bool = Field(False, description="明确恢复已退出的终态员工；运行中和待审中的预算保留")


class MachineIn(BaseModel):
    kind: str = Field(..., description="工具 / 会话记录")
    key: str = Field(..., description="工具卡号（如 T3）或哪家 agent（Claude Code / Codex）")
    value: str = Field("", description="在哪（文件夹）；空着 = 让程序自己找")


class BuiltinIn(BaseModel):
    extra: list[str] = Field(default_factory=list)
    business_modules: list[str] | None = None


class PickFolderIn(BaseModel):
    start: str = Field('', description="从哪个文件夹开始找（可空：项目旁边）")


class NewProjectIn(BaseModel):
    name: str
    where: str = ''
    extra: list[str] = Field(default_factory=list)
    business_modules: list[str] | None = None


class ContentDocumentIn(BaseModel):
    path: str
    text: str
    revision: str = ''
    reason: str = ''
    project_root: str


class DraftPickIn(BaseModel):
    act: str = Field(..., description="行 / 不要")
    fields: dict = Field(default_factory=dict, description="改一下：改过的格（做什么、为了、怎么验……），不给就照原样")


class FinalIn(BaseModel):
    on: bool = Field(True, description="true 定稿，false 取消定稿")
    words: str = Field("", description="你的一句话，写进「规划：定稿 · 日期 · 作者：「…」」")


class ReleaseIn(BaseModel):
    goal: str = Field(..., description="目标，如 S1-9；模块蓝图写模块名")
    sub: str = Field("", description="哪件，如 S2-5")
    note: str = Field("", description="为什么放（下一个接手的看得到）")


class AgentDelIn(BaseModel):
    reason: str = Field("", description="为什么删（挪进回收站，能还原）")


class InstallIn(BaseModel):
    where: str = Field(..., description="project = 装到本项目；machine = 装到本机", examples=["project"])
    overwrite: bool = Field(False, description="那边已经有不一样的同名时，是否覆盖（旧的会先备份）")


class CommandIn(BaseModel):
    name: str = Field(..., description="快捷指令的名字（也是文件名）", examples=["整理本周进展"])
    en: str = Field(..., description="英文短名，装进 Claude Code 后敲 /它", examples=["weekly-review"])
    description: str = Field(..., description="一句话说它干什么")
    body: str = Field(..., description="指令模板，可用空位：{项目} {当前页} {当前模块} {当前文件} {外部资料入口} {待拍板} {我的笔记}")


# ---------------------------------------------------------------- 应用

def create_app(project: Project, *, open_url: str | None = None, watch_interval: float = 0.5,
               global_keys: bool = False, tasks: bool = False) -> FastAPI:
    """global_keys：挂全局快捷键（截图、录屏）。只有正式启动（main）才挂；自动测试不挂，免得占了你电脑上的快捷键。"""
    hub = Hub()

    # ---- 截图和录屏：截好的、录好的进随堂笔记的草稿（作者 2026-09-27：参考微信和 Windows 自带的截图、录屏）----
    def capture_settings(conn) -> dict:
        shot, record, folder = (store._meta(conn, k) for k in ("capture_shot", "capture_record", "capture_folder"))
        default = str(capture.default_record_dir()) if capture.available() else ""
        return {"shot": hotkeys.DEFAULTS["shot"] if shot is None else shot,
                "record": hotkeys.DEFAULTS["record"] if record is None else record,
                "folder": folder or default, "folder_custom": bool(folder), "folder_default": default}

    def _with_conn(fn):
        conn = store.connect(project.db_path)
        try:
            return fn(conn)
        finally:
            conn.close()

    def _landed(what: str, name: str) -> None:            # 记一笔：网页马上知道草稿里多了东西
        def go(conn):
            with store.tx(conn):
                store.log(conn, "人", what, name, None)
        _with_conn(go)

    # 截好、录好的往哪去（作者 2026-09-27：「这些截图和录屏能不能直接进我的笔记之中？」选了「看情况」）：
    # 随堂笔记开着、你正在写 → 进正在写的这条（草稿，跟字一起记下）；小窗关着 → 直接记成一条笔记，不用点「记下」。
    # 开没开、记到哪本，是网页通过 /ws 报上来的；网页都关了 = 小窗关着、记进总览。
    ui: dict = {}                                          # 连着的网页 → {"open", "scope", "at"}
    last: dict = {"capture": None}                         # 最近一次直接记下的，网页拿去提示一句

    def note_target() -> tuple[bool, str]:
        seen = list(ui.values())
        if not seen:
            return False, notebook.MAIN
        u = max(seen, key=lambda x: x["at"])
        try:
            notebook._file(project, u["scope"])
            return u["open"], u["scope"]
        except ValueError:
            return u["open"], notebook.MAIN

    def _land(item: dict, kind: str) -> None:
        is_open, scope = note_target()
        if is_open:
            _landed(f"{kind}进草稿", item["name"])
            return
        def go(conn):
            e = notebook.add(conn, project, scope, "", kind=kind, attach=[item["name"]])
            last["capture"] = {"id": e["id"], "scope": scope, "kind": kind, "at": time.time()}
        _with_conn(go)

    def _on_image(png: bytes) -> None:
        _land(notebook.stage(project, io.BytesIO(png), "image/png"), "截图")

    def _on_video(path) -> None:
        _land(notebook.stage_video_file(project, path), "录屏")

    grab = capture.Grabber(_on_image, _on_video, lambda: _with_conn(capture_settings)["folder"])
    keys: dict = {"mgr": None}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        proj.ensure_skeleton(project)           # 资料/ 和固定模块（蓝图 · 戒律 · 源代码）的文件夹，没有就建；新项目再加起步模块（只建空文件夹）
        conn = store.connect(project.db_path)
        store.migrate(conn)
        if builtin.legacy_folders(project.root):        # 老样子还有 内置/（10-07 以前的、恢复回来的）：先存一档再搬（统一内置）
            try:
                snapshot.save(conn, project, name="统一内置前", why="启动时发现老样子的 内置/ 文件夹，搬之前先存一档",
                              mode="全量", by="程序", auto=True)
                builtin.migrate_layout(conn, project, by="程序（统一内置）")
            except Exception as e:              # noqa: BLE001  搬不成也照常启动，下次再搬
                print(f"[builtin] 统一内置没搬成：{e}", file=sys.stderr)
        store.sync_folders(conn, project)
        workorders.migrate(conn, project)       # 09-27 上午那张全局开工单 → K1（只做一次）
        journal.split_from_notes(conn, project, [m["name"] for m in store.list_folder_modules(conn, project)])   # 笔记里机器记的搬去 笔记/日志/（09-29 分开；没有要搬的就不动）
        conn.close()
        try:
            skills.write_index(project)
        except ValueError as e:
            print(f"[skills] 目录未更新，请修正技能清单：{e}", file=sys.stderr)
        task = asyncio.create_task(watch(project, hub, watch_interval, use_sessions=tasks))
        task2 = asyncio.create_task(watch_tasks(hub)) if tasks else None
        browser_stop = None
        try:
            if global_keys and capture.available():
                keys["mgr"] = hotkeys.Hotkeys(lambda name: grab.start("image" if name == "shot" else "video"))
                cs = _with_conn(capture_settings)
                keys["mgr"].apply({"shot": cs["shot"], "record": cs["record"]})
            if open_url:
                browser_stop = _start_browser_when_ready(urllib.parse.urlsplit(open_url).port or DEFAULT_PORT,
                                                        project, url=open_url)
            yield
        finally:
            if browser_stop:
                browser_stop.set()
            task.cancel()
            if task2:
                task2.cancel()
            grab.cancel()
            if keys["mgr"]:
                keys["mgr"].stop()

    app = FastAPI(
        title="自动化科研交互界面 · 后端",
        description=(
            "网页读写数据走这些接口。**点任意一条 → Try it out → Execute** 就能试。\n\n"
            "- 人从网页写进来的，记为「人」\n"
            "- agent 从 MCP 写进来的，记为「agent:它的名字」，走的是同一套函数、同一张表\n"
            "- 一个模块 = 资料/ 下一个文件夹 = 网页上一页\n"
            "- 阅读页手工删除先移入回收站，可还原；X 清单与操作日志供 agent 读取。彻底删除另行确认"
        ),
        version="M1",
        lifespan=lifespan,
    )

    def get_conn() -> Iterator[sqlite3.Connection]:
        conn = store.connect(project.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @app.middleware("http")
    async def forget_counts(request: Request, call_next):
        """网页写了东西（上传、挪文件、删模块……都不是 GET）：模块文件数作废，下回现数——不用等后台扫到。"""
        resp = await call_next(request)
        if request.method != "GET":
            scanmap.forget_stats(project)
        return resp

    @app.exception_handler(store.Refused)
    async def _refused(_: Request, exc: store.Refused):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(builtin.Invalid)
    async def _builtin_invalid(_: Request, exc: builtin.Invalid):
        conflict = isinstance(exc, builtin.Conflict)
        return JSONResponse({"detail": str(exc), "conflict": conflict}, status_code=409 if conflict else 400)

    @app.exception_handler(content_modules.Invalid)
    async def _content_invalid(_: Request, exc: content_modules.Invalid):
        status = 409 if isinstance(exc, content_modules.Conflict) else 404 if isinstance(exc, content_modules.Missing) else 400
        return JSONResponse({"detail": str(exc), "conflict": isinstance(exc, content_modules.Conflict)}, status_code=status)

    @app.exception_handler(files.Denied)
    async def _denied(_: Request, exc: files.Denied):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(skills.Conflict)
    async def _conflict(_: Request, exc: skills.Conflict):
        return JSONResponse({"detail": str(exc), "conflict": True}, status_code=409)

    @app.exception_handler(commands.Invalid)
    async def _invalid(_: Request, exc: commands.Invalid):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(store.NeedConfirm)
    async def _need_confirm(_: Request, exc: store.NeedConfirm):
        return JSONResponse({"detail": str(exc), "confirm": exc.info}, status_code=409)

    @app.exception_handler(store.Duplicate)
    async def _dup(_: Request, exc: store.Duplicate):
        return JSONResponse({"detail": str(exc), "existing": exc.existing}, status_code=409)

    # ---- 网页 ----

    @app.get("/", include_in_schema=False)
    def page():
        # 网页里写上它是哪个版本：跟后台一对，不一样（改过了）就自己刷新
        html = PAGE.read_text(encoding="utf-8").replace("<head>", f'<head>\n<meta name="rc-ui" content="{ui_version()}">', 1)
        return Response(html, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.get("/governance-ui.js", include_in_schema=False)
    def governance_ui():
        return FileResponse(PAGE.parent / "治理界面.js", media_type="text/javascript; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.get("/内容工作台.js", include_in_schema=False)
    def content_workspace_ui():
        f = PAGE.parent / "内容工作台.js"
        if not f.is_file():
            raise HTTPException(404, "内容工作台文件缺失")
        return FileResponse(f, media_type="text/javascript; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.get("/自动化面板.js", include_in_schema=False)
    def automation_dashboard_ui():
        return FileResponse(PAGE.parent / "自动化面板.js", media_type="text/javascript; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.get("/员工分配图.js", include_in_schema=False)
    def agent_allocation_ui():
        f = PAGE.parent / "员工分配图.js"
        if not f.is_file():
            raise HTTPException(404, "员工分配图文件缺失")
        return FileResponse(f, media_type="text/javascript; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.get('/流程编辑器.js', include_in_schema=False)
    def workflow_editor_ui():
        f = PAGE.parent / '流程编辑器.js'
        if not f.is_file():
            raise HTTPException(404, '流程编辑器文件缺失')
        return FileResponse(f, media_type='text/javascript; charset=utf-8', headers={'Cache-Control': 'no-store'})

    @app.get('/小窗.js', include_in_schema=False)
    def pane_spirit_ui():
        f = PAGE.parent / '小窗.js'
        if not f.is_file():
            raise HTTPException(404, '小窗组件文件缺失')
        return FileResponse(f, media_type='text/javascript; charset=utf-8', headers={'Cache-Control': 'no-store'})

    @app.get("/brand.png", include_in_schema=False)
    def brand_phoenix():
        f = PAGE.parent / "外观" / "品牌" / "凤凰.png"          # 10-07 统一内置：外观/内置/品牌 → 外观/品牌
        if not f.is_file():
            raise HTTPException(404, "品牌图片缺失")
        return FileResponse(f, media_type="image/png", headers={"Cache-Control": "no-cache"})

    @app.get("/icons/{name}.svg", include_in_schema=False)
    def nav_icon_sprite(name: str):
        if name not in {"经典", "神话", "玉金", "品牌M", "精气神"}:
            raise HTTPException(404, "没有这组图标")
        f = PAGE.parent / "外观" / "图标" / (name + ".svg")
        if not f.is_file():
            raise HTTPException(404, "图标文件缺失")
        return FileResponse(f, media_type="image/svg+xml", headers={"Cache-Control": "no-cache"})

    @app.get("/skin/{name}.css", include_in_schema=False)
    def skin_css(name: str):
        """外观（皮肤）：外观/<名字>.css，网页在样式后面加上它把颜色盖掉（作者 10-01：外观做成设置里能换的）。"""
        f = skins.css_file(name)
        if f is None:
            raise HTTPException(404, "没有这套外观")
        return FileResponse(f, media_type="text/css; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.get("/代码地图.js", include_in_schema=False)
    def page_codemap():
        """源代码页的代码地图（S1-1 S2-21）：画图的那段网页程序，单独一份。"""
        return FileResponse(PAGE.parent / "代码地图.js", media_type="text/javascript; charset=utf-8", headers={"Cache-Control": "no-store"})

    @app.get("/界面英文.js", include_in_schema=False)
    def page_en():
        """纯英文界面的对照表（设置 → 通用 → 语言 → English）。没有这个文件也照常用，只是换不成英文。"""
        f = PAGE.parent / "界面英文.js"
        if not f.is_file():
            return Response("", media_type="text/javascript; charset=utf-8")
        return FileResponse(f, media_type="text/javascript; charset=utf-8", headers={"Cache-Control": "no-store"})

    # ---- 读 ----

    @app.get("/api/skins", tags=["读"], summary="外观：有哪几套皮肤（默认黑白极简排第一，自带的跟着，玩家自己做的在后面）")
    def skins_list():
        return {"skins": skins.listing(), "default": skins.DEFAULT, "folder": "外观/"}

    @app.get("/api/ping", tags=["读"], summary="后端活着吗（启动时用来判断是不是已经开着了）")
    def ping():
        return {"app": APP_ID, "root": str(project.root), "pid": os.getpid(), "ui": ui_version()}

    def _running():
        wo = workorders.running(project)
        return {"code": wo["code"], "name": wo["name"]} if wo else None

    @app.get("/api/state", tags=["读"], summary="整页数据：模块（文件夹）、蓝图、待拍板、决定、笔记")
    def state(conn=Depends(get_conn)):
        return store.get_state(conn, project) | {
            "drafts": notebook.draft_counts(project),        # 随堂笔记里没记下的截图、录屏几个
            "frameless": notebook.frameless(project),         # 直接记下、还没抽画面的录屏：网页开着就补
            "last_capture": last["capture"],
            "deliveries": deliveries.pending(project),        # 交付单等你验收几张（总览顶上那一行）
            "running": _running()}                           # 在跑的那张开工单（总览顶上那一行）

    @app.get("/api/events", tags=["读"], summary="最近发生了什么：谁、什么时候、干了什么")
    def events(limit: int = 50, conn=Depends(get_conn)):
        return store.recent_events(conn, min(max(limit, 1), 500))

    @app.get("/api/modules/{name}/tree", tags=["读"], summary="一个模块的目录：文件名、大小、时间（含挂进来的链接）；蓝图 · 戒律 · 源代码 还分「总的 / 目录」")
    def tree(name: str):
        t = files.tree(project, name)
        t.update(outline.sections(project, name, t["items"]))
        return t

    @app.get("/api/content/{module}", tags=["内容工作台"], summary="只读内容工作台目录、模板和文件来源")
    def content_workspace(module: str):
        return content_modules.workspace(project, module)

    @app.get("/api/content/{module}/document", tags=["内容工作台"], summary="读取正文及完整 SHA 版本；声明的内置模板只读")
    def content_document(module: str, path: str):
        return content_modules.read_document(project, module, path)

    @app.post("/api/content/{module}/document", tags=["内容工作台"], summary="保存论文或测试正文；旧版冲突拒绝覆盖、更新前留历史")
    def content_document_save(module: str, body: ContentDocumentIn, conn=Depends(get_conn)):
        return content_modules.write_document(conn, project, module, body.path, body.text, body.revision,
                                              body.project_root, by="人", source="http", reason=body.reason)

    @app.get("/api/modules/{name}/codemap", tags=["读"], summary="代码地图：模块里（含挂进来的）每个程序文件一句话，取自文件开头那句说明")
    def codemap_says(name: str):
        return outline.codemap(project, name, files.tree(project, name)["items"])

    # 代码地图（S1-1 S2-21；作者 10-02「我想做的可视化是这个」）：先给目录，全文网页看到哪块才来取
    @app.get("/api/modules/{name}/codemap/files", tags=["读"], summary="代码地图：模块里每个程序文件多少行、改过几次、谁最后改的（全文另取）")
    def codemap_files(name: str):
        return codemap.listing(project, name)

    @app.get("/api/codemap/text", tags=["读"], summary="代码地图：一个文件的全文（按行）；path 从项目根算")
    def codemap_text(path: str):
        return codemap.text(project, path)

    @app.get("/api/codemap/diff", tags=["读"], summary="代码地图：没交的改动——哪个文件哪几行加了、改了、删了（跟上一次 git 记账比）")
    def codemap_diff():
        return codemap.diff(project)

    @app.get("/api/modules/{name}/codemap/search", tags=["读"], summary="代码地图：一个词在哪些文件哪几行")
    def codemap_search(name: str, q: str = ""):
        return codemap.search(project, name, q)

    @app.get("/api/codemap/defs", tags=["读"], summary="代码地图：一个文件里的函数和类")
    def codemap_defs(path: str):
        return codemap.defs(project, path)

    @app.get("/api/modules/{name}/codemap/uses", tags=["读"], summary="代码地图：一个函数名、类名在别处哪几行用到")
    def codemap_uses(name: str, word: str, path: str = "", line: int = 0):
        return codemap.uses(project, name, word, path, line)

    @app.get("/api/modules/{name}/preview", tags=["读"], summary="预览一个文件：文字直接给内容，图片/PDF/网页给地址")
    def preview(name: str, path: str, conn=Depends(get_conn)):
        target = files.resolve(project, name, path)
        normalized = path.replace("\\", "/")
        original = project.root / normalized[2:] if normalized.startswith("@/") else project.materials / name / normalized
        return _with_plugin(conn, file_actions.preview_file(project, target, path, original=original), target)

    def _with_plugin(conn, d: dict, target) -> dict:
        """有插件能照原样显示这种文件（PPT 预览…）：带上它能不能用、这个项目启用了没有。压缩包带上它在项目里的路径（看里面要用）。"""
        d["plugin"] = plugins.info_for(conn, project, target)
        if d.get("kind") == "zip":
            d["zip"]["path"] = target.resolve().relative_to(project.root.resolve()).as_posix()
        return d

    @app.get("/lib/{path:path}", include_in_schema=False)
    def lib_static(path: str):
        """应用自带的库（工具库/下载/：pdf.js、KaTeX、Mermaid、Three.js），网页和沙箱里的图解都能用（文献 S2-3）。"""
        base = (CODE_DIR / "工具库" / "下载").resolve()
        target = (base / path).resolve()
        if not target.is_relative_to(base) or not target.is_file():
            raise HTTPException(404, "没有这个文件")
        kind = {".mjs": "text/javascript", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
                ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".wasm": "application/wasm"}.get(target.suffix.lower())
        return FileResponse(target, media_type=kind, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "max-age=3600"})

    @app.get("/files/{name}/{path:path}", include_in_schema=False)
    def raw(name: str, path: str, embed: int = 0, slide: int = 0, pic: int = 0, as_: str = Query("", alias="as"),
            conn=Depends(get_conn)):
        return _raw(files.resolve(project, name, path), embed, slide, pic, as_, conn)

    def _raw(target, embed: int, slide: int = 0, pic: int = 0, as_: str = "", conn=None):
        if as_ == "pdf":                                   # 插件转成的 PDF（PPT 预览：照原样一页页翻）
            f = _converted(conn, target)
            return FileResponse(f, media_type="application/pdf", content_disposition_type="inline",
                                filename=target.stem + ".pdf", headers={"Cache-Control": "no-store"})
        if slide and target.suffix.lower() == ".pptx":       # PPT 第 slide 页的第 pic 张图（核心列字时配图用）
            try:
                blob, kind = office.pptx_picture(target, slide, pic)
            except (IndexError, KeyError):
                raise HTTPException(404, "这一页没有这张图")
            return Response(blob, media_type=kind, headers={"Cache-Control": "max-age=600"})
        headers = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"}
        is_html = target.suffix.lower() in (".html", ".htm")
        if is_html or target.suffix.lower() == ".svg":
            # 资料里的网页可能是下载来的：沙箱里跑，碰不到这个后端
            headers["Content-Security-Policy"] = "sandbox allow-scripts allow-popups allow-modals allow-forms"
        if is_html and embed:
            # 嵌进模块页时：让它把自己的高度报给外面，外面把框撑到一样高——
            # 滚的是整个网页，不是框里再套一个滚动条
            body = target.read_bytes() + EMBED_JS
            return Response(body, media_type="text/html", headers=headers)
        return FileResponse(target, headers=headers)

    # ---- 写（人）----

    @app.post("/api/modules", tags=["写 · 人"], summary="加一个模块：建 资料/<名>/ 文件夹（记为「人」加的）")
    def add_module(body: AddModuleIn, conn=Depends(get_conn)):
        m = store.add_module(conn, project, body.name, one_line=body.one_line, en=body.en, by="人", source="human")
        journal.add(conn, project, f"新建模块「{m['name']}」，文件夹 资料/{m['name']}/", kind="新建模块", scope=m["name"])
        return store.get_state(conn, project)

    @app.get("/api/search", tags=["读"], summary="全站检索：文件名、文字文件内容、笔记、决定、蓝图")
    def search(q: str = "", conn=Depends(get_conn)):
        q = q.strip()
        if not q:
            return {"files": [], "notes": [], "truncated": False}
        hits, cut = files.proj_search(project, q)
        like = f"%{q}%"
        notes = [{"kind": r["kind"], "code": r["code"], "text": r["text"][:160]} for r in conn.execute(
            "SELECT kind, code, text FROM note WHERE kind IN ('草稿', '决定', '待拍板') AND (text LIKE ? OR detail LIKE ?) "
            "ORDER BY id DESC LIMIT 30", (like, like))]
        notes += blueprint.search(project, q)            # 蓝图里的目标和 S2
        return {"files": hits, "notes": notes, "truncated": cut}

    @app.get("/api/project/tree", tags=["读"], summary="整个项目的目录（像 VS Code 左边那一栏；不列 .git、索引/、缓存）")
    def project_tree():
        return files.proj_tree(project)

    @app.get("/api/project/preview", tags=["读"], summary="预览项目里任意一个文件")
    def project_preview(path: str, conn=Depends(get_conn)):
        target = files.proj_resolve(project, path)
        original = project.root / path.replace("\\", "/")
        return _with_plugin(conn, file_actions.preview_file(project, target, path, original=original), target)

    @app.post("/api/files/trash", tags=["写 · 人"], summary="人在阅读页删一个文件：移入回收站，保留X清单与agent可读机器日志")
    def file_to_trash(body: FileTrashIn, conn=Depends(get_conn)):
        return file_actions.move_file(conn, project, body.path, body.project, body.revision, body.reason)

    @app.get("/api/builtin/files", tags=["设置"], summary="只读文件内置状态或人工标记清单，不创建正本")
    def builtin_files(path: str = ""):
        return file_actions.builtin_status(project, path) if path else builtin.list_marks(project.root)

    @app.put("/api/builtin/files", tags=["写 · 人"], summary="设置文件是否内置：版本核对、原文件不搬动、记录操作日志")
    def builtin_file_set(body: BuiltinFileIn, conn=Depends(get_conn)):
        return builtin.set_mark(conn, project, body.path, body.enabled, body.project, body.revision, by="人")

    @app.get("/api/zip", tags=["读"], summary="看压缩包里面（只读，不解开）：没给 inner 就列出文件树和说明在哪；给了就读那一个文件（网页、脚本当文字）")
    def zip_look(path: str, inner: str = ""):
        target = files.proj_resolve(project, path)
        try:
            return zips.read(target, inner) if inner else zips.entries(target)
        except FileNotFoundError:
            raise HTTPException(404, f"压缩包里没有「{inner}」")
        except Exception as e:                            # 坏的压缩包
            raise HTTPException(400, f"这个压缩包读不出来：{type(e).__name__}")

    @app.get("/zfiles", include_in_schema=False)
    def zip_image(path: str, inner: str):
        try:
            blob, kind = zips.image(files.proj_resolve(project, path), inner)
        except FileNotFoundError:
            raise HTTPException(404, "不是压缩包里的图片")
        return Response(blob, media_type=kind, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "max-age=600"})

    @app.get("/pfiles/{path:path}", include_in_schema=False)
    def project_raw(path: str, embed: int = 0, slide: int = 0, pic: int = 0, as_: str = Query("", alias="as"),
                    conn=Depends(get_conn)):
        return _raw(files.proj_resolve(project, path), embed, slide, pic, as_, conn)

    def _converted(conn, target):
        """用启用了的插件把这份文件转成 PDF（转过、没改过就直接拿缓存）。没插件、没启用、转不出来都写清楚。"""
        c = plugins.converter_for(target)
        if c is None:
            raise HTTPException(404, f"没有插件能照原样显示 {target.suffix} 文件")
        if not plugins.enabled(conn, c["name"]):
            raise HTTPException(403, f"「{c['name']}」插件这个项目还没启用：在网页上点开这份文件，点「启用」")
        try:
            return plugins.convert(project, c["name"], target)
        except RuntimeError as e:
            raise HTTPException(500, str(e))

    @app.get("/api/plugins", tags=["读"], summary="插件：有哪些、这台电脑能不能用、这个项目启用了没有（S1-11 玩家自己组装）")
    def plugin_list(recheck: int = 0, conn=Depends(get_conn)):
        out = []
        for x in plugins.list_plugins():
            ck = plugins.check(x["name"]) if recheck else plugins.check_cached(x["name"])
            out.append({k: x[k] for k in ("name", "one_line", "version", "exts", "to", "body", "page")}
                       | {"ok": ck["ok"], "msg": ck["msg"], "enabled": plugins.enabled(conn, x["name"]),
                          "folder": f"插件/{x['dir'].name}/"})
        return out

    @app.post("/api/plugins/{name}/enable", tags=["写 · 人"], summary="启用 / 停用一个插件（只有人点；每个项目自己记）")
    def plugin_enable(name: str, body: PluginOnIn, conn=Depends(get_conn)):
        try:
            if body.on and not plugins.check(name)["ok"]:
                raise HTTPException(400, f"「{name}」在这台电脑上还用不了：{plugins.check_cached(name)['msg']}")
            plugins.set_enabled(conn, name, body.on)
        except KeyError:
            raise HTTPException(404, f"没有「{name}」这个插件")
        journal.add(conn, project, f"{'启用' if body.on else '停用'}插件「{name}」", kind="插件")
        return {"ok": True, "enabled": body.on}

    # 挂一页的插件（S1-11 S2-6）：网页终端这种。人点「打开」核心才把它跑起来；跑起来以后它自己活着，核心重启了照着接上
    @app.get("/api/pages", tags=["读"], summary="挂一页的插件：有哪些、能不能用、启用没有、在不在跑（在跑给地址）")
    def page_list(conn=Depends(get_conn)):
        out = []
        for x in plugins.pages():
            ck = plugins.check_cached(x["name"])
            out.append({"name": x["name"], "title": x["page"], "one_line": x["one_line"], "ok": ck["ok"], "msg": ck["msg"],
                        "enabled": plugins.enabled(conn, x["name"])} | plugins.page_status(project, x["name"]))
        return out

    @app.post("/api/pages/{name}/open", tags=["写 · 人"], summary="打开一页（人点的）：在跑就接上，不在跑就起一个；给嵌进网页的地址")
    def page_open(name: str, conn=Depends(get_conn)):
        try:
            return plugins.open_page(conn, project, name)
        except KeyError:
            raise HTTPException(404, f"没有「{name}」这个插件")
        except RuntimeError as e:
            raise HTTPException(400, str(e))

    @app.post("/api/pages/{name}/close", tags=["写 · 人"], summary="关掉一页的服务（里面的窗口一起关）")
    def page_close(name: str, conn=Depends(get_conn)):
        try:
            r = plugins.close_page(project, name)
        except KeyError:
            raise HTTPException(404, f"没有「{name}」这个插件")
        journal.add(conn, project, f"关掉了插件「{name}」那页的服务", kind="插件")
        return r

    @app.get("/api/auto/launch", tags=["自动化"], summary="全自动开工（S1-8 S2-50）：开没开、同时最多几个、最近自动开了谁、网页终端里现在有几个窗口")
    def launch_state(conn=Depends(get_conn)):
        import construction_plans
        return autolaunch.settings(conn) | {"recent": autolaunch.recent(conn), "windows": autolaunch.windows(project),
            "plans": construction_plans.listing(project), "pause": workorders.paused(conn),
            "status": [autolaunch.runner_state(project, a['code']) | {'code': a['code'], 'name': a['name']} for a in agents.list_all(project) if a.get('auto')],
            "missing_roles": autolaunch.missing_roles(conn, project)}

    @app.put("/api/auto/launch", tags=["写 · 人"], summary="全自动开工的总开关和同时最多几个（只有人点：开了以后谁领着件、没开窗口，网页终端就自动给它开一个）")
    def launch_set(body: LaunchIn, conn=Depends(get_conn)):
        restoring = body.on is True and (body.resume or not autolaunch.settings(conn)['on'] or bool(workorders.paused(conn)))
        st = autolaunch.set_settings(conn, on=body.on, max_=body.max)
        if body.on is True:
            workorders.resume(conn)
            from automation_mcp import resume_inactive_runners
            resume_inactive_runners(project, restoring=restoring, by='人', reason='网页恢复自动化', explicit_resume=body.resume)
        elif body.on is False:
            with store.tx(conn):
                store._set_meta(conn, workorders.PAUSE, '网页关闭自动化')
        _logged(conn, "改了全自动开工", "自动化", ("开" if st["on"] else "关") + f" · 同时最多 {st['max']} 个")
        return st

    @app.post("/api/agents/{key}/launcher", tags=["写 · 人"], summary="开工脚本：照档案（用什么、模型、开工的话）写 索引/开工/start-<编号>.ps1，返回跑它的那一行（网页终端里点「开工」用；只写文件，不启动）")
    def agent_launcher(key: str, conn=Depends(get_conn)):
        return agents.launcher(project, key) | autolaunch.window_metadata(conn, project, agents.get(project, key))

    @app.post("/api/plugins/convert", tags=["读"], summary="用启用了的插件把一份文件转成 PDF（放 索引/预览缓存/，原文件不动）；转好了网页再用 ?as=pdf 取")
    def plugin_convert(body: ConvertIn, conn=Depends(get_conn)):
        target = files.resolve(project, body.module, body.path) if body.module else files.proj_resolve(project, body.path)
        t = time.time()
        f = _converted(conn, target)
        return {"ok": True, "size": f.stat().st_size, "seconds": round(time.time() - t, 1)}

    @app.post("/api/open-local", tags=["读"], summary="用这台电脑上的默认程序打开（Word、Excel、PowerPoint、WPS、播放器）；只开文档、表格、图片、音视频")
    def open_local(body: OpenLocalIn):
        target = files.resolve(project, body.module, body.path) if body.module else files.proj_resolve(project, body.path)
        try:
            office.open_local(target)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except OSError as e:
            raise HTTPException(400, f"打不开：{e.strerror or e}（这台电脑上可能没有能打开它的软件）")
        return {"ok": True, "name": target.name}

    @app.get("/api/guide", tags=["读"], summary="使用说明（lang=zh 中文 / en English）")
    def guide(lang: str = "zh"):
        f = project.root / ("使用说明.en.md" if lang == "en" else "使用说明.md")
        if not f.is_file():
            return {"text": "# Guide\n\nNot written yet." if lang == "en" else "# 使用说明\n\n还没写。"}
        return {"text": f.read_text(encoding="utf-8")}

    @app.get("/api/plans", tags=["读"], summary="计划：项目根 计划/ 里的每一份（新改的在前）；内容用 /api/project/preview 读")
    def plans():
        return {"items": files.plans(project)}

    # ---- 技能库 / 快捷指令（工具自带的部件）----

    def _where(w: str) -> str:
        if w not in ("project", "machine"):
            raise HTTPException(400, "where 只能是 project（本项目）或 machine（本机）")
        return w

    def _logged(conn, action: str, target: str, detail: str = ""):
        """网页上做的事，做完在日志里记一条（带编号，志-…），事件表里也有。人的笔记只放人写的。"""
        journal.add(conn, project, f"{target}" + (f"：{detail}" if detail else ""), kind=action)

    @app.get("/api/repos", tags=["工具"], summary="开源项目：别人的项目，学它、借它；每个带许可证和能不能借（工具 S2-3、S2-4）")
    def repos_list():
        return {"items": repos.listing()}

    @app.get("/api/tools/guides", tags=["工具"], summary="内置应用指南与明确关联（只读、不执行清单命令）")
    def tools_guides():
        return tool_guides.listing(project.root)

    @app.get("/api/tools/guides/document", tags=["工具"], summary="读取内置 Markdown 与合法图片/指南引用")
    def tools_guide_document(path: str = Query(...)):
        try:
            return tool_guides.document(project.root, path)
        except (ValueError, OSError) as err:
            raise HTTPException(400, str(err))

    @app.get("/api/tools/guides/{key}", tags=["工具"], summary="一份工具指南全文、版本与来源")
    def tools_guide(key: str, route: str = ""):
        try:
            return tool_guides.read(project.root, key, route)
        except KeyError as err:
            raise HTTPException(404, str(err))
        except (ValueError, OSError) as err:
            raise HTTPException(400, str(err))

    @app.get("/api/tools/links", tags=["工具"], summary="网页链接：常用的权威网站，按组列（工具库/网页链接.md；工具 S2-11）")
    def tools_links():
        return {"groups": links.groups(), "file": "工具库/网页链接.md"}

    @app.get("/api/tools/catalog", tags=["工具"], summary="市面上的智能体：美国、中国两组，哪家、什么样、能不能接本应用、这台电脑装没装（工具库/智能体.md；工具 S2-13）")
    def tools_catalog():
        return {"groups": toolbox.catalog(project), "file": "工具库/智能体.md", "mcp": toolbox.mcp_config(project)}

    @app.get("/api/tools/agents", tags=["工具"], summary="Agent 程序：这台电脑装了哪家 agent、会话记录在哪、最近哪个连上来过（只读，不启动 agent）")
    def tools_agents(conn=Depends(get_conn)):
        return {"items": toolbox.agent_programs(conn, project)}

    @app.get("/api/tools", tags=["工具"], summary="工具库：外部工具一个一张卡（T1、T2…），写清怎么调")
    def tools_list():
        return {"items": tools.list_tools(project.root / "工具库")}

    @app.post("/api/tools", tags=["工具"], status_code=201, summary="手工添加普通工具卡，不安装或执行命令")
    def tools_create(body: ManualToolIn, conn=Depends(get_conn)):
        try:
            card = tools.create(**body.model_dump(), by="人", lib=project.root / "工具库")
        except tools.Duplicate as e:
            raise HTTPException(409, {"message": str(e), "existing": e.card}) from e
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        _logged(conn, "手工添加工具", card['code'], card['name'])
        return card

    @app.post("/api/tools/{code}/check", tags=["工具"], summary="查这个工具装没装：只跑卡上那条「检查」命令，不替人跑工具")
    def tools_check(code: str):
        try:
            return tools.check(code, project.root / "工具库")
        except KeyError:
            raise HTTPException(404, f"工具库里没有 {code}")

    @app.post("/api/tools/{code}/installed", tags=["工具"], summary="人装好了「待你装」的工具：跑一遍检查，通过就去掉「待你装」")
    def tools_installed(code: str, conn=Depends(get_conn)):
        try:
            r = tools.check(code, project.root / "工具库")
        except KeyError:
            raise HTTPException(404, f"工具库里没有 {code}")
        if r.get("ok") is False:
            raise HTTPException(400, f"还没通：{r.get('msg') or '检查没过'}")
        if any(t['code'] == code and t.get('manual') and not t['check'] for t in tools.list_tools(project.root / "工具库")):
            raise HTTPException(400, "手工工具尚未配置检查，不能标记装好了")
        tools.set_state(code, "", project.root / "工具库")
        _logged(conn, "装好了工具", code, r.get("version", ""))
        for q in store.list_pending(conn):                  # agent 请人装它的那条问答，一起了结
            if q["text"].startswith(f"请你装 {code} "):
                store.answer(conn, q["code"], f"装好了 {code}" + (f"（{r['version']}）" if r.get("version") else ""))
        return r

    # ---- 自动化：一张张开工单（作者 2026-09-27：「左边目录应该是每个自定义清单的一个文件……准备好了之后，按照要求把这些交给agent」）----

    @app.get("/api/workorders", tags=["自动化"], summary="开工单 K：每张的状态（备料 / 在跑 / 等你验收 / 做完 / 搁置）、最差的灯、绿了几样")
    def wo_list(conn=Depends(get_conn)):
        return workorders.summary(conn, project)

    @app.post("/api/workorders", tags=["自动化"], summary="新开一张：名字 + 目标（S1 或几件 S2），按目标自动配好用到的")
    def wo_new(body: WorkOrderNewIn, conn=Depends(get_conn)):
        wo = workorders.create(conn, project, body.name, body.target, body.product, module=body.module)
        _logged(conn, "新开工单", f"{wo['code']} {wo['name']}", "、".join(wo["target"]))
        return workorders.detail(conn, project, wo["code"])

    @app.get("/api/workorders/{code}", tags=["自动化"], summary="一张单：写了什么、用到的每样一盏灯、在跑时的进度和交付单")
    def wo_get(code: str, conn=Depends(get_conn)):
        return workorders.detail(conn, project, code)

    @app.get("/api/workorders/{code}/options", tags=["自动化"], summary="「＋ 加一样」能挑的：戒律文件、模块、工具卡、材料文件、存档")
    def wo_options(code: str):
        return workorders.options(project, code)

    @app.put("/api/workorders/{code}", tags=["自动化"], summary="改一张单：只改带上的字段（用到的每类整列换）")
    def wo_put(code: str, body: WorkOrderPatchIn, conn=Depends(get_conn)):
        workorders.update(conn, project, code, body.model_dump(exclude_unset=True))
        return workorders.detail(conn, project, code)

    @app.post("/api/workorders/{code}/fill", tags=["自动化"], summary="照目标配齐：按目标把该用到的模块、戒律、工具、存档加上（已列的不动）")
    def wo_fill(code: str, conn=Depends(get_conn)):
        workorders.fill(conn, project, code)
        return workorders.detail(conn, project, code)

    @app.post("/api/workorders/{code}/copy", tags=["自动化"], summary="复制这张：用到的、交代原样带过去，开一张新的")
    def wo_copy(code: str, conn=Depends(get_conn)):
        wo = workorders.copy(conn, project, code)
        return workorders.detail(conn, project, wo["code"])

    @app.post("/api/workorders/{code}/start", tags=["自动化"], summary="交给 agent：有红的交不出去；一次只跑一张")
    def wo_start(code: str, conn=Depends(get_conn)):
        wo = workorders.start(conn, project, code)
        _logged(conn, "交给 agent", f"{wo['code']} {wo['name']}", f"档 {wo['level']} · 每次最多 {wo['rounds']} 圈")
        return workorders.detail(conn, project, code)

    @app.post("/api/workorders/{code}/stop", tags=["自动化"], summary="叫停：agent 下一圈看见就停")
    def wo_stop(code: str, conn=Depends(get_conn)):
        wo = workorders.stop(conn, project, code)
        _logged(conn, "叫停", f"{wo['code']} {wo['name']}")
        return workorders.detail(conn, project, code)

    @app.post("/api/workorders/{code}/shelve", tags=["自动化"], summary="搁置（on=false 拿回来）")
    def wo_shelve(code: str, body: ConfirmIn, conn=Depends(get_conn)):
        workorders.shelve(conn, project, code, body.confirm)
        return workorders.detail(conn, project, code)

    # ---- agent 档案（作者 2026-09-30：「得给agent注册……职责啥的都可以随着项目变迁」「我还是想让玩家可以自己动手diy」）----

    @app.get("/api/agents", tags=["自动化"], summary="名册 + 样子 + 分工规矩（自动化/协议.md）")
    def agents_all(conn=Depends(get_conn)):
        proto = project.root / "自动化" / "协议.md"
        return {"items": agents.roster(conn, project), "templates": list(agents.TEMPLATES),
                "protocol": proto.read_text(encoding="utf-8") if proto.is_file() else ""}

    @app.get("/api/org", tags=["自动化"], summary="组织和流程：每个 agent 的岗位、等级、上级、下面的人；一件事要过的几关，每关几件、谁管")
    def org_all(conn=Depends(get_conn)):
        return agents.org(conn, project)

    @app.get("/api/agents/{key}", tags=["自动化"], summary="一个 agent 的档案：编号、管哪些、交代、变迁")
    def agent_one(key: str, conn=Depends(get_conn)):
        a = agents.get(project, key)
        return a | {"roster": next((r for r in agents.roster(conn, project) if r["name"] == a["name"]), None),
                    "path": f"{agents.DIR.as_posix()}/{a['file']}"}

    @app.post("/api/agents", tags=["自动化"], summary="新建一个 agent 档案（从样子开始）；它来了报同样的名字就接上")
    def agent_new(body: AgentNewIn, conn=Depends(get_conn)):
        return agents.create(conn, project, body.name, body.template, by="人", program=body.program, line=body.line)

    @app.put("/api/agents/{key}", tags=["自动化"], summary="改档案：只改带上的，「变迁」记一行")
    def agent_patch(key: str, body: AgentPatchIn, conn=Depends(get_conn)):
        fields = {k: v for k, v in body.model_dump().items() if k != "why" and v is not None}
        return agents.update(conn, project, key, fields, by="人", why=body.why)

    @app.post("/api/agents/{key}/copy", tags=["自动化"], summary="照这张复制一份，给另一个名字")
    def agent_copy(key: str, body: AgentCopyIn, conn=Depends(get_conn)):
        return agents.copy(conn, project, key, body.name, by="人")

    @app.post("/api/agents/{key}/delete", tags=["自动化"], summary="删档案：挪进回收站（能还原），它领着的活放手")
    def agent_delete(key: str, body: AgentDelIn, conn=Depends(get_conn)):
        return agents.delete(conn, project, key, by="人", reason=body.reason)

    @app.get("/api/tasks", tags=["自动化"], summary="后台任务表：各家 agent 的会话（在跑 · 停了 · 做完）、模型、token、调了几次工具、现在在干嘛")
    def tasks_all(conn=Depends(get_conn)):
        held = {}
        for r in claims.active(conn):
            if r["goal"] != claims.CORE:
                held.setdefault(agents.short(r["agent"]), []).append(f"{r['goal']} {r['sub']}".strip() + " " + r["what"])
        out = []
        for r in sessions.board():
            a = agents.find(project, r["agent"])
            out.append(r | {"code": a["code"] if a else "", "program": a["program"] if a else "", "holding": held.get(agents.short(r["agent"]), [])})
        return {"items": out, "sources": {k: str(v) for k, v in sessions.sources().items()}}

    @app.get("/api/tasks/{session_id}", tags=["自动化"], summary="一份会话的全过程（最近几百条）：人说的、它说的、用了什么工具、结果")
    def task_one(session_id: str):
        d = sessions.detail(session_id)
        if d is None:
            raise HTTPException(404, "没有这份会话（或还没读到）")
        a = agents.find(project, d["agent"])
        return d | {"code": a["code"] if a else "", "events": [e | {"at": sessions.fmt_time(e["at"])} for e in d["events"]]}

    @app.get("/api/supervise", tags=["自动化"], summary="监管：网页自己看到的越界、卡住（开着的、最近关了的）和七条规矩")
    def supervise_all(conn=Depends(get_conn)):
        return supervise.listing(conn)

    @app.post("/api/supervise/{fid}/ack", tags=["自动化"], summary="知道了：这一条收起来（不改任何文件）")
    def supervise_ack(fid: int, conn=Depends(get_conn)):
        return supervise.ack(conn, fid)

    @app.get("/api/settings/machine", tags=["设置"], summary="本机：每个工具、每家 agent 的会话记录在这台电脑上的哪（找到了没）")
    def machine_all():
        m = machine.load()
        rows = []
        for t in tools.list_tools(project.root / "工具库"):
            if t["kind"] == "技术栈" or not t["check"] or t["check"].startswith("文件 "):
                continue
            r = tools.check_cached(t["code"], lib=project.root / "工具库")
            rows.append({"kind": "工具", "key": t["code"], "name": t["name"], "set": m["tools"].get(t["code"], ""),
                         "found": bool(r.get("ok")), "path": r.get("path", ""), "msg": r.get("msg", "")})
        for kind, path in sessions.sources().items():
            rows.append({"kind": "会话记录", "key": kind, "name": kind, "set": m["sessions"].get(kind, ""),
                         "found": path.is_dir(), "path": str(path), "msg": "" if path.is_dir() else "没找到这个文件夹"})
        return {"items": rows, "file": str(machine.FILE)}

    @app.get('/api/settings/builtin', tags=['设置'], summary='新项目默认内置与预计复制统计')
    def builtin_get():
        try:
            return new_project.preview(project.root)
        except (OSError, ValueError) as e:
            raise HTTPException(400, str(e)) from e

    @app.post('/api/settings/builtin/preview', tags=['设置'], summary='预览这次额外选择的复制统计，不保存为默认配置')
    def builtin_preview(body: BuiltinIn):
        try:
            return new_project.preview(project.root, body.extra, body.business_modules)
        except (OSError, ValueError) as e:
            raise HTTPException(400, str(e)) from e

    @app.get('/api/settings/builtin/browse', tags=['设置'], summary='新建项目弹窗逐层勾选额外内容')
    def builtin_browse(path: str = ''):
        try:
            result = builtin.browse(project.root, path)
            optional = set(new_project.available_business_modules(project.root))
            for item in result['items']:
                parts = item['path'].split('/')
                if len(parts) == 2 and parts[0] == '资料':
                    item['business_module'] = parts[1] if parts[1] in optional else None
                    item['required'] = parts[1] in proj.FIXED_NAMES
            return result
        except (OSError, ValueError) as e:
            raise HTTPException(400, str(e)) from e

    @app.post('/api/settings/pick-folder', tags=['设置'], summary='在本机弹出「选文件夹」窗口，返回选中的完整路径（取消返回空）；新建项目选位置用')
    def settings_pick_folder(body: PickFolderIn):
        start = body.start.strip().strip('"')
        if not start or not Path(start).is_dir():
            start = str(project.root.parent)
        code = ("import sys, tkinter as tk\nfrom tkinter import filedialog\n"
                "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
                "p = filedialog.askdirectory(parent=r, initialdir=sys.argv[1], title='新项目放在哪个文件夹 · Where to create the new project', mustexist=True)\n"
                "sys.stdout.buffer.write((p or '').encode('utf-8'))")
        try:                                             # 另起一个进程弹窗：不卡住后台，关了窗口就结束
            r = subprocess.run([sys.executable, '-c', code, start], capture_output=True, timeout=600)
        except subprocess.TimeoutExpired:
            raise HTTPException(408, '选文件夹的窗口开太久了，没选上；再点一次') from None
        if r.returncode:
            raise HTTPException(500, '弹不出选文件夹的窗口：' + r.stderr.decode('utf-8', 'replace')[-300:])
        path = r.stdout.decode('utf-8', 'replace').strip()
        return {'path': str(Path(path)) if path else ''}

    @app.post('/api/settings/new-project', tags=['设置'], summary='固定带内置并复制当次勾选的额外资料，目标已存在不覆盖')
    def settings_new_project(body: NewProjectIn, conn=Depends(get_conn)):
        try:
            name = proj.check_name(body.name)
            if name == '内置':
                raise ValueError('请为项目起一个具体名称')
            where = body.where.strip().strip('"')
            if where and not Path(where).is_absolute():
                raise ValueError('保存位置需要完整目录路径')
            target = ((Path(where) if where else project.root.parent) / name).resolve()
            copied = new_project.make(target, project.root, extra=body.extra, business_modules=body.business_modules)
            result = json.loads((target / '新项目复制清单.json').read_text(encoding='utf-8'))
            journal.add(conn, project, '新建项目：' + str(target) + '；业务模块：' + ('沿用默认' if body.business_modules is None else '、'.join(body.business_modules)) + '；当次额外：' + '、'.join(body.extra), by='人', kind='新建项目', scope='源代码')
            return {'target': str(target), 'copied': copied, 'file_count': result['file_count'],
                    'bytes': result['bytes'], 'manifest': '新项目复制清单.json'}
        except FileExistsError as e:
            raise HTTPException(409, str(e)) from e
        except (OSError, ValueError) as e:
            raise HTTPException(400, str(e)) from e

    @app.put("/api/settings/machine", tags=["设置"], summary="改本机设置：某个工具、某家会话记录在哪（空着 = 让程序自己找）")
    def machine_put(body: MachineIn):
        section = {"工具": "tools", "会话记录": "sessions"}.get(body.kind)
        if not section:
            raise HTTPException(400, "kind 写「工具」或「会话记录」")
        machine.put(section, body.key, body.value)
        if section == "tools":
            tools.forget(body.key)
        return machine_all()

    @app.get("/api/drafts", tags=["蓝图"], summary="草稿区：agent 起草的任务、需求（等你看的在前）；每张带审核到哪（等审 · 准 · 打回 · 交给你 · 没人审）")
    def drafts_list():
        return {"items": [d | {"stage": drafts.stage(project, d)} for d in drafts.listing(project)]}

    @app.post("/api/drafts/{code}", tags=["蓝图"], summary="草稿区里点一条：行（照原样或改过的收进正式文件，编号接着排）/ 不要（只有人点）")
    def drafts_decide(code: str, body: DraftPickIn, conn=Depends(get_conn)):
        with store.tx(conn):                              # 先记「人」：监管看得出正式文件是网页上人点的
            store.log(conn, "人", "草稿区" + body.act, code, None)
        try:
            d = drafts.decide(project, code, body.act, body.fields or None)
        except store.Refused as e:
            raise HTTPException(409, str(e))
        journal.add(conn, project, f"{code}（{d['kind']} · {d['where']}，{d['by'].replace('agent:', '')} 提的）：{d['result']}", kind="草稿区", scope=d["where"])
        return d

    @app.get("/api/blueprint/look", tags=["蓝图"], summary="蓝图全局：每个大问题一张卡（底下几块、定稿几块、做完几件）、卡在哪（需求压着几件没做完）")
    def blueprint_look():
        return {"big": bplook.big_cards(project), "stuck": bplook.stuck(project)}

    @app.get("/api/blueprint/timeline", tags=["蓝图"], summary="蓝图按时间排：每件那一行最后一次变动（取本机 git；没记进 git 的用文件时间），最新的在前")
    def blueprint_timeline():
        return {"items": bplook.timeline(project)}

    @app.get("/api/blueprint/final/{code}", tags=["蓝图"], summary="能不能定稿：定没定、还缺什么（缺需求、需求没对上任务、没写怎么验、没有模块戒律、格式不对）")
    def final_check(code: str):
        r = next((x for x in dispatch.plan_status(project) if x["code"] == code), None)
        if r is None:
            raise HTTPException(404, f"找不到 {code}")
        return {"code": code, "final": r["final"], "missing": r["missing"], "file": r["file"]}

    @app.post("/api/blueprint/final/{code}", tags=["蓝图"], summary="定稿 / 取消定稿（只有人按）：写上或去掉「规划：定稿 · 日期 · 原话」；定稿了 agent 才自己挑这块的活，缺东西就拒")
    def final_set(code: str, body: FinalIn, conn=Depends(get_conn)):
        with store.tx(conn):                              # 先记「人」：监管看得出这是网页上人改的
            store.log(conn, "人", "定稿" if body.on else "取消定稿", code, body.words or None)
        try:
            r = dispatch.set_final(project, code, body.on, body.words)
        except store.Refused as e:
            raise HTTPException(409, str(e))
        journal.add(conn, project, f"{code}：{r['final'] or '去掉了定稿那一行'}（{r['file']}）", kind="定稿" if body.on else "取消定稿", scope=code)
        return r

    @app.post("/api/claims/release", tags=["自动化"], summary="让它放手：这件不再算它的，别人能领（agent 下次来领活时就知道了）")
    def claim_release(body: ReleaseIn, conn=Depends(get_conn)):
        if not claims.release(conn, body.goal.strip(), body.sub.strip(), note=body.note or "人在网页上让它放手"):
            raise HTTPException(404, f"{body.goal} {body.sub} 没人领着")
        return {"ok": True}

    @app.get("/api/auto/timeline", tags=["自动化"], summary="一件的来龙去脉：领了 · 放手 · 交付 · 通过 / 打回 · 本机 git")
    def auto_timeline(goal: str, sub: str = "", conn=Depends(get_conn)):
        return {"items": agents.timeline(conn, project, goal, sub)}

    @app.get("/api/board", tags=["自动化"], summary="任务看板：蓝图里每一件在哪一列（能做 / 在做 / 等着 / 做完）、各列几件、总览四张图（最近 14 天）的数")
    def board_all(conn=Depends(get_conn)):
        return board.snapshot(conn, project)

    @app.get("/api/work-package", tags=["源代码"], summary="只读编程工作包：目标、需求、批准范围、规则和所选技能")
    def work_package(goal: str, sub: str, plan_code: str = "", skill_ids: list[str] = Query(default=[]), lang: str = "zh"):
        with work_packages.open_read_connection(project) as conn:
            return work_packages.build(conn, project, goal, sub, plan_code=plan_code, skill_ids=skill_ids, lang=lang)

    @app.get("/api/board/item", tags=["自动化"], summary="一件的详情：为什么那条链（S0 → 大问题 → 目标 / 模块 → 需求原文）、守的戒律、开工单、交付、来龙去脉")
    def board_item(goal: str, sub: str, conn=Depends(get_conn)):
        d = board.detail(conn, project, goal, sub)
        if d is None:
            raise HTTPException(404, f"蓝图里没有这一件：{goal} {sub}")
        import timeline
        try:                                                    # 出生在哪一档、做完在哪一档（S1-8 S2-54）
            d["life"] = timeline.life(conn, project, goal=goal, sub=sub)
        except Exception:
            d["life"] = {"born": "", "done": ""}
        return d

    @app.get("/api/handovers/{code}", tags=["自动化"], summary="一张交接单的全文")
    def handover_one(code: str):
        h = next((x for x in agents.handovers(project) if x["code"] == code), None)
        if h is None:
            raise HTTPException(404, f"没有交接单 {code}")
        return h | {"text": (project.root / h["path"]).read_text(encoding="utf-8")}

    # ---- 下载清单（作者 2026-09-27：「很多agent没有下载权限需要手动下载……有链接直达，下载好的就是绿色」）----

    def _dl_mod(module: str) -> str:
        if proj.module_dir(project, module) is None:
            raise HTTPException(404, f"没有「{module}」这个模块")
        return module

    @app.get("/api/downloads/{module}", tags=["下载清单"], summary="下载清单：每篇的灯（绿 = 文件在、是 PDF）、链接、能不能直接下")
    def dl_list(module: str, conn=Depends(get_conn)):
        m = _dl_mod(module)
        try:
            library.scan(conn, project, m)          # 你照「存成」的名字放进 原文/ 的：马上认出是哪一行
        except store.Refused:
            pass
        return {"items": downloads.list_all(project, m), "folder": f"资料/{m}/{downloads.DIR}/",
                "downloads_dir": str(downloads.downloads_dir()), "file": f"资料/{m}/{downloads.FILE}"}

    @app.post("/api/downloads/{module}", tags=["下载清单"], summary="排进清单一篇（链接或 DOI）；有 DOI 的后台去找合法的免费版")
    def dl_add(module: str, body: DownloadIn, conn=Depends(get_conn)):
        return downloads.add(conn, project, _dl_mod(module), title=body.title, url=body.url, doi=body.doi, why=body.why,
                             authors=body.authors, year=body.year, venue=body.venue, note=body.note)

    @app.post("/api/downloads/{module}/fetch-all", tags=["下载清单"], summary="能直接下的、还没下好的，全部下")
    def dl_fetch_all(module: str):
        m = _dl_mod(module)
        todo = [x["code"] for x in downloads.list_all(project, m) if x["direct"] and x["lamp"] != "ok" and x["state"] != "下载中"]
        for code in todo:
            downloads.fetch_later(project, m, code)
        return {"started": todo}

    @app.post("/api/downloads/{module}/{code}/fetch", tags=["下载清单"], summary="直接下这一篇（后台下，下好了灯变绿）")
    def dl_fetch(module: str, code: str):
        m = _dl_mod(module)
        if not downloads.get(project, m, code)["direct"]:
            raise HTTPException(400, "这一篇没有能直接下的地址：点链接自己下")
        downloads.fetch_later(project, m, code)
        return downloads.get(project, m, code)

    @app.post("/api/downloads/{module}/{code}/find", tags=["下载清单"], summary="再去 OpenAlex 找一次合法的免费版")
    def dl_find(module: str, code: str):
        m = _dl_mod(module)
        threading.Thread(target=downloads.find_free, args=(project, m, code), daemon=True).start()
        return downloads.get(project, m, code)

    @app.post("/api/downloads/{module}/{code}/watch", tags=["下载清单"], summary="你点了链接自己去下：盯「下载」文件夹 10 分钟，新的 PDF 复制进来")
    def dl_watch(module: str, code: str):
        m = _dl_mod(module)
        downloads.watch(project, m, code)
        return downloads.get(project, m, code)

    @app.post("/api/downloads/{module}/{code}/file", tags=["下载清单"], summary="勾「下好了」：选（或拖）下好的那个 PDF 给这一行")
    def dl_file(module: str, code: str, file: UploadFile = File(...)):
        m = _dl_mod(module)
        tmp = project.index_dir / f".上传-{uuid.uuid4().hex}.pdf"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(tmp, "wb") as out:
                shutil.copyfileobj(file.file, out)
            return downloads.take(project, m, code, tmp)
        finally:
            tmp.unlink(missing_ok=True)

    # ---- 文献库（文献 S2-1、S2-2；作者：「原文所有的原文一个文件夹……另一个文件夹专门放解释，然后一一对应」）----

    @app.get("/api/library/{module}", tags=["文献库"], summary="文献库：每篇（原文 ↔ 解读 一一对应、信息、三格里有什么）+ 对不上的；还没入库的先入库")
    def lib_list(module: str, conn=Depends(get_conn)):
        m = _dl_mod(module)
        library.scan(conn, project, m)
        items, problems = library.entries(project, m)
        return {"items": items, "problems": problems, "states": list(library.STATES)}

    @app.post("/api/library/{module}/add", tags=["文献库"], summary="拖进来一个 PDF：复制进 原文/，编 L 号、建 解读/ 那一篇的文件夹（原件不动）")
    def lib_add(module: str, file: UploadFile = File(...), conn=Depends(get_conn)):
        m = _dl_mod(module)
        tmp = project.index_dir / f".上传-{uuid.uuid4().hex}.pdf"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(tmp, "wb") as out:
                shutil.copyfileobj(file.file, out)
            x = library.add(conn, project, m, tmp, name=file.filename or "")
        finally:
            tmp.unlink(missing_ok=True)
        return x                          # 不进总笔记：文献的事归文献自己管（作者 09-28），谁加的、什么时候在这篇的 信息.json 里

    @app.get("/api/library/{module}/{code}/notes", tags=["文献库"], summary="这篇的笔记（解读/L…/文本/笔记.md）：每条带页码、原句、颜色")
    def lib_notes(module: str, code: str):
        return {"items": library.notes(project, _dl_mod(module), code)}

    @app.post("/api/library/{module}/{code}/note", tags=["文献库"], summary="边读边记：选中一句记一条（页码、原句、颜色）")
    def lib_note(module: str, code: str, body: PaperNoteIn, conn=Depends(get_conn)):
        return library.add_note(conn, project, _dl_mod(module), code, page=body.page, quote=body.quote, text=body.text, color=body.color)

    @app.put("/api/library/{module}/{code}/notes/{i}", tags=["文献库"], summary="阅读时改一条笔记（第 i 条，从 0 数）：改字、换颜色；改前的原样留进 文本/.笔记历史.md")
    def lib_note_edit(module: str, code: str, i: int, body: PaperNoteEditIn, conn=Depends(get_conn)):
        return library.edit_note(conn, project, _dl_mod(module), code, i, at=body.at, text=body.text, color=body.color)

    @app.delete("/api/library/{module}/{code}/notes/{i}", tags=["文献库"], summary="删一条笔记（原样留进 文本/.笔记历史.md，找得回来）")
    def lib_note_delete(module: str, code: str, i: int, at: str, conn=Depends(get_conn)):
        return library.delete_note(conn, project, _dl_mod(module), code, i, at=at)

    @app.get("/api/library/{module}/{code}/marks", tags=["文献库"], summary="这篇的批注（解读/L…/批注.json）：高亮、便签、笔画")
    def lib_marks(module: str, code: str):
        return {"items": library.marks(project, _dl_mod(module), code)}

    @app.post("/api/library/{module}/{code}/marks", tags=["文献库"], summary="加一条批注：高亮 · 便签 · 笔（原版 PDF 不改）")
    def lib_mark(module: str, code: str, body: PaperMarkIn, conn=Depends(get_conn)):
        return library.add_mark(conn, project, _dl_mod(module), code, page=body.page, kind=body.kind, color=body.color,
                                points=body.points, rects=body.rects, at=body.at, text=body.text, width=body.width)

    @app.delete("/api/library/{module}/{code}/marks/{mark}", tags=["文献库"], summary="擦掉一条批注（橡皮、撤销）")
    def lib_unmark(module: str, code: str, mark: str, conn=Depends(get_conn)):
        return library.remove_mark(conn, project, _dl_mod(module), code, mark)

    @app.put("/api/library/{module}/{code}", tags=["文献库"], summary="管文献：改标签、分组、阅读状态（写回 信息.json）")
    def lib_update(module: str, code: str, body: LibInfoIn, conn=Depends(get_conn)):
        return library.update(conn, project, _dl_mod(module), code, body.model_dump(exclude_unset=True))

    # ---- 想法 → 需求（作者 2026-09-27：「把想法变成需求模块也要优化」）----

    @app.get("/api/ideas", tags=["想法"], summary="想法表：每个想法、去向，待整理的带上 agent 写的候选")
    def ideas_list(conn=Depends(get_conn)):
        out = []
        for x in ideas.list_all(project):
            cs = ideas.candidates(conn, x["code"]) if x["state"] == "待整理" else []
            out.append(x | {"candidates": [c | {"say": ideas.describe(c)} for c in cs]})
        return {"items": out, "groups": list(ideas.GROUPS)}

    @app.post("/api/ideas", tags=["想法"], summary="记一个想法（写原话；关于哪个模块）")
    def ideas_add(body: IdeaIn, conn=Depends(get_conn)):
        return ideas.add(conn, project, body.text, source=body.source, about=body.about)

    @app.post("/api/ideas/{code}/adopt", tags=["想法"], summary="点一个候选：写进模块的需求 / 戒律，或放进问答请你改总的")
    def ideas_adopt(code: str, body: PickIn, conn=Depends(get_conn)):
        x = ideas.adopt(conn, project, code, body.index)
        _logged(conn, "想法去向", code, x["dest"])
        return x

    @app.post("/api/ideas/{code}/dest", tags=["想法"], summary="放一放 / 不要 / 重新整理")
    def ideas_dest(code: str, body: DestIn, conn=Depends(get_conn)):
        return ideas.settle(conn, project, code, body.dest)

    @app.get("/api/governance/document", tags=["读"])
    def governance_document(path: str):
        import governance
        try:
            return governance.read_document(project, path)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.get("/api/governance/draft", tags=["读"])
    def governance_draft(kind: str, module: str = "", goal: str = ""):
        import governance
        try:
            return governance.draft(project, kind, module, goal)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.put("/api/governance/document", tags=["写"])
    def governance_save(body: dict, conn=Depends(get_conn)):
        import governance
        try:
            return governance.save_document(conn, project, body.get('path', ''), body.get('text', ''), body.get('revision', ''), by='人', reason='网页手写')
        except store.Refused as e:
            raise HTTPException(409, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.get("/api/governance", tags=["读"], summary="集中治理：目标、需求或模块的全文与关联")
    def governance_detail(kind: str = "module", key: str = ""):
        import governance
        try:
            return governance.detail(project, kind, key)
        except ValueError as e:
            raise HTTPException(404, str(e))

    @app.post("/api/governance/assign", tags=["想法"], summary="人设置需求的目标与承接模块")
    def governance_assign(body: dict, conn=Depends(get_conn)):
        import governance
        goals, modules = body.get('goals', []), body.get('modules', [])
        if not isinstance(goals, list) or not isinstance(modules, list) or not all(isinstance(x, str) for x in goals + modules):
            raise HTTPException(400, '目标和模块必须是列表')
        governance.validate_links(project, goals, modules)
        try:
            row = requirements.assign(project, body.get('key', ''), goals, [governance.normalize_module(project, m) for m in modules], conn=conn, revision=body.get('revision'))
        except ValueError as e:
            raise HTTPException(400, str(e))
        _logged(conn, '关联了需求', row['scope'], row['key'])
        return row

    @app.get("/api/requirements/{module}", tags=["想法"], summary="一个模块的需求 + 蓝图：每条需求达到没有、哪几件在为它做；在装它的开工单")
    def req_view(module: str):
        if proj.module_dir(project, module) is None and module not in {m["key"] for m in __import__("governance").module_catalog(project)} and not requirements.read(project, module):
            raise HTTPException(404, f"没有「{module}」这个模块")
        v = requirements.view(project, module)
        v["workorders"] = [{"code": w["code"], "name": w["name"], "state": workorders.state(project, w)}
                           for w in workorders.list_all(project) if module in w["modules"]]
        v["ideas"] = [x for x in ideas.list_all(project) if x["about"] == module]
        return v

    @app.post("/api/requirements/{module}/skeleton", tags=["想法"], summary="给这个模块建空的 需求.md、蓝图.md（已有的不动）")
    def req_skeleton(module: str, conn=Depends(get_conn)):
        try:
            made = requirements.skeleton(project, module)
        except ValueError as e:
            raise HTTPException(404, str(e))
        if made:
            _logged(conn, "建了需求和蓝图", module, "、".join(made))
        return {"made": made}

    @app.get("/api/deliveries", tags=["自动化"], summary="交付单 J：等你验收的在最上")
    def deliveries_list():
        return {"items": deliveries.list_all(project)}

    @app.post("/api/deliveries/{code}/accept", tags=["自动化"], summary="验收通过：蓝图里那件改「做完」")
    def deliveries_accept(code: str, conn=Depends(get_conn)):
        return deliveries.accept(conn, project, code)

    @app.post("/api/deliveries/{code}/reject", tags=["自动化"], summary="打回：写一句为什么，那件回到「在做」，agent 下一圈照改")
    def deliveries_reject(code: str, body: ReasonIn, conn=Depends(get_conn)):
        return deliveries.reject(conn, project, code, body.reason)

    @app.get("/api/skills", tags=["技能"], summary="技能库里有哪些技能、各自装没装（本项目 / 本机）")
    def skills_list():
        try:
            return skills.list_skills(project)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.get("/api/skills/catalog", tags=["技能"], summary="本项目技能：业务阶段、双语正本、来源许可与缺项；只读")
    def skills_catalog():
        try:
            return skills.inventory(project)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.get("/api/skills/{sid}", tags=["技能"], summary="读同一份技能正本全文，不安装或执行")
    def skills_read(sid: str, language: str = "zh-CN"):
        try:
            return skills.read(project, sid, language)
        except KeyError:
            raise HTTPException(404, f"技能库里没有「{sid}」")
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.post("/api/skills/{sid}/install", tags=["技能"], summary="装一个技能：同名不一样时先问，覆盖前备份")
    def skills_install(sid: str, body: InstallIn, conn=Depends(get_conn)):
        try:
            r = skills.install(project, sid, _where(body.where), overwrite=body.overwrite)
        except KeyError:
            raise HTTPException(404, f"技能库里没有「{sid}」")
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not r["already"]:
            _logged(conn, "装技能", sid, ("本项目" if body.where == "project" else "本机") + ("（旧的已备份）" if r["backup"] else ""))
        return {**r, "skills": skills.list_skills(project)}

    @app.post("/api/skills/{sid}/fork", tags=["技能"], summary="复制一份改：技能库里多一个「（我的）」")
    def skills_fork(sid: str, conn=Depends(get_conn)):
        try:
            new = skills.fork(project, sid)
        except KeyError:
            raise HTTPException(404, f"技能库里没有「{sid}」")
        except ValueError as e:
            raise HTTPException(400, str(e))
        _logged(conn, "复制技能", new, f"从「{sid}」复制")
        return {"id": new, "skills": skills.list_skills(project)}

    @app.get("/api/commands", tags=["快捷指令"], summary="全部快捷指令（含装没装进 Claude Code）")
    def commands_list():
        return commands.list_commands(project)

    @app.post("/api/commands", tags=["快捷指令"], summary="新建一条快捷指令")
    def commands_new(body: CommandIn, conn=Depends(get_conn)):
        commands.save(body.name, body.en, body.description, body.body, create=True)
        _logged(conn, "新建快捷指令", body.name.strip())
        return commands.list_commands(project)

    @app.put("/api/commands/{cid}", tags=["快捷指令"], summary="改一条快捷指令（名字不改）")
    def commands_edit(cid: str, body: CommandIn, conn=Depends(get_conn)):
        commands.save(cid, body.en, body.description, body.body, create=False)
        _logged(conn, "改快捷指令", cid)
        return commands.list_commands(project)

    @app.post("/api/commands/{cid}/install", tags=["快捷指令"], summary="装进 Claude Code（.claude/commands/英文短名.md）")
    def commands_install(cid: str, body: InstallIn, conn=Depends(get_conn)):
        try:
            r = commands.install(project, cid, _where(body.where), overwrite=body.overwrite)
        except KeyError:
            raise HTTPException(404, f"没有「{cid}」这条快捷指令")
        if not r["already"]:
            _logged(conn, "装快捷指令进 Claude Code", cid, "本项目" if body.where == "project" else "本机")
        return {**r, "commands": commands.list_commands(project)}

    # ---- 外部资料入口 Intake ----

    @app.post("/api/inbox", tags=["外部资料入口"], summary="放进外部资料入口：先进 资料/_外部资料入口/，一模一样的不存第二份")
    def upload(files_: list[UploadFile] = File(..., alias="files")):
        out = {"added": [], "dup": []}
        project.index_dir.mkdir(parents=True, exist_ok=True)
        for f in files_:
            tmp = project.index_dir / f"upload-{uuid.uuid4().hex}.part"   # 先写到 索引/，写完才进外部资料入口
            with open(tmp, "wb") as w:
                shutil.copyfileobj(f.file, w)
            conn = store.connect(project.db_path)
            try:
                r = intake.receive(conn, project, tmp, f.filename or "未命名")
            finally:
                conn.close()
                tmp.unlink(missing_ok=True)
            (out["dup"] if r["dup"] else out["added"]).append(r["item"]["name"])
        if out["added"] or out["dup"]:
            conn = store.connect(project.db_path)
            try:
                text = (f"放进来 {len(out['added'])} 个：" + "、".join(out["added"]) if out["added"] else "没有新文件")
                if out["dup"]:
                    text += "\n跟已有的一模一样、没存第二份：" + "、".join(out["dup"])
                journal.add(conn, project, text, kind="放进外部资料入口")
            finally:
                conn.close()
        return out

    @app.get("/api/inbox", tags=["外部资料入口"], summary="待分拣的文件和它们的候选模块")
    def inbox(conn=Depends(get_conn)):
        store.get_state(conn, project)                 # 顺手对一次账：直接丢进文件夹的也算
        return {"items": intake.waiting(conn)}

    @app.post("/api/inbox/{iid}/oss", tags=["外部资料入口"], summary="放进开源项目：压缩包读出名字和许可证、建 O 卡，原件挪进 工具库/开源项目/原件/（工具 S2-3）")
    def inbox_oss(iid: int, conn=Depends(get_conn)):
        x = repos.take(conn, project, iid, by="人")
        journal.add(conn, project, f"从外部资料入口放进开源项目：{x['code']} {x['name']}（{x['license'] or '没许可证'} · {x['borrow']}）", kind="放进来", scope="工具")
        return {"items": intake.waiting(conn), "repo": x}

    @app.get("/api/inbox/folders", tags=["外部资料入口"], summary="一个模块里有哪些文件夹（分拣时挑「具体模块的具体文件夹」）")
    def inbox_folders(module: str, conn=Depends(get_conn)):
        m = store.find_module(conn, module)
        if not m:
            raise store.Refused(f"没有「{module}」这个模块")
        return {"module": m["name"], "folders": intake.module_folders(project, m["name"])}

    @app.post("/api/inbox/{iid}/sort", tags=["外部资料入口"], summary="人点了「放这里」：挪进那个模块（或模块里的某个文件夹）")
    def sort(iid: int, body: SortIn, conn=Depends(get_conn)):
        before = intake.get(conn, iid)
        it = intake.sort(conn, project, iid, body.module, folder=body.folder)
        picked = next((c for c in (before or {}).get("candidates", []) if c["module"] == body.module
                       and (c.get("folder") or "") == body.folder.strip().strip("/")), None)
        why = f"（选的是 {picked['by']} 给的候选：把握 {picked['conf']}，{picked['reason']}）" if picked else "（候选里没有，自己选的）"
        journal.add(conn, project, f"从外部资料入口放进来：{it['sorted_to']}{why}", kind="放进来", scope=body.module)
        return {"items": intake.waiting(conn)}

    # ---- 笔记本：笔记/ 文件夹，按模块一个文件，每条有编号 ----

    def _names(conn):
        return [m["name"] for m in store.list_folder_modules(conn, project)]

    def _scope_ok(scope: str) -> str:
        try:
            notebook._file(project, scope)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return scope

    @app.get("/api/notes", tags=["笔记本"], summary="笔记本目录：总览 + 每个模块各一本，还有复制历史")
    def notes_index(conn=Depends(get_conn)):
        return {"scopes": notebook.scopes(project, _names(conn)), "history": notebook.history(project),
                "log": journal.months(project),                     # 日志（笔记/日志/，机器记的）：一个月一行
                "last_copy": store._meta(conn, "note_last_copy")}

    @app.get("/api/log", tags=["日志"], summary="日志：机器记的（网页上点的操作、agent 做的事）。month=2026-09 看一个月，不给看最近的")
    def log_read(month: str = "", limit: int = 300):
        es = journal.read(project, month or None)
        return {"months": journal.months(project), "entries": es[-min(max(limit, 1), 5000):] if not month else es}

    @app.get("/api/notes/since-copy", tags=["笔记本"], summary="上次复制给 agent 以后新记的笔记")
    def notes_since(conn=Depends(get_conn)):
        return notebook.since_last_copy(conn, project, _names(conn))

    @app.post("/api/notes/copy", tags=["笔记本"], summary="复制给 agent 的那段：存进 笔记/历史/，永不删")
    def notes_copy(body: TextIn, conn=Depends(get_conn)):
        name = notebook.archive_copy(conn, project, body.text, _names(conn))
        store.export_instruction(conn, body.text)
        return {"history": name}

    @app.get("/api/notes/{scope}", tags=["笔记本"], summary="一本笔记的全部条目")
    def notes_read(scope: str):
        return {"scope": scope, "entries": notebook.read(project, _scope_ok(scope))}

    @app.post("/api/notes/{scope}", tags=["笔记本"], summary="记一条（自动编号）")
    def notes_add(scope: str, body: NoteIn, conn=Depends(get_conn)):
        sc = _scope_ok(scope)
        if (body.kind or "笔记") not in journal.HUMAN:
            raise HTTPException(400, "笔记只记人写的（笔记、截图、录屏、删除请求）；机器记的进日志")
        e = notebook.add(conn, project, sc, body.text, kind=body.kind or "笔记", attach=body.attach)
        if body.idea:                                   # 「是想法」：想法表多一行，连回这条笔记
            about = sc if sc != notebook.MAIN and proj.module_dir(project, sc) else ideas.WHOLE
            e["idea"] = ideas.add(conn, project, body.text, source=f"笔记 {e['id']}", about=about)["code"]
        return e

    @app.put("/api/notes/{scope}/{eid}", tags=["笔记本"], summary="改一条（原文先记进 笔记/历史/改动记录.md）")
    def notes_edit(scope: str, eid: str, body: TextIn, conn=Depends(get_conn)):
        return notebook.edit(conn, project, _scope_ok(scope), eid, body.text)

    @app.post("/api/notes/{scope}/{eid}/delete", tags=["笔记本"], summary="删一条（原文先记进 笔记/历史/改动记录.md）")
    def notes_delete(scope: str, eid: str, conn=Depends(get_conn)):
        notebook.remove(conn, project, _scope_ok(scope), eid)
        return {"ok": True}

    @app.put("/api/note", tags=["写 · 人"], summary="存笔记草稿（边打字边存）；一下子少了一大截时旧的先留底")
    def save_note(body: DraftIn, conn=Depends(get_conn)):
        return store.save_draft(conn, body.text, recorded=body.recorded)

    @app.get("/api/note/backups", tags=["写 · 人"], summary="草稿留底：清空、整段删掉之前的样子，能找回来")
    def note_backups(conn=Depends(get_conn)):
        return {"items": store.draft_backups(conn)}

    @app.get("/api/note/drafts", tags=["截图录屏"], summary="随堂笔记里还没记下的截图、录屏（录屏带着它的画面）")
    def note_drafts():
        return {"items": notebook.drafts(project)}

    @app.post("/api/note/drafts", tags=["截图录屏"], summary="贴进来 / 拖进来一张图或一段录屏：先放草稿，记下时才挪进 笔记/截图/ 或 笔记/录屏/")
    def note_draft_add(file: UploadFile = File(...)):
        return notebook.stage(project, file.file, file.content_type, file.filename)

    @app.put("/api/note/drafts/{name}", tags=["截图录屏"], summary="画过的图换掉草稿里那张（截图，或录屏的一张画面）")
    def note_draft_replace(name: str, file: UploadFile = File(...)):
        return notebook.replace_draft(project, name, file.file, file.content_type)

    @app.post("/api/note/drafts/{name}/frames", tags=["截图录屏"], summary="网页从录屏里抽的画面（最多 5 张），放在录屏旁边给 agent 看")
    def note_draft_frames(name: str, files_: list[UploadFile] = File(..., alias="files")):
        return notebook.save_frames(project, name, [(f.file, f.content_type) for f in files_])

    @app.post("/api/note/drafts/{name}/drop", tags=["截图录屏"], summary="去掉一张还没记下的截图 / 一段录屏（草稿，不进回收站）")
    def note_draft_drop(name: str):
        notebook.drop_draft(project, name)
        return {"items": notebook.drafts(project)}

    @app.post("/api/note/saved/frames", tags=["截图录屏"], summary="已经记下的录屏补上画面（网页抽的）：放在录屏旁边，那条笔记末尾补上")
    def notes_frames(path: str, files_: list[UploadFile] = File(..., alias="files"), conn=Depends(get_conn)):
        e = notebook.add_frames(conn, project, path, [(f.file, f.content_type) for f in files_])
        return {"entry": e}

    @app.put("/api/note/saved/image", tags=["截图录屏"], summary="笔记本里画过的截图换掉原来那张；原图先留进 笔记/历史/原图/")
    def notes_image(path: str, file: UploadFile = File(...), conn=Depends(get_conn)):
        return notebook.replace_saved_image(conn, project, path, file.file, file.content_type)

    @app.get("/api/note/capture", tags=["截图录屏"], summary="现在在等什么：image 等你框选 / video 在录屏 / null 没在等")
    def capture_status():
        return grab.status()

    @app.post("/api/note/capture", tags=["截图录屏"], summary="叫出系统截图（image）或录屏（video）；截好、录好的自己进草稿")
    def capture_start(body: CaptureIn):
        if not capture.available():
            raise HTTPException(400, "这台电脑叫不出系统截图：用系统自带的截图截好，在笔记里 Ctrl+V 贴")
        try:
            return grab.start(body.kind)
        except capture.Busy as e:
            raise HTTPException(409, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.post("/api/note/capture/cancel", tags=["截图录屏"], summary="不等了")
    def capture_cancel():
        grab.cancel()
        return grab.status()

    def capture_view(conn) -> dict:
        cs = capture_settings(conn)
        live = keys["mgr"] is not None
        return cs | {"available": capture.available(), "live": live,
                     "status": keys["mgr"].status if live else {"shot": "not_running", "record": "not_running"},
                     "folder_exists": bool(cs["folder"]) and os.path.isdir(cs["folder"])}

    @app.get("/api/capture-settings", tags=["截图录屏"], summary="截图、录屏的快捷键和录屏文件夹，快捷键在不在用")
    def capture_settings_get(conn=Depends(get_conn)):
        return capture_view(conn)

    @app.put("/api/capture-settings", tags=["截图录屏"], summary="改快捷键、录屏文件夹；马上生效")
    def capture_settings_put(body: CaptureSettingsIn, conn=Depends(get_conn)):
        out = {}
        for k, label in (("shot", "截图快捷键"), ("record", "录屏快捷键")):
            try:
                out[k] = hotkeys.fmt(getattr(body, k))
            except ValueError as e:
                raise HTTPException(400, f"{label}：{e}")
        if out["shot"] and out["shot"] == out["record"]:
            raise HTTPException(400, "截图和录屏的快捷键不能一样")
        folder = body.folder.strip().strip('"')
        if folder and not os.path.isabs(folder):
            raise HTTPException(400, "录屏文件夹要写完整的路径，比如 D:\\视频\\录屏")
        with store.tx(conn):
            store._set_meta(conn, "capture_shot", out["shot"])
            store._set_meta(conn, "capture_record", out["record"])
            store._set_meta(conn, "capture_folder", folder)
            store.log(conn, "人", "改截图录屏设置", None, f"截图 {out['shot'] or '不用'} · 录屏 {out['record'] or '不用'}")
        if keys["mgr"]:
            keys["mgr"].apply(out)
        return capture_view(conn)

    @app.post("/api/note/export", tags=["写 · 人"], summary="记下一条导出给 agent 的指令")
    def export_note(body: TextIn, conn=Depends(get_conn)):
        return store.export_instruction(conn, body.text)

    @app.post("/api/pending/{code}/answer", tags=["写 · 人"], summary="给一条待拍板拍板，生成一条决定")
    def answer(code: str, body: TextIn, conn=Depends(get_conn)):
        d = store.answer(conn, code, body.text)
        journal.add(conn, project, f"{code}「{d['detail']}」→ {d['text']}（记为决定 {d['code']}）", kind="拍板")
        answers.close_pending(conn, project, code, d["code"], body.text)   # 从这条待拍板来的答疑，标上「你拍板了」
        return store.get_state(conn, project)

    @app.get("/api/answers", tags=["自动化"], summary="答疑记录：agent 的问题、查了哪些、自动答上还是转给了你（新的在前）")
    def answers_list():
        return {"items": answers.read(project)}

    @app.get("/api/qa", tags=["问答"], summary="问答页一次拿全：agent 问你（待你判断 D- · 答疑 Q · 决定 A-）· 你问 agent（问- → 答-）")
    def qa_all(conn=Depends(get_conn)):
        return {"pending": store.list_pending(conn), "answers": answers.read(project),
                "decisions": store.list_decisions(conn, 1000), "asked": store.list_asked(conn)}

    @app.post("/api/qa/ask", tags=["问答"], summary="你问 agent：记下来，agent 下一次看全貌时先答（where 写出处，比如「文献 L1 第 3 页」）")
    def qa_ask(body: AskIn, conn=Depends(get_conn)):
        q = store.ask_agent(conn, body.text, where=body.where)
        _logged(conn, "问 agent", q["code"], body.text[:80])
        return q

    @app.get("/api/trash", tags=["清理"], summary="清理页：回收站清单（X…）+ 还没处理的删除请求 + 能彻底删到哪（最近定性的存档）")
    def trash_all(conn=Depends(get_conn)):
        names = [m["name"] for m in store.list_folder_modules(conn, project)]
        return {"items": trash.read(project), "requests": trash.pending_requests(project, names),
                "cutoff": snapshot.settled_cutoff(project)}

    @app.post("/api/trash/{code}/restore", tags=["清理"], summary="从回收站还原；原位置有东西，要人确认（confirm）才把现有的也挪进回收站")
    def trash_restore(code: str, body: ConfirmIn, conn=Depends(get_conn)):
        r = trash.restore(conn, project, code, by="人", swap=body.confirm)
        _logged(conn, "从回收站还原", code, r["back_to"] + (f"（原位置上的挪进了 {r['swapped']}）" if r["swapped"] else ""))
        return r

    @app.post("/api/trash/purge", tags=["清理"], summary="彻底删掉（收不回来）：回收站里的都能删，要人确认（10-07 起不用先定性存档）")
    def trash_purge(body: PurgeIn, conn=Depends(get_conn)):
        if not body.confirm:
            raise store.NeedConfirm(f"彻底删掉 {'、'.join(body.codes)}？删了就收不回来了。", {"codes": body.codes})
        r = trash.purge(conn, project, body.codes, by="人")
        _logged(conn, "彻底删掉", "、".join(body.codes), f"腾出 {snapshot._human(r['freed'])}")
        return r

    # ---- 存档（作者 2026-09-22：「就是打游戏先储存，死了之后到复活点复活」）----

    @app.get("/api/checkpoints", tags=["存档"], summary="全部存档（新的在前）、一共占多大、只留几档、丢过哪些")
    def ck_list(conn=Depends(get_conn)):
        return {"saves": snapshot.list_saves(project), "total": snapshot.total_size(project),
                "picks": snapshot.last_picks(conn), "cutoff": snapshot.settled_cutoff(project),
                "keep": snapshot.KEEP, "core": snapshot.CORE, "dropped": snapshot.dropped(project)}

    # 存档是总入口（S1-8 S2-54）：一档 = 一个时间节点；中间发生了什么、一件事出生在哪一档做完在哪一档，都现算
    @app.get("/api/timeline", tags=["存档"], summary="世界树总览：每一档（从早到晚，最后是「现在」）跟上一档之间几条想法、需求、件、交付、日志、拍板，改了几个文件")
    def timeline_all(conn=Depends(get_conn)):
        import timeline
        return {"nodes": timeline.summary(conn, project)}

    @app.get("/api/timeline/life", tags=["存档"], summary="一件事出生在哪一档、做完在哪一档：件 goal+sub · 想法 idea · 需求 need（「项目 需-3」）")
    def timeline_life(goal: str = "", sub: str = "", idea: str = "", need: str = "", conn=Depends(get_conn)):
        import timeline
        return timeline.life(conn, project, goal=goal, sub=sub, idea=idea, need=need)

    @app.get("/api/timeline/{code}", tags=["存档"], summary="一档（或「现在」）跟上一档之间发生了什么：想法、需求、件、交付、日志、拍板、改了的文件")
    def timeline_node(code: str, conn=Depends(get_conn)):
        import timeline
        return timeline.node(conn, project, code)

    # 世界树（S1-8 S2-55、S2-56）：从一档长一根枝 = 整份取出来放在项目旁边，自己的后台、库、核心锁；结果实、G1 验收、合回主干
    @app.get("/api/worldtree", tags=["存档"], summary="世界树的枝：每根从哪一档长、为了什么、谁在上面、开着没有、结果了没有；here = 这个项目自己是不是一根枝")
    def wt_list():
        import worldtree
        bs = worldtree.list_branches(project)
        for b in bs:
            b["running"] = b["state"] in ("长着", "结果了") and worldtree.running(b)
            b["held"] = worldtree.held(b) if b["exists"] and b["state"] == "长着" else []
        import branching
        return {"branches": bs, "here": worldtree.is_branch(project), "forest": str(worldtree.forest(project)),
                "pins": snapshot.pins(project), "groups": branching.groups(project)}

    @app.post("/api/worldtree/pick", tags=["存档"], summary="（档位 3、4）比较单上挑一根合回，没挑中的砍掉；branch 空 = 全打回接着长")
    def wt_pick(body: FruitPickIn, conn=Depends(get_conn)):
        import branching
        g = branching.pick(conn, project, body.code, body.branch, body.why, by="人")
        _logged(conn, "挑果实", body.code, (f"合了 {g.get('pick')}" if g["state"] == "合了" else g["state"]) + f"：{body.why}")
        return g

    # 设置 → 自动化、存档（S1-8 S2-57、S2-59；作者 10-03「就是自动化的程度吧，有档位……存档可以设计成最多存多少档，默认如何存档等等，可以自定义多一点」）
    @app.get("/api/settings/auto", tags=["设置"], summary="自动化：四个档位、现在的各个数、开着没有、暂停着没有、员工开关")
    def set_auto_get(conn=Depends(get_conn)):
        import autolaunch
        import knobs
        return {"knobs": knobs.all_auto(conn), "spec": knobs.describe(), "launch": autolaunch.settings(conn),
                "paused": workorders.paused(conn),
                "agents": [{"code": a["code"], "name": a["name"], "program": a.get("program", ""), "roles": agents.jobs(a),
                            **{k: bool(a.get(k)) for k in agents.SWITCHES}} for a in agents.list_all(project)]}

    @app.put("/api/settings/auto", tags=["设置"], summary="改自动化设置：选档位（带上那一档的数）或改单个数")
    def set_auto_put(body: KnobsIn, conn=Depends(get_conn)):
        import knobs
        r = knobs.set_many(conn, body.patch, by="人")
        if r["changed"]:
            _logged(conn, "改了自动化设置", "设置", "、".join(r["changed"]))
        return r

    @app.get("/api/settings/saves", tags=["设置"], summary="存档：最多几档、什么时候自动存、空间上限、世界树；现在占多大；不存的")
    def set_saves_get(conn=Depends(get_conn)):
        import knobs
        import worldtree
        k = knobs.all_saves(conn)
        return {"knobs": k, "spec": knobs.describe(), "status": snapshot.status(project), "space": worldtree.space(project),
                "forest": str(worldtree.forest(project)), "live": len(worldtree.live(project)),
                "recycle_old": worldtree.recycle_old(project, k["wt_recycle_days"]), "ignore": snapshot.ignore_rows(project),
                "builtin": [{"path": x, "why": w} for x, w in (("存档/", "存档自己"), ("回收站/", "删掉的东西"), ("索引/", "库、缓存、本机设置"),
                                                                 (".git/", "版本库"), (".claude/worktrees/", "agent 的临时工作副本"),
                                                                 ("__pycache__、node_modules、.venv……", "缓存，能重新生成"))]}

    @app.put("/api/settings/saves", tags=["设置"], summary="改存档设置")
    def set_saves_put(body: KnobsIn, conn=Depends(get_conn)):
        import knobs
        r = knobs.set_many(conn, body.patch, by="人")
        if r["changed"]:
            _logged(conn, "改了存档设置", "设置", "、".join(r["changed"]))
            snapshot.prune(conn, project, by="人")       # 留几档改小了：马上照新的清
        return r

    @app.put("/api/settings/save-ignore", tags=["设置"], summary="改存档不存的（存档忽略.txt），整张表写回")
    def set_ignore_put(body: IgnoreIn, conn=Depends(get_conn)):
        rows = snapshot.set_ignore(conn, project, body.rows, by="人")
        _logged(conn, "改了存档不存的", "存档忽略.txt", "、".join(r["path"] for r in rows)[:200])
        return {"ignore": rows}

    # 清理 → 查乱 · 归档（S1-8 S2-61；需-29：作者 10-03「清理模块不光得有垃圾桶的功能，还得有重铸的功能……相当于上下文压缩了」）
    @app.get("/api/tidy", tags=["清理"], summary="查乱：重复的段落、能归档的旧记录、没人用的程序、太长的正本、计划重号；fresh=1 现查一遍（会存下来）")
    def tidy_get(fresh: int = 0, conn=Depends(get_conn)):
        import tidy
        d = None if fresh else tidy.last(project)
        return d or tidy.report(conn, project)

    @app.get("/api/archive", tags=["清理"], summary="归档：已经收了哪些（按月）、现在能收哪些（照设置的天数，days 能临时改了看看）")
    def archive_get(days: int = 0, conn=Depends(get_conn)):
        import archive
        return {"summary": archive.summary(project), "items": [r for r in archive.index(project) if r.get("state") in ("归档", "旧版")],
                "candidates": archive.candidates(conn, project, days=days or None)}

    @app.post("/api/archive", tags=["清理"], summary="收进归档（要人确认）：先存一档，整份搬进 归档/年-月/，带索引；能拿回来")
    def archive_put(body: ArchiveIn, conn=Depends(get_conn)):
        import archive
        if not body.confirm:
            cands = archive.candidates(conn, project)
            n = len(cands) if body.rels is None else len(body.rels)
            raise store.NeedConfirm(f"把 {n} 份旧记录收进 归档/？原文原样搬、带索引，收之前先存一档，随时能拿回来。", {"count": n})
        r = archive.put_away(conn, project, body.rels, by="人")
        _logged(conn, "收进归档", "归档", f"{len(r['moved'])} 份 · {r['bytes'] // 1024} KB")
        return r

    @app.post("/api/archive/back", tags=["清理"], summary="从归档拿回来：放回原处（原处有同名的不放）")
    def archive_back(body: BackIn, conn=Depends(get_conn)):
        import archive
        return archive.bring_back(conn, project, body.rels, by="人")

    # 清理 → 摘要 · 重写（S1-8 S2-62、S2-63）
    @app.get("/api/digest", tags=["清理"], summary="摘要：有哪些（现在的样子、总的、每月）、现在该写哪几份、谁来写")
    def digest_get(conn=Depends(get_conn)):
        import digest
        import knobs
        held = {r["sub"]: r["agent"] for r in claims.active(conn) if r["goal"] == digest.JOB}
        return {"items": digest.listing(project), "due": [d | {"by": held.get(d["key"], "")} for d in digest.due(conn, project)],
                "digest_by": knobs.get(conn, "digest_by")}

    @app.get("/api/rewrite", tags=["清理"], summary="重写单：每张改哪份、几处、多大、状态；该出单的；能重写的正本")
    def rewrite_get(conn=Depends(get_conn)):
        import rewrite
        held = {r["sub"]: r["agent"] for r in claims.active(conn) if r["goal"] == rewrite.JOB}
        return {"items": [{k: v for k, v in x.items() if k != "text"} for x in rewrite.listing(project)],
                "wanted": [w | {"by": held.get(w["rel"], "")} for w in rewrite.wanted(conn, project)], "canon": rewrite.canon(project)}

    @app.get("/api/rewrite/{code}/diff", tags=["清理"], summary="一张重写单的对照（现在 → 改后，一行一行）")
    def rewrite_diff(code: str):
        import rewrite
        return rewrite.diff(project, code) | {"sheet": {k: v for k, v in rewrite.get(project, code).items() if k != "text"}}

    @app.post("/api/rewrite/{code}/accept", tags=["清理"], summary="换上（要人确认）：换前存档，旧版收进归档、标被取代")
    def rewrite_accept(code: str, body: ConfirmIn, conn=Depends(get_conn)):
        import rewrite
        x = rewrite.get(project, code)
        if not body.confirm:
            raise store.NeedConfirm(f"用 {code} 换掉「{x['target']}」？换之前先存一档，现在这份收进 归档/…/旧版/，能找回来。", {"code": code})
        r = rewrite.accept(conn, project, code, by="人")
        _logged(conn, "换上重写单", code, x["target"])
        return r

    @app.post("/api/rewrite/{code}/drop", tags=["清理"], summary="不要这张重写单（写为什么）")
    def rewrite_drop(code: str, body: BranchActIn, conn=Depends(get_conn)):
        import rewrite
        return rewrite.drop(conn, project, code, by="人", why=body.why)

    @app.post("/api/rewrite/ask", tags=["清理"], summary="让 agent 重写一份正本：记一件「写重写单」的活（规划的员工或 G1 领）")
    def rewrite_ask(body: RewriteAskIn, conn=Depends(get_conn)):
        import rewrite
        return rewrite.ask(conn, project, body.path, by="人", note=body.note)

    @app.get("/api/rebirth", tags=["清理"], summary="重生：全量备份的进度（正在跑的那份）、以前的备份、重生计划（治理/计划/ 里开头写着「重生:」的）")
    def rebirth_get():
        import rebirth
        return {"job": rebirth.status(project), "history": rebirth.history(project), "plans": rebirth.plans(project)}

    @app.get("/api/rebirth/size", tags=["清理"], summary="全量备份带存档、不带存档各要多大，磁盘还剩多少（数一遍要一两秒，存五分钟）")
    def rebirth_size(fresh: int = 0):
        import rebirth
        return rebirth.sizes(project, fresh=bool(fresh))

    @app.post("/api/rebirth/backup", tags=["清理"], summary="全量备份（要人确认）：项目和世界树原样复制到项目旁边，能不带存档；后台跑，一次一份，磁盘不够拒")
    def rebirth_backup(body: BackupIn):
        import rebirth
        from snapshot import _human
        s = rebirth.sizes(project, fresh=True)
        need = s["with_saves" if body.with_saves else "without_saves"]
        if not body.confirm:
            raise store.NeedConfirm(f"全量备份{'（连存档）' if body.with_saves else '（不带存档）'}：{need['files']} 个文件、{_human(need['bytes'])}，"
                                    f"放到 {s['where']} 下的「{project.root.name} · 全量备份 日期 时分」；那个盘还剩 {_human(s['free'])}。"
                                    "在后台复制，可以接着干别的。", {"with_saves": body.with_saves})
        return rebirth.start(project, with_saves=body.with_saves, by="人")      # 跑完在日志里记一条（在后台线程里记，免得备份抄到正在变的日志）

    @app.get("/api/settings/tidy", tags=["设置"], summary="清理：归档多久以前的、要不要自动归档、多久查一次乱、正本多长算太长")
    def set_tidy_get(conn=Depends(get_conn)):
        import knobs
        return {"knobs": {k: knobs.get(conn, k) for k in knobs.TIDY}, "spec": knobs.describe()}

    @app.put("/api/settings/tidy", tags=["设置"], summary="改清理设置")
    def set_tidy_put(body: KnobsIn, conn=Depends(get_conn)):
        import knobs
        r = knobs.set_many(conn, body.patch, by="人")
        if r["changed"]:
            _logged(conn, "改了清理设置", "设置", "、".join(r["changed"]))
        return r

    @app.post("/api/checkpoints/gc", tags=["存档"], summary="收掉对象库里没有任何档用到的内容")
    def ck_gc(conn=Depends(get_conn)):
        r = snapshot.gc_objects(project)
        if r["removed"]:
            _logged(conn, "收掉没人用的存档内容", "存档", f"{r['removed']} 个，腾出 {snapshot._human(r['freed'])}")
        return r

    @app.post("/api/worldtree", tags=["存档"], summary="长一根枝：从一档（或现在，先存一档）整份取出来，放到项目旁边的「<项目名> 世界树/枝-<号> 名字/」")
    def wt_grow(body: GrowIn, conn=Depends(get_conn)):
        import worldtree
        b = worldtree.grow(conn, project, name=body.name, by="人", why=body.why, base=body.base, for_=body.for_)
        _logged(conn, "长了一根枝", b["code"], f"{b['name']} · 从 {b['base']}")
        return b

    @app.get("/api/worldtree/{code}/changes", tags=["存档"], summary="识别改动：拿长枝那一档当底，枝改了什么（直接换上 / 枝删了 / 两边都改要三方合并 / 改得一样 / 枝的记录），主干同期改了几个")
    def wt_changes(code: str):
        import worldtree
        return worldtree.changes(project, code)

    @app.post("/api/worldtree/{code}/start", tags=["存档"], summary="起枝的后台（看 demo）：枝自己的程序、自己的端口；在跑就接上")
    def wt_start(code: str):
        import worldtree
        return worldtree.start(project, code)

    @app.post("/api/worldtree/{code}/stop", tags=["存档"], summary="停枝的后台")
    def wt_stop(code: str):
        import worldtree
        worldtree.stop(project, code)
        return {"ok": True}

    @app.post("/api/worldtree/{code}/assign", tags=["存档"], summary="派到枝上：在枝的库里替员工领下这件，在网页终端里开窗口（标题「枝-3 · G5 名字」，进枝的文件夹）")
    def wt_assign(code: str, body: AssignIn, conn=Depends(get_conn)):
        import worldtree
        return worldtree.assign(conn, project, code, body.agent, body.goal, body.sub, by="人", open_window=body.open)

    @app.post("/api/worldtree/{code}/merge", tags=["存档"], summary="验收过了，合回主干：合前存一档；只枝改的换上、两边改的三方合并、合不开的不覆盖（放进 自动化/世界树/枝-n/冲突/）；合完存一档")
    def wt_merge(code: str, body: BranchActIn, conn=Depends(get_conn)):
        import worldtree
        if not body.confirm:
            ch = worldtree.changes(project, code)
            raise store.NeedConfirm(f"把 {code} 合回主干？换上 {len(ch['take'])} 个、三方合并 {len(ch['both'])} 个、删 {len(ch['delete'])} 个；"
                                    "合之前先存一档，合不开的不覆盖。", {"code": code, "counts": ch["counts"]})
        r = worldtree.merge(conn, project, code, by="人")
        _logged(conn, "合回主干", code, f"换上 {len(r['took'])} · 三方合并 {len(r['merged'])} · 合不开 {len(r['conflicts'])}")
        return r

    @app.post("/api/worldtree/{code}/reject", tags=["存档"], summary="验收不过，打回：枝接着长，打回的话写进枝里")
    def wt_reject(code: str, body: BranchActIn, conn=Depends(get_conn)):
        import worldtree
        b = worldtree.reject(conn, project, code, by="人", why=body.why)
        _logged(conn, "打回果实", code, body.why)
        return b

    @app.post("/api/worldtree/{code}/cut", tags=["存档"], summary="砍掉一根枝：停后台，文件夹挪到「<项目名> 世界树/.回收/」（能拿回来），记录留着")
    def wt_cut(code: str, body: BranchActIn, conn=Depends(get_conn)):
        import worldtree
        if not body.confirm:
            raise store.NeedConfirm(f"砍掉 {code}？它的文件夹挪进世界树的 .回收，能拿回来；没合的改动不进主干。", {"code": code})
        b = worldtree.cut(conn, project, code, by="人", why=body.why)
        _logged(conn, "砍了一根枝", code, body.why)
        return b

    @app.post("/api/worldtree/fruit", tags=["存档"], summary="（在枝里）结果实：存一档、标「结果了」、写 demo 说明和检查")
    def wt_fruit(body: FruitIn, conn=Depends(get_conn)):
        import worldtree
        return worldtree.bear_fruit(conn, project, demo=body.demo, checks=body.checks, by="人")

    @app.get("/api/checkpoints/tree", tags=["存档"], summary="「自定义」打勾用：项目顶层和下一层，每项多少文件、多大")
    def ck_tree():
        return {"items": snapshot.tree(project)}

    @app.post("/api/checkpoints/estimate", tags=["存档"], summary="存之前先算：要复制几个文件、多大")
    def ck_estimate(body: EstimateIn):
        return snapshot.estimate(project, snapshot.offered(body.mode), [])

    @app.post("/api/checkpoints", tags=["存档"], summary="存一档（记为「人」存的）")
    def ck_save(body: SaveIn, conn=Depends(get_conn)):
        m = snapshot.save(conn, project, name=body.name, why=body.why, mode=snapshot.offered(body.mode), by="人")
        _logged(conn, "存档", f"{m['code']} {m['name']}", f"{m['mode']} · 复制 {m['copied_files']} 个文件（{snapshot._human(m['copied_bytes'])}）")
        return m

    @app.get("/api/checkpoints/{code}", tags=["存档"], summary="一档的详情：凭据、检查、复制了哪些")
    def ck_detail(code: str):
        return snapshot.detail(project, code)

    @app.get("/api/checkpoints/{code}/diff", tags=["存档"], summary="从这一档到现在（against=now）或到另一档：新加、改了、删了")
    def ck_diff(code: str, against: str = "now"):
        return snapshot.diff(project, code, against)

    @app.get("/api/checkpoints/{code}/file", tags=["存档"], summary="这一档里某个文件那时候的样子")
    def ck_file(code: str, path: str):
        target, got = snapshot.old_file(project, code, path)
        out = files.preview_path(target, path)
        out["from"] = got
        return out

    @app.get("/ckfiles/{code}/{path:path}", include_in_schema=False)
    def ck_raw(code: str, path: str, embed: int = 0):
        return _raw(snapshot.old_file(project, code, path)[0], embed)

    @app.post("/api/checkpoints/{code}/restore", tags=["存档"], summary="复活（整档或某些文件）：换下来的进回收站；没带 confirm 先返回警告")
    def ck_restore(code: str, body: RestoreIn, conn=Depends(get_conn)):
        r = snapshot.restore(conn, project, code, by="人", paths=body.paths, confirm=body.confirm, whole=body.whole,
                             builtin_revision=body.builtin_revision)
        if not r.get("nothing"):
            _logged(conn, "复活", code + (f"（{'、'.join(body.paths)}）" if body.paths else "（整档）"),
                    f"换回 {r['replaced']} · 放回 {r['restored']} · 挪进回收站 {r['trashed']}" + (f"（{r['trash_code']}）" if r["trash_code"] else ""))
        return r

    @app.post("/api/checkpoints/{code}/settle", tags=["存档"], summary="定性：人说这一档是安全点")
    def ck_settle(code: str, conn=Depends(get_conn)):
        m = snapshot.settle(conn, project, code, by="人")
        _logged(conn, "存档定性", f"{code} {m['name']}")
        return m

    @app.post("/api/checkpoints/{code}/remove", tags=["存档"], summary="删一档：挪进回收站；定性过的要人确认")
    def ck_remove(code: str, body: ConfirmIn, conn=Depends(get_conn)):
        r = snapshot.remove(conn, project, code, by="人", confirm=body.confirm)
        _logged(conn, "删存档", code, f"挪进了 {r['trash_code']}")
        return r

    @app.post("/api/modules/{name}/remove", tags=["设置"], summary="删模块：文件夹挪进回收站。空的直接做；有文件要人确认（confirm）")
    def module_remove(name: str, body: ConfirmIn, conn=Depends(get_conn)):
        r = store.remove_module(conn, project, name, by="人", confirm=body.confirm)
        _logged(conn, "删模块", name, f"文件夹挪进了回收站 {r['code']}" + (f"（{r['files']} 个文件）" if r["files"] else "（空的）"))
        return store.get_state(conn, project)

    @app.get("/api/auto", tags=["自动化"], summary="自动化页一次拿全：工作流、最近的运行（每一圈）、答疑记录、设置")
    def auto_all(conn=Depends(get_conn)):
        import claims
        import vcs
        return {"workflows": runs.list_workflows(project=project), "runs": runs.list_runs(project), "answers": answers.read(project),
                "settings": runs.settings(conn),
                "claims": claims.active(conn),                  # 谁在干什么（几个 agent 一起干时，自动化/协议.md）
                "paused": workorders.paused(conn),              # 人叫停过：agent 不自己开新单
                "agents": agents.roster(conn, project),          # 名册（作者 09-30：「得给agent注册」）
                "handovers": agents.handovers(project),
                # 总览（作者 10-01：「自动化也要有一个总览」）：agent 问你、还没拍板的；最近的动静
                "pending": [{"code": r["code"], "text": r["text"], "by": r["created_by"]} for r in store.list_pending(conn)],
                "recent": [{"at": r["at"][5:16].replace("T", " "), "who": r["actor"], "what": r["action"], "target": r["target"] or "",
                            "detail": r["detail"] or ""} for r in conn.execute(
                    "SELECT at, actor, action, target, detail FROM event WHERE action IN ('领了', '放手', '交付', '验收通过', '打回', "
                    "'改了档案', '叫停', '交给 agent', '跑完放下', '接着自动推进') OR action LIKE '报到%' OR action LIKE '建档案%' "
                    "ORDER BY id DESC LIMIT 12")],
                "supervise": supervise.listing(conn),           # 监管：网页自己看到的（10-01）
                "stuck": agents.stuck(conn, project),           # 卡住了往上报给谁（S1-8 S2-36）
                "plan": dispatch.plan_status(project),          # 离全自动还差什么（10-01：「要先和人一起规划，这个完毕之后才是全自动」）
                "git": vcs.log(project, 12)}                     # 本机 git 记账：谁、什么时候、交了哪件

    @app.get('/api/auto/workflows', tags=['自动化'], summary='本项目可编辑工作流与当前启用版本')
    def workflow_graphs():
        import workflow_graph
        return workflow_graph.list_all(project)

    @app.get('/api/auto/workflows/{code}', tags=['自动化'], summary='读取普通 W 文件、图与版本')
    def workflow_graph_read(code: str):
        import workflow_graph
        return workflow_graph.read(project, code)

    @app.post('/api/auto/workflows', tags=['写 · 人'], summary='保存工作流草稿；不启动员工')
    @app.put('/api/auto/workflows', tags=['写 · 人'], summary='修订工作流草稿；版本冲突不覆盖')
    def workflow_graph_save(body: dict, conn=Depends(get_conn)):
        import workflow_graph
        return workflow_graph.save(conn, project, str(body.get('code') or ''), str(body.get('name') or ''),
                                   body.get('graph'), str(body.get('revision') or ''), by='人')

    @app.post('/api/auto/workflows/validate', tags=['自动化'], summary='校验节点、条件、任务与员工绑定；只读')
    def workflow_graph_validate(body: dict):
        import workflow_graph
        return workflow_graph.validate(project, body.get('graph'))

    @app.post('/api/auto/workflows/dry-run', tags=['自动化'], summary='按真实记录演练路径；不认领、不派活')
    def workflow_graph_dry_run(body: dict, conn=Depends(get_conn)):
        import workflow_graph
        return workflow_graph.dry_run(conn, project, body.get('graph'))

    @app.post('/api/auto/workflows/{code}/control', tags=['写 · 人'], summary='明确启用已保存版本或停止流程；不打开自动化开关')
    def workflow_graph_control(code: str, body: dict, conn=Depends(get_conn)):
        import workflow_graph
        return workflow_graph.control(conn, project, code, str(body.get('action') or ''),
                                      str(body.get('revision') or ''), by='人')

    @app.get("/api/freeze", tags=["蓝图"], summary="离固化还差什么（S1-6 S2-12）：四条固化条件各一盏灯——定稿几块 · 接口和格式多久没改 · 跑完真论文没有 · 最近两周改了几次核心")
    def freeze_state(conn=Depends(get_conn)):
        return freeze.status(conn, project)

    @app.post("/api/freeze/paper", tags=["写 · 人"], summary="作者点「跑完了」：分好岗位的 agent 跑完一篇真论文（固化条件第三条）")
    def freeze_paper(body: PaperIn, conn=Depends(get_conn)):
        freeze.mark_paper(conn, body.done)
        return freeze.status(conn, project)

    def scan_view() -> dict:
        st, r = scanmap.state(project), scanmap.read_rules(project)
        return dict(SCAN, project=str(project.root), on=st["on"], busy=st["busy"],
                    hot=[{"area": a, "why": w} for a, w in sorted(st["hot"].items())],
                    dirty=[{"area": a, "n": n} for a, n in sorted(st["dirty"].items())],
                    next_sweep=max(0, round((st["next_sweep"] - time.time()) / 60)) if st["on"] else None,
                    sweep=r["sweep"], sweeps=list(scanmap.SWEEPS), rules=r["rules"], modes=list(scanmap.MODES),
                    builtin=scanmap.BUILTIN, file=scanmap.RULES_FILE)

    @app.get("/api/scan", tags=["设置"], summary="扫描（S1-8 S2-43 走到哪扫到哪）：正在盯着的片和为什么、记了有变动等走到再扫的、兜底几分钟、自定义规则、上一回扫了哪几片")
    def scan_state():
        return scan_view()

    @app.put("/api/scan", tags=["设置"], summary="改扫描：兜底几分钟、自定义规则（一直盯着 / 走到才扫 / 不看）；存进 自动化/扫描规则.md，马上生效")
    async def scan_put(body: ScanIn, conn=Depends(get_conn)):          # async：叫醒 watch 要在同一个循环里
        try:
            r = scanmap.write_rules(project, body.sweep, [x.model_dump() for x in body.rules])
        except ValueError as e:
            raise store.Refused(str(e)) from None
        _logged(conn, "改了扫描规则", scanmap.RULES_FILE, f"兜底每 {r['sweep']} 分钟 · " + ("、".join(f"{x['path']} {x['mode']}" for x in r["rules"]) or "没有自定义"))
        hub.poke.set()
        return scan_view()

    @app.get("/api/scan/dir", tags=["设置"], summary="设置 → 扫描那棵勾选的树：一个文件夹下面一层，每个带现在怎么扫、照的哪条（S1-8 S2-44）")
    def scan_dir(path: str = ""):
        try:
            return scanmap.children(project, path, scanmap.read_rules(project)["rules"])
        except ValueError as e:
            raise store.Refused(str(e)) from None

    @app.post("/api/scan/set", tags=["设置"], summary="勾上的几个一起设成 一直盯着 / 走到才扫 / 不看，或去掉自定义；存进 自动化/扫描规则.md，马上生效")
    async def scan_set(body: ScanSetIn, conn=Depends(get_conn)):
        try:
            scanmap.set_paths(project, body.paths, body.mode, " ".join(body.note.replace("|", "／").split()))
        except ValueError as e:
            raise store.Refused(str(e)) from None
        _logged(conn, "改了扫描规则", scanmap.RULES_FILE, ("、".join(body.paths[:8]) + (f" 等 {len(body.paths)} 个" if len(body.paths) > 8 else ""))
                + (f" 设成「{body.mode}」" if body.mode else " 去掉自定义"))
        hub.poke.set()
        return scan_view()

    @app.post("/api/scan/now", tags=["设置"], summary="现在扫这一片（记了有变动、等走到再扫的）")
    async def scan_now(body: ScanNowIn):
        hub.now.add(scanmap._norm(body.area))
        hub.poke.set()
        return {"ok": True}

    @app.put("/api/modules/{name}/info", tags=["设置"], summary="改模块的英文名、一句话（改名、删掉不在这：写进笔记交给 agent；扫描在 设置 → 扫描）")
    def module_info(name: str, body: ModuleInfoIn, conn=Depends(get_conn)):
        m = store.set_module_info(conn, name, by="人", en=body.en, one_line=body.one_line)
        _logged(conn, "改了模块设置", m["name"], f"英文名「{m['en']}」· 一句话「{m['one_line']}」")
        return m

    @app.put("/api/modules-order", tags=["设置"], summary="排第二栏的顺序（固定的三个永远在最前）")
    def module_order(body: OrderIn, conn=Depends(get_conn)):
        names = store.set_module_order(conn, project, body.names, by="人")
        _logged(conn, "改了模块顺序", " · ".join(names))
        return {"names": names}

    @app.put("/api/settings", tags=["自动化"], summary="改自动化设置：档位（0 手动 / 1 半自动 / 2 自动）、每次最多几圈")
    def settings_put(body: SettingsIn, conn=Depends(get_conn)):
        st = runs.set_settings(conn, body.level, body.rounds)
        _logged(conn, "改了自动化设置", f"档位 {st['level']} · 每次最多 {st['rounds']} 圈")
        return st

    # ---- 推送 ----

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        hub.clients.add(websocket)
        try:
            conn = store.connect(project.db_path)
            try:
                await websocket.send_json({"type": "hello", "v": store.version(conn), "ui": ui_version()})
            finally:
                conn.close()
            while True:                         # 网页报两件事：随堂笔记开没开、记到哪本（截图往哪去看这个）· 在看哪页（走到哪扫到哪）
                try:
                    m = json.loads(await websocket.receive_text())
                except ValueError:
                    continue
                if isinstance(m, dict) and m.get("type") == "note":
                    ui[websocket] = {"open": bool(m.get("open")), "scope": str(m.get("scope") or notebook.MAIN)[:40],
                                     "at": time.time()}
                elif isinstance(m, dict) and m.get("type") == "focus":   # 网页换页、切走切回（S1-8 S2-43）：那几片变热，有账的先扫
                    f = (str(m.get("view") or "")[:20], str(m.get("module") or "")[:80])
                    hub.focus[websocket] = f
                    hub.poke.set()
                    await websocket.send_json({"type": "focus", "areas": sorted(scanmap.focus_areas(project, *f)),
                                               "dirty": dict(scanmap.state(project)["dirty"])})
        except WebSocketDisconnect:
            pass
        finally:
            hub.clients.discard(websocket)
            ui.pop(websocket, None)
            if hub.focus.pop(websocket, None):
                hub.poke.set()

    return app


# ---------------------------------------------------------------- 启动

_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 开着系统代理（Clash 等）也别把本机请求送出去


def _already_running(port: int, project: Project) -> bool:
    try:
        with _NO_PROXY.open(f"http://127.0.0.1:{port}/api/ping", timeout=0.6) as r:
            info = json.loads(r.read().decode("utf-8"))
        return info.get("app") == APP_ID and info.get("root") == str(project.root)
    except Exception:
        return False


def _open_browser_when_ready(port: int, project: Project, stop: threading.Event, *,
                             timeout: float = 120.0, url: str | None = None) -> bool:
    """新项目初始化结束、当前项目真能接 HTTP 后才开网页；退出时取消，不靠固定秒数猜。"""
    url = url or f"http://127.0.0.1:{port}/"
    deadline = time.monotonic() + timeout
    while not stop.is_set():
        if _already_running(port, project):
            if stop.is_set():
                return False
            print(f"后台已就绪，打开网页：{url}")
            webbrowser.open(url)
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print(f"后台尚未就绪，暂未打开网页：{url}；请查看本窗口的启动错误或初始化进度，"
                  "准备好后可打开上面的网址。", file=sys.stderr)
            return False
        stop.wait(min(0.2, remaining))
    return False


def _start_browser_when_ready(port: int, project: Project, *, url: str | None = None) -> threading.Event:
    stop = threading.Event()
    threading.Thread(target=_open_browser_when_ready, args=(port, project, stop), kwargs={"url": url},
                     name="research-console-browser", daemon=True).start()
    return stop


def _running_port(project: Project, preferred: int) -> int | None:
    """这个项目的后端是不是已经开着了？开着就返回它的端口。

    先看 索引/server.json 记的端口（首选端口被别的程序占了时，它会退到后面的端口，
    只看首选端口就找不到它）；再看首选端口。
    """
    try:
        port = int(json.loads(_server_file(project).read_text(encoding="utf-8"))["port"])
        if _already_running(port, project):
            return port
    except Exception:
        pass
    return preferred if _already_running(preferred, project) else None


def _server_file(project: Project):
    return project.index_dir / "server.json"


def _bind(preferred: int) -> socket.socket:
    """先自己占住端口再交给 uvicorn——报出去的端口一定是真占到的那个。"""
    for port in [preferred, *range(preferred + 1, preferred + 30), 0]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):   # Windows：不许别人跟我们抢同一个端口
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            s.bind(("127.0.0.1", port))
            return s
        except OSError:
            s.close()
    raise RuntimeError("找不到空闲端口")


def _no_quick_edit() -> None:
    """Windows 黑窗口的「快速编辑」：在窗口里点一下，整个后端就停住，直到按回车——网页就刷不出来。关掉它。"""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-10)                       # 标准输入
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, (mode.value & ~0x40) | 0x80)   # 去掉快速编辑，保留其余
    except Exception:
        pass


def main() -> None:
    _no_quick_edit()
    for stream in (sys.stdout, sys.stderr):
        try:   # 逐行输出：输出被转进文件时也立刻看得见，不会攒在缓冲区里
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="自动化科研交互界面 · 后端")
    # 一份应用只管一个项目：项目就是应用自己这个文件夹（作者 2026-09-23：「左边项目是锁死的」）。
    # --project 只给自动测试用，不写进说明。
    ap.add_argument("--project", help=argparse.SUPPRESS)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"想用的端口，占用了会往后找（默认 {DEFAULT_PORT}）")
    ap.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    ap.add_argument("--no-reload", action="store_true", help="改了程序不自动重启（打包成安装包时用）")
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)       # 管家起的干活进程
    args = ap.parse_args()

    project = resolve(args.project)
    if args.child:
        _serve_child(project, args.port)
        return
    running = _running_port(project, args.port)
    if running:
        url = f"http://127.0.0.1:{running}/"
        print(f"已经开着了，直接打开：{url}")
        if not args.no_browser:
            webbrowser.open(url)
        return

    sock = _bind(args.port)
    port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    # 记下端口：再双击一次「启动.bat」时靠它找到这个，不会开出第二个
    sf = _server_file(project)
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps({"port": port, "pid": os.getpid(), "url": url}, ensure_ascii=False), encoding="utf-8")
    print("自动化科研交互界面 · 后台正在启动")
    print(f"  网页  {url}")
    print(f"  接口  {url}docs")
    print(f"  项目  {project.root}")
    print(f"  库    {project.db_path}")
    print("关掉这个窗口 = 关掉后端（网页会显示「没连后端」，数据都在库里不会丢）")

    if args.no_reload:
        app = create_app(project, global_keys=True, tasks=True)
        runner = lambda: uvicorn.Server(uvicorn.Config(app, log_level="warning", timeout_graceful_shutdown=2)).run(sockets=[sock])
    else:
        print("改了 backend/ 里的程序会自己重启；网页改了会自己刷新")
        sock.close()
        runner = lambda: _supervise(project, port)
    browser_stop = None
    try:
        if not args.no_browser:
            browser_stop = _start_browser_when_ready(port, project, url=url)
        runner()
    finally:
        if browser_stop:
            browser_stop.set()
        try:   # 正常退出就把记录删掉；直接关窗口删不掉也没关系——下次会 ping 一下确认它真活着
            if json.loads(sf.read_text(encoding="utf-8")).get("pid") == os.getpid():
                sf.unlink()
        except Exception:
            pass


# ---------------------------------------------------------------- 自动重启：一个小管家 + 一个干活的进程
# 作者 2026-09-27：「自动更新网页」。改了 backend/ 里的程序，管家停掉干活的、再起一个新的，端口不变；
# 网页那边收到新版本自己刷新。不用 uvicorn 自带的重启：它在 Windows 上靠发 Ctrl+C 停旧进程，
# 窗口不是普通控制台时发不到，旧进程就一直停不下来（实测踩过）。

def _code_stamp() -> dict:
    return {f.name: f.stat().st_mtime_ns for f in HERE.glob("*.py")}


def _supervise(project: Project, port: int) -> None:
    cmd = [sys.executable, str(HERE / "main.py"), "--child", "--port", str(port), "--project", str(project.root)]
    env = dict(os.environ, RC_PARENT_PID=str(os.getpid()))
    child = None
    try:
        while True:
            seen = _code_stamp()
            child = subprocess.Popen(cmd, env=env)
            changed = False
            while child.poll() is None:
                time.sleep(1)
                if _code_stamp() != seen:
                    changed = True
                    time.sleep(0.5)                          # 等编辑器把文件写完
                    print(f"{datetime.now():%H:%M:%S} backend/ 改了，后台重启……")
                    child.terminate()
                    child.wait(10)
                    break
            if changed:
                continue
            if child.returncode == 0:
                return
            print(f"{datetime.now():%H:%M:%S} 后台出错停了（退出码 {child.returncode}）：改好 backend/ 里的程序，它会自己再起")
            while _code_stamp() == seen:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if child and child.poll() is None:
            child.terminate()


def _watch_parent() -> None:
    """管家没了（窗口被强行关掉之类），干活的也跟着退出，不留在后台占着端口。"""
    pid = int(os.environ.get("RC_PARENT_PID") or 0)
    if not pid or sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    h = k.OpenProcess(0x00100000, False, pid)                 # SYNCHRONIZE
    if not h:
        os._exit(0)

    def wait() -> None:
        k.WaitForSingleObject(h, 0xFFFFFFFF)
        os._exit(0)
    threading.Thread(target=wait, daemon=True).start()


def _serve_child(project: Project, port: int) -> None:
    _watch_parent()
    for _ in range(40):                                        # 旧的刚停，端口可能还要一小会儿才放出来
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", port))
            break
        except OSError:
            sock.close()
            time.sleep(0.25)
    else:
        raise SystemExit(f"端口 {port} 一直被占着，起不来")
    app = create_app(project, global_keys=True, tasks=True)
    uvicorn.Server(uvicorn.Config(app, log_level="warning", timeout_graceful_shutdown=2)).run(sockets=[sock])


if __name__ == "__main__":
    main()
