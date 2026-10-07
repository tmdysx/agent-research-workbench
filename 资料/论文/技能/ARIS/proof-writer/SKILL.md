---
name: mh-paper-aris-module-proof-writer
description: "严格证明起草与可行性；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 严格证明起草与可行性

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

需证定理、定义、假设、允许引用的定理.

## 方法

1. 正规化命题和量词，先找明显反例、缺条件或与已知结论冲突。
2. 建立引理—主定理依赖顺序，分清可由现成定理推出与需要新证明的部分。
3. 逐步写完整证明，每次引用写清适用条件，不用省略句遮住困难步骤。
4. 核边界和所有结论，证不出则说明障碍、可证明子结论或反例。

## 产物与验收

可检查证明、依赖图、假设边界与未完成部分.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
