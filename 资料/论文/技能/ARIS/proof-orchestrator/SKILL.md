---
name: mh-paper-aris-module-proof-orchestrator
description: "跨轮证明接手方法；基于完整ARIS原文的本地方法适配，运行依赖未随此包安装。"
license: MIT
---

# 跨轮证明接手方法

本入口为方法适配，并非逐字全文翻译。完整上游原文单独保留。材料和产物写当前获准工作区，先读本轮目标、计划、适用戒律和最新接手记录。

## 输入

明确命题、历史证明尝试、当前运行目录和预算.

## 方法

1. 先冻结目标命题、假设、量词和允许来源，在独立本轮目录区分沿用事实、推导和未证义务。
2. 实际尝试完整本地证明、反证或诊断，并逐项核引理、归约、等式、界和量词；在local-proof里保存完整尝试及最小阻塞。
3. 按[notation-audit](references/support/skills/proof-orchestrator/references/notation-audit.md)保留完整七行scorecard：核心对象保留100%、未定义符号和符号冲突均为0；不能靠发明定义、条件或关系达标。
4. 非平凡推导按“目标→足够的子目标→各依赖来源→合回目标”写清；核依赖无环、不倒置蕴含、不让子目标偷用结论。记录Top-down derivation structure的PASS/FAIL/NOT_APPLICABLE，失败不标READY_FOR_USER。
5. 本地尝试卡住后才准备人工接手包，保留命题、符号、限制、实际失败尝试和具体待答问题；不把困难探测当最终证明。
6. GPT Pro或DeepSeek只在真实获准通道使用，第二意见是附加证据；本地正确性审计和proof-checker核验仍须实际完成。

## 产物与验收

运行账本、失败尝试、接手包及未证义务；保留EtaSkill重许可声明.

每项结论和完成状态能回到实际文件、来源及检查。缺材料、缺独立环境或未执行检查明确报告；产物已写不代替平台交付验收。

## 依赖与边界

`runtime_enabled=false`.

本包安装文本方法与参考；脚本、MCP、模型API、云GPU、上传、消息与定时器没有启用。仅在本轮已授权且能力实际存在时开展相应动作；模型名称不能证明独立审查，评分不能授予权限。

实际原文依赖与未带附件见 [SOURCE.md](SOURCE.md)。必要支持文档已在本包 `references/support/` 内保留；其中旧工具路径和动作只是上游背景。

## 来源

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
