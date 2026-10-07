---
name: mh-paper-aris-module-formula-derivation
description: "Formula derivation with assumption layers; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Formula derivation with assumption layers

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Target formula, notation, assumptions and existing proof/reference.

## Method

1. Freeze the mathematical object and assumptions; separate exact identities, approximations and interpretations.
2. Expand definitions/algebra stepwise, state theorem conditions, and check dimensions, boundaries and degeneracies.
3. Record unsupported steps as proof obligations and consider counterexamples or a narrower claim.
4. Deliver a checkable derivation and notation table; intuition or numerical agreement is not proof.

## Outputs and acceptance

Stepwise derivation, notation/assumption table, open obligations and counterexamples.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
