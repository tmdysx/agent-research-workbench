---
name: mh-paper-aris-module-specification-writing
description: "专利说明书与支持链；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 专利说明书与支持链

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

真实权利要求、发明披露、实施例和附图.

## 方法

1. 按技术领域、背景、发明内容、附图、实施方式和摘要组织说明书。
2. 背景只陈述可核问题，发明内容与权利要求术语保持一致。
3. 实施方式补足必要条件、步骤和部件关系，效果与数据不得凭空补写。
4. 逐条核权利要求在正文/附图中有支持；辖区要求使用当前官方来源。

## 产物与验收

说明书草稿、权利要求支持矩阵和待发明人确认项.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
