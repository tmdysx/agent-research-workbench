"""后台任务表：几个 agent 各在跑什么——从各家 agent 存在这台电脑上的会话记录里读（只读，不改，不上传）。

作者 2026-10-01：「我希望，网页端能有这样的表」（Claude 桌面版的 Background tasks：谁在跑、跑了多久、模型、
token、调了几次工具、现在在干嘛、看全过程）；「做后台任务表吧」。
- 读两家：Claude Code（`~/.claude/projects/**/*.jsonl`，子 agent 在 `<会话>/subagents/` 下，旁边的 .meta.json 写着任务名、
  是不是被人停了）· Codex（`~/.codex/sessions/年/月/日/rollout-*.jsonl`）
- 一份会话算谁的：它自己报到（register_agent）报的名字；没报到、但调本项目接口时写了 agent 的，用那个名字。
  认不出是谁的不算——别的项目、闲聊都不进这张表
- 只看最近 3 天改过的记录；读过的记下读到哪，文件长了只读新的那段（主会话一份能有几十 MB）
- 状态：在跑（3 分钟内有动静）· 停了（没说做完、也没动静了；人停的写「被人停了」）· 做完（这一轮说完了）
- 别家没有会话记录、或格式不认得：名册照样有，只是少了模型、token 这几项（项-3 不绑死某一家）
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

SOURCES: dict | None = None    # 测试用：直接给哪几个文件夹；平常是 None，照 sources() 找
KINDS = (("Claude Code", "CLAUDE_CONFIG_DIR", ".claude", "projects"), ("Codex", "CODEX_HOME", ".codex", "sessions"))
DAYS = 3                       # 只看最近几天改过的记录
RUNNING = 3 * 60               # 几秒内有动静算在跑
KEEP = 400                     # 每份会话留最近几条给「看全过程」
SERVER = "research-console"    # 本项目接口的名字
_STATE: dict[str, dict] = {}   # 路径 → 读到哪、算出来的
_LOCK = threading.Lock()

ACTION = {"Bash": "在跑命令", "PowerShell": "在跑命令", "Read": "在读文件", "Write": "在写文件", "Edit": "在改文件",
          "NotebookEdit": "在改文件", "Grep": "在找", "Glob": "在找", "WebFetch": "在上网查", "WebSearch": "在上网查",
          "Agent": "在开子 agent", "Task": "在开子 agent", "TodoWrite": "在列待办", "Skill": "在读技能"}


def sources() -> dict[str, Path]:
    """各家的会话记录在哪：本机设置里填过的 → 那家自己的环境变量（CLAUDE_CONFIG_DIR、CODEX_HOME）→ 用户目录下的默认位置。
    不写死哪台电脑的路径（作者 10-01：「用户的文件目录跟我的可不一样」）。"""
    if SOURCES is not None:
        return dict(SOURCES)
    import machine
    out = {}
    for kind, env, home, sub in KINDS:
        set_ = machine.get("sessions", kind)
        base = Path(os.environ[env]) if os.environ.get(env) else Path.home() / home
        out[kind] = Path(set_) if set_ else base / sub
    return out


def _ts(s: str) -> float:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _short(v, n: int = 160) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "…"


def model_name(m: str) -> str:
    """「claude-opus-5-5」→「Opus 5.5」；别的照原样。"""
    x = re.match(r"claude-([a-z]+)-(\d+)-(\d+)", m or "")
    return f"{x.group(1).title()} {x.group(2)}.{x.group(3)}" if x else (m or "")


_REG = re.compile(r"register_agent['\"]?\s*,?\s*'?\{[^{}]*?\"name\"\s*:\s*\"([^\"]+)\"")
_AGENT = re.compile(r"rc\.py\s+\w+\s+'\{[^{}]*?\"agent\"\s*:\s*\"([^\"]+)\"")


def _who(s: dict, name: str = "", agent: str = "") -> None:
    """记下这份会话是谁的：报到报的名字优先；调接口时写的 agent 只在没报到时用。"""
    if name and not s.get("reg"):
        s["reg"] = name
    if agent:
        s["agent_seen"] = s.get("agent_seen") or agent


def _event(s: dict, at: float, who: str, text: str) -> None:
    s["events"].append({"at": at, "who": who, "text": text})
    if len(s["events"]) > KEEP:
        del s["events"][: len(s["events"]) - KEEP]


def _claude_line(s: dict, d: dict) -> None:
    at = _ts(d.get("timestamp"))
    s["first"] = s["first"] or at
    s["last"] = max(s["last"], at)
    m = d.get("message") or {}
    if d.get("type") == "assistant":
        s["model"] = m.get("model") or s["model"]
        u = m.get("usage") or {}
        if u:
            s["tokens"] = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
        s["done"] = m.get("stop_reason") == "end_turn"
        for b in m.get("content") or []:
            if b.get("type") == "text" and b.get("text", "").strip():
                _event(s, at, "它", b["text"].strip()[:2000])
            elif b.get("type") == "tool_use":
                name, inp = b.get("name", ""), b.get("input") or {}
                s["tools"] += 1
                if name.startswith("mcp__"):
                    tool = name.split("__")[-1]
                    s["action"] = f"在调接口：{tool}"
                    if SERVER.replace("-", "_") in name.replace("-", "_"):
                        _who(s, inp.get("name", "") if tool == "register_agent" else "", inp.get("agent", ""))
                else:
                    s["action"] = ACTION.get(name, f"在用 {name}")
                    target = inp.get("file_path") or inp.get("notebook_path")
                    if name in ("Edit", "Write", "NotebookEdit", "MultiEdit") and isinstance(target, str):
                        s["edits"].append((at, target))          # 监管用：这个文件是谁改的
                        del s["edits"][:-300]
                    cmd = inp.get("command") if isinstance(inp.get("command"), str) else ""
                    if cmd:
                        r, a = _REG.search(cmd), _AGENT.search(cmd)
                        _who(s, r.group(1) if r else "", a.group(1) if a else "")
                _event(s, at, "用", f"{name} · {_short(inp)}")
    elif d.get("type") == "user":
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            s["title"] = s["title"] or _short(c, 60)
            _event(s, at, "人", c.strip()[:2000])
            s["done"] = False
        elif isinstance(c, list):
            for b in c:
                if b.get("type") == "tool_result":
                    r = b.get("content")
                    r = " ".join(x.get("text", "") for x in r if isinstance(x, dict)) if isinstance(r, list) else r
                    _event(s, at, "结果", _short(r or "", 300))
                elif b.get("type") == "text" and b.get("text", "").strip():
                    s["title"] = s["title"] or _short(b["text"], 60)
                    _event(s, at, "人", b["text"].strip()[:2000])


def _codex_line(s: dict, d: dict) -> None:
    at = _ts(d.get("timestamp"))
    s["first"] = s["first"] or at
    s["last"] = max(s["last"], at)
    p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
    t = d.get("type")
    if t == "turn_context":
        s["model"] = p.get("model") or s["model"]
    elif t == "event_msg":
        k = p.get("type")
        if k == "token_count":
            s["tokens"] = int(((p.get("info") or {}).get("total_token_usage") or {}).get("total_tokens") or s["tokens"])
        elif k == "task_complete":
            s["done"] = True
        elif k == "task_started":
            s["done"] = False
        elif k == "item_completed":
            it = p.get("item") or {}
            kind = it.get("type")
            if kind == "McpToolCall":
                s["tools"] += 1
                s["action"] = f"在调接口：{it.get('tool', '')}"
                args = it.get("arguments") or {}
                if it.get("server") == SERVER:
                    _who(s, args.get("name", "") if it.get("tool") == "register_agent" else "", args.get("agent", ""))
                _event(s, at, "用", f"{it.get('server')}.{it.get('tool')} · {_short(args)}")
            elif kind == "CommandExecution":
                s["tools"] += 1
                s["action"] = "在跑命令"
                cmd = it.get("command")
                _event(s, at, "用", "命令 · " + _short(cmd[-1] if isinstance(cmd, list) and cmd else cmd))
            elif kind in ("FileChange", "PatchApply"):
                s["tools"] += 1
                s["action"] = "在改文件"
                _event(s, at, "用", "改文件 · " + _short(it, 200))
            elif kind == "AgentMessage":
                text = " ".join(x.get("text", "") for x in it.get("content") or [] if isinstance(x, dict)).strip()
                if text:
                    _event(s, at, "它", text[:2000])
            elif kind == "UserMessage":
                text = " ".join(x.get("text", "") for x in it.get("content") or [] if isinstance(x, dict)).strip()
                if text:
                    s["title"] = s["title"] or _short(text, 60)
                    _event(s, at, "人", text[:2000])


def _new(path: Path, kind: str) -> dict:
    return {"path": str(path), "kind": kind, "offset": 0, "first": 0.0, "last": 0.0, "model": "", "tokens": 0, "tools": 0,
            "action": "", "done": False, "title": "", "reg": "", "agent_seen": "", "events": [], "meta": {}, "edits": []}


def _read(path: Path, kind: str) -> dict:
    """读一份会话记录：读过的接着读新的那段（文件变短了就从头读）。"""
    key = str(path)
    s = _STATE.get(key)
    size = path.stat().st_size
    if s is None or size < s["offset"]:
        s = _STATE[key] = _new(path, kind)
    if size > s["offset"]:
        with open(path, "rb") as f:
            f.seek(s["offset"])
            data = f.read(size - s["offset"])
        end = data.rfind(b"\n") + 1                      # 只读到最后一个整行，半行留到下回
        for line in data[:end].splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            (_claude_line if kind == "Claude Code" else _codex_line)(s, d)
        s["offset"] += end
    meta = path.with_name(path.stem + ".meta.json")      # Claude Code 子 agent：任务名、是不是被人停了
    if kind == "Claude Code" and meta.is_file():
        try:
            s["meta"] = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return s


def _files(sources: dict[str, Path], days: float) -> list[tuple[Path, str]]:
    cut = time.time() - days * 86400
    out = []
    for kind, root in sources.items():
        if not root.is_dir():
            continue
        for f in root.rglob("*.jsonl"):
            try:
                if f.stat().st_mtime >= cut:
                    out.append((f, kind))
            except OSError:
                continue
    return out


def scan(sources: dict[str, Path] | None = None, days: float = DAYS) -> list[dict]:
    """把最近的会话记录读一遍（读过的只读新的），返回认得出是谁的那几份。"""
    with _LOCK:
        got = []
        for f, kind in _files(sources if sources is not None else globals()["sources"](), days):
            try:
                s = _read(f, kind)
            except OSError:
                continue
            if s["reg"] or s["agent_seen"]:
                got.append(s)
        return got


def who_edited(path: Path, since: float) -> str:
    """最近谁改过这个文件（有会话记录时；Claude Code 的 Edit / Write 记着改的哪个文件）。看不出来返回空。"""
    target = os.path.normcase(os.path.normpath(str(path)))
    best, at_best = "", 0.0
    with _LOCK:
        for s in _STATE.values():
            name = s["reg"] or s["agent_seen"]
            for at, f in s.get("edits", []):
                if name and at >= since and at > at_best and os.path.normcase(os.path.normpath(f)) == target:
                    best, at_best = name, at
    return best


def sid(s: dict) -> str:
    return hashlib.sha1(s["path"].encode("utf-8")).hexdigest()[:12]


def summary(s: dict, now: float | None = None) -> dict:
    now = now or time.time()
    meta = s.get("meta") or {}
    stopped = bool(meta.get("stoppedByUser"))
    state = "做完" if s["done"] else "在跑" if (now - s["last"] < RUNNING and not stopped) else "停了"
    return {"id": sid(s), "kind": s["kind"], "agent": s["reg"] or s["agent_seen"], "registered": bool(s["reg"]),
            "title": meta.get("description") or s["title"], "model": model_name(s["model"]), "tokens": s["tokens"],
            "tools": s["tools"], "action": s["action"] if state == "在跑" else ("被人停了" if stopped else ""),
            "state": state, "started": s["first"], "last": s["last"],
            "seconds": int((now if state == "在跑" else s["last"]) - s["first"]) if s["first"] else 0}


def board(sources: dict[str, Path] | None = None, days: float = DAYS) -> list[dict]:
    """后台任务表：在跑的在前，然后按最后动静新的在前。"""
    now = time.time()
    rows = [summary(s, now) for s in scan(sources, days)]
    return sorted(rows, key=lambda r: (r["state"] != "在跑", -r["last"]))


def detail(session_id: str) -> dict | None:
    """一份会话：表上那一行 + 最近的过程（人说的、它说的、用了什么工具、结果）。"""
    with _LOCK:
        s = next((x for x in _STATE.values() if sid(x) == session_id), None)
        if s is None:
            return None
        return summary(s) | {"path": s["path"], "events": list(s["events"])}


def fmt_time(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).astimezone().strftime("%m-%d %H:%M:%S") if t else ""
