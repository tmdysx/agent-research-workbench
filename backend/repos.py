"""开源项目：别人的项目，我们学它、借它（工具 S2-3、S2-4、S2-6）。

作者 10-01：「我觉得工具这个模块也要分几个小模块，一个是开源项目……」「那些开源项目在外部文件那里你自己调一下」。
- 一个项目一张卡：`工具库/开源项目/O1 名字.md`（编号 O，号不回收），开头 --- 之间写 编号 · 名字 · 链接 · 许可证 · 能不能借 · 一句话 · 状态 · 带什么 · 原件 · 大小 · 收进来
  正文三节：借了什么 · 用在哪 · 变成了什么（人和 agent 往下加）
- 原件（GitHub 下载的压缩包）放 `工具库/开源项目/原件/`，原样不改；**不进 git**（太大），新项目不带
- 解读：`工具库/开源项目/解读/O1 名字.md`，agent 写：干什么的 · 能借什么 · 怎么用（借思路 / 抄代码 / 装成插件 / 装成技能 / 装成 MCP）
- 能不能借，只看许可证（项-9 商用收费）：宽松许可证 → 能抄（要署名）；认不出的 → 只借思路（等人看）；
  传染（GPL / AGPL / LGPL）、不许商用（NC）、没许可证 → 不许抄。只读压缩包，不解开、不跑里面的东西
"""
from __future__ import annotations

import os
import re
import zipfile
from datetime import date
from pathlib import Path

import atomic
import store
from project import CODE_DIR, Project
from skills import frontmatter

DIR = CODE_DIR / "工具库" / "开源项目"
STATES = ("收着", "看过", "借鉴了", "变成了插件或技能", "用不上")
GREEN = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "BSD", "ISC", "Unlicense", "0BSD", "CC0-1.0", "Zlib")
RED = ("GPL", "AGPL", "LGPL", "NC", "没许可证")
CAN, IDEAS, NO = "能抄", "只借思路", "不许抄"
_CODE = re.compile(r"^O(\d+) ")
_LICFILE = re.compile(r"^(LICENSE|LICENCE|COPYING|UNLICENSE)(\.(md|txt|rst))?$", re.I)
# 许可证原文里认得出的那一句 → 名字（先认传染的、不许商用的，再认宽松的）
_TEXTS = (
    (r"GNU AFFERO GENERAL PUBLIC LICENSE", "AGPL"), (r"GNU LESSER GENERAL PUBLIC LICENSE", "LGPL"), (r"GNU GENERAL PUBLIC LICENSE", "GPL"),
    (r"NonCommercial|Non-Commercial|Noncommercial", "NC"), (r"Mozilla Public License", "MPL-2.0"),
    (r"Apache License", "Apache-2.0"), (r"Permission is hereby granted, free of charge", "MIT"), (r"MIT License", "MIT"),
    (r"Permission to use, copy, modify, and/or distribute", "ISC"),
    (r"Redistribution and use in source and binary forms", "BSD"), (r"This is free and unencumbered software", "Unlicense"),
    (r"Creative Commons Zero|CC0 1\.0", "CC0-1.0"), (r"Creative Commons", "CC-BY"),
)
_SPDX = re.compile(r'"license"\s*:\s*"([^"]+)"|^license\s*=\s*["{]?\s*(?:text\s*=\s*)?"?([A-Za-z0-9.\-+ ]+)"?', re.M)


def borrow(lic: str) -> str:
    """能不能借：绿 能抄（要署名）· 黄 只借思路 · 红 不许抄。"""
    if not lic or lic == "没许可证" or any(lic.startswith(r) or f"-{r}" in lic for r in RED if r != "没许可证"):
        return NO
    return CAN if lic in GREEN or lic.startswith("BSD") else IDEAS


def _root(names: list[str]) -> str:
    tops = {n.split("/", 1)[0] for n in names if n.strip("/")}
    return (tops.pop() + "/") if len(tops) == 1 and any("/" in n for n in names) else ""


