---
name: mh-paper-aris-module-writing-systems-papers
description: "系统论文段落与性能证据；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 系统论文段落与性能证据

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

系统问题、设计取舍、实现及真实性能结果.

## 方法

1. 将问题、设计洞见、机制、实现和评估分别定义读者必须理解的内容。
2. 按论证需要分配章节及段落职责；原10–12页比例只作参考，当前会议要求另核。
3. 性能结论同时给负载、基线、机器、测量范围和代价，解释适用边界。
4. 检查每段承接及证据位置，删除无证夸张，不把写作模式当实验完成。

## 产物与验收

系统论文结构、段落任务与性能论断证据表.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
