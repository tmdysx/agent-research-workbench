---
name: mh-paper-aris-module-vast-gpu
description: "Vast resource selection and spending boundary; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Vast resource selection and spending boundary

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Workload, data-transfer permission, cost limit and explicit rental authorization.

## Method

1. Filter real offers by VRAM, bandwidth, reliability, image and location with timestamped costs.
2. Define preparation, training, result collection and cleanup checkpoints with instance/project identity.
3. Without explicit rental authorization, provide candidates/budget only; this installed method creates or destroys no instance.
4. For authorized operations, retain actual IDs, start/exit, cost and cleanup evidence without repeated unbounded spending.

## Outputs and acceptance

Offer/budget comparison, authorized resource manifest and actual lifecycle or pending state.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
