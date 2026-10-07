---
name: mh-paper-aris-module-vast-gpu
description: "Vast算力选择与费用边界；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# Vast算力选择与费用边界

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

负载、数据传输许可、成本上限和明确租用授权.

## 方法

1. 按显存、带宽、稳定性、镜像与地区筛选真实报价，保留查询时间和估算费用。
2. 将准备、训练、结果拉回和回收定义为独立检查点，明确实例和项目身份。
3. 没有明确租用授权只交候选与预算，内置方法不创建或销毁任何实例。
4. 获准实际操作时保存真实ID、启动/退出、费用及资源回收证据，失败不得反复花费。

## 产物与验收

报价/预算对照、授权资源清单、真实生命周期或待执行状态.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
