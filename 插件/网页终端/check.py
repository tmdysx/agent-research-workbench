"""网页终端的检查：这台电脑能不能用——pywinpty 装没装、画终端的 xterm.js 在不在。退出码 0 = 能用。"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
LIBS = (HERE / "lib", HERE.parent.parent / "工具库" / "下载" / "xterm")   # 自己的 lib/ 或工具库里应用带的那份
miss = []
try:
    import winpty  # noqa: F401
except ImportError:
    miss.append("pywinpty（在 Windows 上开终端）")
gone = [f for f in ("xterm.js", "xterm.css", "addon-fit.js") if not any((d / f).is_file() for d in LIBS)]
if gone:
    miss.append("工具库/下载/xterm/ 里的 " + "、".join(gone) + "（网页里画终端）")
if miss:
    print("还缺：" + "；".join(miss) + "。装法见 插件.md")
    sys.exit(1)
print("能用")
