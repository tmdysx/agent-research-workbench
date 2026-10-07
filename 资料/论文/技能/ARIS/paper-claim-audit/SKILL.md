---
name: mh-paper-aris-module-paper-claim-audit
description: "论文论断与原始结果核对；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 论文论断与原始结果核对

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

当前稿件、实际结果文件、评价版本、独立读审环境.

## 方法

1. 枚举数字、排名比较、范围和实验设置论断，定位到正文表图。
2. 为每条找到原结果文件、键、分母、统计方法和代码/数据版本；不足就标缺证据。
3. 由真实新上下文审查者仅根据本轮材料核对，不把作者总结或此前通过作为依据。
4. 记录PASS/WARN/FAIL及具体证据范围；缺独立审查时只交自查结果，不虚报零上下文审查。

## 产物与验收

完整论断核对表、真实输入指纹、问题位置及判定限度.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
