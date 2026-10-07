"""网页终端（插件，S1-8 S2-47）：在网页里开 PowerShell 窗口，能看能打字，agent 就开在这里头。

作者 10-02「就不能在网页端展示这个吗？」选了「网页里直接嵌终端」；「我觉得你应该自己先做那个终端镶嵌的任务，这样好监管」。
- 一个小服务，核心在人点「打开」时把它跑起来（plugins.open_page），之后它自己活着：关了网页、核心重启，窗口都不停，回来接上
- 每个窗口一个 PowerShell（pywinpty 开的），最近的输出留着（约 40 万字符），新连上的先看到这些
- 只听 127.0.0.1；所有口子都要带令牌 ?t=（核心启动时给的，别的网页拿不到），WebSocket 还要从自己的页面连（看 Origin），
  所以别的网站没法偷偷连进来打命令
- 不启动 agent：窗口里跑什么是人在网页上点的（「开工」把那个 agent 的开工脚本打进去）
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import json
import re
import sys
import threading
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator

HERE = Path(__file__).parent
LIBS = (HERE / "lib", HERE.parent.parent / "工具库" / "下载" / "xterm")   # 画终端的 xterm.js：先找自己的 lib/，再找工具库里应用带的那份
KEEP = 400_000                                     # 每个窗口留多少字符，按完整输出块淘汰
SHELL = ["powershell.exe", "-NoLogo"]
NAME = "网页终端"
PROTOCOL = 2


class _Link:
    """每条连接只有一个发送队列，历史和实时输出按同一顺序送。"""

    def __init__(self, ws: WebSocket, structured: bool) -> None:
        self.ws, self.structured = ws, structured
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self.sender: asyncio.Task | None = None


class Term:
    """一个窗口：一个 PowerShell，读出来的字留一段、发给连着的网页。"""

    def __init__(self, title: str, cwd: str, cmd: str, loop: asyncio.AbstractEventLoop, spawn=None,
                 *, agent_code: str = "", task_key: str = "") -> None:
        if spawn is None:
            from winpty import PtyProcess
            spawn = PtyProcess.spawn
        self.id = uuid.uuid4().hex[:8]
        self.title, self.cwd, self.cmd = title, cwd, cmd
        self.project_root = str(Path(cwd).resolve())
        self.agent_code, self.task_key = agent_code, task_key
        self.cols, self.rows, self.seq = 120, 30, 0
        self.started = time.time()
        self.proc = spawn(SHELL, cwd=cwd, dimensions=(self.rows, self.cols))
        self.buf: collections.deque[str] = collections.deque()
        self.size = 0
        self.clients: dict[WebSocket, _Link] = {}
        self.loop = loop
        self.alive = True
        self.manual_closed = False
        threading.Thread(target=self._read, daemon=True).start()
        if cmd:
            self.proc.write(cmd + "\r\n")

    def _read(self) -> None:
        while True:
            try:
                data = self.proc.read(4096)
            except Exception:                           # EOF：PowerShell 退出了
                break
            if data:
                if not self._post(data):
                    break
            elif not self.proc.isalive():
                break
            else:
                time.sleep(0.02)
        self.alive = False
        self._post("\r\n\x1b[90m[这个窗口关了]\x1b[0m\r\n")

    def _post(self, data: str) -> bool:
        try:
            self.loop.call_soon_threadsafe(self._push, data)
            return True
        except RuntimeError:                            # 服务在退出：不用再发了
            return False

    def _push(self, data: str) -> None:
        self.seq += 1
        self.buf.append(data)
        self.size += len(data)
        while self.size > KEEP and len(self.buf) > 1:
            self.size -= len(self.buf.popleft())
        for link in list(self.clients.values()):
            self.offer(link, {"type": "output", "data": data, "seq": self.seq} if link.structured else data)

    def offer(self, link: _Link, message) -> None:
        try:
            link.queue.put_nowait(message)
        except asyncio.QueueFull:
            # 慢连接不能无限吃内存；断开后由页面重新取完整历史。
            self.clients.pop(link.ws, None)
            if link.sender:
                link.sender.cancel()
            asyncio.create_task(link.ws.close(code=1013))

    def attach(self, ws: WebSocket, *, structured: bool = False) -> _Link:
        """快照、排入历史、登记实时连接之间不 await，读线程的输出不会落在缝里。"""
        link = _Link(ws, structured)
        self.offer(link, {"type": "history", "data": self.history(), "seq": self.seq,
                          "cols": self.cols, "rows": self.rows} if structured else self.history())
        self.clients[ws] = link
        link.sender = asyncio.create_task(self._send(link))
        return link

    async def _send(self, link: _Link) -> None:
        try:
            while True:
                message = await link.queue.get()
                await link.ws.send_text(json.dumps(message, ensure_ascii=False) if link.structured else message)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.clients.pop(link.ws, None)
            try:
                await link.ws.close(code=1011)
            except Exception:
                pass

    def history(self) -> str:
        return "".join(self.buf)

    def write(self, text: str) -> None:
        if self.alive:
            self.proc.write(text)

    def resize(self, cols: int, rows: int) -> None:
        if not 20 <= cols <= 1000 or not 5 <= rows <= 500:  # 不理看不见时的量测和异常大尺寸
            return
        try:
            self.proc.setwinsize(max(rows, 2), max(cols, 10))
            self.cols, self.rows = cols, rows
            for link in list(self.clients.values()):
                if link.structured:
                    self.offer(link, {"type": "size", "cols": cols, "rows": rows})
        except Exception:
            pass

    def close(self) -> None:
        try:
            self.proc.terminate(force=True)
        except Exception:
            pass
        self.alive = False

    def view(self) -> dict:
        return {"id": self.id, "title": self.title, "alive": self.alive, "started": int(self.started),
                "cmd": self.cmd, "manual_closed": self.manual_closed, "cols": self.cols, "rows": self.rows,
                "agent_code": self.agent_code, "task_key": self.task_key, "project_root": self.project_root}


def request_employee_stop(cwd: str, title: str) -> bool:
    """网页人工关窗先给运行器停止信号，让它写交接；其他PowerShell仍直接关闭。"""
    found = re.match(r'^(G\d+)\s', title)
    if not found:
        return False
    backend = str(HERE.parent.parent / 'backend')
    if backend not in sys.path:
        sys.path.insert(0, backend)
    import agents, autolaunch, journal, store
    from project import Project
    p = Project(Path(cwd).resolve())
    try:
        a = agents.get(p, found[1])
    except store.Refused:
        return False
    autolaunch.write_runner_state(p, a['code'], 'stopped', stop_requested=True, reason='人在网页关了员工窗口', by='人')
    c = store.connect(p.db_path)
    try:
        journal.add(c, p, f"关了员工窗口 {a['code']}；恢复自动化前不重开", by='人', kind='叫停员工', scope='自动化')
    finally:
        c.close()
    return True


class NewIn(BaseModel):
    title: str = "窗口"
    cmd: str = ""
    agent_code: str = Field(default="", max_length=40, pattern=r"^(?:G\d+)?$")
    task_key: str = Field(default="", max_length=300)
    project_root: str = Field(default="", max_length=2000)

    @field_validator("task_key", "project_root")
    @classmethod
    def clean_metadata(cls, value: str) -> str:
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError("窗口关联不能含控制字符")
        return value.strip()


def create(token: str, port: int, cwd: str, spawn=None) -> FastAPI:
    """spawn：测试用，换掉真的 PowerShell。"""
    app = FastAPI(title=NAME, docs_url=None, redoc_url=None, openapi_url=None)
    terms: dict[str, Term] = {}
    origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def need(t: str | None) -> None:
        if t != token:
            raise HTTPException(403, "令牌不对：从应用里打开这一页")

    @app.get("/ping")
    def ping(t: str | None = None):
        need(t)
        return {"app": NAME, "terms": len(terms), "protocol": PROTOCOL,
                "capabilities": {"watch": True, "structured": True}}

    @app.get("/", response_class=HTMLResponse)
    def page(t: str | None = None):
        need(t)
        return HTMLResponse((HERE / "index.html").read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

    @app.get("/lib/{name}")
    def lib(name: str):
        f = next((d / name for d in LIBS if (d / name).is_file()), None)
        if "/" in name or "\\" in name or f is None:
            raise HTTPException(404, "没有")
        return FileResponse(f)

    @app.get("/api/terms")
    def listing(t: str | None = None):
        need(t)
        return {"items": [x.view() for x in terms.values()]}

    @app.post("/api/terms")
    async def new(body: NewIn, t: str | None = None):
        need(t)
        if body.project_root and Path(body.project_root).resolve() != Path(cwd).resolve():
            raise HTTPException(403, "窗口关联的项目与终端服务不一致")
        x = Term(" ".join(body.title.split())[:40] or "窗口", cwd, body.cmd.strip(), asyncio.get_running_loop(), spawn,
                 agent_code=body.agent_code, task_key=body.task_key)
        terms[x.id] = x
        return x.view()

    @app.post("/api/terms/{tid}/close")
    def close(tid: str, t: str | None = None):
        need(t)
        x = terms.get(tid)
        if x is None:
            raise HTTPException(404, "没有这个窗口")
        x.manual_closed = True
        if request_employee_stop(cwd, x.title):
            threading.Timer(8, x.close).start()
        else:
            terms.pop(tid, None)
            x.close()
        return {"ok": True}

    @app.post("/quit")
    def quit_(t: str | None = None):
        """应用里点「关掉网页终端」：所有窗口一起关，服务退出。"""
        need(t)
        for x in terms.values():
            x.close()
        threading.Timer(0.3, lambda: __import__("os")._exit(0)).start()
        return {"ok": True}

    @app.websocket("/ws/{tid}")
    async def ws(websocket: WebSocket, tid: str, t: str | None = None, view: str = "", v: str = ""):
        origin = websocket.headers.get("origin")
        x = terms.get(tid)
        if t != token or (origin and origin not in origins) or x is None:
            await websocket.close(code=4403)
            return
        await websocket.accept()
        readonly, structured = view == "1", v == "2"
        link = x.attach(websocket, structured=structured)
        try:
            while True:
                try:
                    m = json.loads(await websocket.receive_text())
                except ValueError:
                    continue
                if not isinstance(m, dict):
                    continue
                if readonly and ("i" in m or "r" in m):
                    if structured:
                        x.offer(link, {"type": "denied", "operation": "input" if "i" in m else "resize", "reason": "watch-only"})
                    continue
                if "i" in m:
                    x.write(str(m["i"]))
                elif "r" in m:
                    dims = m["r"]
                    if isinstance(dims, list) and len(dims) == 2 and all(isinstance(n, int) and not isinstance(n, bool) for n in dims):
                        x.resize(dims[0], dims[1])
                elif m.get("type") == "ping" and structured:
                    x.offer(link, {"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            x.clients.pop(websocket, None)
            if link.sender:
                link.sender.cancel()
                try:
                    await link.sender
                except asyncio.CancelledError:
                    pass

    @app.on_event("shutdown")
    def bye():
        for x in terms.values():
            x.close()

    return app


def main() -> None:
    ap = argparse.ArgumentParser(description=NAME)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--cwd", required=True, help="新窗口从哪个文件夹开（项目根）")
    a = ap.parse_args()
    uvicorn.run(create(a.token, a.port, a.cwd), host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
