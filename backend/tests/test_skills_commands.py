"""技能库 / 快捷指令：人点了才装；那边已有不一样的先问、覆盖前备份；「本机」在测试里指向临时目录。"""
import shutil

import pytest
from fastapi.testclient import TestClient

import commands
import skills
from main import create_app
from project import CODE_DIR


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "假的用户目录"
    monkeypatch.setenv("RC_HOME", str(h))              # 「本机」= 这里，不碰真的 ~/.claude
    return h


def test_skills_list_install_conflict_backup(proj, home):
    for name in ("自动化科研交互界面", "网页前端", "交付自查"):
        shutil.copytree(CODE_DIR / "技能库" / name, proj.root / "技能库" / name)
    with TestClient(create_app(proj)) as client:
        lst = {s["id"]: s for s in client.get("/api/skills").json()}
        assert {"自动化科研交互界面", "网页前端", "交付自查"} <= set(lst)
        assert lst["交付自查"]["description"] and lst["交付自查"]["project"] is None
        r = client.post("/api/skills/交付自查/install", json={"where": "project"}).json()
        dst = proj.root / ".claude" / "skills" / "交付自查" / "SKILL.md"
        assert dst.is_file() and r["already"] is False
        assert client.post("/api/skills/交付自查/install", json={"where": "project"}).json()["already"] is True
        dst.write_text("被人改过", encoding="utf-8")                              # 那边变得不一样了
        r = client.post("/api/skills/交付自查/install", json={"where": "project"})
        assert r.status_code == 409 and r.json()["conflict"] is True               # 先问，不覆盖
        assert dst.read_text(encoding="utf-8") == "被人改过"
        r = client.post("/api/skills/交付自查/install", json={"where": "project", "overwrite": True}).json()
        assert dst.read_text(encoding="utf-8").startswith("---")
        backup = proj.index_dir / "技能备份"
        assert any((b / "SKILL.md").read_text(encoding="utf-8") == "被人改过" for b in backup.iterdir())  # 旧的在备份里
        client.post("/api/skills/网页前端/install", json={"where": "machine"})
        assert (home / ".claude" / "skills" / "网页前端" / "参考" / "模板.html").is_file()
        assert client.post("/api/skills/不存在/install", json={"where": "project"}).status_code == 404
        assert client.post("/api/skills/交付自查/install", json={"where": "别处"}).status_code == 400


def test_skill_fork(proj, home, tmp_path, monkeypatch):
    lib = tmp_path / "技能库"
    shutil.copytree(CODE_DIR / "技能库", lib)
    # 默认只看当前临时项目的技能库，不回退到应用根目录。
    new = skills.fork(proj, "交付自查")
    assert new == "交付自查（我的）" and "name: 交付自查（我的）" in (lib / new / "SKILL.md").read_text(encoding="utf-8")
    assert skills.fork(proj, "交付自查") == "交付自查（我的2）"


def test_commands_save_fill_and_install(proj, home, tmp_path, monkeypatch):
    d = tmp_path / "快捷指令"
    shutil.copytree(CODE_DIR / "快捷指令", d)
    monkeypatch.setattr(commands, "DIR", d)
    with TestClient(create_app(proj)) as client:
        lst = {c["id"]: c for c in client.get("/api/commands").json()}
        assert {"整理本周进展", "分拣外部资料", "交接给新agent", "检查有没有违反戒律"} <= set(lst)
        assert lst["交接给新agent"]["en"] == "handover" and "{当前文件}" in lst["交接给新agent"]["body"]
        new = {"name": "查引用", "en": "check-refs", "description": "查文献引用对不对", "body": "看 {当前文件} 里的引用。补充：{我的笔记}"}
        assert client.post("/api/commands", json=new).status_code == 200
        assert client.post("/api/commands", json=new).status_code == 400                     # 同名
        assert client.post("/api/commands", json={**new, "name": "别的", "en": "Check Refs"}).status_code == 400   # 英文短名不合规
        assert client.post("/api/commands", json={**new, "name": "别的", "en": "handover"}).status_code == 400     # 英文短名撞了
        client.put("/api/commands/查引用", json={**new, "body": "改过的：{当前文件}"})
        assert (d / "查引用.md").read_text(encoding="utf-8").endswith("改过的：{当前文件}\n")
        r = client.post("/api/commands/交接给新agent/install", json={"where": "project"}).json()
        f = proj.root / ".claude" / "commands" / "handover.md"
        text = f.read_text(encoding="utf-8")
        assert "$ARGUMENTS" in text and "{" not in text and "get_overview" in text and r["already"] is False
        assert client.post("/api/commands/交接给新agent/install", json={"where": "project"}).json()["already"] is True
        f.write_text("被改过", encoding="utf-8")
        assert client.post("/api/commands/交接给新agent/install", json={"where": "project"}).status_code == 409
        client.post("/api/commands/交接给新agent/install", json={"where": "project", "overwrite": True})
        assert any(b.read_text(encoding="utf-8") == "被改过" for b in (proj.index_dir / "快捷指令备份").iterdir())
