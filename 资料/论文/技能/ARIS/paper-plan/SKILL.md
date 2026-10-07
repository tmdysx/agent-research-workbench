---
name: mh-paper-aris-module-paper-plan
description: "论断驱动论文大纲；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 论断驱动论文大纲

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

审查结论、真实实验、主要论断与目标要求.

## 方法

1. 先整理论断—证据对应，选定论文类型和唯一主线。
2. 按章节目的设计段落任务、读者问题和可支持结论，预留局限。
3. 为每幅图指定目的和真实结果来源，为每条关键引用指定支持位置。
4. 获准审查后交结构和开放问题；大纲成立不意味着实验或正文已完成。

## 产物与验收

逐章大纲、图计划、引用支架和证据缺口.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
