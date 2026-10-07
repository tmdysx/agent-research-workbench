---
name: mh-paper-aris-module-invention-structuring
description: "发明披露结构化；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 发明披露结构化

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

原始发明想法、已实现内容、限制与发明人信息.

## 方法

1. 用技术问题—解决方案—真实优势整理发明，不把预期效果当实验事实。
2. 分解结构、步骤、材料或算法特征，列必要条件与替代实现。
3. 识别可讨论的权利要求主题，制定附图和实施例计划。
4. 核特征依赖、证据缺口与发明人确认，外部审查缺失不写已通过。

## 产物与验收

发明披露、特征依赖表、附图计划及确认清单.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
