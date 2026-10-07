# 来源与改编 · Source and adaptation

- 稳定ID / Stable ID: `biz:paper:aris-module:wiki-enrich`
- 上游原文件 / Upstream path: `skills/wiki-enrich/SKILL.md`
- 固定来源 / Fixed source: [GitHub original](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/0472e530251cdbd3364c33b110063c58f819edd7/skills/wiki-enrich/SKILL.md)
- Archive comment commit: `0472e530251cdbd3364c33b110063c58f819edd7`
- Archive SHA-256: `ff9af6777b38318e75bbf369210de8b3021c84600c5718d7a1e3799d039aa359`
- 原文SHA-256 / Original SHA-256: `ef2636d24dedbf0824f4b0bec96dee8daf1aef3c4b72ebe772b87a2febe3ea39`
- 来源审查日期 / Reviewed: 2026-10-06
- License: MIT, Copyright (c) 2026 wanshuiyin; [LICENSE.txt](LICENSE.txt) retained verbatim.

## 内容 / Contents

- [完整上游方法原文 / Complete verbatim upstream method](references/upstream.md) retained unchanged.
- SKILL.md and SKILL.en.md are equivalent local **method adaptations**, not a full word-for-word translation of the original. Adaptation contribution: tmdysx, agent-assisted, under this package MIT license.
- 原文元数据里的allowed-tools、固定模型、脚本位置与自动动作不是本平台授权；入口按当前计划、权限、预算及停止条件执行。
- Original allowed-tools, fixed models, script locations, and automation instructions do not grant platform permissions. Follow the current approved task, scope, budget, and stop conditions.

## 包内保留的必要文本 / Retained package-local texts

- [skills/shared-references/integration-contract.md](<references/support/skills/shared-references/integration-contract.md>) · SHA-256 `891b4254337b6da02b25bef55cbe750e90f36fd7c8b537218e49febf6d69ddc0`
- [skills/shared-references/output-language.md](<references/support/skills/shared-references/output-language.md>) · SHA-256 `7b326400dca5130ce4beedf72fc2010680afe96eb56a6ab21210d323adc9a52e`
- [skills/shared-references/output-manifest.md](<references/support/skills/shared-references/output-manifest.md>) · SHA-256 `28e29bc8e53c52afe4eeeb590df8893282a3bbced08e105e154ad228b6cd1922`
- [skills/shared-references/wiki-helper-resolution.md](<references/support/skills/shared-references/wiki-helper-resolution.md>) · SHA-256 `ef6af207034a2eea17d437ac2f4c620962f72960ae7a5bf0d00818e1bafc71c2`

## 外部能力与未带附件 / External capabilities and excluded attachments

`runtime_enabled=false`. 方法已收录不等于运行工具已安装或科学关口已验收。Method available does not mean runtime installed or a scientific gate passed.

- 本地research_wiki.py；联网arXiv/AlphaXiv元数据与论文摘要
- 原文声明可作cron；本次不创建定时任务

Excluded executable/asset references (not installed):
- `tools/research_wiki.py`

原文中的定时循环、通知、上传、云GPU和外部审阅均保留作方法背景，不在安装或阅读时执行。Upstream timers, notifications, uploads, cloud GPU and external review remain inactive reference background.
项目非商用条款不替代第三方MIT许可；图片、会议模板及独立工具依赖按自身权利另查。Platform noncommercial terms do not replace third-party MIT rights; images, venue assets and external dependencies need their own checks.
