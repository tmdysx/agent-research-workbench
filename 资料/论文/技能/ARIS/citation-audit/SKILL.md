---
name: mh-paper-aris-module-citation-audit
description: "引用身份与支持审计；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 引用身份与支持审计

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

稿件、引用库、检索权限、是否冻结文献库.

## 方法

1. 按正文每次引用的原句定位，而不是只核参考文献表；记录引用支持的具体论断。
2. 分别核论文是否存在、作者题名年份DOI是否一致、全文相应位置是否支持论断。
3. 交KEEP/FIX/REPLACE/REMOVE建议及证据；联网失败记未知，不当引用不存在。
4. 冻结文献库时只交正文调整或候选建议，不自动改bib；修订后复核受影响引用。

## 产物与验收

引用—原句—来源位置—判定表，未核身份或缺全文清单.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
