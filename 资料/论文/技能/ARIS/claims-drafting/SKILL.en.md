---
name: mh-paper-aris-module-claims-drafting
description: "Patent-claim drafting reference; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Patent-claim drafting reference

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Actual invention disclosure, features, prior art and target jurisdiction.

## Method

1. Separate essential features and optional implementations, linking terms to disclosure support.
2. Draft a defensible independent claim, then supported fallback dependent claims.
3. Check antecedent basis, consistent terminology, dependencies and specification support without unsupported broadening.
4. Check current official jurisdiction requirements; technical drafts remain distinct from legal opinions or filing.

## Outputs and acceptance

Claim draft, feature-support map, scope and unresolved checks.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
