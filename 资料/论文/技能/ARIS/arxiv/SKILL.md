---
name: mh-paper-aris-module-arxiv
description: "按检索式或论文 ID 获取 arXiv 元数据，并在获准范围保存原文。"
license: MIT
---

# arXiv 检索与原文获取

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

检索词或准确 arXiv ID、年份/类别等范围、结果上限，以及需要仅元数据还是原文下载。

## 方法

1. 先区分 ID 获取与主题检索；准确 ID 直接核对论文，主题检索用可复查关键词和筛选条件，不把一次排序当穷尽综述。
2. 经可用检索入口读取 Atom 元数据，保留标题、作者、摘要、发布日期/更新日、版本、abs 与 PDF 链接。
3. 按问题相关性筛选，区分预印本版本与另有出版信息的版本；不存在的 ID、空结果或网络限制如实记录。
4. 需要且已获准下载时只保存选定 PDF 到明确目录，核对文件实际存在与可读性；不批量抓取未要求的论文或私人库。
5. 阅读已取得文本后写问题、方法、主要证据与局限，注明只读摘要或已读原文；知识库写入仅使用当前项目已有授权入口。

## 产物与验收

检索记录与论文身份表；下载分支另有真实文件清单；解读标明阅读深度。验收核对 ID/版本/来源和实际下载数，不把空文件或链接当作已取得原文。

## 依赖与边界

在线获取需要 arXiv 服务和网络工具；上游 arxiv_fetch.py/research_wiki.py 并未在方法包中安装。用户提供的论文可用本地阅读步骤处理。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/arxiv/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
