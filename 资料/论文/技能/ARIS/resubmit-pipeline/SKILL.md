---
name: mh-paper-aris-module-resubmit-pipeline
description: "受限文字重投准备；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 受限文字重投准备

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

旧提交版本、新目标要求、禁改清单和真实证据.

## 方法

1. 在独立目录保存新版本，原提交不覆盖；先核目标当前格式和匿名要求。
2. 先只读审数字、引用和范围，固定本轮不新实验、不改bib、不改研究框架等约束。
3. 只实施获准的小范围文字修改，重审所有受影响复述及论断。
4. 编译/打开后交逐文件差异和当前检查；Overleaf推送、投稿均不由此方法自动执行。

## 产物与验收

隔离新稿、约束核对、文字差异及真实编译/审查记录.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
