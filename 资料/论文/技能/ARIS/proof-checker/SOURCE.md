# 来源与改编 · Source and adaptation

- 稳定ID / Stable ID: `biz:paper:aris-module:proof-checker`
- 上游原文件 / Upstream path: `skills/proof-checker/SKILL.md`
- 固定来源 / Fixed source: [GitHub original](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/0472e530251cdbd3364c33b110063c58f819edd7/skills/proof-checker/SKILL.md)
- Archive comment commit: `0472e530251cdbd3364c33b110063c58f819edd7`
- Archive SHA-256: `ff9af6777b38318e75bbf369210de8b3021c84600c5718d7a1e3799d039aa359`
- 原文SHA-256 / Original SHA-256: `65900678dc8d68c5157971c087497094c8cc0e05b3c6d22e6a9351b88882657e`
- 来源审查日期 / Reviewed: 2026-10-06
- License: MIT, Copyright (c) 2026 wanshuiyin; [LICENSE.txt](LICENSE.txt) retained verbatim.

## 内容 / Contents

- [完整上游方法原文 / Complete verbatim upstream method](references/upstream.md) retained unchanged.
- SKILL.md and SKILL.en.md are equivalent local **method adaptations**, not a full word-for-word translation of the original. Adaptation contribution: tmdysx, agent-assisted, under this package MIT license.
- 原文元数据里的allowed-tools、固定模型、脚本位置与自动动作不是本平台授权；入口按当前计划、权限、预算及停止条件执行。
- Original allowed-tools, fixed models, script locations, and automation instructions do not grant platform permissions. Follow the current approved task, scope, budget, and stop conditions.

## 包内保留的必要文本 / Retained package-local texts

- [skills/shared-references/acceptance-gate.md](<references/support/skills/shared-references/acceptance-gate.md>) · SHA-256 `acfe2e790d97445396ff4eb605b91e4de756082d617b89cf9278bff76dc25623`
- [skills/shared-references/assurance-contract.md](<references/support/skills/shared-references/assurance-contract.md>) · SHA-256 `01745ff874cf2e662ce1349f79fa7549db4d6f25182af86ef90b621d598b755b`
- [skills/shared-references/external-cadence.md](<references/support/skills/shared-references/external-cadence.md>) · SHA-256 `d0d8e92c9c8f5e60555c8ddf32cf15c78d0bdc61a367ef35d8b0fef8dab906f3`
- [skills/shared-references/fan-out-pattern.md](<references/support/skills/shared-references/fan-out-pattern.md>) · SHA-256 `a788fd9fdc88d8b8e1331bcd9c64979914a44cf69018e1ce5be4cfd071a240cb`
- [skills/shared-references/reviewer-independence.md](<references/support/skills/shared-references/reviewer-independence.md>) · SHA-256 `fbbfcb6e7ff53010b596e8e01ce456d1906734f5bd198745f76ccd62787af3e3`
- [skills/shared-references/reviewer-routing.md](<references/support/skills/shared-references/reviewer-routing.md>) · SHA-256 `151fd817e746dfbebfd9988d7f09660d6f2f8d1e43cd5d67c91acbdb58201434`

## 外部能力与未带附件 / External capabilities and excluded attachments

`runtime_enabled=false`. 方法已收录不等于运行工具已安装或科学关口已验收。Method available does not mean runtime installed or a scientific gate passed.

- Codex MCP/Manual Review/Oracle外部证明审阅
- Agent fan-out并行检查；本地pdflatex报告；多轮有限修订
- 正文禁止外层定时包装，不得自行替代review判定

Excluded executable/asset references (not installed):
- `tools/research_wiki.py`
- `tools/verify_paper_audits.sh`

原文中的定时循环、通知、上传、云GPU和外部审阅均保留作方法背景，不在安装或阅读时执行。Upstream timers, notifications, uploads, cloud GPU and external review remain inactive reference background.
项目非商用条款不替代第三方MIT许可；图片、会议模板及独立工具依赖按自身权利另查。Platform noncommercial terms do not replace third-party MIT rights; images, venue assets and external dependencies need their own checks.
