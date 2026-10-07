---
name: mh-paper-aris-module-result-to-claim
description: "Check numeric evidence existence before assessing supported scope and routing toward rejection, added evidence or writing preparation."
license: MIT
---

# Three-way routing from actual results to claims

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

Actual main results, each claim’s cited value and source file, baseline/seeds/splits, and any existing experiment-integrity audit.

## Method

1. Collect complete results and intended claims, separating sanity from main experiments, real from proxy evaluation and positive from negative outcomes. Record ID, value, source and scope for each numeric claim.
2. Perform deterministic existence checks: missing files or absent values become evidence_not_found and cannot support the claim; unparseable evidence is not checked. Finding a number proves existence, not computational correctness or claim support.
3. Submit existence-checked claims, actual controls and audit concerns to an authorized real review to assess conditions, scope, gaps and weaker defensible statements. Without independent review, retain REVIEW_UNAVAILABLE or an unreviewed draft rather than granting a supportive pass yourself.
4. Route three ways: no records failure/refutation and proposes a pivot; partial narrows the working claim and lists supplementary evidence; yes records supported scope and checks remaining ablation/writing evidence. Subsequent actions are proposals or currently authorized tasks only.
5. Preserve any existing integrity audit status. Good-looking results cannot turn warn/fail into pass, and one dataset does not establish universal claims.
6. For an existing authorized graph, link real experiment nodes before supports/invalidates edges. Empirical evidence must not change proof status. Retain actual reviewer identity, raw feedback and incomplete work.

## Outputs and acceptance

Per-claim existence checks, support scope and yes/partial/no routing with integrity status, evidence/review locations and next tasks. Verify that existence and scientific support are distinct gates and unreviewed claims are not treated as yes.

## Dependencies and boundaries

Upstream’s supportive verdict depends on Codex MCP; W&B, evidence_check.py and wiki helpers are not guaranteed ready. Perform authorized local evidence checks and negative findings first, without pinning a model, endlessly reviewing, auto-running supplements or creating support edges.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [evidence-precheck.md](references/support/skills/shared-references/evidence-precheck.md)
- [experiment-integrity.md](references/support/skills/shared-references/experiment-integrity.md)
- [acceptance-gate.md](references/support/skills/shared-references/acceptance-gate.md)
- [reviewer-routing.md](references/support/skills/shared-references/reviewer-routing.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/result-to-claim/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
