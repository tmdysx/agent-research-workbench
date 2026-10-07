---
name: mh-paper-aris-module-claims-drafting
description: "专利权利要求起草参考；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 专利权利要求起草参考

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

真实发明披露、技术特征、现有技术与目标辖区.

## 方法

1. 将发明拆成必要特征与可选实现，明确每个术语在披露中的支持位置。
2. 先写可防守的独立权利要求，再用从属项表达有依据的备选范围。
3. 核前置基础、术语一致、依赖编号及说明书支持，避免无依据地扩张范围。
4. 按当前官方辖区要求复查；技术草稿和法律结论/正式提交分开。

## 产物与验收

权利要求草稿、特征支持表、范围与待核项.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
