---
name: mh-paper-aris-index
display_name: "论文技能 Paper skills"
description: "论文模块的ARIS方法索引；82个基础方法分别按阶段选择，复用7个旧正本并新增75个方法包。"
---

# 论文技能：ARIS方法索引

先读当前目标、计划、适用戒律和最新交接，只选择本轮需要的技能。下表按用途分组，并不声明所有阶段已完成。

82个基础方法=75个新方法包+7个保留原ID/来源的已有入口；82个Codex镜像和23个review变体不作为额外独立技能。

本模块安装方法文本、完整上游原文和必要MIT参考，未安装运行脚本、会议样式、MCP或模型API。依赖缺口在每包SOURCE里，方法适配不是原文全文逐字译。

## 科研阶段入口 / Research phases

- [科研路线](<../../../技能库/research-route/SKILL.md>)
- [选题与假设](<../../../技能库/research-topic/SKILL.md>)
- [文献与证据](<../../../技能库/research-literature-evidence/SKILL.md>)
- [数据与实验设计](<../../../技能库/research-experiment-design/SKILL.md>)
- [复现与运行](<../../../技能库/research-reproduce-run/SKILL.md>)
- [结果分析与图表](<../../../技能库/research-results-figures/SKILL.md>)
- [论文写作与引用](<../../../技能库/research-manuscript-citations/SKILL.md>)
- [投稿准备](<../../../技能库/research-submission-package/SKILL.md>)
- [返修与回复](<../../../技能库/research-revision/SKILL.md>)

## 路线与方案 / route

| 方法 | 入口与来源状态 |
|---|---|
| [研究阶段与交接参考](<../../../技能库/业务/paper/aris/research-pipeline/SKILL.md>) · `research-pipeline` | 复用原正本 / Existing canonical, pin 213203… |
| [稳定方法到实验路线的交接](<ARIS/research-refine-pipeline/SKILL.md>) · `research-refine-pipeline` | 方法包 / Method package, runtime disabled |
| [问题锚定的最小机制细化](<ARIS/research-refine/SKILL.md>) · `research-refine` | 方法包 / Method package, runtime disabled |
| [研究知识节点与证据关系](<ARIS/research-wiki/SKILL.md>) · `research-wiki` | 方法包 / Method package, runtime disabled |
| [已建论文页的忠实补全](<ARIS/wiki-enrich/SKILL.md>) · `wiki-enrich` | 方法包 / Method package, runtime disabled |

## 想法与新颖性 / topic

| 方法 | 入口与来源状态 |
|---|---|
| [研究候选生成与证据筛选](<ARIS/idea-creator/SKILL.md>) · `idea-creator` | 方法包 / Method package, runtime disabled |
| [机器人选题与仿真验证计划](<ARIS/idea-discovery-robot/SKILL.md>) · `idea-discovery-robot` | 方法包 / Method package, runtime disabled |
| [研究想法筛选与验证](<../../../技能库/业务/paper/aris/idea-discovery/SKILL.md>) · `idea-discovery` | 复用原正本 / Existing canonical, pin 213203… |
| [机制新颖性与最近工作核查](<ARIS/novelty-check/SKILL.md>) · `novelty-check` | 方法包 / Method package, runtime disabled |

## 文献与资料 / evidence

| 方法 | 入口与来源状态 |
|---|---|
| [单篇论文分层速读](<ARIS/alphaxiv/SKILL.md>) · `alphaxiv` | 方法包 / Method package, runtime disabled |
| [arXiv 检索与原文获取](<ARIS/arxiv/SKILL.md>) · `arxiv` | 方法包 / Method package, runtime disabled |
| [通信领域分层文献综述](<ARIS/comm-lit-review/SKILL.md>) · `comm-lit-review` | 方法包 / Method package, runtime disabled |
| [论文渐进检索与分节阅读](<ARIS/deepxiv/SKILL.md>) · `deepxiv` | 方法包 / Method package, runtime disabled |
| [带内容提取的网页检索](<ARIS/exa-search/SKILL.md>) · `exa-search` | 方法包 / Method package, runtime disabled |
| [AI 辅助文献发现与核验](<ARIS/gemini-search/SKILL.md>) · `gemini-search` | 方法包 / Method package, runtime disabled |
| [开放学术元数据与引文关系查询](<ARIS/openalex/SKILL.md>) · `openalex` | 方法包 / Method package, runtime disabled |
| [多源文献检索、核实与综合](<ARIS/research-lit/SKILL.md>) · `research-lit` | 方法包 / Method package, runtime disabled |
| [Semantic Scholar文献检索](<ARIS/semantic-scholar/SKILL.md>) · `semantic-scholar` | 方法包 / Method package, runtime disabled |

