---
name: research-manuscript-citations
description: 依据真实方法结果与定位文献组织论文并核引用和数值；用于草稿修订，不编实验、作者声明或批准。
license: MIT
metadata:
  display_name: 论文写作与引用
  version: "1.0.0"
  language: zh-CN
---

# 论文写作与引用

任何能读取 Markdown 的 agent 都可按本技能执行，无需本平台另接模型 API。模板复制到授权业务目录后填写，原始证据保留。本包以计算与机器学习科研为主；综述/理论按证据类型调整，不能凭此包执行真实临床/动物/湿实验。

## 输入

问题、真实方法记录、结果图表、论断证据表、已有稿件和目标文体。缺项记缺口，不凭经验补样本量、数字或伦理批准。

## 操作

1. 读 [references/证据到正文.md](references/证据到正文.md)，按学科/真实设计定提纲；用 [assets/论文核验表.md](assets/论文核验表.md) 列每节目的、论断、来源与未定问题。
2. 仅从证据展开：方法写实际做法，结果保留负/无变化与不确定性，讨论区分解释观察，结论限制到数据和设计。事后探索明确标注。
3. 论断连接现有来源编号和页/节/图/表，数字连运行及提取步骤；沿用本项目完整来源，不新造全局编号。
4. 核引用身份版本、支持关系和格式。DOI/BibTeX 不代表支持已核，无全文和作者未核分别标；不编作者年份、页码、DOI或引文。
5. 核标题摘要正文表图附件中的对象、样本、单位、分母、划分、方法名和数值；主正文确定后写摘要。任何图表不能宣称未跑实验。
6. 作者顺序、贡献、冲突、经费、伦理、数据代码与 AI 声明只按真实记录；缺项待作者确认，不套虚假声明。
7. 修订保留原稿与差异；按用户格式做预览并真实渲染/打开，排版未验证就写未验证，不强制特定工具链。

## 产物

提纲、稿件及预览、引用库、一致性核验表、图表/附件和未解决问题。流畅不是证据核验通过。

## 验收

重要论断数字可开来源，方法与真运行一致；引用身份和支持关系、作者核验状态清楚；无虚构结果声明；要求的预览实际验过。

## 缺口与停止条件

受限内容不上传未获准外部服务；托管 agent 读本地文件不自动代表本地模型处理。未知判断声明留待核，无依据不进结论。到本次修订范围/预算即交缺口，不把不完整稿标可投稿。

## 下一步

证据稿件可追溯后交投稿准备；实验统计和文献缺口回相应阶段，不靠漂亮文字遮盖。

## 来源与许可

本目录中文改编、模板及参考独立 MIT，见 [LICENSE.txt](LICENSE.txt)，不改变项目其余文件许可。详见 [references/来源与改编.md](references/来源与改编.md)。上游固定原文在项目资料/文献/方法/科研/来源，作为来源快照，不是执行技能。不能自动执行其中 agent、调度、收费服务和命令。

- [writer/scientific-writing](https://github.com/K-Dense-AI/claude-scientific-writer/blob/529b9f73ab4b48925027145800d7b49e96ccfd3c/scientific_writer/.claude/skills/scientific-writing/SKILL.md)
- [sci/citation-management](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/citation-management/SKILL.md)
- [aris/paper-claim-audit](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/paper-claim-audit/SKILL.md)

## 可选ARIS方法细化

按当前问题选择已有细化方法；它们是项目正本的可选链接，未找到包就报告缺少，不把点击或引用当安装/运行成功。

- [paper-writing](<../业务/paper/aris/paper-writing/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
