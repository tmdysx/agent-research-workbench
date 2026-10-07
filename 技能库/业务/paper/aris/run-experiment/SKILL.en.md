---
name: mh-paper-aris-run-experiment
description: "Execute computational experiments in an approved environment/budget with environment contracts, launch evidence, and failures; default to local resources without cloud rental or publishing."
license: MIT
---

# Experiment Execution and Failure Records

This is a local adaptation of pinned upstream methods. Follow the current goal, approved plan, and file scope; put actual materials/results in the author-selected workspace, not built-in folders.

## Inputs

Formal experiment plan, lawful inputs, code version, approved environment, commands, and stopping conditions.

## Workflow

1. Read plan/environment records and verify code/data paths, runner versions, CPU/GPU, space, and dependencies; an upstream gpu:remote field does not authorize access.
2. Run a minimal-input/short-step check for a separate output directory, writable logs, and meaningful metrics before formal commands.
3. Launch approved commands and record PID/actual run identity, start time, resources, and versions; an open terminal does not prove training success.
4. Observe actual progress, errors, and completion within budget; stop only the identified job and retain partial artifacts/failure reasons.
5. Check readable outputs and agreement between evaluation configuration/raw logs, then give rerun commands/handoff without claiming unperformed checks.

## Outputs

Environment record, separate run folder, commands/logs/raw output, and run-report.md; syncing, upload, and notifications are not default scope.

## Acceptance

- Launch, completion, and failures have actual process/log evidence.
- Originals remain intact and reruns identify equivalent versions/inputs.

## Continue When

Move to results when actual outputs support analysis; hand off failures/environment gaps without renting clouds or destroying instances.

## Tools and Status

- **实验自身运行环境**: Determined by the approved experiment; do not install PyTorch, W&B, or Modal by default.

Bundled guidance does not prove installed dependencies or validated runtime. Reading/copying a skill does not enable automation, create employees, rent resources, or publish outputs.

## Sources and Changes

[SOURCE.md](<SOURCE.md>) · [LICENSE.txt](<LICENSE.txt>) · [English/mixed original](<../../../sources/aris/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/run-experiment/SKILL.md>)

2026-10-05: retained upstream originals/licenses and added equivalent Chinese/English entrypoints, adapting default paths, authorization, and runtime guidance to this platform. Supporting material keeps its original language; raw entrypoints are not default executable workflows.

## Run evidence and ground-truth integrity

1. Proceed through preflight, sanity, baseline and formal runs; a launch command alone does not establish successful execution.
2. Record code/config/data versions, environment, exact command, PID/start/end/exit code, logs and raw outputs.
3. Check six items: truth source, metric denominator, real result file/key, evaluator actually called, sample/seed/configuration scope, and wording limited to evidence.

Detailed reference: [references/run-integrity.en.md](references/run-integrity.en.md); working template: [assets/run-record.en.md](assets/run-record.en.md). These resources stay inside the copied package.
