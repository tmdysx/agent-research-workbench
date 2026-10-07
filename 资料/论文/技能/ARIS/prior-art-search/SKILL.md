---
name: mh-paper-aris-module-prior-art-search
description: "现有技术检索与范围记录；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 现有技术检索与范围记录

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

发明技术要素、同义词、辖区和时间边界.

## 方法

1. 从技术问题、结构步骤及用途提取检索概念与多语关键词。
2. 查专利数据库和学术来源，保存查询、日期、分类号和原文标识。
3. 按要素、公开时间及相关性分类，近似方案和反例均保留。
4. 实施自由讨论只能标初步风险线索；检索未发现不等于没有专利或可以商用。

## 产物与验收

可复查检索日志、现有技术表、要素差异与范围限制.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
