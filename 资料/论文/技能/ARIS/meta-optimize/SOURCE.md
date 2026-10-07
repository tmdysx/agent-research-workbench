# 来源与改编 · Source and adaptation

- 稳定ID / Stable ID: `biz:paper:aris-module:meta-optimize`
- 上游原文件 / Upstream path: `skills/meta-optimize/SKILL.md`
- 固定来源 / Fixed source: [GitHub original](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/0472e530251cdbd3364c33b110063c58f819edd7/skills/meta-optimize/SKILL.md)
- Archive comment commit: `0472e530251cdbd3364c33b110063c58f819edd7`
- Archive SHA-256: `ff9af6777b38318e75bbf369210de8b3021c84600c5718d7a1e3799d039aa359`
- 原文SHA-256 / Original SHA-256: `0599dcc7eec1b7204e67bb7960487c652b5034af8b2d18323f0a3ff057580fd2`
- 来源审查日期 / Reviewed: 2026-10-06
- License: MIT, Copyright (c) 2026 wanshuiyin; [LICENSE.txt](LICENSE.txt) retained verbatim.

## 内容 / Contents

- [完整上游方法原文 / Complete verbatim upstream method](references/upstream.md) retained unchanged.
- SKILL.md and SKILL.en.md are equivalent local **method adaptations**, not a full word-for-word translation of the original. Adaptation contribution: tmdysx, agent-assisted, under this package MIT license.
- 原文元数据里的allowed-tools、固定模型、脚本位置与自动动作不是本平台授权；入口按当前计划、权限、预算及停止条件执行。
- Original allowed-tools, fixed models, script locations, and automation instructions do not grant platform permissions. Follow the current approved task, scope, budget, and stop conditions.

## 包内保留的必要文本 / Retained package-local texts

- [skills/shared-references/acceptance-gate.md](<references/support/skills/shared-references/acceptance-gate.md>) · SHA-256 `acfe2e790d97445396ff4eb605b91e4de756082d617b89cf9278bff76dc25623`
- [skills/shared-references/capture-antipatterns.md](<references/support/skills/shared-references/capture-antipatterns.md>) · SHA-256 `419b914ade074842b815bff5133c18993a31305ca36e40b08918856777857378`
- [skills/shared-references/integration-contract.md](<references/support/skills/shared-references/integration-contract.md>) · SHA-256 `891b4254337b6da02b25bef55cbe750e90f36fd7c8b537218e49febf6d69ddc0`
- [skills/shared-references/output-language.md](<references/support/skills/shared-references/output-language.md>) · SHA-256 `7b326400dca5130ce4beedf72fc2010680afe96eb56a6ab21210d323adc9a52e`
- [skills/shared-references/output-manifest.md](<references/support/skills/shared-references/output-manifest.md>) · SHA-256 `28e29bc8e53c52afe4eeeb590df8893282a3bbced08e105e154ad228b6cd1922`
- [skills/shared-references/output-versioning.md](<references/support/skills/shared-references/output-versioning.md>) · SHA-256 `73a4269b537be728b0ecc35789f11fa6d1fafa6d0430d07ad2738f064b1e4da3`
- [skills/shared-references/review-tracing.md](<references/support/skills/shared-references/review-tracing.md>) · SHA-256 `b531253ccee0414bde9e3d233e743d9dba9a4283cd40ec527c5863ba0fee6d44`

## 外部能力与未带附件 / External capabilities and excluded attachments

`runtime_enabled=false`. 方法已收录不等于运行工具已安装或科学关口已验收。Method available does not mean runtime installed or a scientific gate passed.

- Codex MCP外部adversarial审阅
- 读取Claude hook日志、capture_filter/provenance/trigger_eval等本地helper
- 原文涉及~/.claude skill corpus候选patch与hook配置；本次禁止执行变更

Excluded executable/asset references (not installed):
- `templates/claude-hooks/corpus_write_guard.json`
- `templates/claude-hooks/meta_logging.json`
- `tools/capture_filter.py`
- `tools/meta_opt/check_ready.sh`
- `tools/meta_opt/trigger_eval.py`
- `tools/meta_opt/trigger_evals.sample.json`
- `tools/provenance.py`
- `tools/save_trace.sh`

原文中的定时循环、通知、上传、云GPU和外部审阅均保留作方法背景，不在安装或阅读时执行。Upstream timers, notifications, uploads, cloud GPU and external review remain inactive reference background.
项目非商用条款不替代第三方MIT许可；图片、会议模板及独立工具依赖按自身权利另查。Platform noncommercial terms do not replace third-party MIT rights; images, venue assets and external dependencies need their own checks.
