---
name: mh-paper-aris-module-ablation-planner
description: "Turn existing main results and mechanism claims into ablations with predictions, priorities and a compute budget."
license: MIT
---

# Claim-driven ablation planning

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

Removable or replaceable components, differences from the baseline, actual main results, supported or partly supported claims, and the authorized compute budget.

## Method

1. Map mechanism claims to existing evidence first. If main results are not established, record the gap instead of using extensive ablations to conceal a failed main experiment.
2. Remove components or replace them with simpler alternatives to isolate the new mechanism. Do not schedule no-op ablations of components identical to the baseline.
3. State what each comparison tests and what should happen if the component matters; then add key hyperparameter sensitivity and natural design alternatives.
4. Record must-run and optional items, code versus configuration changes, dependencies and estimated cost. Prioritize informative component ablations and configuration changes; estimates are not measured runtime.
5. Propose justified cuts when the list exceeds the budget and retain that decision. If execution is authorized, smoke-test before full runs and record positive and negative outcomes to revise the claims.

## Outputs and acceptance

An ablation matrix with variants, claims, discriminating predictions, controls, priorities, run order and budget. Each item must answer a mechanism question; existing numbers must point to actual results and unrun items remain planned.

## Dependencies and boundaries

Upstream asks Codex MCP to design ablations and continues into implementation and execution. Local planning is usable for the authorized task; external review, GPU training and W&B are not activated by this entry.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [experiment-integrity.md](references/support/skills/shared-references/experiment-integrity.md)
- [acceptance-gate.md](references/support/skills/shared-references/acceptance-gate.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/ablation-planner/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
