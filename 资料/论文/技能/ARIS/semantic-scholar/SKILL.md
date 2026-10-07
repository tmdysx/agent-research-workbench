---
name: mh-paper-aris-module-semantic-scholar
description: "Semantic Scholar文献检索；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# Semantic Scholar文献检索

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

学术查询、年份/领域边界、实际联网条件.

## 方法

1. 明确查询与返回范围，检索题名作者年份、发表场所和可用标识。
2. 对具体论文查详情，核arXiv与正式发表版本，按DOI/身份去重而非题名相似。
3. 引用数和TLDR仅为发现线索，重要结论需原文位置支持。
4. 原fetch helper未内置，使用真实获准查询工具；失败标未知并保存日期/查询。

## 产物与验收

检索日志、身份/版本核验表和原文阅读缺口.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
