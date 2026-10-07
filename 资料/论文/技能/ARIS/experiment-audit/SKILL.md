---
name: mh-paper-aris-module-experiment-audit
description: "定位真值、指标、结果文件和代码路径中的完整性风险，区分自查与真实独立审查。"
license: MIT
---

# 实验完整性证据审计

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

当前获准范围的评估/数据加载代码、真实结果文件、数据划分与真值来源、论文论断及已有运行记录。

## 方法

1. 先列出评估脚本、数据入口、结果和论断文件及版本，保留原始材料；需要独立审查时向审查者提供路径和检查问题，不附引导其通过的辩护。
2. 核对真值是否来自真实数据集/既定标准，是否将模型自身或另一模型输出冒充真值；合成 proxy 明确标注用途。
3. 检查指标定义、分母与归一化，排查以本模型最大值自归一化制造高分及各系统口径不一致。
4. 核对文件存在、数字确在结果中、代码实际走到计算路径；区分假想结果、未运行死分支和可追溯真实输出。
5. 评估数据/场景范围是否足以支撑所述泛化，报告 real_gt、synthetic_proxy 等评估类型与逐项 PASS/WARN/FAIL 或未检查状态。
6. 把问题映射到具体论断和修复建议；只有真实独立审查已完成才标独立结论，未审/失败不因原文“advisory”而被升级为已通过。

## 产物与验收

有 file:line/结果位置证据的完整性报告，含评估类型、真值/归一化/存在性/死代码/范围检查及论断影响；验收未检查项与独立审阅缺口明确。

## 依赖与边界

上游 Codex/Manual/Oracle MCP 审查与 trace helper 均不自动启用。当前本地自查可找问题，不能自称跨模型独立审计已完成；原脚本未打包或未跑不宣称其门控通过。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [experiment-integrity.md](references/support/skills/shared-references/experiment-integrity.md)
- [reviewer-independence.md](references/support/skills/shared-references/reviewer-independence.md)
- [acceptance-gate.md](references/support/skills/shared-references/acceptance-gate.md)
- [review-tracing.md](references/support/skills/shared-references/review-tracing.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/experiment-audit/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
