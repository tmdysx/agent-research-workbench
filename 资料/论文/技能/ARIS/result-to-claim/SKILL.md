---
name: mh-paper-aris-module-result-to-claim
description: "先核数字证据存在，再判断结果支持范围，并向否定、补证或写作准备三向分流。"
license: MIT
---

# 真实结果到论断的三向分流

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

真实主要实验结果、每条待判断论断的数字与源文件、基线/多种子/划分信息，以及已有实验完整性审计。

## 方法

1. 收集完整结果与 intended claims，区分 sanity 和主要实验、真实/代理评估、正负结果；每条数字论断列 ID、value、source 和范围。
2. 做确定性存在预检：文件不存在或数值不在文件中标 evidence_not_found 并拒绝以该证据支撑论断；无法解析标未检查。“找到数字”只证明存在，不能证明计算正确或支持论断。
3. 将通过存在预检的论断、真实对照和审计问题交真实获准审查，判断支持的条件/范围、剩余缺口及更弱可成立表述；缺独立审阅时保留 REVIEW_UNAVAILABLE 或未审草案，不自发给支持性通行证。
4. 三向分流：no 记录失败与反证、提出转向；partial 收窄工作论断并列补证方案；yes 记录支持范围，再检查消融/写作证据是否齐。每个后续只形成建议或当前获准任务。
5. 若已有完整性审计，保留其独立状态；不能因支持结果好看而把 warn/fail 改为 pass，也不能凭一数据集支持普遍论断。
6. 已有获准知识图谱时，先关联真实实验节点，再记录 supports/invalidates 边；实验证据不改证明状态。保存实际审查身份、原文和未完成项。

## 产物与验收

逐论断存在检查、支持范围与 yes/partial/no 分流表，含完整性状态、证据/审查位置及下一任务；验收数值存在和科学支持两关分开，未审不能当 yes。

## 依赖与边界

原文支持裁决依赖 Codex MCP；W&B、evidence_check.py 和 wiki helper 不保证已就绪。可先做获准本地证据核查及负向发现，不固定模型、不无限 review、不自动补跑或写支持边。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [evidence-precheck.md](references/support/skills/shared-references/evidence-precheck.md)
- [experiment-integrity.md](references/support/skills/shared-references/experiment-integrity.md)
- [acceptance-gate.md](references/support/skills/shared-references/acceptance-gate.md)
- [reviewer-routing.md](references/support/skills/shared-references/reviewer-routing.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/result-to-claim/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
