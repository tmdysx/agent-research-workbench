---
name: mh-paper-aris-module-patent-review
description: "Critical patent-draft review; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Critical patent-draft review

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Claims, specification, drawings, prior art and review scope.

## Method

1. Collect the full draft/evidence and specify jurisdiction and actual independent review context.
2. Locate novelty risks, unclear terms, unsupported claims, enablement gaps and drawing conflicts.
3. Repair only authorized technical/text issues without changing the invention or inventing tested effects.
4. Recheck revised support chains and preserve gaps; simulated examination is not an official outcome.

## Outputs and acceptance

Located review, actual revisions, support chains and open issues.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
