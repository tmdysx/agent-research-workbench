---
name: mh-paper-aris-module-experiment-queue
description: "Experiment queue and resource manifest; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Experiment queue and resource manifest

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Approved experiment blocks, real resources, dependencies and budget.

## Method

1. Map each experiment to its command, resources, output path and prerequisites in a checkable queue manifest.
2. Check exclusive resources and ordering; only ready inputs/environments make a job runnable.
3. Update pending/running/failed/completed states from real logs, processes and output files.
4. The scheduler and remote 60-second polling are not bundled; reading the manifest launches no job and execution follows the approved platform process.

## Outputs and acceptance

Queue, resource/dependency map, actual run states and blocking reasons.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