def _license(z: zipfile.ZipFile, names: list[str], root: str) -> str:
    for n in names:
        rest = n[len(root):]
        if "/" not in rest and _LICFILE.match(rest):
            text = z.read(n)[:6000].decode("utf-8", "replace")
            for pat, name in _TEXTS:
                if re.search(pat, text, re.I):
                    if name == "GPL" and re.search(r"Version 2", text):
                        return "GPL-2.0"
                    return {"GPL": "GPL-3.0", "AGPL": "AGPL-3.0", "LGPL": "LGPL"}.get(name, name)
            return "认不出（有 " + rest + "）"
    for n in (root + "package.json", root + "pyproject.toml"):          # 没有许可证文件：看包的说明里写没写
        if n in names:
            m = _SPDX.search(z.read(n)[:20000].decode("utf-8", "replace"))
            if m:
                return (m.group(1) or m.group(2) or "").strip()
    return "没许可证"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _readme(z: zipfile.ZipFile, names: list[str], root: str, name: str) -> tuple[str, str]:
    """README 里第一句像样的话、它自己的 github 链接（仓库名跟项目名对得上才算，对不上宁可空着）。"""
    n = next((x for x in names if x[len(root):].lower() in ("readme.md", "readme.rst", "readme.txt", "readme")), None)
    if not n:
        return "", ""
    text = z.read(n)[:40000].decode("utf-8", "replace")
    link = ""
    for owner, repo in re.findall(r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?=[/)\s\"'#?]|$)", text):
        if _norm(repo) == _norm(name) or (len(_norm(repo)) >= 8 and _norm(name).startswith(_norm(repo))):   # 包名后面多个 -mcp 这种也算
            link = f"https://github.com/{owner}/{repo}"
            break
    line, top = "", True
    for raw in text.splitlines():
        x = raw.strip()
        top = top and not x.startswith("## ")
        if top and x.startswith("<") and re.search(r"<(strong|b)>", x):   # 开头那段加粗的一句（工具 S2-14：三省六部那句就藏在 <p><strong> 里）
            y = re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", " ", x)).strip()
            if len(y) >= 40:                               # 太短的是口号（「Compose in symbols.」），不算
                x = y
        if not x or x.startswith(("#", "<", "[!", "![", "|", "```", "---", ">", "=", "*   ", "- [")) or re.fullmatch(r"[\W_]+", x):
            continue
        if len(re.findall(r"\]\(|<a\s", x)) >= 2 or " | " in x or re.search(r"sponsor|support of|赞助|\b(src|href|alt|width|height)=", x, re.I):
            continue                                       # 导航、徽章、赞助那种行不算
        x = re.sub(r"<[^>]+>", "", x)
        x = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", x)
        x = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", x)
        x = re.sub(r"[*_`]+", "", x).strip()
        if x.endswith(("：", ":")) or re.fullmatch(r"https?://\S+", x):   # 「大多数框架的套路是：」这种引子句、光一个网址，不算一句话
            continue
        if re.search(r"sign up|waitlist|subscribe|join (our|the)|→|👉", x, re.I):   # 「Sign up for the waitlist →」这种招呼不算
            continue
        if len(x) < 25 and not re.search(r"[。.!！，,]", x):   # 只是个名字（「BilldDesk Pro」）：往下找正经那句
            continue
        if len(re.sub(r"\W", "", x)) >= 10:
            line = x[:160]
            break
    return line, link


def inspect(path: Path) -> dict:
    """只读一个压缩包：名字、许可证、能不能借、一句话、链接、带什么。"""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        root = _root(names)
        lic = _license(z, names, root)
        name = re.sub(r"\s*\(\d+\)$", "", re.sub(r"-(main|master)$", "", root.rstrip("/") or path.stem))
        line, link = _readme(z, names, root, name)
        skills = sum(1 for n in names if n.endswith("/SKILL.md") or n == "SKILL.md")
        has = [x for x, ok in (
            (f"技能 {skills} 个（SKILL.md）", skills),
            ("MCP", any(re.search(r"(^|/)(mcp[^/]*\.(py|ts|js|json)|server\.py)$", n, re.I) for n in names) or any("mcp" in n.lower().split("/")[-1] for n in names[:400])),
            ("Claude Code 插件", any("/.claude-plugin/" in n or n.startswith(".claude-plugin/") for n in names)),
            ("Python", any(n.endswith(("pyproject.toml", "requirements.txt", "setup.py")) for n in names)),
            ("Node", any(n.endswith("package.json") and n.count("/") <= root.count("/") + 1 for n in names)),
        ) if ok]
    return {"name": name, "license": lic, "borrow": borrow(lic), "one_line": line, "link": link, "has": has,
            "size": path.stat().st_size, "files": len(names)}


def _cards(d: Path | None = None) -> list[Path]:
    d = d or DIR
    return sorted((f for f in d.glob("O*.md") if _CODE.match(f.name)), key=lambda f: int(_CODE.match(f.name).group(1))) if d.is_dir() else []


def listing(d: Path | None = None) -> list[dict]:
    """全部开源项目卡，按编号排；带上解读（有的话）。"""
    d = d or DIR
    out = []
    for f in _cards(d):
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        body = text[text.find("\n---", 3) + 4:].lstrip() if text.startswith("---") else text
        note = d / "解读" / f.name
        lic = fm.get("许可证", "")
        out.append({"code": fm.get("编号") or f.name.split(" ")[0], "name": fm.get("名字", f.stem), "link": fm.get("链接", ""),
                    "license": lic, "borrow": fm.get("能不能借") or borrow(lic), "one_line": fm.get("一句话", ""),
                    "state": fm.get("状态", "收着"), "has": fm.get("带什么", ""), "raw": fm.get("原件", ""), "size": fm.get("大小", ""),
                    "at": fm.get("收进来", ""), "file": f"工具库/开源项目/{f.name}", "body": body,
                    "notes": note.read_text(encoding="utf-8", errors="replace") if note.is_file() else "",
                    "notes_file": f"工具库/开源项目/解读/{f.name}"})
    return out


