---
name: mh-paper-aris-module-patent-pipeline
description: "Staged patent-document route; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Staged patent-document route

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Actual disclosure, prior art, inventor requirements and jurisdiction.

## Method

1. Organize disclosure/confirmations and perform traceable prior-art search and technical novelty discussion.
2. Define the problem-solution structure and essential features; draft claims before specification/embodiments.
3. Check drawings, terms, effects, claim support and actual content before jurisdiction formatting.
4. Preserve sources, gaps and versions per stage; deliver local technical drafts without upload, filing or legal guarantees.

## Outputs and acceptance

Staged disclosure, searches, claims, specification/format package and gaps.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
