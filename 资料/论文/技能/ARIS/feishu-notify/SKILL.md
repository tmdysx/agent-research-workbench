---
name: mh-paper-aris-module-feishu-notify
description: "飞书通知协议准备；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 飞书通知协议准备

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

通知目的、获准收件方、配置状态及隐私边界.

## 方法

1. 明确需要通知的事件与最小内容，把状态、证据和需要决定的事项分开。
2. 核真实Webhook/交互配置并保护密钥，只在明确授权的发送范围使用。
3. 双向答复按真实来源记录，超时是待回复，不能替代人的批准。
4. 未配置或未获发送授权只交通知草稿；安装不发送消息、不建轮询。

## 产物与验收

通知草稿、配置/授权缺口及实际发送/回复凭据.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
