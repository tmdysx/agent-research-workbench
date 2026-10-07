---
name: research-reproduce-run
description: 在获准资源内复现基线和执行计算实验，保存命令、版本、原始结果及失败；不启动平台模型或租资源。
license: MIT
metadata:
  display_name: 复现与运行
  version: "1.0.0"
  language: zh-CN
---

# 复现与运行

任何能读取 Markdown 的 agent 都可按本技能执行，无需本平台另接模型 API。模板复制到授权业务目录后填写，原始证据保留。本包以计算与机器学习科研为主；综述/理论按证据类型调整，不能凭此包执行真实临床/动物/湿实验。

## 输入

已定方案、数据清单、代码版本、授权资源、预算和运行顺序。说明书不等于远程服务器运行授权，只读授权目录。

## 操作

1. 用 [assets/运行记录.md](assets/运行记录.md) 写实际命令、目录、代码版本/差异、配置、依赖、种子、输入指纹和输出。每次独立目录，原始结果不覆盖。
2. 先查方案所需小样本加载、形状、标签、指标方向、训练验证隔离和输出保存，再跑基线；与论文差异写条件，不改评价追分。
3. 读 [references/运行与故障.md](references/运行与故障.md)，按顺序启动授权实验，保留 stdout/stderr、结束码、开始结束时间和实际资源。检查运行明确标为检查，不进正式比较。
4. 用现有获准方式监控本任务进程；技能不建调度器、租 GPU、购买服务或启动其他 agent。远程/学校环境按对应授权及专属技能执行。
5. 崩溃、超时、内存不足、取消均保留，指标记缺失原因，不能用 0 当成绩。明显程序错误可按限次修复并记录变更；到次数上限交接。
6. 结束核真实产物、日志、评价一致性和泄漏；从原始输出提取结果保留转换步骤。验证集优化与最终测试不可混用。

## 产物

独立运行目录、环境说明、日志与原始结果、复跑命令、基线差异和失败记录。原始及派生结果分开。

## 验收

人能打开真实日志找到状态、配置和原始结果，换 agent 能按输入预算复跑。只记真实次数时间资源；未启动、在跑、失败和取消不算完成。

## 缺口与停止条件

输入/资源/依赖未齐则记具体缺口。超预算、评价异常、泄漏或用户叫停时保存现场，终止仅能确定归本任务的进程。上游原项目不 fork、不改，实验实现置独立授权目录。

## 下一步

真实结果交结果分析与图表；异常先查评价日志，补跑仍须在方案和预算内。

## 来源与许可

本目录中文改编、模板及参考独立 MIT，见 [LICENSE.txt](LICENSE.txt)，不改变项目其余文件许可。详见 [references/来源与改编.md](references/来源与改编.md)。上游固定原文在项目资料/文献/方法/科研/来源，作为来源快照，不是执行技能。不能自动执行其中 agent、调度、收费服务和命令。

- [aris/run-experiment](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/run-experiment/SKILL.md)
- [aris/training-check](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/training-check/SKILL.md)

## 可选ARIS方法细化

按当前问题选择已有细化方法；它们是项目正本的可选链接，未找到包就报告缺少，不把点击或引用当安装/运行成功。

- [run-experiment](<../业务/paper/aris/run-experiment/SKILL.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
