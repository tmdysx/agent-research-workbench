---
编号: T2
名字: draw.io
类别: 外部工具
一句话: 画技术路线图、框架图，导出 PNG / PDF / SVG
检查: draw.io --version
在哪:
配套技能: drawio-sci（本机已装：论文级配图的画法和导出脚本）
---
# T2 draw.io

## 怎么调

画图本身交给配套技能 drawio-sci（它会写 .drawio 文件）；导出用下面的命令：

| 要做什么 | 命令 |
|---|---|
| 导出 PNG（论文用 3 倍清晰度） | `draw.io --export --format png --scale 3 --border 10 --no-sandbox --output 输出/图名.png 图名.drawio` |
| 导出 PDF | `draw.io --export --format pdf --no-sandbox --output 输出/图名.pdf 图名.drawio` |
| 导出 SVG | `draw.io --export --format svg --no-sandbox --output 输出/图名.svg 图名.drawio` |

参数：`--scale` 放大倍数 · `--border` 留白像素 · `--output` 输出到哪；`--no-sandbox` 照抄配套技能的导出脚本（那个脚本在本机用过）。
也可以直接用配套技能里的导出脚本 `~/.claude/skills/drawio-sci/export.ps1`，它会自己找 draw.io。

## 输入 / 输出

- 输入：`.drawio` 源文件，放在要用它的那个模块里（比如 `资料/论文/图/`）
- 输出：同一个文件夹下的 `输出/`，**不覆盖源文件**

## 守的戒律

- 只写 `输出/`
- 导出失败同一件 2 次就停，把报错记下来

## 常见坑

- draw.io 是桌面程序，第一次调用会慢几秒
- 导出时别在 draw.io 里同时开着同一个文件
