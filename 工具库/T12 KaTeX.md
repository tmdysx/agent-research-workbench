---
编号: T12
名字: KaTeX
类别: 技术栈
一句话: 把 $…$ 公式排成论文里那样（译文、速读、笔记、图解里都用）
检查: 文件 工具库/下载/katex/katex.min.js
在哪: 工具库/下载/katex
配套技能:
---
# T12 KaTeX

## 用在哪

- 译文、速读、笔记、图解里的公式（文献蓝图 S2-11）

## 为什么要

- 读论文少不了公式：译文、速读、笔记里写 `$…$`、`$$…$$`，网页上照论文的样子显示（文献蓝图 S2-11）
- 快、小、开源（MIT），放在应用里不联网

## 装在哪

已经下好了（09-27，作者授权，版本 0.18.9）：`工具库/下载/katex/`（katex.min.js、katex.min.css、contrib/auto-render.min.js、fonts/），来源和校验见 `工具库/下载/清单.md`。

## 怎么调

- 网页从 `/lib/katex/` 加载 `katex.min.css`、`katex.min.js`、`contrib/auto-render.min.js`，对译文那块调 `renderMathInElement(el, {delimiters: [...]})`
- 图解页里同样从 `/lib/katex/` 加载

## 改动注意

- 升级先问人
