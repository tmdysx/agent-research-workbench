---
name: mh-paper-aris-experiment-plan
description: "Turn research claims into minimal required experiment blocks, run order, and budget; use for experiment matrices, ablations, and fair comparisons."
license: MIT
---

# Experiment Matrix and Budget

This is a local adaptation of pinned upstream methods. Follow the current goal, approved plan, and file scope; put actual materials/results in the author-selected workspace, not built-in folders.

## Inputs

Stable method proposal, primary claims, nearest baselines, data rights, evaluation protocol, and actual resources.

## Workflow

1. Freeze one main claim and necessary supporting claims with the problem, failure conditions, and required evidence.
2. Map claims to core comparisons, ablations, mechanism checks, robustness, and cost blocks, separating required/optional work from unrelated benchmarks.
3. Specify data/independent units, splits, seeds, metrics, baselines, statistics, output format, and interpretation per block; do not select methods on test data.
4. Order small checks before core evidence with milestones, estimated budget, and stopping conditions; diagnose failures instead of extending computation indefinitely.
5. Produce experiment plan/tracker for existing plan review, separating run, failed, resource-waiting, and optional states.

## Outputs

EXPERIMENT_PLAN.md and EXPERIMENT_TRACKER.md with claims, inputs, commands, cost, evidence, and acceptance per block.

## Acceptance

- Each core block answers its claim with explicit fair budgets/leakage prevention.
- Optional large experiments do not block minimal results; unapproved budget is not spent.

## Continue When

Move to reproduction once the plan is authorized and minimal inputs ready; this skill plans without launching jobs.

## Tools and Status

Reading/textual methods require no runtime installation or model API. Actual business actions are carried out by the current agent and authorized tools.

Bundled guidance does not prove installed dependencies or validated runtime. Reading/copying a skill does not enable automation, create employees, rent resources, or publish outputs.

## Sources and Changes

[SOURCE.md](<SOURCE.md>) · [LICENSE.txt](<LICENSE.txt>) · [English/mixed original](<../../../sources/aris/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/experiment-plan/SKILL.md>)

2026-10-05: retained upstream originals/licenses and added equivalent Chinese/English entrypoints, adapting default paths, authorization, and runtime guidance to this platform. Supporting material keeps its original language; raw entrypoints are not default executable workflows.

## Claims and minimal experiment blocks

1. Map each claim to an alternative explanation, minimum experiment, independent unit, data split, fair baseline and budget.
2. Specify support/refutation/inconclusive criteria, metric denominators, statistics, command/output and stop conditions beforehand.
3. Run sanity before formal execution; a negative result can complete construction without supporting the claim.

Detailed reference: [references/claim-blocks.en.md](references/claim-blocks.en.md); working template: [assets/experiment-matrix.en.md](assets/experiment-matrix.en.md). These resources stay inside the copied package.
