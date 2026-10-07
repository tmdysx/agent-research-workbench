"""网页员工的外层运行器：真实 MCP 领动作，非交互 Codex 每次只做一轮。

等待审核时只由这个 Python 进程检查记录，不启动模型。所有持久状态、交接和放手
都通过项目 MCP 写入；本文件不直接改治理记录或运行状态文件。
"""
from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

import agents
import store
from project import CODE_DIR, Project, resolve

ACTIVE = {"execute", "submit_plan", "review_plan", "review_delivery", "review_draft", "draft", "pick_fruit", "write_digest", "write_rewrite", "review_rewrite"}
STATE_DIR = Path("自动化") / "运行状态"
TERMINAL = {"stopped", "limit", "failed"}
COORDINATION_CLAIMS = {"核心", "施工审核", "审核", "验收"}
STATE_FIELDS = {"pid", "session", "rounds", "cycles", "failure_counts", "blocked", "current", "last_result", "status", "reason", "action"}
_INTERRUPTED = False


@dataclass
class Outcome:
    returncode: int
    output: str = ""
    stopped: str = ""


def load_state(p: Project, key: str) -> dict:
    """可直接读普通文件；写入只能经过 report_employee_runtime。"""
    import autolaunch
    return autolaunch.runner_state(p, key)


def local_stop_reason(p: Project, key: str) -> str:
    """检查模型进程外的暂停信号；只读数据库，避免 MCP 拥塞妨碍停止。"""
    if _INTERRUPTED:
        return "运行窗口收到停止信号"
    a = agents.find(p, key)
    if not a:
        return "员工档案已移除"
    if a.get("paused"):
        return "员工已暂停"
    runtime = load_state(p, key)
    if runtime.get('stop_requested'):
        return '人在网页关了员工窗口'
    current = runtime.get('current') if isinstance(runtime.get('current'), dict) else {}
    flow = current.get('workflow') or {}
    if isinstance(flow, dict) and flow.get('code'):
        target = current.get('task') or current.get('construction_plan') or current.get('review') or {}
        if target.get('goal') and target.get('sub'):
            import workflow_graph
            try:
                active = workflow_graph.metadata(p, target['goal'], target['sub'])
            except (OSError, ValueError, store.Refused):
                return '流程状态无法核对，停止当前模型轮次'
            if not active or active.get('stopped') or active.get('revision') != flow.get('revision'):
                return '流程已停用或启用版本已更换，停止当前模型轮次'
    if p.db_path.is_file():
        try:
            with sqlite3.connect(p.db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1) as c:
                row = c.execute("SELECT value FROM meta WHERE key='auto_paused'").fetchone()
                if row and row[0]:
                    return str(row[0])
        except sqlite3.Error:
            pass
    return ""


@contextmanager
def singleton(p: Project, name: str):
    """本机同一项目同一员工只准一个运行器，不需要写锁文件。"""
    identity = str(p.root.resolve()).casefold() + "\0" + agents.short(name)
    port = 35000 + int(hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8], 16) % 20000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
    except OSError as e:
        sock.close()
        raise RuntimeError("这个项目的该员工运行器已经在运行，或本机锁端口不可用") from e
    try:
        yield
    finally:
        sock.close()


def action_key(action: dict) -> str:
    kind = action.get("action", "idle")
    task = action.get("task") or {}
    if task:
        return f"{kind}:{task.get('goal', '')}:{task.get('sub', '')}"
    record = action.get("construction_plan") or action.get("fruit") or action.get("review") or action.get("draft") or action.get("plan") or {}
    if action.get("digest"):
        record = {"code": action["digest"].get("key", "")}
    if action.get("rewrite"):
        record = {"code": action["rewrite"].get("rel", "")}
    if action.get("rewrite_review"):
        record = {"code": action["rewrite_review"].get("code", "")}
    if kind == "draft" and isinstance(record, dict):
        record = record.get("draft") or record.get("row") or record
    return f"{kind}:{record.get('code', '')}"


