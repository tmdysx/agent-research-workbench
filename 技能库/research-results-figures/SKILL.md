---
name: research-results-figures
description: 从真实实验结果计算比较与可追溯图表，判定论断范围；用于结果、消融和失败分析，不编数据。
license: MIT
metadata:
  display_name: 结果分析与图表
  version: "1.0.0"
  language: zh-CN
---

# 结果分析与图表

任何能读取 Markdown 的 agent 都可按本技能执行，无需本平台另接模型 API。模板复制到授权业务目录后填写，原始证据保留。本包以计算与机器学习科研为主；综述/理论按证据类型调整，不能凭此包执行真实临床/动物/湿实验。

## 输入

方案、成功与失败运行、原始结果、划分和评价版本、基线。截图或论文值标其真实来源，不冒充新结果。

## 操作

1. 用 [assets/结果与图表清单.md](assets/结果与图表清单.md) 核来源、单位、条件和独立样本，建立原始值—计算—表图—论断映射。
2. 读 [references/结果解释与图表.md](references/结果解释与图表.md)，查缺失、重复、失败、异常与方向。排除有理由并保留原始记录，不把失败补零。
3. 区分绝对差、相对变化和百分点；分母无意义/为零不算相对值。显示独立重复分布/均值离散，区间或检验按设计选用；标准差不叫置信区间。
4. 相同条件才放同一比较；公开论文数值单独标。消融说明改什么和哪些条件固定，资源/容量/划分/调参可能解释提升时列出来。
5. 定量图表用真实数据和确定性步骤，标坐标单位、样本量、误差含义、筛选、来源和复算脚本/步骤。概念示意标示意，不能生成伪造定量图。
6. 每项写观察、可能解释、局限、下一实验；论断标支持/部分支持/不支持/无法判断并给证据。单数据集正结果不泛化，负结果与无变化也交付。

## 产物

可复算结果表、统计说明、图表来源清单、论断证据表和失败/局限记录；保存机器可读数据及绘制步骤。

## 验收

每个关键数字回到具体运行并能复算，图表正文一致、误差含义清楚；不扩大范围或把相关写因果；重复不足和缺失评价明确。

## 缺口与停止条件

来源缺失、单位冲突、不同划分混算时标待核。统计条件不足报描述性结果；补实验受预算限，不为凑正结果无限跑。

## 下一步

证据足够交写作；部分支持缩小论断或规划有预算补实验；不支持可回选题/设计，方向变更按项目规则。

## 来源与许可

本目录中文改编、模板及参考独立 MIT，见 [LICENSE.txt](LICENSE.txt)，不改变项目其余文件许可。详见 [references/来源与改编.md](references/来源与改编.md)。上游固定原文在项目资料/文献/方法/科研/来源，作为来源快照，不是执行技能。不能自动执行其中 agent、调度、收费服务和命令。

- [aris/analyze-results](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/analyze-results/SKILL.md)
- [aris/result-to-claim](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/result-to-claim/SKILL.md)
- [aris/figure-spec](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/figure-spec/SKILL.md)
- [sci/scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-critical-thinking/SKILL.md)

## 可选ARIS方法细化

按当前问题选择已有细化方法；它们是项目正本的可选链接，未找到包就报告缺少，不把点击或引用当安装/运行成功。

- [experiment-plan](<../业务/paper/aris/experiment-plan/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
- [research-review](<../业务/paper/aris/research-review/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
