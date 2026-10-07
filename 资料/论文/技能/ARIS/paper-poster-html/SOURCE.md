# 来源与改编 · Source and adaptation

- 稳定ID / Stable ID: `biz:paper:aris-module:paper-poster-html`
- 上游原文件 / Upstream path: `skills/paper-poster-html/SKILL.md`
- 固定来源 / Fixed source: [GitHub original](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/0472e530251cdbd3364c33b110063c58f819edd7/skills/paper-poster-html/SKILL.md)
- Archive comment commit: `0472e530251cdbd3364c33b110063c58f819edd7`
- Archive SHA-256: `ff9af6777b38318e75bbf369210de8b3021c84600c5718d7a1e3799d039aa359`
- 原文SHA-256 / Original SHA-256: `b3c55d212f5c0cbccc94ec62813ad8df9302467edd825c62959edb4ba2778f8e`
- 来源审查日期 / Reviewed: 2026-10-06
- License: MIT, Copyright (c) 2026 wanshuiyin; [LICENSE.txt](LICENSE.txt) retained verbatim.

## 内容 / Contents

- [完整上游方法原文 / Complete verbatim upstream method](references/upstream.md) retained unchanged.
- SKILL.md and SKILL.en.md are equivalent local **method adaptations**, not a full word-for-word translation of the original. Adaptation contribution: tmdysx, agent-assisted, under this package MIT license.
- 原文元数据里的allowed-tools、固定模型、脚本位置与自动动作不是本平台授权；入口按当前计划、权限、预算及停止条件执行。
- Original allowed-tools, fixed models, script locations, and automation instructions do not grant platform permissions. Follow the current approved task, scope, budget, and stop conditions.

## 包内保留的必要文本 / Retained package-local texts

- [skills/paper-poster-html/DESIGN_FINAL.md](<references/support/skills/paper-poster-html/DESIGN_FINAL.md>) · SHA-256 `1e1931569efe301a05ce815c238f48b05b7f27a92a7d179f84ebe1d5e22fdf25`
- [skills/paper-poster-html/IMPLEMENTATION_CONVENTIONS.md](<references/support/skills/paper-poster-html/IMPLEMENTATION_CONVENTIONS.md>) · SHA-256 `59cdf8fafb92a22efa93971b647e05386f46c473909c752674d65990b8886483`
- [skills/paper-poster-html/LICENSES/posterly-MIT.txt](<references/posterly-MIT.txt>) · SHA-256 `0f097b552f2be95d202723d681c73a1dec10d64d0afea3ee0a0eaf63def9a5be`
- [skills/paper-poster-html/NOTICE.md](<NOTICE.md>) · SHA-256 `058090d55f2c7d143f70b4e3020cb7bcb8349480edd9dbf46921e05067862ab1`
- [skills/paper-poster-html/templates/COMPONENTS.md](<references/support/skills/paper-poster-html/templates/COMPONENTS.md>) · SHA-256 `382e60604f4bbe9a8aa96272348f34314089de847760c1897a6f701b5984f8b8`
- [skills/paper-poster-html/templates/README.md](<references/support/skills/paper-poster-html/templates/README.md>) · SHA-256 `366923d0de663296a2e3aca8479775423ac280b126d9d9272aa0041413dca309`
- [skills/shared-references/review-tracing.md](<references/support/skills/shared-references/review-tracing.md>) · SHA-256 `b531253ccee0414bde9e3d233e743d9dba9a4283cd40ec527c5863ba0fee6d44`
- [skills/shared-references/taste-calibration.md](<references/support/skills/shared-references/taste-calibration.md>) · SHA-256 `245e12a52b6c013022ddbcd8c682e4e5290bda6e38ecc6f14d7b2eaeb2988af8`
- [templates/README.md](<references/support/templates/README.md>) · SHA-256 `334aac9654abd110dd1201f0e56915f11a3e1e47304079856ce0db66c25dc635`

## 外部能力与未带附件 / External capabilities and excluded attachments

`runtime_enabled=false`. 方法已收录不等于运行工具已安装或科学关口已验收。Method available does not mean runtime installed or a scientific gate passed.

- Codex MCP fresh海报审阅
- 本地Playwright/Chromium、PyMuPDF/Pillow、Poppler；可选Inkscape/pdf2svg
- 附件scripts是可执行测量/门控工具，缺失时原流程不可运行
- 模板默认MathJax jsdelivr CDN；SKILL要求先下载本地；QR工具可选

Excluded executable/asset references (not installed):
- `skills/paper-poster-html/scripts/_posterly/__init__.py`
- `skills/paper-poster-html/scripts/_posterly/canvas.py`
- `skills/paper-poster-html/scripts/_posterly/measure.py`
- `skills/paper-poster-html/scripts/_posterly/polish.py`
- `skills/paper-poster-html/scripts/_posterly/preflight.py`
- `skills/paper-poster-html/scripts/_posterly/render.py`
- `skills/paper-poster-html/scripts/_posterly/textutil.py`
- `skills/paper-poster-html/scripts/_posterly/verify_final.py`
- `skills/paper-poster-html/scripts/asset_check.py`
- `skills/paper-poster-html/scripts/extract_pdf_figures.py`
- `skills/paper-poster-html/scripts/poster_check.py`
- `skills/paper-poster-html/scripts/preprocess_figures.py`
- `skills/paper-poster-html/scripts/render_preview.py`
- `skills/paper-poster-html/scripts/run_gates.py`
- `skills/paper-poster-html/scripts/style_check.py`
- `skills/paper-poster-html/templates/landscape_4col.html`
- `skills/paper-poster-html/templates/landscape_hero.html`
- `skills/paper-poster-html/templates/portrait_2col.html`
- `skills/paper-poster-html/templates/tokens/acl.json`
- `skills/paper-poster-html/templates/tokens/cvpr.json`
- `skills/paper-poster-html/templates/tokens/generic.json`
- `skills/paper-poster-html/templates/tokens/iclr.json`
- `skills/paper-poster-html/templates/tokens/icml.json`
- `skills/paper-poster-html/templates/tokens/neurips.json`

原文中的定时循环、通知、上传、云GPU和外部审阅均保留作方法背景，不在安装或阅读时执行。Upstream timers, notifications, uploads, cloud GPU and external review remain inactive reference background.
项目非商用条款不替代第三方MIT许可；图片、会议模板及独立工具依赖按自身权利另查。Platform noncommercial terms do not replace third-party MIT rights; images, venue assets and external dependencies need their own checks.
