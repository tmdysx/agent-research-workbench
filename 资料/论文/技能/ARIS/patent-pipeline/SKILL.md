---
name: mh-paper-aris-module-patent-pipeline
description: "专利文书分阶段路线；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 专利文书分阶段路线

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

真实发明披露、现有技术、发明人需求与辖区.

## 方法

1. 整理原披露及确认项，先做有来源的现有技术检索和技术新颖性讨论。
2. 明确问题解决结构与必要特征，先定权利要求再写说明书和实施例。
3. 核附图、术语、效果、权利要求支持及真实技术内容，再准备辖区格式。
4. 各阶段保留来源、未解项和版本；只交本地技术草稿，不上传、提交或承诺法律结果。

## 产物与验收

分阶段披露、检索、权利要求、说明书与格式包及缺口.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
