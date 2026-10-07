---
name: mh-paper-aris-module-wiki-enrich
description: "在保留论文身份、原摘要和图关系的前提下补全既有页面的空白解读。"
license: MIT
---

# 已建论文页的忠实补全

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

获准的已有论文页、明确待补的 TODO 章节、原文/摘要与已有项目背景；是否允许覆盖已有解读需当前任务明确。

## 方法

1. 逐页核对 node_id、标题和原来源，只选择 TODO 空节；已有正文默认跳过，没有现成 wiki 不自动建库。
2. 来源按可得性由 overview、全文/brief 深化，最后才用 arXiv 或页内原摘要；记录实际来源，二手摘要和只读摘要的边界明确。
3. 分别补一句话机制、问题/缺口、方法、关键结果、假设、限制、可复用部件和开放问题；数字与单位照来源，未提及内容写“来源未说明”。
4. Claims 只引用已存在的图关系，项目相关性只依据给定简报/缺口；缺上下文写未设定，不自行制造 claim 节点或项目方向。
5. 只替换唯一匹配的标题+TODO，保留 YAML、Connections 与 Abstract (original)；记录每页实际来源与补过/跳过章节。

## 产物与验收

逐页补全记录与可审差异、来源/阅读深度和仍缺内容；验收元数据、原摘要、图生成关系不变，既有解读未被默认覆盖。

## 依赖与边界

AlphaXiv/arXiv/DeepXiv 与 research_wiki.py 是原文获取/记账依赖；不保证就绪，不自动开 cron。当前单任务可以对已提供原文补全获准页面。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [output-language.md](references/support/skills/shared-references/output-language.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)
- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/wiki-enrich/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
