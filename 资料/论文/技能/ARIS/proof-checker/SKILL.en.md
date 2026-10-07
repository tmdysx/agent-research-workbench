---
name: mh-paper-aris-module-proof-checker
description: "Proof gaps and global closure; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Proof gaps and global closure

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Theorem/proof, assumptions, cited results and actual review environment.

## Method

1. Build an obligation ledger and dependency graph with explicit quantifiers, domains and assumptions.
2. Independently check missing conditions, circularity, dimensional mistakes and boundaries; seek counterexamples to key steps.
3. For authorized repairs, provide full derivations and recheck dependent restatements, corollaries and prose claims.
4. Verify global closure; when unrecoverable, report blockers/open obligations and ranked options to narrow the claim, strengthen assumptions, add a lemma or restructure the argument for an authorized decision. A proof gap alone is not a counterexample.

## Outputs and acceptance

Proof obligations, gaps/repairs, counterexamples, global checks and actual independence record.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
