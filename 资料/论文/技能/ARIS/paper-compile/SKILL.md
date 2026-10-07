---
name: mh-paper-aris-module-paper-compile
description: "论文编译与产物核验；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 论文编译与产物核验

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

稿件入口、实际编译环境、参考文献和目标要求.

## 方法

1. 先确认编译器、主文件、引用及资源齐全；单文件tex在支持的agent用内置编译器。
2. 在独立输出位置执行获准编译，按日志修确有错误，不清除原件或擅换会议模板。
3. 默认最多三次修复，检查未定义引用、页数、缺图、过期章节及实际PDF内容。
4. 对目标当前要求列对照，编译成功和满足投稿要求分别判定。

## 产物与验收

实际编译日志、打开检查、错误修复与准备缺口.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
