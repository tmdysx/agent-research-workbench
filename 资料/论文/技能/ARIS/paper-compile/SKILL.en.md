---
name: mh-paper-aris-module-paper-compile
description: "Paper compilation and artifact checks; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Paper compilation and artifact checks

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Manuscript entry, actual build environment, references and target requirements.

## Method

1. Verify compiler, main file, references and assets; use the built-in compiler for supported standalone tex.
2. Build into a separate output location and repair actual logged errors without removing originals or replacing venue assets.
3. Normally allow up to three repair attempts, checking undefined references, page count, figures, stale sections and actual PDF content.
4. Map current target requirements separately; build success is not submission readiness.

## Outputs and acceptance

Actual build log, open checks, repairs and readiness gaps.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