## 实验设计 / design

| 方法 | 入口与来源状态 |
|---|---|
| [论断驱动的消融计划](<ARIS/ablation-planner/SKILL.md>) · `ablation-planner` | 方法包 / Method package, runtime disabled |
| [有界设计空间探索](<ARIS/dse-loop/SKILL.md>) · `dse-loop` | 方法包 / Method package, runtime disabled |
| [实验矩阵与预算计划](<../../../技能库/业务/paper/aris/experiment-plan/SKILL.md>) · `experiment-plan` | 复用原正本 / Existing canonical, pin 213203… |

## 执行与工程 / run

| 方法 | 入口与来源状态 |
|---|---|
| [实验计划到代码契约与初始证据](<ARIS/experiment-bridge/SKILL.md>) · `experiment-bridge` | 方法包 / Method package, runtime disabled |
| [实验队列与资源清单](<ARIS/experiment-queue/SKILL.md>) · `experiment-queue` | 方法包 / Method package, runtime disabled |
| [实验进度只读检查](<ARIS/monitor-experiment/SKILL.md>) · `monitor-experiment` | 方法包 / Method package, runtime disabled |
| [启智作业管理操作参考](<ARIS/qzcli/SKILL.md>) · `qzcli` | 方法包 / Method package, runtime disabled |
| [实验执行与失败记录](<../../../技能库/业务/paper/aris/run-experiment/SKILL.md>) · `run-experiment` | 复用原正本 / Existing canonical, pin 213203… |
| [Modal云计算方案参考](<ARIS/serverless-modal/SKILL.md>) · `serverless-modal` | 方法包 / Method package, runtime disabled |
| [系统瓶颈测量与证据](<ARIS/system-profile/SKILL.md>) · `system-profile` | 方法包 / Method package, runtime disabled |
| [训练健康单次检查](<ARIS/training-check/SKILL.md>) · `training-check` | 方法包 / Method package, runtime disabled |
| [Vast算力选择与费用边界](<ARIS/vast-gpu/SKILL.md>) · `vast-gpu` | 方法包 / Method package, runtime disabled |
| [工程问题检索与来源分级](<ARIS/web-debug-search/SKILL.md>) · `web-debug-search` | 方法包 / Method package, runtime disabled |

## 结果与证据 / results

| 方法 | 入口与来源状态 |
|---|---|
| [真实结果比较与解释](<ARIS/analyze-results/SKILL.md>) · `analyze-results` | 方法包 / Method package, runtime disabled |
| [实验完整性证据审计](<ARIS/experiment-audit/SKILL.md>) · `experiment-audit` | 方法包 / Method package, runtime disabled |
| [真实结果到论断的三向分流](<ARIS/result-to-claim/SKILL.md>) · `result-to-claim` | 方法包 / Method package, runtime disabled |

## 数学与证明 / proof

| 方法 | 入口与来源状态 |
|---|---|
| [公式推导与假设分层](<ARIS/formula-derivation/SKILL.md>) · `formula-derivation` | 方法包 / Method package, runtime disabled |
| [证明缺口与全局闭合核验](<ARIS/proof-checker/SKILL.md>) · `proof-checker` | 方法包 / Method package, runtime disabled |
| [跨轮证明接手方法](<ARIS/proof-orchestrator/SKILL.md>) · `proof-orchestrator` | 方法包 / Method package, runtime disabled |
| [严格证明起草与可行性](<ARIS/proof-writer/SKILL.md>) · `proof-writer` | 方法包 / Method package, runtime disabled |

## 正文与结构 / write

