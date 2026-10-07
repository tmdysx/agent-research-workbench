---
name: mh-paper-aris-module-analyze-results
description: "Organize actual results, repeated-run statistics and anomalies while separating observation, interpretation and follow-up validation."
license: MIT
---

# Analyze actual experimental results

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

Authorized JSON/CSV/log results, configuration and baseline definitions, metric direction, and seeds or repeated-run information.

## Method

1. Read actual results by run and configuration; check units, sample definitions, splits and missing values. Retain failed and incomplete runs separately.
2. Use model, hyperparameter and data settings as independent variables and list primary and secondary metrics. Explain the denominator for baseline-relative changes; do not force a relative gain when the baseline is zero or definitions differ.
3. Report mean and standard deviation only when repeated runs exist, with the actual repeat count. Identify monotonic, U-shaped or plateau trends in sweeps and flag outliers.
4. For every finding, separate observation, possible explanation, implication and a testable next step. An associated trend is not automatically a causal mechanism.
5. Link important findings to result files and versions and propose report updates. Keep the conclusion unresolved when runs or essential comparisons are missing.

## Outputs and acceptance

A sourced comparison table, actual repeat statistics, anomaly list and observation–interpretation–validation notes. Key numbers must be recomputable from raw results; failed runs must not be treated as zero or successful outcomes.

## Dependencies and boundaries

The body requires no MCP, model API, cloud GPU or schedule. Use the authorized local analysis tools; this entry does not launch experiments or read unauthorized research directories.

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/analyze-results/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
