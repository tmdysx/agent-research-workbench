---
name: mh-paper-aris-module-kill-argument
description: "强反驳与逐点裁决；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 强反驳与逐点裁决

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

稳定稿件、证据包、两个真实独立审查上下文.

## 方法

1. 让第一位新审查者基于稿件构造最强拒稿论点，默认用紧凑约200词备忘录。
2. 第二位新审查者同时读稿件和攻击备忘录，逐点分清可辩护、需修订及仍致命的问题。
3. 将每条裁决锚定到原文和证据，按严重度列行动；缺独立上下文则明确只是自查练习。
4. 只在稿件/证据改变后按获准范围复核，不在时钟循环里反复制造新裁决。

## 产物与验收

攻击原文、逐点裁决、未解决重大问题与行动表.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
