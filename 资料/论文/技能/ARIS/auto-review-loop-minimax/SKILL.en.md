---
name: mh-paper-aris-module-auto-review-loop-minimax
description: "MiniMax review-method reference; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# MiniMax review-method reference

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Research materials, review questions, authorized MiniMax access and budget.

## Method

1. Prepare a bounded review package and verify actual authorized MiniMax access; without it, prepare the package only.
2. Request a bounded review and retain input, response and call provenance; a fixed model label is not identity evidence.
3. Map comments to locations, evidence and corrections; distinguish completed changes from plans.
4. Recheck the changes within budget and retain blocked issues; do not enable timers or infer approval from timeouts.

## Outputs and acceptance

Review package, actual response records and disposition map; MiniMax runtime requires configuration.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