def _write(f: Path, text: str) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    atomic.replace(tmp, f)


def _card(code: str, info: dict, raw: str, by: str) -> str:
    def clean(v):
        return " ".join(str(v).replace("\n", " ").split())
    return (f"---\n编号: {code}\n名字: {clean(info['name'])}\n链接: {clean(info['link'])}\n许可证: {clean(info['license'])}\n能不能借: {info['borrow']}\n"
            f"一句话: {clean(info['one_line'])}\n状态: 收着\n带什么: {clean('、'.join(info['has']))}\n原件: {raw}\n"
            f"大小: {info['size'] / 1e6:.1f} MB · {info['files']} 个文件\n收进来: {date.today().isoformat()} · {by}\n---\n"
            f"# {code} {info['name']}\n\n"
            f"> 别人的项目，学它、借它。能不能抄代码只看许可证：{info['license']} → {info['borrow']}（工-1：红灯的只借思路）。原件在 `{raw}`，原样不改（工-4）。\n\n"
            f"## 借了什么\n\n（还没有）\n\n## 用在哪\n\n（还没有：借了就写交付单 J 号、任务 S2 号）\n\n## 变成了什么\n\n（还没有：装成插件、技能、MCP 了就写在这，两边互相链接）\n")


def take(conn, p: Project, iid: int, *, by: str = "人", d: Path | None = None) -> dict:
    """外部资料入口里的一个压缩包「放进开源项目」：读出信息、建 O 卡，原件挪进 工具库/开源项目/原件/。同名不覆盖。"""
    import intake
    d = d or DIR
    with store.tx(conn):
        it = intake.get(conn, iid)
        if not it or it["status"] != "waiting":
            raise store.Refused(f"外部资料入口里没有 #{iid}（可能已经分拣过了）")
        src = intake.inbox_dir(p) / it["name"]
        if not src.is_file():
            raise store.Refused(f"「{it['name']}」不在外部资料入口里了")
        if not zipfile.is_zipfile(src):
            raise store.Refused(f"「{it['name']}」不是压缩包（开源项目收 GitHub 下载的 .zip）")
        info = inspect(src)
        raw_dir = d / "原件"
        raw_dir.mkdir(parents=True, exist_ok=True)
        name = intake._free_name(raw_dir, it["name"], it["sha256"])
        n = max([int(_CODE.match(f.name).group(1)) for f in _cards(d)] or [0]) + 1
        code = f"O{n}"
        safe = re.sub(r'[\\/:*?"<>|]', "-", info["name"])[:60]
        raw = f"工具库/开源项目/原件/{name}"
        conn.execute("UPDATE intake SET status = 'sorted', sorted_to = ?, sorted_by = ?, sorted_at = ? WHERE id = ?",
                     (f"工具/开源项目 {code}", by, store.now(), iid))
        store.log(conn, by, "放进开源项目", f"#{iid}", f"{it['name']} → {code} {info['name']}（{info['license']} · {info['borrow']}）")
        os.replace(src, raw_dir / name)                    # 最后挪：挪不成就回滚
    _write(d / f"{code} {safe}.md", _card(code, info, raw, by))
    return next(x for x in listing(d) if x["code"] == code)


def write_notes(code: str, text: str, *, by: str, d: Path | None = None) -> dict:
    """agent 写解读：干什么的 · 能借什么 · 怎么用。整份换掉（旧的进 git 有记录）。"""
    d = d or DIR
    x = next((r for r in listing(d) if r["code"] == code), None)
    if x is None:
        raise store.Refused(f"没有 {code}")
    if len(text.strip()) < 20:
        raise store.Refused("解读太短：写清干什么的、能借什么、怎么用")
    body = text.strip()
    if body.startswith("# "):                              # 自己带了大标题：换成统一的
        body = body.split("\n", 1)[1].strip() if "\n" in body else ""
    head = f"# {code} {x['name']} · 解读\n\n> {by} 写的 · {date.today().isoformat()} · 能不能借：{x['license'] or '没许可证'} → {x['borrow']}\n\n"
    _write(d / "解读" / Path(x["file"]).name, head + body + "\n")
    if x["state"] == "收着":                                # 写了解读就算看过了
        card = d / Path(x["file"]).name
        _write(card, card.read_text(encoding="utf-8").replace("\n状态: 收着\n", "\n状态: 看过\n", 1))
    return next(r for r in listing(d) if r["code"] == code)
