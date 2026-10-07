---
name: mh-paper-aris-module-formula-derivation
description: "公式推导与假设分层；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 公式推导与假设分层

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

目标公式、符号、假设、现有证明或参考.

## 方法

1. 冻结需要推导的数学对象及假设，区分精确恒等式、近似和直观解释。
2. 逐步展开定义和代数转换，列使用的定理及条件，核维度、边界和退化情况。
3. 将不能证明的步骤列作待证义务，必要时构造反例或缩小论断。
4. 交可复查推导及符号表，不把直觉或数值一致当证明。

## 产物与验收

分步推导、符号/假设表、待证与反例记录.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
