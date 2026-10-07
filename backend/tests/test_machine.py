"""本机设置：只在这台电脑上对的东西不写进项目，换台电脑自己找（作者 10-01：「这个核心最后要给用户用，用户的文件目录跟我的可不一样」）。"""
import machine
import sessions
import tools


def _exe(d, name):
    d.mkdir(parents=True, exist_ok=True)
    f = d / (name + ".exe")
    f.write_text("", encoding="utf-8")
    return f


def test_programs_are_found_on_any_computer_and_remembered(tmp_path, monkeypatch):
    monkeypatch.setattr(tools.shutil, "which", lambda name: None)          # PATH 里没有
    exe = _exe(tmp_path / "别人家" / "Git" / "cmd", "fakegit")
    assert tools.find_exe("fakegit", "D:\\Git\\cmd", "T3") is None        # 卡上写的是作者电脑的盘符：别人电脑上不对
    machine.put("tools", "T3", str(exe.parent))                              # 设置 → 本机 填一下
    assert tools.find_exe("fakegit", "D:\\Git\\cmd", "T3") == str(exe)
    machine.put("tools", "T3", "")
    monkeypatch.setattr(machine, "common_dirs", lambda: [tmp_path / "别人家"])   # 或者装在常见的位置：自己找到、记下来
    assert tools.find_exe("fakegit", "", "T3") == str(exe)
    assert machine.get("tools", "T3") == str(exe.parent)


def test_session_records_follow_the_settings_and_each_agents_own_variables(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "SOURCES", None)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex家"))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    src = sessions.sources()
    assert src["Codex"] == tmp_path / "codex家" / "sessions"
    machine.put("sessions", "Claude Code", str(tmp_path / "别处" / "projects"))
    assert sessions.sources()["Claude Code"] == tmp_path / "别处" / "projects"


def test_the_settings_page_lists_and_changes_them(proj, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from main import create_app
    monkeypatch.setattr(sessions, "SOURCES", None)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "没有这个"))
    with TestClient(create_app(proj)) as client:
        rows = {r["key"]: r for r in client.get("/api/settings/machine").json()["items"]}
        assert rows["Codex"]["found"] is False and rows["Codex"]["kind"] == "会话记录"
        (tmp_path / "有了" ).mkdir()
        rows = {r["key"]: r for r in client.put("/api/settings/machine", json={"kind": "会话记录", "key": "Codex", "value": str(tmp_path / "有了")}).json()["items"]}
        assert rows["Codex"]["found"] is True and rows["Codex"]["set"] == str(tmp_path / "有了")
