---
name: mh-paper-aris-module-idea-discovery-robot
description: "按机器人实体、传感、任务和基准约束筛选想法，优先仿真或已有离线证据。"
license: MIT
---

# 机器人选题与仿真验证计划

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

任务族、机器人实体/执行器、传感器、控制/策略接口、可用仿真器/基准/离线数据和资源约束。

## 方法

1. 写机器人问题框架：实体、任务、感知—动作瓶颈、时间/安全约束、数据来源与 sim2real 风险；缺项明确假设。
2. 建立文献矩阵，逐篇记录实体、传感、任务、控制范式、benchmark、成功与失败指标，核查相同名称是否实际相同设置。
3. 候选必须落到具体可用基准/仿真器及明确 baseline，说明改进哪个失败模式；仅把 VLM/扩散模型套到机器人上不自动成为贡献。
4. 制定 simulation-first 或离线回放 pilot，列成功率以外的碰撞、干预、延迟、能耗或其它任务相关失败指标。
5. 按实体、任务、基准、传感和控制策略共同核查新颖性；可比较仿真差异，但不能用仿真性能代替真实硬件可靠性。
6. 已有可用且获准环境时执行当前小试验，否则交具体 pilot 计划；需硬件的候选标为“待物理验证”，保留独立审查未做状态。

## 产物与验收

机器人候选卡、benchmark/baseline 矩阵、pilot 协议与 sim2real/硬件证据缺口；验收每项有明确实体、失败指标与可检验环境，未跑不算验证。

## 依赖与边界

仿真器、机器人软件、离线数据、外部模型与 GPU 的准备状态须据实查。入口不启动机器人、硬件试验、网络下载或云租用；物理操作须已在当前任务授权中。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [output-language.md](references/support/skills/shared-references/output-language.md)
- [output-versioning.md](references/support/skills/shared-references/output-versioning.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/idea-discovery-robot/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
