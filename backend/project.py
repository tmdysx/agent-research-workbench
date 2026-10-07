"""项目在哪、模块有哪些、每个模块里有什么。

两个位置分开记：
- CODE_DIR    本工具自己的代码（网页文件在这）
- 项目根       被治理的那个项目（资料/、笔记/、计划/、索引/ 在这；蓝图是 资料/蓝图/ 里的 S0、S1）

**一个模块 = 资料/ 下的一个文件夹 = 网页上的一页。**
想法 / 蓝图 / 戒律 / 源代码 / 测试 / 文献 / 论文 是固定模块（排最前、不能删）；实验 / 汇报 / 素材 是新项目顺手建的起步模块；以 _ 开头的（_外部资料入口）留给系统，不算模块；回收站在项目根 回收站/，不在这里。

有些文件必须待在原位（代码、AGENTS.md——别的程序靠路径找它们），搬不进模块。
那就在模块文件夹里放一个 .链接.txt，一行写一个路径（从项目根算），挂过来：
网页上照样能在这个模块里看到、能预览，原件一个字节不动。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent

# 固定模块：第二栏最前面，按这个顺序；永远在，不能删（作者 2026-09-25：「中间要固化的模块是蓝图，戒律，放第一接着是源代码，这几个不能删」）
# 09-27 加「想法」排最前：一条线 想法 → 需求 → 蓝图 → 戒律（作者：「把想法变成需求模块也要优化」）
FIXED = [("想法", "Ideas"), ("蓝图", "Blueprint"), ("戒律", "Rules"), ("源代码", "Code"),
         ("测试", "Testing"), ("文献", "Literature"), ("论文", "Paper")]
# 起步模块：新项目第一次启动时顺手建好（科研是默认场景），之后跟自己加的一样，能删、删了不自动建回来
# 09-29 加「汇报」（PPT、讲稿）「素材」（视频、录屏、剪出来的片段、图片）——作者选的：本事放底座，另加两个放东西的地方
STARTER = [("实验", "Experiments"), ("汇报", "Reports"), ("素材", "Media")]
FIXED_NAMES = [n for n, _ in FIXED]
CONTENT_NAMES = ["文献", "论文", "测试"]  # 通用内容导航；真实目录和原编号保留
# 治理工具模块：想法、蓝图、戒律、源代码本身就是管需求的工具，自己不写需求、不开工单装修。
# 10-06 文献、论文、测试也成了固定模块（不能删），但它们是装内容的，照样有自己的需求（10-07 修）
TOOL_NAMES = ["想法", "蓝图", "戒律", "源代码"]
GOVERNANCE_NAMES = FIXED_NAMES  # 七个固定模块，业务模块另列
STARTER_NAMES = [n for n, _ in STARTER]
DEFAULT_NAMES = FIXED_NAMES + STARTER_NAMES      # 工具自己建的（来源记成「默认」）
# 常见模块名的英文，文件夹里发现这些名字时自动配上（标签一律「中文 English」）
KNOWN_EN = dict(FIXED) | dict(STARTER) | {"技能": "Skill", "心得": "Insights", "测试": "Testing",
                                          "数据": "Data", "图表": "Figures", "笔记": "Notes", "PPT": "Presentation"}
INBOX = "_外部资料入口"          # 外部资料入口（缓存区）：资料/_外部资料入口/
LINKS_FILE = ".链接.txt"
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv"}

_BAD_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


@dataclass(frozen=True)
class Project:
    root: Path

    @property
    def materials(self) -> Path:
        return self.root / "资料"

    @property
    def index_dir(self) -> Path:
        return self.root / "索引"

    @property
    def db_path(self) -> Path:
        # 数据库路径可配：设了 RC_DB 就用它（桌面版会用到），否则放 索引/ 下
        env = os.environ.get("RC_DB")
        return Path(env) if env else self.index_dir / "state.db"


def resolve(project: str | None) -> Project:
    return Project(Path(project).resolve() if project else CODE_DIR)


# ---------------------------------------------------------------- 模块 = 文件夹

def check_name(name: str) -> str:
    """模块名就是文件夹名，所以得是 Windows 上合法的文件夹名。不合法就抛 ValueError，消息给人看。"""
    name = " ".join((name or "").split())
    if not name:
        raise ValueError("模块得有个名字")
    if len(name) > 40:
        raise ValueError("名字太长了，40 个字以内")
    if _BAD_CHARS.search(name):
        raise ValueError('名字里不能有 \\ / : * ? " < > | 这些符号（它要当文件夹名）')
    if name.startswith(("_", ".")) or name.endswith((".", " ")):
        raise ValueError("名字不能以 _ 或 . 开头（留给系统用），也不能以 . 结尾")
    if name.upper() in _RESERVED:
        raise ValueError(f"「{name}」是 Windows 的保留名，当不了文件夹名")
    return name


def ensure_skeleton(p: Project) -> list[str]:
    """建好 资料/ 和固定模块的文件夹（每次都补），新项目第一次还顺手建起步模块。
    返回这次新建了哪些。只建空文件夹，不碰任何已有的东西。"""
    made = []
    born = not p.materials.exists()                    # 资料/ 还没有 = 新项目第一次启动
    for name in FIXED_NAMES + (template_start_names(p.root) if born else []):
        d = p.materials / name
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            made.append(name)
    return made


def template_start_names(root: Path) -> list[str]:
    """普通文件决定模板起步模块；无配置的旧项目保持原来的科研起步方式。"""
    import json
    f = root / '模板配置.json'
    if not f.is_file():
        return STARTER_NAMES
    if f.is_symlink() or f.is_junction():
        raise ValueError('模板配置不能是链接')
    cfg = json.loads(f.read_text(encoding='utf-8-sig'))
    names = cfg.get('modules')
    if cfg.get('version') != 1 or not isinstance(names, list) or len(names) > 100:
        raise ValueError('模板配置的 modules 必须是模块名列表')
    return list(dict.fromkeys(check_name(n) for n in names))


def check_module_labels(labels: object) -> dict[str, str]:
    """标签是模板作者的明确声明，不从模块内容推断。"""
    if not isinstance(labels, dict) or len(labels) > 100:
        raise ValueError('模板配置的 module_labels 必须是模块名到英文的字典')
    result = {}
    for name, label in labels.items():
        if not isinstance(name, str) or not isinstance(label, str):
            raise ValueError('模块标签必须是文字')
        name = check_name(name)
        if len(label) > 80 or any(ord(c) < 32 for c in label):
            raise ValueError('模块英文标签须在 80 字以内且不含控制字符')
        result[name] = label.strip()
    return result


def template_module_labels(root: Path) -> dict[str, str]:
    import json
    f = root / '模板配置.json'
    if not f.is_file():
        return {}
    if f.is_symlink() or f.is_junction():
        raise ValueError('模板配置不能是链接')
    cfg = json.loads(f.read_text(encoding='utf-8-sig'))
    if cfg.get('version') != 1:
        raise ValueError('模板配置版本不支持')
    return check_module_labels(cfg.get('module_labels', {}))


# 10-07 起不再给每个模块、每个管理目录补空的 内置/（作者：「每个模块都干净一点」）：
# 带不带进新项目统一看项目根 内置标记.json，在 设置 → 内置 里按模块勾（见 builtin.py）


def module_dirs(p: Project) -> list[str]:
    """资料/ 下的模块文件夹名（不含 _ 和 . 开头的）。"""
    if not p.materials.is_dir():
        return []
    out = []
    with os.scandir(p.materials) as it:
        for e in it:
            if e.is_dir(follow_symlinks=False) and not e.name.startswith(("_", ".")):
                out.append(e.name)
    return out


def module_dir(p: Project, name: str) -> Path | None:
    """按名字找模块文件夹；名字不合法或不存在就返回 None。"""
    if not name or _BAD_CHARS.search(name) or name.startswith(("_", ".")) or name in ("..", "."):
        return None
    d = p.materials / name
    return d if d.is_dir() else None


def read_links(p: Project, name: str) -> tuple[list[str], list[str]]:
    """读模块的 .链接.txt → (能用的链接, 问题)。链接只许指向项目里面，指到外面的一律不认。"""
    d = module_dir(p, name)
    f = d / LINKS_FILE if d else None
    if not f or not f.is_file():
        return [], []
    links, probs = [], []
    root = p.root.resolve()
    for raw in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip().replace("\\", "/").strip("/")
        if not line:
            continue
        import governance_paths as gp
        try:
            target = gp.resolve(p, line)
        except ValueError:
            probs.append(f"{name}/{LINKS_FILE}：{line} 指到项目外面去了")
            continue
        if not target.is_relative_to(root) or target == root:
            probs.append(f"{name}/{LINKS_FILE}：「{line}」指到项目外面去了，不认")
        elif not target.exists():
            probs.append(f"{name}/{LINKS_FILE}：「{line}」找不到")
        else:
            links.append(line)
    return links, probs


def walk(d: Path):
    """递归列文件，跳过 . 开头的和 __pycache__ 这类杂物。"""
    stack = [d]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    if e.name.startswith(".") or e.name in SKIP_DIRS:
                        continue
                    if e.is_dir(follow_symlinks=False):
                        stack.append(Path(e.path))
                    elif e.is_file(follow_symlinks=False):
                        yield Path(e.path)
        except OSError:
            continue


def _targets(p: Project, name: str) -> list[Path]:
    d = module_dir(p, name)
    if not d:
        return []
    links, _ = read_links(p, name)
    return [d] + [p.root / l for l in links]


def module_stats(p: Project, name: str) -> dict:
    """一个模块有多少文件、多大、最近什么时候动过。挂的链接也算进去。"""
    files = size = 0
    latest = 0.0
    for t in _targets(p, name):
        for f in ([t] if t.is_file() else walk(t)):
            try:
                st = f.stat()
            except OSError:
                continue
            files += 1
            size += st.st_size
            latest = max(latest, st.st_mtime)
    links, _ = read_links(p, name)
    return {
        "files": files,
        "bytes": size,
        "latest": datetime.fromtimestamp(latest).isoformat(timespec="seconds") if latest else None,
        "links": links,
    }


