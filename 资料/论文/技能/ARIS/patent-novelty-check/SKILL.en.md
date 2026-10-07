---
name: mh-paper-aris-module-patent-novelty-check
description: "Patent novelty technical comparison; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Patent novelty technical comparison

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Candidate claims, original prior art and target jurisdiction.

## Method

1. Decompose essential elements of each independent claim with source locations.
2. Check complete disclosure in a single prior-art item before discussing combinations and technical motivation.
3. Separate novelty/inventive-step discussion from legal determination and mark missing texts, dates and provenance.
4. Use current official jurisdiction standards for a technical comparison/risk report, not a legal opinion or grant guarantee.

## Outputs and acceptance

Element comparison, novelty/combination risks and unverified evidence.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
