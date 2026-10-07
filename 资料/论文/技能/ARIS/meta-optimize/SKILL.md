---
name: mh-paper-aris-module-meta-optimize
description: "技能日志分析与改进提案；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 技能日志分析与改进提案

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

获准技能、真实使用日志、失败与成本证据.

## 方法

1. 只读检查使用数据是否足以判断，先定位当前瓶颈而不是广泛改规则。
2. 将改善候选绑定到重复出现的日志证据，列收益、风险和原技能位置。
3. 生成待审补丁与可复查前后行为，独立预审是建议而不是提权或落地批准。
4. 交暂存候选供平台正式计划审核；本技能不修改自己的技能库或权限。

## 产物与验收

证据排序的优化报告、暂存补丁、验证方案和未建议改动理由.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
