"""网页链接：常用的权威网站一处点开（工具 S2-11；作者 10-01：「工具模块还要加一个网页链接」）。

- 一份纯文字：`工具库/网页链接.md`，`## 组名` 下面一张表（名字 · 网址 · 干什么用）；人照着加一行就多一个
- 只读出来给网页列；网页点了在新标签打开，后台不替人上网
"""
from __future__ import annotations

import re
from pathlib import Path

from project import CODE_DIR

FILE = CODE_DIR / "工具库" / "网页链接.md"
_URL = re.compile(r"^https?://\S+$")


def groups(f: Path | None = None) -> list[dict]:
    """[{group, items: [{name, url, what}]}]，照文件里的顺序；网址不像网址的那一行跳过。"""
    f = f or FILE
    if not f.is_file():
        return []
    out, cur = [], None
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            cur = {"group": line[3:].strip(), "items": []}
            out.append(cur)
            continue
        if cur is None or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("名字", "") or set("".join(cells)) <= set("-: "):
            continue
        url = cells[1].split()[0] if cells[1] else ""
        if not _URL.match(url):
            continue
        cur["items"].append({"name": cells[0], "url": url, "what": cells[2] if len(cells) > 2 else ""})
    return [g for g in out if g["items"]]
