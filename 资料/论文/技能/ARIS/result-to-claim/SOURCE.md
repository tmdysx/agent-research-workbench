# 来源与改编 · Source and adaptation

- 稳定ID / Stable ID: `biz:paper:aris-module:result-to-claim`
- 上游原文件 / Upstream path: `skills/result-to-claim/SKILL.md`
- 固定来源 / Fixed source: [GitHub original](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/0472e530251cdbd3364c33b110063c58f819edd7/skills/result-to-claim/SKILL.md)
- Archive comment commit: `0472e530251cdbd3364c33b110063c58f819edd7`
- Archive SHA-256: `ff9af6777b38318e75bbf369210de8b3021c84600c5718d7a1e3799d039aa359`
- 原文SHA-256 / Original SHA-256: `ba53865e333fb05271ad116b94879d567d1e681f592dec2a7e8ae7eac6ef13d6`
- 来源审查日期 / Reviewed: 2026-10-06
- License: MIT, Copyright (c) 2026 wanshuiyin; [LICENSE.txt](LICENSE.txt) retained verbatim.

## 内容 / Contents

- [完整上游方法原文 / Complete verbatim upstream method](references/upstream.md) retained unchanged.
- SKILL.md and SKILL.en.md are equivalent local **method adaptations**, not a full word-for-word translation of the original. Adaptation contribution: tmdysx, agent-assisted, under this package MIT license.
- 原文元数据里的allowed-tools、固定模型、脚本位置与自动动作不是本平台授权；入口按当前计划、权限、预算及停止条件执行。
- Original allowed-tools, fixed models, script locations, and automation instructions do not grant platform permissions. Follow the current approved task, scope, budget, and stop conditions.

## 包内保留的必要文本 / Retained package-local texts

- [skills/shared-references/acceptance-gate.md](<references/support/skills/shared-references/acceptance-gate.md>) · SHA-256 `acfe2e790d97445396ff4eb605b91e4de756082d617b89cf9278bff76dc25623`
- [skills/shared-references/evidence-precheck.md](<references/support/skills/shared-references/evidence-precheck.md>) · SHA-256 `919a437a2e4a618ff6bcac6c03b7ec12bde3fef33d1a2aea25c9d98fcbd5e2d2`
- [skills/shared-references/experiment-integrity.md](<references/support/skills/shared-references/experiment-integrity.md>) · SHA-256 `22150fbdc5867e7790c88f968bccb367079c2db4c190ddce980709aea7e76f60`
- [skills/shared-references/external-cadence.md](<references/support/skills/shared-references/external-cadence.md>) · SHA-256 `d0d8e92c9c8f5e60555c8ddf32cf15c78d0bdc61a367ef35d8b0fef8dab906f3`
- [skills/shared-references/integration-contract.md](<references/support/skills/shared-references/integration-contract.md>) · SHA-256 `891b4254337b6da02b25bef55cbe750e90f36fd7c8b537218e49febf6d69ddc0`
- [skills/shared-references/review-tracing.md](<references/support/skills/shared-references/review-tracing.md>) · SHA-256 `b531253ccee0414bde9e3d233e743d9dba9a4283cd40ec527c5863ba0fee6d44`
- [skills/shared-references/reviewer-routing.md](<references/support/skills/shared-references/reviewer-routing.md>) · SHA-256 `151fd817e746dfbebfd9988d7f09660d6f2f8d1e43cd5d67c91acbdb58201434`
- [skills/shared-references/wiki-helper-resolution.md](<references/support/skills/shared-references/wiki-helper-resolution.md>) · SHA-256 `ef6af207034a2eea17d437ac2f4c620962f72960ae7a5bf0d00818e1bafc71c2`

## 外部能力与未带附件 / External capabilities and excluded attachments

`runtime_enabled=false`. 方法已收录不等于运行工具已安装或科学关口已验收。Method available does not mean runtime installed or a scientific gate passed.

- Codex MCP外部论断裁决必需；不可用必须REVIEW_UNAVAILABLE
- W&B API可选输入；本地evidence_check.py/wiki写入及trace
- 正文禁止定时包装；仅负向确定性证据检查可不经review

Excluded executable/asset references (not installed):
- `tools/evidence_check.py`
- `tools/install_aris.sh`
- `tools/research_wiki.py`
- `tools/save_trace.sh`
- `tools/smart_update.sh`

原文中的定时循环、通知、上传、云GPU和外部审阅均保留作方法背景，不在安装或阅读时执行。Upstream timers, notifications, uploads, cloud GPU and external review remain inactive reference background.
项目非商用条款不替代第三方MIT许可；图片、会议模板及独立工具依赖按自身权利另查。Platform noncommercial terms do not replace third-party MIT rights; images, venue assets and external dependencies need their own checks.
