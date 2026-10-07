---
name: mh-paper-aris-module-feishu-notify
description: "Feishu notification-protocol preparation; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Feishu notification-protocol preparation

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Notification purpose, authorized recipient, setup state and privacy boundary.

## Method

1. Define events and minimal content, separating status, evidence and requested decisions.
2. Check real webhook/interactive configuration and protect secrets; send only within explicit authorization.
3. Record genuine reply provenance; timeout means pending, not human approval.
4. Without setup/send authorization, prepare drafts only; installation sends no message or poll.

## Outputs and acceptance

Notification drafts, setup/authorization gaps and actual send/reply receipts.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
