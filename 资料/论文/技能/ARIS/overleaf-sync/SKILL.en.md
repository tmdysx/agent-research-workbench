---
name: mh-paper-aris-module-overleaf-sync
description: "Overleaf sync boundary and conflicts; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Overleaf sync boundary and conflicts

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Local manuscript scope, Overleaf project ID and actual Git-bridge authorization.

## Method

1. Verify official Git-bridge availability and project identity; credentials are safely user-configured, never written into chat/materials.
2. Use a separate sync copy and compare remote changes with local edits.
3. Preserve both sides of conflicts and sync only authorized files; pushing needs explicit external-action authorization.
4. Report local/remote state and actual differences; unavailable access or unperformed pushes remain unexecuted.

## Outputs and acceptance

Sync diff, conflicts/dispositions and actual pushed/unpushed status.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
