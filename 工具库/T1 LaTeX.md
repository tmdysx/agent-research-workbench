---
编号: T1
名字: LaTeX
类别: 外部工具
一句话: 把 .tex 编成 PDF（中文用 xelatex）
检查: latexmk -v
在哪:
配套技能:
---
# T1 LaTeX

## 怎么调

在 .tex 所在的文件夹里跑（路径有中文时用相对路径最稳）：

| 要做什么 | 命令 |
|---|---|
| 编译成 PDF | `latexmk -xelatex -interaction=nonstopmode -file-line-error -outdir=输出 主文件.tex` |
| 清掉中间文件 | `latexmk -c -outdir=输出 主文件.tex` |

参考文献用 biber / bibtex 的，latexmk 会自己多跑几遍，不用手动。

## 输入 / 输出

- 输入：`资料/论文/` 里的 `主文件.tex`（和它引用的 .bib、图）
- 输出：同一个文件夹下的 `输出/`：PDF 和所有中间文件都在这，**不写到源文件旁边**

## 守的戒律

- 只写 `输出/`；不改 .tex 源文件——要改稿，先写进计划
- 编译失败：把 `输出/主文件.log` 最后 30 行记下来（自动转圈时记进这次的自动化日志，手动时贴给人看）；**同一件失败 2 次就停**，不反复重试

## 常见坑

- 中文必须 xelatex + ctex 宏包，pdflatex 编不了中文
- latexmk 开头会打印「Initial Win CP…」两行，是它在切换代码页，不是报错
- 本机新开的窗口可能找不到 latexmk（PATH 有乱码）：用上面「在哪」里的完整路径
