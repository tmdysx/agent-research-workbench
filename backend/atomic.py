"""写文件的最后一步：临时文件换成正式文件（先写 .tmp 再换，写到一半断电也不会留下半个文件）。

Windows 上正式文件这一刻正被别的程序读着（网页自己刷新、git 记账、另一个 agent、杀毒软件），换的时候会「拒绝访问」——
稍等再试，最多约 2 秒。几个 agent 一起干时更常见（2026-09-30 交 J17 时撞上过一次：交付单写好了、蓝图那一格没改上）。
不 import 项目里别的模块，谁都能用。
"""
from __future__ import annotations

import os
import time


def replace(src, dst, tries: int = 10) -> None:
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.05 * (i + 1))
