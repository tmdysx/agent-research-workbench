---
name: mh-paper-aris-module-monitor-experiment
description: "实验进度只读检查；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 实验进度只读检查

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

获准作业身份、日志/结果位置、当前进程信息.

## 方法

1. 先确认作业、机器和窗口身份，关联不明就不猜测正在运行什么。
2. 只读查看进程、日志时间、训练进展及结果文件，区分退出、仍运行、断连和未知。
3. WandB等外部指标仅在实际已配置且获准时读取，收集信息不替代结果质量评价。
4. 输出最近成功观测和下一次需要查的事实；此方法不建立周期监控或发送通知。

## 产物与验收

当前进度、真实日志/退出证据、结果位置与未确认状态.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
