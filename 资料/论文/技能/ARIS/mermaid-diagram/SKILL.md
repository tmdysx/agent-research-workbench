---
name: mh-paper-aris-module-mermaid-diagram
description: "Mermaid可编辑关系图；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# Mermaid可编辑关系图

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

明确关系、图类型、标签、输出用途及实际渲染器.

## 方法

1. 按流程、时序、类/实体关系或时间安排选适当图型，不凭布局猜业务关系。
2. 写可编辑Mermaid源码和文字说明，控制节点密度并保持术语一致。
3. 有实际renderer时检查语法再打开图，修溢出、交叉、乱码和对比度。
4. 缺renderer只交源码和未验证状态；最多三轮语法修复，不虚报视觉评审。

## 产物与验收

Mermaid源码、关系说明和实际语法/视觉检查.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
