---
name: mh-paper-aris-module-paper-slides
description: "论文到幻灯片与讲者备注；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 论文到幻灯片与讲者备注

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

已核论文、受众、讲述时长和输出格式.

## 方法

1. 提取一条报告主线，把每页设计成一个读者要点，张数按时间和信息密度决定。
2. 按原论文证据组织图表、标签和逐页备注，不夸张结果。
3. 选择实际可用的Beamer/PPTX制作能力，输出可编辑版本与必要预览。
4. 实际打开/渲染核版式，写讲稿并计时排练；未装工具和未测时长明确。

## 产物与验收

逐页大纲、备注讲稿、可编辑slides及实际预览/计时.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