| 方法 | 入口与来源状态 |
|---|---|
| [论断驱动论文大纲](<ARIS/paper-plan/SKILL.md>) · `paper-plan` | 方法包 / Method package, runtime disabled |
| [逐节起草与逆向大纲](<ARIS/paper-write/SKILL.md>) · `paper-write` | 方法包 / Method package, runtime disabled |
| [研究叙事与论文框架](<../../../技能库/业务/paper/aris/paper-writing/SKILL.md>) · `paper-writing` | 复用原正本 / Existing canonical, pin 213203… |
| [系统论文段落与性能证据](<ARIS/writing-systems-papers/SKILL.md>) · `writing-systems-papers` | 方法包 / Method package, runtime disabled |

## 图形与可视化 / figures

| 方法 | 入口与来源状态 |
|---|---|
| [结构化学术图形规范](<ARIS/figure-spec/SKILL.md>) · `figure-spec` | 方法包 / Method package, runtime disabled |
| [Mermaid可编辑关系图](<ARIS/mermaid-diagram/SKILL.md>) · `mermaid-diagram` | 方法包 / Method package, runtime disabled |
| [真实结果到学术图表](<ARIS/paper-figure/SKILL.md>) · `paper-figure` | 方法包 / Method package, runtime disabled |
| [Image2学术示意图方案](<ARIS/paper-illustration-image2/SKILL.md>) · `paper-illustration-image2` | 方法包 / Method package, runtime disabled |
| [学术AI绘图与校对方法](<ARIS/paper-illustration/SKILL.md>) · `paper-illustration` | 方法包 / Method package, runtime disabled |
| [像素SVG插画](<ARIS/pixel-art/SKILL.md>) · `pixel-art` | 方法包 / Method package, runtime disabled |

## 审查与投稿前核验 / audit

| 方法 | 入口与来源状态 |
|---|---|
| [论文有界修订与复核](<ARIS/auto-paper-improvement-loop/SKILL.md>) · `auto-paper-improvement-loop` | 方法包 / Method package, runtime disabled |
| [外部LLM审查轮次参考](<ARIS/auto-review-loop-llm/SKILL.md>) · `auto-review-loop-llm` | 方法包 / Method package, runtime disabled |
| [MiniMax评阅方法参考](<ARIS/auto-review-loop-minimax/SKILL.md>) · `auto-review-loop-minimax` | 方法包 / Method package, runtime disabled |
| [独立评阅与修订关口](<ARIS/auto-review-loop/SKILL.md>) · `auto-review-loop` | 方法包 / Method package, runtime disabled |
| [引用身份与支持审计](<ARIS/citation-audit/SKILL.md>) · `citation-audit` | 方法包 / Method package, runtime disabled |
| [诚信取证方法与义务表](<ARIS/integrity-forensics/SKILL.md>) · `integrity-forensics` | 方法包 / Method package, runtime disabled |
| [强反驳与逐点裁决](<ARIS/kill-argument/SKILL.md>) · `kill-argument` | 方法包 / Method package, runtime disabled |
| [论文论断与原始结果核对](<ARIS/paper-claim-audit/SKILL.md>) · `paper-claim-audit` | 方法包 / Method package, runtime disabled |
| [研究方案与证据审查](<../../../技能库/业务/paper/aris/research-review/SKILL.md>) · `research-review` | 复用原正本 / Existing canonical, pin 213203… |

## 返修与重投 / revision

| 方法 | 入口与来源状态 |
|---|---|
| [审稿回应与返修映射](<../../../技能库/业务/paper/aris/rebuttal/SKILL.md>) · `rebuttal` | 复用原正本 / Existing canonical, pin 213203… |
| [受限文字重投准备](<ARIS/resubmit-pipeline/SKILL.md>) · `resubmit-pipeline` | 方法包 / Method package, runtime disabled |

## 报告与海报 / presentation

| 方法 | 入口与来源状态 |
|---|---|
| [HTML学术海报设计方法](<ARIS/paper-poster-html/SKILL.md>) · `paper-poster-html` | 方法包 / Method package, runtime disabled |
| [旧海报入口兼容](<ARIS/paper-poster/SKILL.md>) · `paper-poster` | 方法包 / Method package, runtime disabled |
| [论文到幻灯片与讲者备注](<ARIS/paper-slides/SKILL.md>) · `paper-slides` | 方法包 / Method package, runtime disabled |
| [学术报告端到端路线](<ARIS/paper-talk/SKILL.md>) · `paper-talk` | 方法包 / Method package, runtime disabled |
| [幻灯片逐页润色](<ARIS/slides-polish/SKILL.md>) · `slides-polish` | 方法包 / Method package, runtime disabled |

