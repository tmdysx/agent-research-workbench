---
name: mh-paper-aris-module-auto-review-loop-llm
description: "External LLM review rounds; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# External LLM review rounds

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Review target, permitted materials, authorized reviewer backend and round budget.

## Method

1. Specify claims, materials and the real reviewer channel; mark unavailable review as unperformed.
2. Send current facts and questions per round; retain verbatim responses, context origins and call evidence.
3. Separate criticism, proposals and checked results; implement authorized changes before reporting them back.
4. Recheck relevant issues within the round limit; a human decision remains pending rather than approved by timeout.

## Outputs and acceptance

Verbatim reviews, revision evidence and unresolved issues; the LLM interface is not bundled.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
