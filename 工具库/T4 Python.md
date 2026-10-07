---
编号: T4
名字: Python
类别: 外部工具
一句话: 跑脚本、跑实验、跑测试
检查: python --version
在哪: %LOCALAPPDATA%\Programs\Python\Python312
配套技能:
---
# T4 Python

## 怎么调

| 要做什么 | 命令 |
|---|---|
| 跑一个脚本 | `python 脚本.py` |
| 跑测试 | `python -m pytest` |
| 看装了哪些库 | `python -m pip list` |

## 守的戒律

- **装新库、升级库之前先问人**：改环境不是没影响的操作，可能让别的项目跑不起来
- 实验结果只来自真跑出来的输出，不编数字（戒律 通-8）

## 常见坑

- **本机新开的窗口找不到 python**（PATH 里 Python 那几行是乱码）：用上面「在哪」里的完整路径 `…\Python312\python.exe`
- 输出中文乱码时加 `-X utf8`：`python -X utf8 脚本.py`
