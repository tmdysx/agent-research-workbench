"""快捷指令：一份定义，两处用。

- 定义在应用根目录 `快捷指令/<名字>.md`：开头 description（一句话）+ en（英文短名），正文是指令模板
- **网页上**：笔记窗顶上一排按钮，点一下按当前页面把空位填好，追加进笔记
- **Claude Code 里**：「装进 Claude Code」→ .claude/commands/<英文短名>.md，在那边敲 /英文短名
模板里能用的空位：{项目} {当前页} {当前模块} {当前文件} {外部资料入口} {待拍板} {我的笔记}
"""
from __future__ import annotations

import re
from pathlib import Path

from project import CODE_DIR, Project, check_name
from skills import frontmatter, place, target_base

DIR = CODE_DIR / "快捷指令"
SLOTS = ["{项目}", "{当前页}", "{当前模块}", "{当前文件}", "{外部资料入口}", "{待拍板}", "{我的笔记}"]
_EN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

# 装进 Claude Code 时，网页才能现填的空位换成让 agent 自己去看的说法
FOR_CLAUDE = {
    "{项目}": "这个项目",
    "{当前页}": "（我正在看的页面，见我的笔记或问我）",
    "{当前模块}": "（我正在看的模块，见我的笔记或问我）",
    "{当前文件}": "（我正在看的文件，见我的笔记或问我）",
    "{外部资料入口}": "外部资料入口里等分拣的文件（用 list_inbox 看）",
    "{待拍板}": "等我拍板的问题（get_overview 里有）",
    "{我的笔记}": "$ARGUMENTS",
}


class Invalid(Exception):
    """输入不对，消息给人看。"""


def _body(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            return text[end + 4:].lstrip("\n")
    return text


def _file(cid: str, d: Path) -> Path:
    try:
        check_name(cid)
    except ValueError:
        raise KeyError(cid) from None
    f = d / f"{cid}.md"
    if not f.is_file():
        raise KeyError(cid)
    return f


def list_commands(p: Project | None = None, d: Path | None = None) -> list[dict]:
    d = d or DIR
    out = []
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        meta = frontmatter(text)
        item = {"id": f.stem, "description": meta.get("description", ""), "en": meta.get("en", ""), "body": _body(text)}
        if p is not None and item["en"]:
            item["project"] = _cc_status(p, item, "project")
            item["machine"] = _cc_status(p, item, "machine")
        out.append(item)
    return out


def _render(description: str, en: str, body: str) -> str:
    return f"---\ndescription: {description}\nen: {en}\n---\n\n{body.strip()}\n"


def save(name: str, en: str, description: str, body: str, *, create: bool, d: Path | None = None) -> dict:
    """新建（create=True，同名就拒）或改（只改 一句话 / 英文短名 / 正文，名字不改）。"""
    d = d or DIR
    try:
        name = check_name(name)
    except ValueError as e:
        raise Invalid(str(e)) from None
    en = (en or "").strip().lower()
    if not _EN.match(en):
        raise Invalid("英文短名只能用小写字母、数字和 -，比如 weekly-review（Claude Code 里敲 /weekly-review）")
    description = " ".join((description or "").split())
    if not description:
        raise Invalid("写一句话说这条指令是干什么的")
    if not (body or "").strip():
        raise Invalid("正文是空的")
    f = d / f"{name}.md"
    if create and f.exists():
        raise Invalid(f"已经有一条叫「{name}」的了")
    if not create and not f.exists():
        raise Invalid(f"没有「{name}」这条")
    for other in list_commands(None, d):
        if other["en"] == en and other["id"] != name:
            raise Invalid(f"英文短名 {en} 已经被「{other['id']}」用了")
    d.mkdir(parents=True, exist_ok=True)
    f.write_text(_render(description, en, body), encoding="utf-8")
    return next(c for c in list_commands(None, d) if c["id"] == name)


def for_claude(cmd: dict) -> str:
    """变成 Claude Code 的自定义命令：开头先让 agent 自己看现状，空位换成它能理解的说法。"""
    body = cmd["body"]
    for k, v in FOR_CLAUDE.items():
        body = body.replace(k, v)
    return (f"---\ndescription: {cmd['description']}\n---\n\n"
            "先用 research-console 的 get_overview、read_notes 看项目现状和我的笔记。\n\n" + body.strip() + "\n")


def _cc_status(p: Project, cmd: dict, where: str) -> str | None:
    dst = target_base(p, where) / "commands" / f"{cmd['en']}.md"
    if not dst.exists():
        return None
    return "same" if dst.read_text(encoding="utf-8", errors="replace") == for_claude(cmd) else "different"


def install(p: Project, cid: str, where: str, *, overwrite: bool = False, d: Path | None = None) -> dict:
    d = d or DIR
    _file(cid, d)
    cmd = next(c for c in list_commands(None, d) if c["id"] == cid)
    if not cmd["en"]:
        raise Invalid("这条没有英文短名，装不进 Claude Code")
    # 先写到索引/里当源文件，再用跟技能同一套「不静默覆盖、先备份」的放法
    staged = p.index_dir / "快捷指令待装" / f"{cmd['en']}.md"
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text(for_claude(cmd), encoding="utf-8")
    try:
        return place(staged, target_base(p, where) / "commands" / f"{cmd['en']}.md", p.index_dir / "快捷指令备份",
                     overwrite=overwrite)
    finally:
        staged.unlink(missing_ok=True)
