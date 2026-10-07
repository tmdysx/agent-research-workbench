---
name: mh-paper-aris-module-proof-orchestrator
description: "Cross-run proof handoff; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Cross-run proof handoff

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Defined proposition, prior attempts, current run directory and budget.

## Method

1. Freeze the proposition, assumptions, quantifiers and allowed sources; in a separate run folder distinguish inherited facts, derivations and open obligations.
2. Actually attempt a complete local proof, disproof or diagnosis and audit lemmas, reductions, equalities, bounds and quantifiers; retain the full attempt and smallest blocker in local-proof.
3. Use the complete seven-line scorecard in [notation-audit](references/support/skills/proof-orchestrator/references/notation-audit.md): 100% core-object retention and zero undefined symbols/collisions, without inventing definitions, conditions or relations.
4. For nontrivial derivations show target → sufficient subgoals → dependency sources → closure of the target; require an acyclic graph, justified implications and no assumed target. Record Top-down derivation structure as PASS/FAIL/NOT_APPLICABLE; a failed gate is not READY_FOR_USER.
5. Only after a stalled local attempt prepare a manual handoff with proposition, notation, constraints, actual failed attempts and focused questions; a difficulty probe is not the final proof.
6. Use GPT Pro/DeepSeek only through actual authorized access as supplementary evidence; actual local correctness audit and proof-checker verification remain required.

## Outputs and acceptance

Run ledger, failed attempts, handoff package and open obligations; retain EtaSkill relicensing notice.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
