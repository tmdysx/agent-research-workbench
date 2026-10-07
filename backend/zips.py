"""看压缩包里面（S1-10 S2-11、工具 S2-10）：像 GitHub 看仓库那样——文件树、说明、点一个文件看内容。

作者 10-01：「我觉得这个预览功能应该全站可用才对啊」「工具中的那个开源项目应该也要能查看」。
- 只读：不解开、不写盘、不跑里面任何东西；网页、脚本、SVG 一律当文字看（防里面的东西在本机网页里跑起来）
- 图片照常显示（png、jpg、gif、webp、bmp、ico）；别的二进制只写大小
- 路径只认压缩包里真有的那一项（namelist 里逐字对上），所以不存在「解压到外面去」的问题
"""
from __future__ import annotations

import zipfile
from pathlib import Path

MAX_ENTRIES = 5000
MAX_TEXT = 200_000
IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
          ".bmp": "image/bmp", ".ico": "image/x-icon"}


def _root(names: list[str]) -> str:
    tops = {n.split("/", 1)[0] for n in names if n.strip("/")}
    return (tops.pop() + "/") if len(tops) == 1 and any("/" in n for n in names) else ""


def entries(path: Path) -> dict:
    """里面有什么：[{name（去掉最外面那层文件夹）, size}]，按路径排；太多只给前 5000 个。"""
    with zipfile.ZipFile(path) as z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        root = _root([i.filename for i in z.infolist()])
    items = sorted(({"name": i.filename[len(root):], "size": i.file_size} for i in infos if i.filename[len(root):]), key=lambda x: x["name"].lower())
    readme = next((x["name"] for x in items if x["name"].lower() in ("readme.md", "readme.rst", "readme.txt", "readme")), "")
    return {"root": root, "items": items[:MAX_ENTRIES], "total": len(items), "readme": readme}


def read(path: Path, inner: str) -> dict:
    """读里面的一个文件：文字给内容（最多 200 KB）、图片说是图片、别的只给大小。"""
    with zipfile.ZipFile(path) as z:
        root = _root(z.namelist())
        name = root + inner
        try:
            info = z.getinfo(name)
        except KeyError:
            raise FileNotFoundError(inner)
        out = {"name": inner, "size": info.file_size}
        ext = Path(inner).suffix.lower()
        if ext in IMAGES:
            return dict(out, kind="image")
        with z.open(info) as f:
            raw = f.read(MAX_TEXT + 1)
    if b"\x00" in raw[:8000]:
        return dict(out, kind="binary")
    for enc in ("utf-8", "gb18030"):
        try:
            text = raw[:MAX_TEXT].decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw[:MAX_TEXT].decode("utf-8", "replace")
    return dict(out, kind="text", text=text, truncated=len(raw) > MAX_TEXT)


def image(path: Path, inner: str) -> tuple[bytes, str]:
    """里面的一张图：字节和类型。不是图片的不给（网页、SVG 不在网页里跑）。"""
    ext = Path(inner).suffix.lower()
    if ext not in IMAGES:
        raise FileNotFoundError(inner)
    with zipfile.ZipFile(path) as z:
        root = _root(z.namelist())
        try:
            return z.read(root + inner), IMAGES[ext]
        except KeyError:
            raise FileNotFoundError(inner)
