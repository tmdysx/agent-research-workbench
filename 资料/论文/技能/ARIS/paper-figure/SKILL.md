---
name: mh-paper-aris-module-paper-figure
description: "真实结果到学术图表；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 真实结果到学术图表

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

真实实验输出、图表计划、指标/统计定义.

## 方法

1. 从图表计划确定每图要支持的论断和原始文件/键，不从图片估计结果。
2. 选择适合比较、变化、分布或不确定性的图型，核单位、分母和误差。
3. 编写可复算绘图脚本并实际运行，保留数据版本、图文件与正文include对应。
4. 打开产物核字体、裁切、图例和颜色，审查不可用就交真实视觉自查及缺口。

## 产物与验收

绘图脚本、真实数据映射、图表及打开检查.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
