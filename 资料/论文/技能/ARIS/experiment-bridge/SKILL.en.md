---
name: mh-paper-aris-module-experiment-bridge
description: "Translate an approved experiment matrix into inspectable code/environment contracts, sanity checks and an initial-evidence handoff."
license: MIT
---

# From experiment plan to code contract and initial evidence

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

The authorized final proposal, experiment plan/tracker, claim contract, allowed files, existing code/data, environment and budget.

## Method

1. Extract task/split, compared systems, metrics, hyperparameters, seeds, criteria, must-run blocks and milestone order from the plan. Draft a missing claim contract first without inventing additional experiments.
2. Write a code contract linking method components to files, train/eval entries, parameter interfaces, controlled seeds, JSON/CSV outputs and versions. Reuse authorized existing code first.
3. Evaluate all systems against the same dataset ground truth, splits and metrics. Separate supervision, fitting and testing roles; do not substitute model output for truth or change metrics opportunistically.
4. Bind code version, Python/dependency phases, data and commands in an environment description. Distinguish import, training smoke-test and actual-task validation; perform a sanity test only in the available environment and record the actual outcome.
5. Only after an actual sanity pass and within the authorized run scope, proceed through sanity→baseline→main→ablation for this task. Disclose absent independent code review; without an environment, deliver contracts and unrun plans.
6. Collect initial JSON/CSV/log outputs linked to run ID, configuration, ground-truth definitions and failures and hand them to result-to-claim assessment. Do not automatically chain W&B, ablations, notifications or remote queues.

## Outputs and acceptance

A method–code–command–data–result contract, actual sanity record, initial result/failure table and unrun list. Verification must trace real sources; a sanity pass is not completion of main experiments or the full chain.

## Dependencies and boundaries

This method package installs no trainer, queue, W&B or Codex reviewer and does not automatically clone external projects, upload over SSH, rent Vast/Modal GPUs or send notifications. Execute only in an actually available environment already authorized for the current task.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [compute-env-contract.md](references/support/skills/shared-references/compute-env-contract.md)
- [experiment-integrity.md](references/support/skills/shared-references/experiment-integrity.md)
- [RESEARCH_CONTRACT_TEMPLATE.md](references/support/templates/RESEARCH_CONTRACT_TEMPLATE.md)
- [SESSION_RECOVERY_GUIDE.md](references/support/docs/SESSION_RECOVERY_GUIDE.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/experiment-bridge/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
