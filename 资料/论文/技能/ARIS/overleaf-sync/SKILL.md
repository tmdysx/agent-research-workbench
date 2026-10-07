---
name: mh-paper-aris-module-overleaf-sync
description: "Overleaf同步边界与冲突处理；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# Overleaf同步边界与冲突处理

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

本地稿件范围、Overleaf项目ID、实际Git桥接授权.

## 方法

1. 先核官方Git桥接是否可用及项目身份，凭据由人安全配置，不写进对话或资料。
2. 建立独立同步副本，读取远端变化并逐项比对本地修改。
3. 冲突保留双方版本，只有获准文件进入同步；推送属于外部操作，需明确授权。
4. 交本地/远端状态与实际差异，未连通或未推送保持未执行，不安装即自动上传。

## 产物与验收

同步差异、冲突与处理记录；真实推送/未推送状态.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
