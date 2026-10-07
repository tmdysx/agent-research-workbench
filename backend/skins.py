"""外观（皮肤）：网页的颜色、字、圆角能换，三栏布局不动。

作者 2026-10-01：「外观做成设置里能换的……可以先用精简黑白为通用模板适合大众，然后再找两个皮肤放默认里，其他的就可以让玩家自己DIY了」。
- 应用文件夹的 `外观/` 里一套一个 .css：只写变量（--plane、--card、--fg、--accent……），亮、暗各一份；文件名就是名字
- 文件开头的注释写「一句话：」「自带：是」；没写也能用
- 首次默认「玉色科技」（作者2026-10-05）；「黑白极简」写在 模板.html 里，`外观/黑白极简.css` 是它的副本，给人照着改；选它 = 不加任何文件
- 选哪套记在这台电脑的浏览器里（跟亮 / 暗一样），不改项目
"""
from __future__ import annotations

import re
from pathlib import Path

from project import CODE_DIR

DIR = CODE_DIR / "外观"
DEFAULT = "玉色科技"
_NAME = re.compile(r"^[^\\/:*?\"<>|.][^\\/:*?\"<>|]{0,39}$")
_VAR = re.compile(r"--(plane|card|fg|accent)\s*:\s*([^;}\s]+)")


def _path(name: str) -> Path | None:
    """名字 → 外观/名字.css；不在 外观/ 里、名字不像样的都不认。"""
    if not _NAME.match(name or ""):
        return None
    f = (DIR / f"{name}.css").resolve()
    return f if f.parent == DIR.resolve() and f.is_file() else None


def _info(f: Path) -> dict:
    text = f.read_text(encoding="utf-8", errors="replace")
    head = text.split("*/", 1)[0] if text.lstrip().startswith("/*") else ""
    line = next((x.split("：", 1)[1].strip() for x in head.splitlines() if "一句话：" in x), "")
    first = text.split("@media", 1)[0]                      # 亮色那一份（第一个 :root）里的四个颜色，设置页画小色块
    colors = dict(_VAR.findall(first))
    return {"name": f.stem, "one_line": line, "builtin": "自带：是" in head, "default": f.stem == DEFAULT,
            "swatch": [colors.get(k, "") for k in ("plane", "card", "fg", "accent")], "file": f"外观/{f.name}"}


def listing() -> list[dict]:
    """有哪几套：默认的排第一，自带的跟着，玩家自己做的按名字排在后面。"""
    out = [_info(f) for f in sorted(DIR.glob("*.css")) if _NAME.match(f.stem)] if DIR.is_dir() else []
    if not any(x["default"] for x in out):
        # Missing a theme file is not evidence that its colors are available.
        fallback = next((x for x in out if x["name"] == "黑白极简"), None)
        if fallback is not None:
            fallback["default"] = True
            fallback["one_line"] += "（玉色科技文件缺失，使用经典回退）"
        else:
            out.append({"name": "黑白极简", "one_line": "皮肤文件缺失，使用网页自带黑白",
                        "builtin": True, "default": True,
                        "swatch": ["#fafafa", "#ffffff", "#171717", "#171717"], "file": ""})
    return sorted(out, key=lambda x: (not x["default"], not x["builtin"], x["name"]))


def css_file(name: str) -> Path | None:
    return _path(name)