## 专利方法参考 / patent

| 方法 | 入口与来源状态 |
|---|---|
| [专利权利要求起草参考](<ARIS/claims-drafting/SKILL.md>) · `claims-drafting` | 方法包 / Method package, runtime disabled |
| [实施方式与权利要求支撑](<ARIS/embodiment-description/SKILL.md>) · `embodiment-description` | 方法包 / Method package, runtime disabled |
| [专利附图说明与标号核对](<ARIS/figure-description/SKILL.md>) · `figure-description` | 方法包 / Method package, runtime disabled |
| [发明披露结构化](<ARIS/invention-structuring/SKILL.md>) · `invention-structuring` | 方法包 / Method package, runtime disabled |
| [专利辖区格式准备](<ARIS/jurisdiction-format/SKILL.md>) · `jurisdiction-format` | 方法包 / Method package, runtime disabled |
| [专利新颖性技术对照](<ARIS/patent-novelty-check/SKILL.md>) · `patent-novelty-check` | 方法包 / Method package, runtime disabled |
| [专利文书分阶段路线](<ARIS/patent-pipeline/SKILL.md>) · `patent-pipeline` | 方法包 / Method package, runtime disabled |
| [专利草稿批判评阅](<ARIS/patent-review/SKILL.md>) · `patent-review` | 方法包 / Method package, runtime disabled |
| [现有技术检索与范围记录](<ARIS/prior-art-search/SKILL.md>) · `prior-art-search` | 方法包 / Method package, runtime disabled |
| [专利说明书与支持链](<ARIS/specification-writing/SKILL.md>) · `specification-writing` | 方法包 / Method package, runtime disabled |

## 输出与协作工具 / helpers

| 方法 | 入口与来源状态 |
|---|---|
| [飞书通知协议准备](<ARIS/feishu-notify/SKILL.md>) · `feishu-notify` | 方法包 / Method package, runtime disabled |
| [专题教程与面试速查](<ARIS/interview-cheatsheet/SKILL.md>) · `interview-cheatsheet` | 方法包 / Method package, runtime disabled |
| [Overleaf同步边界与冲突处理](<ARIS/overleaf-sync/SKILL.md>) · `overleaf-sync` | 方法包 / Method package, runtime disabled |
| [论文编译与产物核验](<ARIS/paper-compile/SKILL.md>) · `paper-compile` | 方法包 / Method package, runtime disabled |
| [研究记录HTML阅读版](<ARIS/render-html/SKILL.md>) · `render-html` | 方法包 / Method package, runtime disabled |

## 基金申请方法 / grant

| 方法 | 入口与来源状态 |
|---|---|
| [基金申请论证与证据准备](<ARIS/grant-proposal/SKILL.md>) · `grant-proposal` | 方法包 / Method package, runtime disabled |

## 技能优化与落地边界 / meta

| 方法 | 入口与来源状态 |
|---|---|
| [技能改动独立落地关](<ARIS/meta-apply/SKILL.md>) · `meta-apply` | 方法包 / Method package, runtime disabled |
| [技能日志分析与改进提案](<ARIS/meta-optimize/SKILL.md>) · `meta-optimize` | 方法包 / Method package, runtime disabled |

## 如何继续

1. 选择与当前问题匹配的入口，按其输入检查材料；没有的明确列缺口。
2. 执行当前已授权任务，产物写获准业务位置，保留真实原始证据和检查。
3. 实际交付仍走平台K/P/J/H及独立审核；研究支持、质量分数与施工完成分别记录。

[来源清单 / Source inventory](ARIS/来源清单.json) · [来源与融合说明 / Integration audit](ARIS/来源与融合说明.md)

## 写作辅助 · 贡献与证据

[去防御性写作：贡献与证据](<../../../技能库/业务/paper/adkid-zephyr/anti-defensive-writing/SKILL.md>)：默认最小改稿，去掉情绪性示弱，保留真实负结果和必要限制。中英方法及MIT来源已内置，无需安装。它是独立写作辅助，原82个ARIS方法编号不变。
