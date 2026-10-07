---
name: mh-paper-aris-module-monitor-experiment
description: "Read-only experiment progress checks; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Read-only experiment progress checks

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Authorized job identity, log/result paths and current process information.

## Method

1. Verify job, machine and window identity without guessing ambiguous associations.
2. Read processes, log timestamps, progress and outputs, distinguishing exited, running, disconnected and unknown states.
3. Read external metrics such as WandB only when actually configured and authorized; observations do not establish scientific quality.
4. Report the latest successful observation and the next factual check; this method creates no timer or notification.

## Outputs and acceptance

Progress, actual log/exit evidence, output locations and unconfirmed states.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
