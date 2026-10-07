---
name: mh-paper-aris-module-training-check
description: "One-shot training health check; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# One-shot training health check

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Actual training ID, logs/metrics and permitted intervention.

## Method

1. Verify metric freshness/job identity and check NaNs, divergence, stalled progress, idle GPUs and resource shortages.
2. Interpret evidence in the training phase, separating missing observation, transient fluctuation and persistent failure.
3. When uncertain, send evidence through an actual review channel; unavailable review is not a second opinion.
4. Stopping/restarting must fit existing authorization; installation enables no Cron/watchdog integration.

## Outputs and acceptance

Training-health observations, evidence and intervention proposals with unperformed actions.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
