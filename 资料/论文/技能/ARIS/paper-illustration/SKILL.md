---
name: mh-paper-aris-module-paper-illustration
description: "学术AI绘图与校对方法；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 学术AI绘图与校对方法

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

实际科学机制、布局需求、获准生成能力.

## 方法

1. 写清科学内容与布局，再分别检查信息顺序、标签和视觉风格。
2. 将真实机制映射到图形，使用一致术语和可追溯提示词。
3. Gemini/Paperbanana原运行依赖未装；可通过作者现有获准工具执行，但如实记录实际工具。
4. 实际生成后逐项读图，修漏项、伪结构、文字和箭头；评分只是质量参考，不代替任务验收。

## 产物与验收

科学图计划、提示词/工具来源、图像和逐项校对.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
