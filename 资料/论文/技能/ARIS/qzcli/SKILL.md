---
name: mh-paper-aris-module-qzcli
description: "启智作业管理操作参考；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 启智作业管理操作参考

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

获准启智实例、实际qzcli版本、计算组及作业范围.

## 方法

1. 先核实际命令帮助、实例配置和身份，只读查询计算组/资源/现有作业。
2. 将训练命令、镜像、挂载、资源与输出位置整理为待审作业清单。
3. 提交、停止和批量操作仅按当前明确授权范围执行，记录真实job ID与返回。
4. 缺CLI或访问权限时只交准备清单，不把启智接口已配置当默认能力。

## 产物与验收

作业计划、资源检查、实际ID/状态和访问缺口.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
