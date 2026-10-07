---
name: research-topic
description: 将研究兴趣或观察变成有证据边界、可反驳预测和可行性说明的选题；用于开题，不把候选假设当发现。
license: MIT
metadata:
  display_name: 选题与假设
  version: "1.0.0"
  language: zh-CN
---

# 选题与假设

任何能读取 Markdown 的 agent 都可按本技能执行，无需本平台另接模型 API。模板复制到授权业务目录后填写，原始证据保留。本包以计算与机器学习科研为主；综述/理论按证据类型调整，不能凭此包执行真实临床/动物/湿实验。

## 输入

兴趣方向、真实观察或公开文献；时间、数据、设备和学科背景。观察带来源、单位和不确定性，区别文献报告、自己观测与推测。

## 操作

1. 用 [assets/选题卡.md](assets/选题卡.md) 将兴趣缩成一个对象、条件、比较和结果明确的问题。机器学习可问固定预算下效果与代价如何，不能预先保证提升。
2. 读 [references/问题与反证.md](references/问题与反证.md)，分开问题、候选假设、替代解释、预测、测量和证据；无真实观察的方案标为探索性。
3. 检索最近似公开研究，保留查询、日期、已读来源和相似点；未找到写本次检索未发现，不能写从没人做或新颖性已证实。交文献证据技能核原文。
4. 设计能区分解释的最小检查，说明支持、反对和仍无法判断各是什么结果。理论写反例与证明义务，综述写范围和可比较证据。
5. 按价值、数据可得、复现基础、资源和难点说明取舍；既定授权内继续。改变目标或扩大方向按项目方向变更规则处理。

## 产物

选题卡、近似研究比较、最小验证方案。候选想法仍标候选，不覆盖既定目标。

## 验收

人能说清要回答什么、别人已有哪部分、什么会反对解释、资源够不够。至少有可反驳预测；缺口有来源或明确待核。不能看过测试成绩后倒写成预设假设。

## 缺口与停止条件

无合法数据、超预算或领域判断不足时先做公开文献与设计。试点到预算/重试上限即总结。负结果保留，缩小问题有理由；机制不能编造。

## 下一步

问题明确进入文献与证据；已有充分证据表则进入数据与实验设计。

## 来源与许可

本目录中文改编、模板及参考独立 MIT，见 [LICENSE.txt](LICENSE.txt)，不改变项目其余文件许可。详见 [references/来源与改编.md](references/来源与改编.md)。上游固定原文在项目资料/文献/方法/科研/来源，作为来源快照，不是执行技能。不能自动执行其中 agent、调度、收费服务和命令。

- [sci/hypothesis-generation](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/hypothesis-generation/SKILL.md)
- [aris/idea-discovery](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/idea-discovery/SKILL.md)
- [aris/novelty-check](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/novelty-check/SKILL.md)

## 可选ARIS方法细化

按当前问题选择已有细化方法；它们是项目正本的可选链接，未找到包就报告缺少，不把点击或引用当安装/运行成功。

- [idea-discovery](<../业务/paper/aris/idea-discovery/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
