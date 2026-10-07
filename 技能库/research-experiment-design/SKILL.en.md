---
name: research-experiment-design
description: "Turn claims into an experiment plan with data rights, leakage-free splits, fair baselines, metrics, and budget; primarily for computational and machine-learning research."
license: MIT
metadata:
  display_name: "Data and Experiment Design"
  version: "1.0.0"
  language: en
---

# Data and Experiment Design

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

Question, claims, evidence table, data documentation, baselines, and resource limits. Read the applicable experimental protocol. This skill does not replace clinical, animal, or wet-lab protocols and required approvals.

## Workflow

1. In [assets/实验方案.md](assets/实验方案.md), map each main claim to its minimal evidence and rival explanations. Plan the main comparison, essential ablations, robustness, and failure analysis; do not create experiments merely to fill tables.
2. Check data source, rights, task suitability, version, and independent unit. Read [references/机器学习评价边界.md](references/机器学习评价边界.md). Assign training/validation/test roles first; split by group, subject, or time and examine duplicates, future information, and derived-label leakage.
3. Fit preprocessing, feature selection, normalization, resampling, and tuning on training data only. Repeated selection is still selection. Use training-side validation or nested validation when needed; do not select using test data.
4. Specify metric direction, units, statistical unit, and uncertainty method. Plan independent repeats only when randomness matters and budget permits; record count and seeds. Folds or training batches are not independent samples.
5. Compare baselines and the new method under comparable splits, metric implementations, and resources. Record tuning ranges and selection budgets separately. Keep paper-reported and locally reproduced numbers distinct.
6. Schedule minimal checks, baseline, main method, essential ablations, and supplements. Give each task a duration, memory, run count, outcome interpretation, and stopping condition. Without an agreed budget, limit work to planning and reversible small checks.
7. Freeze plan and evaluation versions. Append deviations; label post-result exploration instead of rewriting the original plan.

## Outputs

Experiment plan, data/split inventory, claim-experiment matrix, baseline/ablation matrix, budget, and run order. Do not place actual private data in templates.

## Acceptance

The person sees which question each experiment answers, why comparisons are fair, why test data did not select the method, and what failure means. Rights, scope, budget, evaluation, and plan version are traceable.

## Gaps and stopping conditions

Pause affected formal runs for leakage, unclear units, missing rights, or unmet safety conditions. State limitations from weak baselines or insufficient repeats. Direction changes beyond authorization need a recorded decision.

## Continue

Send the plan to Reproduction and Runs for minimal checks and baselines, then run in order. A large experiment cannot substitute for design.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [aris/experiment-plan](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/experiment-plan/SKILL.md)
- [aris/ablation-planner](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/ablation-planner/SKILL.md)
- [sci/scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-critical-thinking/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [experiment-plan](<../业务/paper/aris/experiment-plan/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
