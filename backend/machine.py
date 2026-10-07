"""本机设置：只在这台电脑上对的东西——工具装在哪、各家 agent 的会话记录在哪。

作者 2026-10-01：「这个核心最后要给用户用，用户的文件目录跟我的可不一样」。
- 存在应用文件夹的 `索引/本机设置.json`：不进 git、不带进新项目、不进发布版；换一台电脑，程序自己重新找、找到了记在这
- 工具卡上只写「怎么查」，盘符这类只在某台电脑上对的不写进卡（09-30 以前卡上写着作者电脑的 `D:\\…`，10-01 挪到这）
- 两组：tools（卡号 → 程序所在的文件夹）· sessions（哪家 agent → 会话记录的文件夹）
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import atomic
from project import CODE_DIR

FILE = CODE_DIR / "索引" / "本机设置.json"
SECTIONS = ("tools", "sessions")
_LOCK = threading.Lock()


def load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {k: dict(d.get(k) or {}) for k in SECTIONS}


def get(section: str, key: str) -> str:
    return load()[section].get(key, "")


def put(section: str, key: str, value: str) -> dict:
    """记一样（value 空 = 去掉，下次重新找）。"""
    if section not in SECTIONS:
        raise KeyError(section)
    with _LOCK:
        d = load()
        value = os.path.expandvars((value or "").strip().strip('"'))
        if value:
            d[section][key] = value
        else:
            d[section].pop(key, None)
        FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_name(FILE.name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        atomic.replace(tmp, FILE)
        return d


def common_dirs() -> list[Path]:
    """别处都找不到时，去这几个常见的安装位置看一层（Windows：Program Files、用户的 Programs、各盘根目录；Mac / Linux 的常见位置）。"""
    out = []
    for v in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        if os.environ.get(v):
            out.append(Path(os.environ[v]))
    if os.environ.get("LOCALAPPDATA"):
        out.append(Path(os.environ["LOCALAPPDATA"]) / "Programs")
    if os.name == "nt":
        out += [Path(f"{d}:\\") for d in "CDEF" if Path(f"{d}:\\").exists()]
    else:
        out += [Path(x) for x in ("/opt/homebrew", "/usr/local", "/opt", "/Applications") if Path(x).is_dir()]
    return list(dict.fromkeys(out))
