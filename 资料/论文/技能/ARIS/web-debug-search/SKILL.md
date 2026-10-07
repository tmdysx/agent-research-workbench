---
name: mh-paper-aris-module-web-debug-search
description: "工程问题检索与来源分级；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 工程问题检索与来源分级

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

实际报错、版本、复现步骤与搜索范围.

## 方法

1. 提取报错、平台、版本和最小复现，按官方文档、代码仓库及社区路由有界查询。
2. 分别标来源可信度、适用版本、复现匹配与方案风险，不按搜索排名当正确答案。
3. 合并重复结果，提出最小可回滚修复并注明来源和测试。
4. 工程经验只能支撑调试，不能直接作为论文论证引用；未验证建议保留为建议。

## 产物与验收

可复查查询、版本适用结果、修复建议与实际验证.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
