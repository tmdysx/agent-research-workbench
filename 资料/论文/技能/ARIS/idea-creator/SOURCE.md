# 来源与改编 · Source and adaptation

- 稳定ID / Stable ID: `biz:paper:aris-module:idea-creator`
- 上游原文件 / Upstream path: `skills/idea-creator/SKILL.md`
- 固定来源 / Fixed source: [GitHub original](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/0472e530251cdbd3364c33b110063c58f819edd7/skills/idea-creator/SKILL.md)
- Archive comment commit: `0472e530251cdbd3364c33b110063c58f819edd7`
- Archive SHA-256: `ff9af6777b38318e75bbf369210de8b3021c84600c5718d7a1e3799d039aa359`
- 原文SHA-256 / Original SHA-256: `e78e20b2eff657953ba95134e89779954c77399779eee0134459b77d84efb602`
- 来源审查日期 / Reviewed: 2026-10-06
- License: MIT, Copyright (c) 2026 wanshuiyin; [LICENSE.txt](LICENSE.txt) retained verbatim.

## 内容 / Contents

- [完整上游方法原文 / Complete verbatim upstream method](references/upstream.md) retained unchanged.
- SKILL.md and SKILL.en.md are equivalent local **method adaptations**, not a full word-for-word translation of the original. Adaptation contribution: tmdysx, agent-assisted, under this package MIT license.
- 原文元数据里的allowed-tools、固定模型、脚本位置与自动动作不是本平台授权；入口按当前计划、权限、预算及停止条件执行。
- Original allowed-tools, fixed models, script locations, and automation instructions do not grant platform permissions. Follow the current approved task, scope, budget, and stop conditions.

## 包内保留的必要文本 / Retained package-local texts

- [skills/shared-references/acceptance-gate.md](<references/support/skills/shared-references/acceptance-gate.md>) · SHA-256 `acfe2e790d97445396ff4eb605b91e4de756082d617b89cf9278bff76dc25623`
- [skills/shared-references/citation-discipline.md](<references/support/skills/shared-references/citation-discipline.md>) · SHA-256 `01fc1cf751d7e0e6bef04897df6ef1bcf1e1b20e5b56d9f208e020cc48ba6725`
- [skills/shared-references/fan-out-pattern.md](<references/support/skills/shared-references/fan-out-pattern.md>) · SHA-256 `a788fd9fdc88d8b8e1331bcd9c64979914a44cf69018e1ce5be4cfd071a240cb`
- [skills/shared-references/injection-hygiene.md](<references/support/skills/shared-references/injection-hygiene.md>) · SHA-256 `bcab2455e4327eaa4feb3810035d1bf6e6a3e352e329badcad6ed95e5fe534de`
- [skills/shared-references/integration-contract.md](<references/support/skills/shared-references/integration-contract.md>) · SHA-256 `891b4254337b6da02b25bef55cbe750e90f36fd7c8b537218e49febf6d69ddc0`
- [skills/shared-references/output-composition.md](<references/support/skills/shared-references/output-composition.md>) · SHA-256 `8de81708431091a21a641be5f91db7958bb9f9a4b85d4fe03f52c5b496948651`
- [skills/shared-references/output-language.md](<references/support/skills/shared-references/output-language.md>) · SHA-256 `7b326400dca5130ce4beedf72fc2010680afe96eb56a6ab21210d323adc9a52e`
- [skills/shared-references/output-manifest.md](<references/support/skills/shared-references/output-manifest.md>) · SHA-256 `28e29bc8e53c52afe4eeeb590df8893282a3bbced08e105e154ad228b6cd1922`
- [skills/shared-references/output-versioning.md](<references/support/skills/shared-references/output-versioning.md>) · SHA-256 `73a4269b537be728b0ecc35789f11fa6d1fafa6d0430d07ad2738f064b1e4da3`
- [skills/shared-references/review-tracing.md](<references/support/skills/shared-references/review-tracing.md>) · SHA-256 `b531253ccee0414bde9e3d233e743d9dba9a4283cd40ec527c5863ba0fee6d44`
- [skills/shared-references/reviewer-routing.md](<references/support/skills/shared-references/reviewer-routing.md>) · SHA-256 `151fd817e746dfbebfd9988d7f09660d6f2f8d1e43cd5d67c91acbdb58201434`

## 外部能力与未带附件 / External capabilities and excluded attachments

`runtime_enabled=false`. 方法已收录不等于运行工具已安装或科学关口已验收。Method available does not mean runtime installed or a scientific gate passed.

- Codex MCP外部筛选；manual/Oracle可选覆写
- WebSearch/WebFetch、verify_papers.py核实论文
- Agent并行文献/候选视角及本地威胁扫描、wiki写入

Excluded executable/asset references (not installed):
- `tests/test_idea_creator_query_pack_scan.py`
- `tools/install_aris.sh`
- `tools/research_wiki.py`
- `tools/save_trace.sh`
- `tools/smart_update.sh`
- `tools/threat_scan.py`
- `tools/verify_papers.py`

原文中的定时循环、通知、上传、云GPU和外部审阅均保留作方法背景，不在安装或阅读时执行。Upstream timers, notifications, uploads, cloud GPU and external review remain inactive reference background.
项目非商用条款不替代第三方MIT许可；图片、会议模板及独立工具依赖按自身权利另查。Platform noncommercial terms do not replace third-party MIT rights; images, venue assets and external dependencies need their own checks.
