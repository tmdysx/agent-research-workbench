---
name: research-reproduce-run
description: "Reproduce baselines and run computational experiments within authorized resources, keeping commands, versions, raw results, and failures; do not start platform models or rent resources."
license: MIT
metadata:
  display_name: "Reproduction and Runs"
  version: "1.0.0"
  language: en
---

# Reproduction and Runs

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

Agreed plan, data inventory, code version, authorized resources, budget, and run order. Instructions are not authorization to run on a remote server. Read only authorized directories.

## Workflow

1. Use [assets/运行记录.md](assets/运行记录.md) to record actual commands, working directory, code version/differences, configuration, dependencies, seeds, input fingerprints, and outputs. Give each run its own directory; do not overwrite raw results.
2. Check small-sample loading, shapes, labels, metric direction, train/validation separation, and saved outputs before running the baseline. Explain differences from the paper's conditions; do not change evaluation to chase its score.
3. Read [references/运行与故障.md](references/运行与故障.md). Run authorized experiments in order, keeping stdout/stderr, exit code, start/end times, and actual resources. Mark check runs as checks; exclude them from formal comparisons.
4. Monitor this task's process through an already authorized method. The skill creates no scheduler, rented GPU, purchased service, or new agent. Remote/school environments follow their specific authorization and skill.
5. Preserve crashes, timeouts, out-of-memory failures, and cancellations. Record why a metric is missing instead of substituting zero. Fix clear code errors within a retry limit, recording changes; hand off at the limit.
6. Check actual outputs, logs, consistent evaluation, and leakage. Preserve transformation steps from raw outputs to results. Validation optimization and final testing remain separate.

## Outputs

Separate run directories, environment notes, logs/raw results, rerun commands, baseline differences, and failure records. Keep raw and derived results separate.

## Acceptance

The person can open actual logs and find status, configuration, and results; another agent can rerun within the input budget. Report only actual counts, times, and resources. Unstarted, running, failed, or cancelled work is not completed.

## Gaps and stopping conditions

Identify missing inputs, resources, and dependencies specifically. Save state when over budget, evaluation is abnormal, leakage appears, or the user stops work. Terminate only processes confidently belonging to this task. Do not fork or modify the upstream project; keep experimental implementation in an independent authorized directory.

## Continue

Send real outputs to Results and Figures. Investigate evaluation/log anomalies first; additional runs must remain within the plan and budget.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [aris/run-experiment](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/run-experiment/SKILL.md)
- [aris/training-check](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/training-check/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [run-experiment](<../业务/paper/aris/run-experiment/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
