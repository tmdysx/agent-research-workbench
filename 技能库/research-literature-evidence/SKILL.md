---
name: research-literature-evidence
description: 建立检索记录、文献比较和论断证据表；用于综述、研究缺口与论文论据，区分来源存在和真正支持论断。
license: MIT
metadata:
  display_name: 文献与证据
  version: "1.0.0"
  language: zh-CN
---

# 文献与证据

任何能读取 Markdown 的 agent 都可按本技能执行，无需本平台另接模型 API。模板复制到授权业务目录后填写，原始证据保留。本包以计算与机器学习科研为主；综述/理论按证据类型调整，不能凭此包执行真实临床/动物/湿实验。

## 输入

研究问题、学科范围、检索截止日、待支撑论断和授权的文献。先读文献模块技能；外部材料从外部资料入口进入，未获准材料只留检索清单。

## 操作

1. 选适合问题的官方数据库/检索入口，记查询、日期、过滤和覆盖限制。浏览器或公开 API 均可，不强制付费搜索。
2. 读 [references/证据核验.md](references/证据核验.md)，核标题、作者、年份、标识和版本，合法取得全文。摘要/搜索片段与查到 DOI 不算已读原文。
3. 用 [assets/文献证据表.md](assets/文献证据表.md) 提取对象、方法、数据、评价、局限及具体页/节/图/表，记录支持或反对方向。链接同一研究不同版本，不重复计证据。
4. 按问题和争议综合，不堆逐篇摘要；保留反证、负结果、更正/撤稿信息和未覆盖范围。
5. 只有真正要求系统综述时，预定纳入排除、筛选理由及记录/报告/研究计数；普通背景检索标叙述性，不能宣称穷尽。
6. 记录已发现、已定位、agent 已查、作者已核，以及核验者和日期；元数据核对与支持关系分开，作者责任不自动替代。

## 产物

检索日志、主题比较、论断—来源—原文位置表、待全文/待核清单，按需要整理引用库。

## 验收

人能打开来源找到对应位置，看清论断成立条件、支持与反证。作者年份版本已核；数字单位和上下文保留；检索范围可复查。

## 缺口与停止条件

访问受限、版权不明、引用身份冲突或无法定位时记待核，不编 DOI、引文和结果，不批量转存未经授权全文。到检索边界先交已有证据及限制。

## 下一步

缺口界定后进入数据与实验设计；写作阶段可直接交论文与引用；关键证据缺失则补查或缩小论断。

## 来源与许可

本目录中文改编、模板及参考独立 MIT，见 [LICENSE.txt](LICENSE.txt)，不改变项目其余文件许可。详见 [references/来源与改编.md](references/来源与改编.md)。上游固定原文在项目资料/文献/方法/科研/来源，作为来源快照，不是执行技能。不能自动执行其中 agent、调度、收费服务和命令。

- [sci/literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/literature-review/SKILL.md)
- [sci/citation-management](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/citation-management/SKILL.md)
- [sci/scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-critical-thinking/SKILL.md)

## 可选ARIS方法细化

按当前问题选择已有细化方法；它们是项目正本的可选链接，未找到包就报告缺少，不把点击或引用当安装/运行成功。

- [idea-discovery](<../业务/paper/aris/idea-discovery/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
