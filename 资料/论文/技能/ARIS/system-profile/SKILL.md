---
name: mh-paper-aris-module-system-profile
description: "系统瓶颈测量与证据；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 系统瓶颈测量与证据

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

获准脚本/进程、评价负载、机器与时间预算.

## 方法

1. 明确要衡量延迟、吞吐、GPU、内存还是互联瓶颈，选代表性负载和基线。
2. 检查实际可用profiler及采样开销，先短时测量以避免改变被测行为。
3. 将时间、资源和调用栈对齐，区分观测到的瓶颈与尚未验证的原因猜想。
4. 记录环境/参数/原始profile及重复性，交建议和复验方案，不凭印象优化。

## 产物与验收

原始profile、环境负载、瓶颈证据与优化复验方案.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
