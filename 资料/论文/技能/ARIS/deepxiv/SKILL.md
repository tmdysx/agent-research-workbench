---
name: mh-paper-aris-module-deepxiv
description: "使用 DeepXiv 的摘要、结构与分节读取层次回答具体文献问题。"
license: MIT
---

# 论文渐进检索与分节阅读

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

主题查询或论文 ID、要回答的问题，以及需要 brief、head、section 或 trending 等哪一种访问。

## 方法

1. 选择与当前问题匹配的访问模式；论文解释先读 brief，定位证据先读 head 章节地图，不默认取整篇或全部热门论文。
2. 核对搜索结果的论文身份和来源，按章节地图选方法、实验或限制等目标 section，记录实际可得内容。
3. 将摘要判断逐步深化到正文段落；用检索时的题名、ID、章节和来源版本定位证据，保留跨层结论变化。
4. trending 或 web-search 结果只作发现线索；出版 venue、引用等元数据在必要时用原出版页面或可用结构化来源核对。
5. 入口或章节不可得时说明失败及未读范围；若任务要求知识库更新，交付已核身份的阅读卡，不自行补装 CLI。

## 产物与验收

分层阅读记录、所读章节与证据卡，包含尚未读到的章节和来源限制；验收能追踪每个回答来自哪一层。

## 依赖与边界

实际在线访问依赖 deepxiv-sdk/DeepXiv CLI 与上游 deepxiv_fetch.py；均不保证已安装。可对用户已提供的分节文本应用同一阅读方法。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/deepxiv/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
