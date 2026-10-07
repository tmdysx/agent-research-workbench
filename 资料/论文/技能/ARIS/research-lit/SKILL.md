---
name: mh-paper-aris-module-research-lit
description: "在指定范围检索和核实候选论文，按方法与证据综合一致、争议和缺口。"
license: MIT
---

# 多源文献检索、核实与综合

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

研究问题、检索范围和筛选标准、已提供材料，以及明确选择的外部来源和是否需要下载原文。

## 方法

1. 先查给定本地材料和获准知识库，记录每个来源的范围。按用户选择确定外部数据库；原文 all 不包含需明确启用的 S2/DeepXiv/Exa/Gemini/OpenAlex，不将名称误解成全部服务授权。
2. 以可复查关键词、时间范围、查询和筛选理由检索；保留缺来源/网络失败与覆盖缺口，不把排序前几篇当系统综述的完整证据。
3. 核实全部候选的题名、作者、ID/DOI 与版本，合并预印本和出版记录时留关联；未核论文仍列出但隔离于可引用论据。
4. 逐篇提取问题、方法、关键结果、假设、限制和可复用机制，科学论断与数字回到原文位置，模型摘要不作最终证据。
5. 按研究问题分组，区分共识、矛盾、设置不可比与真实缺口；比较方法和评估条件，避免只堆论文名单。
6. 交付来源明确的综述和下一步阅读表；只有获准下载/已有知识库写入时再落实对应动作，缺失入口不伪称成功。

## 产物与验收

检索/筛选记录、核实与未核论文表、方法证据矩阵和综合结论；验收每个关键结论有来源，覆盖限制和未读全文项显式保留。

## 依赖与边界

多源 MCP/API/helper 均按实际可用性与当前授权使用；方法包不扫描作者私人论文库、不自动批量下载、写 Obsidian/Zotero、调用额外模型或启动子流水线。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [citation-discipline.md](references/support/skills/shared-references/citation-discipline.md)
- [fan-out-pattern.md](references/support/skills/shared-references/fan-out-pattern.md)
- [output-composition.md](references/support/skills/shared-references/output-composition.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/research-lit/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
