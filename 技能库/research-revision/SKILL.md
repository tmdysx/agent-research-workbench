---
name: research-revision
description: 把本稿审稿意见逐条映射到修改、补实验、正文位置和有据回复；保留原意见，不自动发送。
license: MIT
metadata:
  display_name: 返修与回复
  version: "1.0.0"
  language: zh-CN
---

# 返修与回复

任何能读取 Markdown 的 agent 都可按本技能执行，无需本平台另接模型 API。模板复制到授权业务目录后填写，原始证据保留。本包以计算与机器学习科研为主；综述/理论按证据类型调整，不能凭此包执行真实临床/动物/湿实验。

## 输入

获准处理的本稿审稿意见、投稿版本、编辑要求期限、现有证据和预算。第三方保密审稿文件未授权不读不存。

## 操作

1. 原意见完整只读保留，按审稿人/原编号拆问题，别漏编辑意见；用 [assets/返修矩阵.md](assets/返修矩阵.md) 连问题、行动、证据与新稿位置。
2. 分类为表述、方法证据、统计比较、图表引用或超范围。查真实记录，区分已做未说明、需新做、无法完成、不同意有据。
3. 排顺序预算；补实验回设计技能，标返修后提出，不倒写原计划；真正运行后再写结果，不承诺成已完成。
4. 稿件分版留差异、正文图表附件同步核；新论断有据，不删负结果或虚构满足要求。
5. 回复按问题→行动或有据不同意→证据→新稿页行节。最终渲染后核页行，草稿行号不充数。
6. 按当期期刊规则备标记稿、清稿、回复及附件，全原意见均有回应；未解决写作者待判断，不冒充编辑决定和录用。
7. 正式第三方保密审稿不同于自己的返修，须编辑/作者授权及政策允许；托管 agent 读本地稿可能是外部处理。本包执行自己的返修或公开练习。

## 产物

只读原意见、返修矩阵、分版稿件、补实验记录、回复草稿、本地返修包和缺口。

## 验收

每条意见找到回应、新稿位置与真证据，新实验真跑，异议有理由；清稿标记稿回复附件版本一致，不能隐藏无法满足项。

## 缺口与停止条件

保密授权、关键证据、预算或争议缺口具体记录；到期限/预算交接，不自动申请延期、发回复或上传。拆意见不能改删原文件。

## 下一步

交作者确认与其授权操作者提交；不自动发邮件或投稿。实质问题回对应阶段并复核整矩阵。

## 来源与许可

本目录中文改编、模板及参考独立 MIT，见 [LICENSE.txt](LICENSE.txt)，不改变项目其余文件许可。详见 [references/来源与改编.md](references/来源与改编.md)。上游固定原文在项目资料/文献/方法/科研/来源，作为来源快照，不是执行技能。不能自动执行其中 agent、调度、收费服务和命令。

- [aris/rebuttal](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/rebuttal/SKILL.md)
- [aris/resubmit-pipeline](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/resubmit-pipeline/SKILL.md)
- [sci/peer-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/peer-review/SKILL.md)

## 可选ARIS方法细化

按当前问题选择已有细化方法；它们是项目正本的可选链接，未找到包就报告缺少，不把点击或引用当安装/运行成功。

- [rebuttal](<../业务/paper/aris/rebuttal/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
