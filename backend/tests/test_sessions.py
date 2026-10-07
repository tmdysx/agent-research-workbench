"""后台任务表：从各家 agent 存在本机的会话记录里读（作者 10-01：「我希望，网页端能有这样的表」「做后台任务表吧」）。
测试只用临时文件夹里造的记录，不读你电脑上真的。"""
import json
import time
from datetime import datetime, timezone

import sessions


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _claude_tool(t, name, inp, usage=(2, 500, 70000, 16)):
    return {"type": "assistant", "timestamp": _iso(t), "message": {"model": "claude-opus-5-5", "stop_reason": "tool_use",
            "usage": dict(zip(("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"), usage)),
            "content": [{"type": "tool_use", "name": name, "input": inp}]}}


def test_reads_who_is_doing_what_from_both_kinds_of_records(tmp_path):
    now = time.time()
    claude, codex = tmp_path / "claude", tmp_path / "codex"
    sub = claude / "proj" / "sess" / "subagents" / "agent-1.jsonl"
    _jsonl(sub, [
        {"type": "user", "timestamp": _iso(now - 400), "message": {"role": "user", "content": "你是 claude-code#1……"}},
        _claude_tool(now - 390, "Bash", {"command": 'cd x && python rc.py register_agent \'{"name": "claude-code#1", "program": "Claude Code"}\''}),
        _claude_tool(now - 380, "Read", {"file_path": "AGENTS.md"}),
        _claude_tool(now - 30, "WebFetch", {"url": "https://example.com"}, usage=(2, 600, 117000, 100)),
    ])
    (sub.parent / "agent-1.meta.json").write_text(json.dumps({"description": "试跑 agent 1：W1 各家开工"}, ensure_ascii=False), encoding="utf-8")
    _jsonl(claude / "other" / "chat.jsonl", [                     # 跟这个项目没关系的会话：不进表
        {"type": "user", "timestamp": _iso(now - 100), "message": {"role": "user", "content": "今天天气怎么样"}}])
    _jsonl(codex / "2026" / "10" / "01" / "rollout-1.jsonl", [
        {"type": "session_meta", "timestamp": _iso(now - 900), "payload": {"cwd": "C:/项目"}},
        {"type": "turn_context", "timestamp": _iso(now - 899), "payload": {"model": "gpt-6-astra"}},
        {"type": "event_msg", "timestamp": _iso(now - 890), "payload": {"type": "item_completed", "item": {
            "type": "McpToolCall", "server": "research-console", "tool": "register_agent", "arguments": {"name": "codex", "program": "Codex"}}}},
        {"type": "event_msg", "timestamp": _iso(now - 880), "payload": {"type": "item_completed", "item": {
            "type": "CommandExecution", "command": ["powershell.exe", "-Command", "python -m pytest -q"]}}},
        {"type": "event_msg", "timestamp": _iso(now - 870), "payload": {"type": "token_count", "info": {"total_token_usage": {"total_tokens": 23517}}}},
        {"type": "event_msg", "timestamp": _iso(now - 860), "payload": {"type": "task_complete"}},
    ])
    rows = sessions.board({"Claude Code": claude, "Codex": codex}, days=1)
    assert [r["agent"] for r in rows] == ["claude-code#1", "codex"]                  # 在跑的在前；闲聊那份不算
    a, b = rows
    assert a["state"] == "在跑" and a["title"] == "试跑 agent 1：W1 各家开工" and a["model"] == "Opus 5.5"
    assert a["tools"] == 3 and a["tokens"] == 117702 and a["action"] == "在上网查" and 350 < a["seconds"] < 460
    assert b["state"] == "做完" and b["model"] == "gpt-6-astra" and b["tools"] == 2 and b["tokens"] == 23517 and b["registered"]
    d = sessions.detail(a["id"])
    assert [e["who"] for e in d["events"]] == ["人", "用", "用", "用"] and "register_agent" in d["events"][1]["text"]

    _jsonl(sub, [_claude_tool(now - 5, "Edit", {"file_path": "W1.md"})])          # 记录长了：只读新的那段
    a2 = sessions.board({"Claude Code": claude, "Codex": codex}, days=1)[0]
    assert a2["tools"] == 4 and a2["action"] == "在改文件"
    (sub.parent / "agent-1.meta.json").write_text(json.dumps({"description": "试跑", "stoppedByUser": True}), encoding="utf-8")
    a3 = sessions.board({"Claude Code": claude, "Codex": codex}, days=1)
    assert next(r for r in a3 if r["agent"] == "claude-code#1")["state"] == "停了"      # 人停了：不算在跑
    assert next(r for r in a3 if r["agent"] == "claude-code#1")["action"] == "被人停了"


def test_an_agent_named_only_in_its_calls_still_counts(tmp_path):
    now = time.time()
    _jsonl(tmp_path / "c" / "p" / "s.jsonl", [
        _claude_tool(now - 10, "mcp__research-console__next_task", {"agent": "cursor"})])
    r = sessions.board({"Claude Code": tmp_path / "c"}, days=1)[0]
    assert r["agent"] == "cursor" and not r["registered"] and r["action"] == "在调接口：next_task"


def test_the_page_gets_the_table_and_the_overview(proj, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from main import create_app
    import agents
    import store
    now = time.time()
    _jsonl(tmp_path / "c" / "p" / "s.jsonl", [
        _claude_tool(now - 20, "Bash", {"command": "python rc.py register_agent '{\"name\": \"codex\"}'"})])
    monkeypatch.setattr(sessions, "SOURCES", {"Claude Code": tmp_path / "c"})
    c = store.connect(proj.db_path)
    agents.register(c, proj, "codex", "Codex")
    c.close()
    with TestClient(create_app(proj)) as client:
        rows = client.get("/api/tasks").json()["items"]
        assert [(r["code"], r["agent"], r["state"], r["program"]) for r in rows] == [("G1", "codex", "在跑", "Codex")]
        d = client.get("/api/tasks/" + rows[0]["id"]).json()
        assert d["events"][0]["who"] == "用" and len(d["events"][0]["at"]) == 14
        auto = client.get("/api/auto").json()
        assert auto["pending"] == [] and [e["what"] for e in auto["recent"]] == ["报到 · 用 Codex"]
        assert client.post("/api/claims/release", json={"goal": "S1-1", "sub": "S2-1"}).status_code == 404
