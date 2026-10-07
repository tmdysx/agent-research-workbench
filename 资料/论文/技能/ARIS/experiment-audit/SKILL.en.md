---
name: mh-paper-aris-module-experiment-audit
description: "Locate integrity risks in ground truth, metrics, result files and code paths while distinguishing self-checks from actual independent review."
license: MIT
---

# Evidence audit of experimental integrity

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

Authorized evaluation/data-loading code, actual results, splits and ground-truth provenance, paper claims and run records.

## Method

1. Inventory evaluation scripts, data entries, results and claim files with versions and preserve raw material. For independent review, supply paths and audit questions without a defense designed to induce approval.
2. Verify whether ground truth comes from the dataset or established standard and whether the model’s own or another model’s output is masquerading as truth. Label synthetic proxies and their purpose.
3. Inspect metric definitions, denominators and normalization for self-maximum normalization and inconsistent definitions across systems.
4. Verify that files exist, numbers are present and executed code reaches the computation path. Distinguish imagined results, unrun dead branches and traceable outputs.
5. Assess whether datasets/scenarios support the claimed generality; declare evaluation types such as real_gt or synthetic_proxy and itemized PASS/WARN/FAIL or not-checked status.
6. Map findings to affected claims and repairs. Mark a verdict independent only after actual independent review; upstream’s advisory integration must not turn failed or absent review into a pass.

## Outputs and acceptance

An integrity report with file:line/result evidence, evaluation type, ground-truth/normalization/existence/dead-code/scope checks and claim impact. Verification requires explicit unchecked items and independent-review gaps.

## Dependencies and boundaries

Upstream Codex/Manual/Oracle MCP review and trace helpers are not activated automatically. A local self-check can identify issues but cannot claim completed cross-model independent audit; excluded or unrun scripts cannot be called passed gates.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [experiment-integrity.md](references/support/skills/shared-references/experiment-integrity.md)
- [reviewer-independence.md](references/support/skills/shared-references/reviewer-independence.md)
- [acceptance-gate.md](references/support/skills/shared-references/acceptance-gate.md)
- [review-tracing.md](references/support/skills/shared-references/review-tracing.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/experiment-audit/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
