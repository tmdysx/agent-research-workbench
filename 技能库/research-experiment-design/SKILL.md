---
name: research-experiment-design
description: 把论断转成有数据权限、无泄漏划分、公平基线、评价指标和预算的实验方案；主要用于计算与机器学习研究。
license: MIT
metadata:
  display_name: 数据与实验设计
  version: "1.0.0"
  language: zh-CN
---

# 数据与实验设计

任何能读取 Markdown 的 agent 都可按本技能执行，无需本平台另接模型 API。模板复制到授权业务目录后填写，原始证据保留。本包以计算与机器学习科研为主；综述/理论按证据类型调整，不能凭此包执行真实临床/动物/湿实验。

## 输入

研究问题、论断、证据表、数据说明、基线和资源限制。读适用实验协议；本技能不代替临床、动物和湿实验的领域协议与必要审批。

## 操作

1. 用 [assets/实验方案.md](assets/实验方案.md) 对每条核心论断写最少证据及待排除解释，规划主比较、关键消融、稳健性和失败分析，不为堆表加任务。
2. 查数据来源、许可、任务适用性、版本和独立单位。读 [references/机器学习评价边界.md](references/机器学习评价边界.md)，先定训练/验证/测试角色，按组、主体或时间划分，查重复、未来信息及衍生标签泄漏。
3. 预处理、特征选择、归一化、重采样和调参只在训练侧拟合。反复选择也算选择；按需要训练内验证或嵌套验证，测试集不参与选择。
4. 先定指标方向/单位/统计单位和不确定性方法。随机性显著且预算允许才规划独立重复，记次数与种子；不能把折或训练批次当独立样本。
5. 基线与新方法用可比较划分、指标实现和资源；记录各法调参范围与选择预算。论文数值与本机复现值分开。
6. 排最小检查→基线→主方法→关键消融→补充；每任务写运行时间、内存、次数、成功/失败解释和停条件。预算未定仅做计划和可逆小检查。
7. 固定方案与评价版本；变更追加偏离记录，结果后探索另标，不能倒写原计划。

## 产物

实验方案、数据/划分清单、论断—实验矩阵、基线/消融矩阵、预算和运行顺序。模板不装入真实私人数据。

## 验收

人看出每个实验回答哪个问题、比较如何公平、测试为何没参与选择和失败含义；权限、范围、预算、评价及方案版本可追溯。

## 缺口与停止条件

泄漏、单位不明、权限不足或安全条件缺失时受影响正式运行暂缓。缺强基线或重复写局限；超出方向授权留下待判断。

## 下一步

交复现与运行做最小检查与基线，通过后依顺序正式运行；不以大实验代替设计。

## 来源与许可

本目录中文改编、模板及参考独立 MIT，见 [LICENSE.txt](LICENSE.txt)，不改变项目其余文件许可。详见 [references/来源与改编.md](references/来源与改编.md)。上游固定原文在项目资料/文献/方法/科研/来源，作为来源快照，不是执行技能。不能自动执行其中 agent、调度、收费服务和命令。

- [aris/experiment-plan](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/experiment-plan/SKILL.md)
- [aris/ablation-planner](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/ablation-planner/SKILL.md)
- [sci/scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-critical-thinking/SKILL.md)

## 可选ARIS方法细化

按当前问题选择已有细化方法；它们是项目正本的可选链接，未找到包就报告缺少，不把点击或引用当安装/运行成功。

- [experiment-plan](<../业务/paper/aris/experiment-plan/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
