---
name: mh-paper-aris-module-render-html
description: "HTML reading view of research records; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# HTML reading view of research records

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Authorized MD/JSON records, author style and actual rendering capability.

## Method

1. Identify artifact type/field provenance and preserve the MD/JSON source and real statuses.
2. Organize readable HTML with expandable long text and visible errors/missing fields.
3. Open the result to check Chinese, math, code and links; offline missing math libraries are not successful formula rendering.
4. The original renderer/CDN templates are not bundled; use actual local tools separately and record checks.

## Outputs and acceptance

HTML reading copy, source links, actual browser checks and rendering gaps.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
