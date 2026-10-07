---
name: mh-paper-aris-module-auto-review-loop-llm
description: "外部LLM审查轮次参考；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 外部LLM审查轮次参考

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

审查目标、资料范围、已获准评阅后端及轮次预算.

## 方法

1. 确定要评价的论断、材料和实际外部评阅通道；后端不可用就标未执行。
2. 每轮向审阅者提供这轮事实和待核问题，保留原答复、上下文来源和调用证据。
3. 区分批评、修改建议与已验证结果，逐项落实获准改动后再回报。
4. 只在限定轮次内重审相关问题；需要人的决定仍待确认，超时不代替批准。

## 产物与验收

逐轮原答复、修订证据、未解问题；LLM接口未内置.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
