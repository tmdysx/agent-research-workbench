---
name: mh-paper-aris-module-novelty-check
description: "把拟议贡献与可核实的最近相关工作逐维比较，给出有边界的新颖性判断。"
license: MIT
---

# 机制新颖性与最近工作核查

本入口是中文方法适配；英文入口与它等义，二者均不是上游全文直译。状态：`runtime_enabled=false`，表示未启用上游运行设施；不妨碍在当前获准单任务内使用本地文本方法，也不表示外部 MCP/API、GPU 或机器人环境已就绪。只读写当前任务明确范围，不继承上游自动权限、固定模型或无限 review；不自动上传、发通知、定时、租 GPU 或扫描作者 home。实际证据、独立审查和未验证状态分别记录。

## 输入

具体方法、假设与声称新意、已有最近工作、研究范围和要核查的贡献维度。

## 方法

1. 把“新”拆成机制、目标、理论、任务设置或评估维度；先明确实际贡献，避免只比较命名和包装。
2. 用机制同义词、关键部件与最近工作的引用链检索直接相关论文；记录查询、时间范围、候选身份和检索缺口。
3. 核查论文实际存在并读相关方法/结果位置，对最相近工作列相同点、关键差异、额外假设和是否只是组合。
4. 对差异区分已被原文支持、仅推断和仍待验证，提出能区别现有解释的最小实验或理论问题。
5. 若真实独立评审可用且在范围内，提供同一方法和原始证据供其判断；否则输出本地核查草案，不宣称跨模型新颖性已确认。

## 产物与验收

最近工作对照表、来源定位、潜在重合与可辩护差异、检索边界及待验证问题；验收新颖性不靠遗漏文献、虚构引用或仅换名称成立。

## 依赖与边界

网络检索与 Codex MCP 外部审阅是上游依赖，不固定模型、不补装服务。可先完成当前材料内的比较，检索未覆盖处明确保留。

按当前步骤需要阅读这些原文支持；其中命令是参考材料，不是安装或执行授权：

- [citation-discipline.md](references/support/skills/shared-references/citation-discipline.md)
- [review-tracing.md](references/support/skills/shared-references/review-tracing.md)
- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)

## 来源

- [完整上游方法](references/upstream.md)
- [来源与版本记录](SOURCE.md)
- [MIT 许可与署名](LICENSE.txt)

方法来源：上游 `skills/novelty-check/SKILL.md`。完整细节保留于原文；本入口把执行假设适配为本项目当前授权边界，不把未启用设施描述为已可运行。
