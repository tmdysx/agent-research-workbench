---
name: mh-paper-aris-module-research-refine
description: "将模糊方向细化为有输入输出、训练推理路径和可反证论断的聚焦方法。"
license: MIT
---

# 问题锚定的最小机制细化

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

用户原问题与不能改变的约束、非目标、已有相关方法/失败证据，以及资源和验收条件。

## 方法

1. 冻结问题锚点：必须解决的瓶颈、非目标、资源限制和成功证据；后续建议若改变它，标明方向漂移而不静默替换。
2. 读取相关方法、训练设置与失败模式，找出当前流水线在哪一步失败、朴素修复为何不够，提出最小足够干预。
3. 必要时比较最小机制与确有作用的前沿技术路线，选择主导贡献和复杂度预算；两路都弱则重想问题，不默认合并为大系统。
4. 把方法写到可实现：模块/数据流、表征、监督与损失、训练阶段、推理路径、组件角色、失败处理以及复用部分。
5. 提出验证机制的最小主实验、删除/简化对照和反证条件；实验为机制服务，不让实验菜单替代方法细节。
6. 针对实际收到的审查逐项修订并保存版本、未解决风险与停点；限定本次修订范围，外部审查不存在时标为待审，不自行循环到高分。

## 产物与验收

问题锚点、具体最终方案、机制—证据映射、删去的复杂度与修订记录；验收别人能复述实际训练/推理步骤，且没有把未跑设想写成发现。

## 依赖与边界

原文使用多轮 Codex MCP 评审与最新文献核验；本入口不固定模型或分数阈值、不移植自动停止/续跑权限。可先完成本地方案，独立评审实际未做时据实说明。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [taste-calibration.md](references/support/skills/shared-references/taste-calibration.md)
- [output-language.md](references/support/skills/shared-references/output-language.md)
- [output-versioning.md](references/support/skills/shared-references/output-versioning.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/research-refine/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
