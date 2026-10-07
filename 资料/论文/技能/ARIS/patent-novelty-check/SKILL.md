---
name: mh-paper-aris-module-patent-novelty-check
description: "专利新颖性技术对照；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 专利新颖性技术对照

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

候选权利要求、现有技术原文与目标辖区.

## 方法

1. 拆解每个独立权利要求的必要技术要素并固定来源位置。
2. 先查单一现有技术是否完整公开要素，再讨论多个来源组合及技术动机。
3. 区分新颖性、创造性讨论与法律认定，标出缺全文、日期和来源不确定性。
4. 按当前官方辖区标准交技术对照及风险，不自称完成法律意见或保证授权。

## 产物与验收

要素对照、新颖性/组合风险及未核证据表.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
