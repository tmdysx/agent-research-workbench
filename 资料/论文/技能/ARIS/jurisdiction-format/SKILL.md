---
name: mh-paper-aris-module-jurisdiction-format
description: "专利辖区格式准备；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 专利辖区格式准备

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

完整专利草稿、目标CN/US/EP及当前官方指南.

## 方法

1. 确定本轮目标辖区并读取当前官方要求，原文历史格式只作参考。
2. 按该辖区要求安排请求、权利要求、说明书、摘要和附图，不自行补作者/申请人事实。
3. 交叉核技术内容、编号、术语和申请信息，输出独立版本以保留原件。
4. 实际打开文件并对照要求；准备完成不代表已提交或有法律效力。

## 产物与验收

辖区版本、官方要求对照、差异与待申请人确认项.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
