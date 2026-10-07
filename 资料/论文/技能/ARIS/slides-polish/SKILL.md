---
name: mh-paper-aris-module-slides-polish
description: "幻灯片逐页润色；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 幻灯片逐页润色

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

现有PPTX/Beamer、参考风格和真实页面预览.

## 方法

1. 先列页面问题与优先级，按投影可读性、溢出、对齐和视觉重量查每页。
2. 针对字体、斜体泄漏、文本框和图形位置做获准小修，保留内容证据不改结论。
3. 分别核Beamer与PPTX的真实输出，不假设一个版本通过就另一版通过。
4. 重渲染受影响页并实际打开，交逐页差异和未完成问题。

## 产物与验收

逐页问题、修订前后预览、实际打开与差异日志.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
