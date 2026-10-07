"""测试共用的临时项目：只碰临时目录，不碰真的数据库和 ~/.claude。"""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from project import Project  # noqa: E402

import os  # noqa: E402

os.environ["RC_OFFLINE"] = "1"                  # 测试不上网：查 OpenAlex、arXiv 的都当没查到（要查的测试自己换成假的）


@pytest.fixture
def proj(tmp_path) -> Project:
    """空的临时项目（资料/ 都还没有，像新项目第一次启动）。测试只碰临时目录，不碰真库。"""
    return Project(tmp_path)


@pytest.fixture(autouse=True)
def _machine_settings_in_tmp(tmp_path_factory, monkeypatch):
    """本机设置（工具装在哪、会话记录在哪）：测试写进临时文件，不碰这台电脑真的 索引/本机设置.json。"""
    import machine
    import sessions
    monkeypatch.setattr(machine, "FILE", tmp_path_factory.mktemp("machine") / "本机设置.json")
    monkeypatch.setattr(machine, "common_dirs", lambda: [])          # 测试不去翻整台电脑的安装位置
    monkeypatch.setattr(sessions, "SOURCES", {})                    # 也不读这台电脑真的会话记录（要的测试自己造）
