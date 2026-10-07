---
name: mh-paper-aris-module-paper-poster-html
description: "HTML学术海报设计方法；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# HTML学术海报设计方法

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

已核论文、真实图表、当前会场尺寸、品牌与输出要求.

## 方法

1. 先核会场当前规范与输入，确定故事、版式、色板和必要内容。
2. 每张图追到原论文页/区域/版本，保留真实图而不是重画数字。
3. 设计HTML/CSS版面及文本层级，测量可读性、溢出、间距和图片清晰度。
4. 只有实际运行渲染/测量工具才报告门控通过；本包不带posterly脚本、HTML/CDN模板或图片。
5. 保留posterly NOTICE和MIT，交实际预览/打印检查或明确尚未运行。

## 产物与验收

海报内容/版面规范、图来源清单、实际预览与打印检查.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
