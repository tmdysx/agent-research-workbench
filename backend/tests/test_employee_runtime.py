"""员工权限与真实终端启动约定；只使用临时项目、临时本机设置。"""
import json
from pathlib import Path

import pytest

import agents
import machine
import store


@pytest.fixture
def conn(proj):
    c = store.connect(proj.db_path)
    store.migrate(c)
    yield c
    c.close()


def test_legacy_profiles_remain_manual_and_extra_history_survives(proj, conn):
    a = agents.register(conn, proj, "coder", "Codex")["agent"]
    assert a["crafts"] == [] and not any(a[k] for k in agents.SWITCHES)
    f = proj.root / agents.DIR / a["file"]
    raw = f.read_text(encoding="utf-8").replace("名字: coder", "名字: coder\n作者自定义: 保留我")
    raw += "历史补充：没有编号的旧备注\n\n## 额外交代\n\n自定义内容原样保留。\n"
    f.write_text(raw, encoding="utf-8")
    agents.update(conn, proj, "coder", {"line": "更新说明"}, by="agent:coder")
    text = f.read_text(encoding="utf-8")
    assert "作者自定义: 保留我" in text and "历史补充：没有编号的旧备注" in text
    assert "## 额外交代\n\n自定义内容原样保留。" in text


def test_work_type_scope_avoid_and_pause_share_one_reason(proj, conn):
    a = agents.create(conn, proj, "web", program="Codex", crafts=["网页", "文档"], scope=["S1-8"], avoid=["论文"])
    goal = {"code": "S1-8", "modules": ["源代码"]}
    x = {"code": "S2-45", "what": "〔程序〕做派活判断"}
    assert "工种不匹配" in agents.allows_reason(a, goal, x)
    x["what"] = "〔网页〕〔文档〕修改状态页及说明"
    assert agents.allows(a, goal, x)
    assert "负责范围" in agents.allows_reason(a, {"code": "S1-7"}, x)
    assert "不碰" in agents.allows_reason(a, goal | {"modules": ["论文"]}, x)
    a = agents.update(conn, proj, "web", {"paused": True}, by="人")
    assert agents.allows_reason(a, goal, x) == "员工已暂停"
    with pytest.raises(store.Refused, match="已暂停"):
        agents.take_core(conn, proj, "web")
    assert "工种：网页、文档" in agents.brief_text(a) and "暂停：是" in agents.brief_text(a)
    row = next(r for r in agents.roster(conn, proj) if r["name"] == "web")
    assert row["crafts"] == ["网页", "文档"] and row["paused"]


def test_agents_cannot_promote_themselves_and_authorized_changes_keep_actor(proj, conn):
    agents.create(conn, proj, "worker", program="Codex", crafts=["文档"], scope=["S1-2"], core="不能")
    for field, value in (("crafts", ["程序"]), ("scope", []), ("avoid", []), ("auto", True),
                         ("paused", False), ("plan_required", False), ("roles", ["审核"]), ("core", "能")):
        with pytest.raises(store.Refused, match="只有人能改"):
            agents.update(conn, proj, "worker", {field: value}, by="agent:worker")
    with pytest.raises(store.Refused, match="授权来源"):
        agents.configure(conn, proj, "worker", {"auto": True}, by="agent:chief", authorization="")
    a = agents.configure(conn, proj, "worker", {"crafts": ["程序"], "auto": True, "plan_required": True},
                         by="agent:chief", authorization="用户 2026-10-02 同意统筹配置后台员工")
    assert a["crafts"] == ["程序"] and a["auto"] and a["plan_required"]
    assert "agent:chief" in a["history"][-1] and "用户 2026-10-02" in a["history"][-1]
    with pytest.raises(store.Refused, match="工种只能"):
        agents.update(conn, proj, "worker", {"crafts": ["神奇工种"]}, by="人")


def test_codex_real_exe_beats_path_shim_and_machine_setting_overrides(proj, conn, monkeypatch, tmp_path):
    local = tmp_path / "Local"
    real = local / "OpenAI" / "Codex" / "bin" / "a-version" / "codex.exe"
    real.parent.mkdir(parents=True)
    real.write_text("stub", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setattr(agents.shutil, "which", lambda name: "bad/npm/codex.cmd")
    assert Path(agents.codex_executable()) == real
    configured = tmp_path / "chosen" / "codex.exe"
    configured.parent.mkdir()
    configured.write_text("stub", encoding="utf-8")
    machine.put("tools", "codex-cli", str(configured))
    assert Path(agents.codex_executable()) == configured
    machine.put("tools", "codex-cli", str(tmp_path / "missing.exe"))
    with pytest.raises(store.Refused, match="程序不存在"):
        agents.codex_executable()


def test_codex_command_and_runner_script_bind_project_and_employee(proj, conn, monkeypatch):
    agents.create(conn, proj, "chief", program="Codex", roles=["规划", "审核", "验收"])
    agents.create(conn, proj, "web", program="Codex（gpt-6-astra）", crafts=["网页"])
    monkeypatch.setattr(agents, "codex_executable", lambda: "real-codex.exe")
    root = proj.root.resolve().as_posix()
    cmd = agents.codex_command(proj, "chief")
    assert cmd[:5] == ["real-codex.exe", "exec", "--approve-for-me", "-C", root]
    assert "-m" not in cmd and "--no-alt-screen" not in cmd
    cfg = next(x for x in cmd if x.startswith("mcp_servers.research-console.args="))
    argv = json.loads(cfg.split("=", 1)[1])
    assert argv[1:] == ["--project", root, "--agent", "chief"]
    assert "等 G1" not in cmd[-1] and "Start-Sleep" not in cmd[-1] and "本次进程只执行一个动作" in cmd[-1]
    web = agents.codex_command(proj, "web", prompt="只做指定动作")
    assert web[web.index("-m") + 1] == "gpt-6-astra" and web[-1] == "只做指定动作"
    launch = agents.launcher(proj, "web")
    script = (proj.root / launch["path"]).read_text(encoding="utf-8-sig")
    assert "employee_runner.py" in script and "'--project'" in script and "'--agent' 'web'" in script
    assert launch["agent"] == "web" and launch["project"] == root and launch["model"] == "gpt-6-astra"
    assert "Start-Sleep" not in script


def test_claude_legacy_launcher_keeps_explicit_binding_and_is_manual_by_default(proj, conn):
    a = agents.create(conn, proj, "claude-old", program="Claude Code（Sonnet 5.5）")
    assert not a["auto"]
    launch = agents.launcher(proj, "claude-old")
    cfg = json.loads((proj.index_dir / "开工" / f"mcp-claude-{a['code']}.json").read_text(encoding="utf-8"))
    assert cfg["mcpServers"]["research-console"]["args"][1:] == ["--project", proj.root.resolve().as_posix(), "--agent", "claude-old"]
    script = (proj.root / launch["path"]).read_text(encoding="utf-8-sig")
    assert "& 'claude' '--model' 'sonnet'" in script
