---
name: mh-paper-aris-module-auto-review-loop
description: "独立评阅与修订关口；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 独立评阅与修订关口

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

研究稿、原始证据、真正独立评阅环境、批准计划.

## 方法

1. 冻结审查输入及来源，明确自查、独立员工审查与跨模型审查分别能证明什么。
2. 让实际独立审阅者给出带位置、证据和严重度的问题；保存会话/调用凭证而不是自行声明独立。
3. 施工者落实获准修订并提交结果位置；审阅者只复核对应证据与仍未关闭的问题。
4. 论文质量评分不代替平台计划审核或交付验收；缺少外部评阅工具则交方法准备及能力缺口。

## 产物与验收

原审查、改动对应表、真实独立性凭据、开放问题.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
