---
编号: T13
名字: Mermaid
类别: 技术栈
一句话: 几行字画出流程图、思维导图（速读的导图、图解里的流程）
检查: 文件 工具库/下载/mermaid/mermaid.min.js
在哪: 工具库/下载/mermaid
配套技能:
---
# T13 Mermaid

## 用在哪

- 速读的思维导图、图解里的流程图（文献蓝图 S2-12）

## 为什么要

- 速读.md 里 agent 写几行 ```` ```mermaid ```` 就出一张思维导图（文献蓝图 S2-12）——小绿鲸的「导图」由 agent + 它替代
- 开源（MIT），放在应用里不联网

## 装在哪

已经下好了（09-27，作者授权，版本 12.0.0，一个文件 5.6 MB）：`工具库/下载/mermaid/mermaid.min.js`，来源和校验见 `工具库/下载/清单.md`。

## 怎么调

- 网页加载 `/lib/mermaid/mermaid.min.js`，`mermaid.initialize({startOnLoad: false})`，对 `pre.mermaid` 调 `mermaid.run()`

## 改动注意

- 升级大版本先问人
