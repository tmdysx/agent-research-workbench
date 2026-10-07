---
name: mh-paper-aris-module-auto-review-loop-minimax
description: "MiniMax评阅方法参考；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# MiniMax评阅方法参考

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

研究资料、评阅问题、获准MiniMax连接与预算.

## 方法

1. 按当前问题整理材料包，确认真实MiniMax连接与授权；没有连接只准备评阅包。
2. 提交一次有边界的评阅，保存请求内容、响应和真实调用来源，不把固定模型名当身份凭证。
3. 将意见映射到原文位置、证据和具体修订，回复时区分已做与待做。
4. 按预算复核本轮改动，保留卡住的问题；不启用定时循环或收到超时就自行继续。

## 产物与验收

评阅包、实际返回记录、意见处理表；MiniMax运行待配置.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