def fingerprint(action: dict) -> str:
    record = action.get("construction_plan") or action.get("fruit") or action.get("review") or action.get("draft") or action.get("plan") or {}
    relevant = {"key": action_key(action), "revision": record.get("revision"), "state": record.get("state"),
                "body": record.get("text") or record.get("body"), "workflow": action.get("workflow")}
    return hashlib.sha256(json.dumps(relevant, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def action_prompt(p: Project, name: str, action: dict) -> str:
    kind = action.get("action")
    instructions = {
        "submit_plan": "阅读任务与需求，调用submit_execution_plan提交施工计划；已有打回计划就带原revision修订同一份。写清为了哪条需求、守哪些戒律、工具、文件范围、修改办法和验收。提交后退出，不能施工。",
        "execute": "先读取get_execution_plan检查已批准的完整正文和文件范围。按计划施工；改核心先claim_task('核心')拿锁（拿锁时照设置自动存档；设置里关了就自己save_checkpoint）；不得修改批准范围以外的文件。照验收步骤实际检查，改核心用add_log记『改了核心』，然后deliver交付真实结果。未验过或失败的检查如实填写。",
        "review_plan": "使用get_execution_plan读取待审施工计划。核对目标、需求、戒律、文件范围与验收可执行性；调用review_execution_plan带原revision通过或打回，说明具体理由。不能审自己的计划，不施工、不改变方向。",
        "review_delivery": "独立复跑这张交付单的检查；阅读产物、实际观察结果，调用review_delivery通过或打回并写清证据。不能验自己的交付，不替施工员改东西。",
        "review_draft": "阅读这张别人写的草稿，核对人的需求、来源和验收；通过review_draft审核或打回，并给具体理由。不能自审，不施工。",
        "draft": "按返回的规划工作起草或修订草稿，只调用propose_draft写候选，不擅自改变方向文件。",
        "write_digest": "这是一件写摘要的活：照材料里 ask 的要求，只根据材料里给的日志、交付、交接、总摘要写，每句写出处，不编；写好调用write_digest(kind, key, text)。不改别的文件。",
        "write_rewrite": "这是一件写重写单的活：读那份正本全文，合并重复、去掉过时的、把抄来的换成指向原处，只写现在有效的；调用propose_rewrite(path, text, changes)出单，每处写清改了什么、合并或去掉的出处、为什么。不改别的文件，不自己换上。",
        "review_rewrite": "这是一张别人出的重写单：逐处核对对照——合并或去掉的出处是不是真的、有没有删掉现在还有效的规矩、改后读起来对不对；行就review_rewrite(code, true, why)换上，不行就review_rewrite(code, false, why)写清哪里不对。不审自己出的，不改别的文件。",
        "pick_fruit": "这是一张比较单：同一件在几根世界树的枝上各做了一版（只有一根就是验收它）。逐根看果实——demo说明、检查，用branch_changes看改动，能的话进枝的文件夹跑测试；挑最好的一根调用pick_fruit(code, branch, why)合回，都不行就pick_fruit(code, '', why)打回并写清哪里不对。不能挑自己做的，不替施工员改东西。",
    }
    return (
        f"你是网页终端员工 {name}，项目根是 {p.root.resolve().as_posix()}。MCP已经固定绑定这个项目和名字，agent参数只能写{name}。\n"
        f"先在本轮MCP连接调用register_agent(name='{name}', program='Codex')接回本人档案，再读AGENTS.md、项目自带技能和my_profile。只做下面给定的一项动作，不自行领下一件，不启动任何其他agent。\n"
        f"本轮动作：{kind}。{instructions.get(kind, '')}\n"
        "所有记录通过research-console MCP写入。人的笔记只读。审核/交付完成后记录本轮结果并退出，外层运行器负责下一轮。\n"
        "待审、已暂停、无活、工具不可用或需要人的新决定时直接退出并写实际原因；不sleep、不循环等审核，不编成功。\n"
        "下面是MCP返回的真实任务、计划、适用范围和验收资料，按其原文执行：\n"
        + json.dumps({k: v for k, v in action.items() if k != "runtime"}, ensure_ascii=False, indent=2)
    )


async def call(session, name: str, arguments: dict | None = None, *, structured: bool = False):
    result = await session.call_tool(name, arguments or {})
    text = "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")
    if getattr(result, "isError", False):
        raise RuntimeError(f"MCP {name}：{text}")
    if structured:
        try:
            value = json.loads(text)
        except ValueError as e:
            raise RuntimeError(f"MCP {name} 没有返回结构化记录：{text[:200]}") from e
        if not isinstance(value, dict):
            raise RuntimeError(f"MCP {name} 返回的记录不是对象")
        return value
    return text


async def stop_process(process):
    """先终止模型，再清理它启动的子进程；随后由 MCP 留交接及释放认领。"""
    if process.returncode is not None:
        return
    if os.name == "nt":
        # Windows 终端关停必须包含子进程，否则可遗留正在修改文件的 shell。
        result = await anyio.run_process(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode and process.returncode is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    with anyio.move_on_after(5):
        await process.wait()
    if process.returncode is None:
        process.kill()
        await process.wait()


async def run_codex(p: Project, name: str, action: dict, *, poll_seconds: float = 2,
                    max_seconds: float = 2700, stop_check=local_stop_reason, command=None) -> Outcome:
    argv = command if command is not None else agents.codex_command(p, name, action_prompt(p, name, action))
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    process = await anyio.open_process(argv, cwd=str(p.root), stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **options)
    output, reason, started = [], "", time.monotonic()

    async def copy_output():
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        async for chunk in process.stdout:
            text = decoder.decode(chunk)
            if text:
                print(text, end="", flush=True)
                output.append(text)
                if sum(map(len, output)) > 24000:
                    output[:] = ["".join(output)[-16000:]]

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(copy_output)
            while process.returncode is None:
                reason = stop_check(p, name)
                if reason:
                    await stop_process(process)
                    break
                if time.monotonic() - started >= max_seconds:
                    reason = "单轮运行超时"
                    await stop_process(process)
                    break
                with anyio.move_on_after(poll_seconds):
                    await process.wait()
            code = await process.wait()
        return Outcome(code, "".join(output)[-16000:], reason)
    finally:
        if process.returncode is None:
            with anyio.CancelScope(shield=True):
                await stop_process(process)
        await process.aclose()


async def release_all(session, name: str, holding: list[dict], reason: str, *, preserve_work: bool = False):
    pairs = {(r.get("goal", ""), r.get("sub", "")) for r in holding
             if not preserve_work or r.get("goal") in COORDINATION_CLAIMS}
    pairs.add(("核心", ""))
    for goal, sub in pairs:
        if goal:
            await call(session, "release_task", {"goal": goal, "sub": sub, "note": reason, "agent": name})


def handover_text(state: dict, reason: str, *, status: str = "", result_summary: str = "") -> str:
    current = state.get("current") if isinstance(state.get("current"), dict) else {}
    task = current.get("task") or {}
    files = (current.get("construction_plan") or {}).get("files") or []
    status = status or state.get("status", "")
    waiting = status == "waiting" or (status == "idle" and any(
        r.get('goal') not in COORDINATION_CLAIMS for r in current.get('holding', []) if isinstance(r, dict)))
    result_summary = result_summary or ("最近运行结果见员工运行状态；业务验收以交付单为准"
                                       if state.get("last_result") else "没有启动模型；未做业务检查")
    unfinished = ("施工任务尚未完成，认领已保留；" if waiting else "本次已放手，未完成任务可由符合岗位的员工接续；") + reason
    risk = ("审核、验收或锁释放尚未完成，不视为交付通过；接续先读最新计划和交付。" if waiting
            else "未完成的动作不视为成功；接续先核对实际文件、最新计划及交付。")
    next_step = ("审核、验收或锁释放后由next_action接续原任务。" if waiting
                 else "由next_action读取真实状态后接续；停止或达到上限需人明确恢复。")
    human = "连续失败事项已留在待判断区：" + "；".join(state.get("blocked") or []) if state.get("blocked") else (
        "没有新增需要人判断的事项；当前等待相应员工审核、验收或锁释放。" if waiting else
        "本次运行已停止或达到限制；是否恢复由人决定。" if status in TERMINAL else "本轮没有新增需要人判断的事项。")
    return "\n".join([
        f"- 做了什么：网页员工外层运行器已执行 {state.get('rounds', 0)} 轮；最近动作 {state.get('action', '')}，任务 {task.get('goal', '')} {task.get('sub', '')}。",
        "- 改了哪些文件：允许范围 " + ("、".join(files) or "见各轮施工计划及交付单；运行器不代写业务文件"),
        "- 验了什么、实际结果：" + result_summary,
        "- 没做完的：" + unfinished,
        "- 没验证的和有风险的：" + risk,
        "- 下一步建议：" + next_step,
        "- 等人定的事：" + human,
    ])


async def drive(session, p: Project, name: str, *, poll_seconds: float = 5, idle_seconds: float = 600,
                execute=run_codex, stop_check=local_stop_reason, state_loader=load_state) -> dict:
    await call(session, "register_agent", {"name": name, "program": "Codex"})
    state = dict(state_loader(p, name))
    state |= {"pid": os.getpid(), "session": str(time.time_ns()), "rounds": int(state.get("rounds") or state.get("cycles") or 0),
              "failure_counts": dict(state.get("failure_counts") or {}), "blocked": list(state.get("blocked") or [])}
    current = state.get("current") if isinstance(state.get("current"), dict) else {}
    holding, idle_since, next_ = current.get("holding") or [], None, None
    result_summary = ""

    async def report(status, reason=""):
        state.update(status=status, reason=reason, cycles=state["rounds"])
        fresh = await call(session, "report_employee_runtime", {"state": {k: v for k, v in state.items() if k in STATE_FIELDS}, "agent": name}, structured=True)
        state.update(fresh)
        print(f"\n[{name}] {status} · {reason}", flush=True)

    async def finish(status, reason):
        await release_all(session, name, holding, reason, preserve_work=status in ("waiting", "idle"))
        await call(session, "write_handover", {"text": handover_text(state, reason, status=status, result_summary=result_summary), "agent": name})
        await report(status, reason)
        return state

    # 关窗再开不会清空预算或连续失败；只有网页恢复入口可以重置。
    if state.get("status") in TERMINAL:
        holding = (state.get("current") or {}).get("holding", []) if isinstance(state.get("current"), dict) else []
        return await finish(state["status"], state.get("reason") or "请先在网页恢复员工")
    try:
        while True:
            stopped = stop_check(p, name)
            if stopped:
                return await finish("stopped", stopped)
            action = next_ if next_ is not None else await call(session, "next_action", {"agent": name}, structured=True)
            next_ = None
            if "holding" in action:
                holding = action.get("holding") or []
            kind = action.get("action", "idle")
            state.update(action=kind, current={k: v for k, v in action.items() if k != "runtime"})
            state['current']['holding'] = list(holding)
            if kind == "stopped":
                return await finish("stopped", action.get("reason") or "项目已停止")
            limits = action.get("limits") or {}
            maximum = max(1, int(limits.get("rounds") or 5))
            if state["rounds"] >= maximum:
                return await finish("limit", f"本次运行已到 {maximum} 轮上限")
            key = action_key(action)
            if kind not in ACTIVE or key in state["blocked"]:
                if idle_since is None:
                    idle_since = time.monotonic()
                reason = action.get("reason") or ("这件已连续失败，等待换一件" if key in state["blocked"] else "现在没有可执行动作")
                status = "waiting" if kind == "waiting" else "idle"
                if state.get("status") != status or state.get("reason") != reason:
                    await report(status, reason)
                if time.monotonic() - idle_since >= idle_seconds:
                    # 等待退出保留施工任务；核心/审核/验收锁放手，不占着阻挡其他员工。
                    return await finish(status, reason)
                await anyio.sleep(poll_seconds)
                continue
            idle_since = None
            state["rounds"] += 1
            await report("running", f"执行第 {state['rounds']} 轮：{key}")
            before = fingerprint(action)
            try:
                outcome = await execute(p, name, action)
            except Exception as e:
                outcome = Outcome(1, f"启动或运行失败：{type(e).__name__}: {e}")
            idle_since = time.monotonic()  # 模型施工耗时不算进随后等待审核的时间。
            result_summary = f"本轮动作 {key}；模型退出码 {outcome.returncode}。业务验收结果见交付单。"
            state["last_result"] = outcome.output[-4000:] or f"模型进程退出码 {outcome.returncode}"
            if outcome.stopped:
                status = "failed" if outcome.stopped == "单轮运行超时" else "stopped"
                return await finish(status, outcome.stopped)
            next_ = await call(session, "next_action", {"agent": name}, structured=True)
            holding = next_.get("holding") or []
            progress = outcome.returncode == 0 and fingerprint(next_) != before
            if progress:
                result_summary += " MCP动作状态已有进展。"
                state["failure_counts"].pop(key, None)
                await report("running", f"本轮有实际状态进展：{key}")
                continue
            state["failure_counts"][key] = int(state["failure_counts"].get(key) or 0) + 1
            result_summary += " MCP动作状态没有完成本轮进展。"
            limit = max(1, int(limits.get("failures") or 2))
            count = state["failure_counts"][key]
            if count >= limit:
                state["blocked"].append(key)
                reason = f"{key} 连续 {count} 次没有完成动作；退出码 {outcome.returncode}"
                await release_all(session, name, holding, reason)
                holding = []
                await call(session, "ask_human", {"question": reason + "。已跳过，请查看运行结果后决定是否恢复。",
                           "checked": "已按返回的施工计划/任务尝试并检查MCP实际状态；没有编造完成"})
                await report("running", reason)
                next_ = None  # 下一次 MCP 按持久 blocked 过滤，继续其他件。
            else:
                await report("running", f"{key} 失败 {count}/{limit}，下一轮修正")
    except BaseException as e:
        # 连接异常时尽力放手和留交接；不能靠文件绕过 MCP 伪造记录。
        with anyio.CancelScope(shield=True):
            try:
                await finish("failed", f"运行器异常：{type(e).__name__}: {e}")
            except Exception:
                pass
        raise


async def main_async(p: Project, name: str, poll_seconds: float, idle_seconds: float):
    params = StdioServerParameters(command=sys.executable,
        args=[str(CODE_DIR / "backend" / "mcp_server.py"), "--project", str(p.root.resolve()), "--agent", name, '--runner-control'])
    with singleton(p, name):
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, client_info=Implementation(name=name, version="1")) as session:
                await session.initialize()
                required = {"next_action", "report_employee_runtime", "write_handover", "register_agent", "release_task"}
                offered = {t.name for t in (await session.list_tools()).tools}
                if required - offered:
                    raise RuntimeError("项目MCP缺少运行器接口：" + "、".join(sorted(required - offered)))
                await drive(session, p, name, poll_seconds=poll_seconds, idle_seconds=idle_seconds)


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="网页员工外层运行器")
    ap.add_argument("--project", required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--poll-seconds", type=float, default=5)
    ap.add_argument("--idle-seconds", type=float, default=600)
    args = ap.parse_args()
    if not 0.1 <= args.poll_seconds <= 60 or args.idle_seconds < 0:
        ap.error("检查间隔要在0.1–60秒之间，空闲等待不能是负数")
    p = resolve(args.project)
    a = agents.get(p, args.agent)
    if "codex" not in a.get("program", "").lower():
        ap.error("这个运行器只接Codex员工")
    def interrupted(signum, frame):
        global _INTERRUPTED
        _INTERRUPTED = True
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    anyio.run(main_async, p, a["name"], args.poll_seconds, args.idle_seconds)


if __name__ == "__main__":
    main()
