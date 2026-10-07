---
name: research-results-figures
description: "Calculate comparisons and traceable figures from real experiment outputs and determine claim scope; use for results, ablations, and failure analysis without inventing data."
license: MIT
metadata:
  display_name: "Results and Figures"
  version: "1.0.0"
  language: en
---

# Results and Figures

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

Plan, successful and failed runs, raw results, split/evaluation versions, and baselines. Label screenshots and paper-reported values by their actual source, never as new experiment results.

## Workflow

1. In [assets/结果与图表清单.md](assets/结果与图表清单.md), verify sources, units, conditions, and independent samples. Map raw values to calculations, tables/figures, and claims.
2. Read [references/结果解释与图表.md](references/结果解释与图表.md). Inspect missing, duplicate, failed, abnormal, and reversed metrics. Justify exclusions and preserve originals; do not replace failure with zero.
3. Distinguish absolute differences, relative changes, and percentage points. Do not compute relative change with a zero or meaningless denominator. Show independent-repeat distributions or mean/spread; select intervals/tests according to design. Standard deviation is not a confidence interval.
4. Compare only matched conditions; label published values separately. Describe ablation changes and fixed factors. List resources, capacity, splits, or tuning as alternative explanations when relevant.
5. Produce quantitative figures from actual data and deterministic steps. Label axes/units, sample count, error meaning, filtering, sources, and reproducible scripts/steps. Label conceptual diagrams as illustrations, never fabricated quantitative plots.
6. Separate observations, possible explanations, limitations, and next experiments. Mark claims supported, partly supported, unsupported, or undecided with evidence. One dataset does not justify universal claims; deliver negative and unchanged results too.

## Outputs

Recalculable result tables, statistical notes, figure-source inventory, claim-evidence table, and failure/limitation records. Keep machine-readable data and plotting steps.

## Acceptance

Every important number traces to a run and can be recalculated. Figures and prose agree; uncertainty is clear. Do not expand scope or turn correlation into causation. Explain insufficient repeats and missing evaluation.

## Gaps and stopping conditions

Mark missing sources, unit conflicts, and mixed splits unverified. With insufficient statistical conditions, report descriptive results. Extra experiments remain budgeted rather than continuing until a positive result appears.

## Continue

With sufficient evidence, proceed to writing. For partial support narrow claims or plan budgeted experiments. Unsupported claims can return to topic/design under project direction-change rules.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [aris/analyze-results](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/analyze-results/SKILL.md)
- [aris/result-to-claim](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/result-to-claim/SKILL.md)
- [aris/figure-spec](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/figure-spec/SKILL.md)
- [sci/scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-critical-thinking/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [experiment-plan](<../业务/paper/aris/experiment-plan/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
- [research-review](<../业务/paper/aris/research-review/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
