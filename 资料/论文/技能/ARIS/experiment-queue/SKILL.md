---
name: mh-paper-aris-module-experiment-queue
description: "实验队列与资源清单；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 实验队列与资源清单

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

已批准实验块、真实资源、顺序依赖和预算.

## 方法

1. 把每个实验映射到明确命令、资源、结果位置和前置条件，生成可核队列清单。
2. 核互斥资源和先后顺序，只将环境与输入齐全的实验标可运行。
3. 维护待运行、运行、失败和完成状态，依据真实日志/进程及结果文件更新。
4. 原调度脚本和远程60秒轮询未装；读清单不启动任何作业，实际执行走当前平台批准流程。

## 产物与验收

实验队列、资源/依赖表、真实运行状态与阻塞原因.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
