# 来源与改编 · Source and adaptation

- 稳定ID / Stable ID: `biz:paper:aris-module:research-lit`
- 上游原文件 / Upstream path: `skills/research-lit/SKILL.md`
- 固定来源 / Fixed source: [GitHub original](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/0472e530251cdbd3364c33b110063c58f819edd7/skills/research-lit/SKILL.md)
- Archive comment commit: `0472e530251cdbd3364c33b110063c58f819edd7`
- Archive SHA-256: `ff9af6777b38318e75bbf369210de8b3021c84600c5718d7a1e3799d039aa359`
- 原文SHA-256 / Original SHA-256: `00d9f549e4db72f3b02d55b9f6dcd61b20403f5a7e25cf3396160423140b9183`
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
- [skills/shared-references/integration-contract.md](<references/support/skills/shared-references/integration-contract.md>) · SHA-256 `891b4254337b6da02b25bef55cbe750e90f36fd7c8b537218e49febf6d69ddc0`
- [skills/shared-references/output-composition.md](<references/support/skills/shared-references/output-composition.md>) · SHA-256 `8de81708431091a21a641be5f91db7958bb9f9a4b85d4fe03f52c5b496948651`
- [skills/shared-references/wiki-helper-resolution.md](<references/support/skills/shared-references/wiki-helper-resolution.md>) · SHA-256 `ef6af207034a2eea17d437ac2f4c620962f72960ae7a5bf0d00818e1bafc71c2`

## 外部能力与未带附件 / External capabilities and excluded attachments

`runtime_enabled=false`. 方法已收录不等于运行工具已安装或科学关口已验收。Method available does not mean runtime installed or a scientific gate passed.

- Zotero/Obsidian MCP可选知识库入口
- 联网arXiv/Semantic Scholar/OpenAlex/DeepXiv/WebSearch/WebFetch多源检索
- Gemini搜索可选；Exa须显式请求且EXA_API_KEY+exa-py
- 本地各fetch helper、wiki写入与verify_papers.py

Excluded executable/asset references (not installed):
- `tools/arxiv_fetch.py`
- `tools/deepxiv_fetch.py`
- `tools/exa_search.py`
- `tools/install_aris.sh`
- `tools/openalex_fetch.py`
- `tools/research_wiki.py`
- `tools/semantic_scholar_fetch.py`
- `tools/smart_update.sh`
- `tools/verify_papers.py`

原文中的定时循环、通知、上传、云GPU和外部审阅均保留作方法背景，不在安装或阅读时执行。Upstream timers, notifications, uploads, cloud GPU and external review remain inactive reference background.
项目非商用条款不替代第三方MIT许可；图片、会议模板及独立工具依赖按自身权利另查。Platform noncommercial terms do not replace third-party MIT rights; images, venue assets and external dependencies need their own checks.
