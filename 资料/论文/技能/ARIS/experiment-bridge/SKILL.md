---
name: mh-paper-aris-module-experiment-bridge
description: "把已批准实验矩阵落实为可核对的代码/环境契约、小样检查和初始结果交接。"
license: MIT
---

# 实验计划到代码契约与初始证据

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

获准的最终方案、实验计划/跟踪表、研究论断契约、允许修改文件、已有代码/数据、运行环境与预算。

## 方法

1. 从计划逐项提取任务/划分、比较系统、指标、超参数、种子、判据、必须跑项和阶段顺序；缺论断契约先补对应草案，不能额外发明实验。
2. 写代码契约：方法部件对应哪些文件、训练/评估入口、参数接口、固定但可控种子、JSON/CSV 输出和版本记录；优先复用获准现有代码。
3. 评估所有系统用同一数据真值和相同划分/指标；监督、拟合与测试职责分清，不能把模型输出充当 ground truth 或偷改指标。
4. 以环境说明绑定代码版本、Python/依赖阶段、数据和命令，区分包导入、训练小样、实际任务三层检查；先完成可用环境的小样并记录实际结果。
5. 只有小样实际通过且当前运行范围获准时，再按 sanity→baseline→main→ablation 次序落实本次运行；独立代码审查缺席如实标注，缺环境则交契约和未跑计划。
6. 收集初始 JSON/CSV/日志并关联 run ID、配置、真值口径和失败原因，交给结果—论断判断；W&B、自动消融、通知、远端队列都不默认连动。

## 产物与验收

方法—代码—命令—数据—结果契约、实际小样记录、初始结果/失败表和未跑清单；验收能追到真实来源，小样通过不等于主实验或整链已完成。

## 依赖与边界

本方法包不安装训练器、队列、W&B 或 Codex 审查，不自动 clone 外部项目、SSH 上传、租 Vast/Modal GPU 或发通知。运行只使用当前任务已经授权并实际可用的环境。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [compute-env-contract.md](references/support/skills/shared-references/compute-env-contract.md)
- [experiment-integrity.md](references/support/skills/shared-references/experiment-integrity.md)
- [RESEARCH_CONTRACT_TEMPLATE.md](references/support/templates/RESEARCH_CONTRACT_TEMPLATE.md)
- [SESSION_RECOVERY_GUIDE.md](references/support/docs/SESSION_RECOVERY_GUIDE.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/experiment-bridge/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
