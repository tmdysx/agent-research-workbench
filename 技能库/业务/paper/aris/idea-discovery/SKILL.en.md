---
name: mh-paper-aris-idea-discovery
description: "Select research ideas through literature, candidates, feasibility pilots, novelty checks, and critical assessment without automatically renting GPUs or creating reviewer agents."
license: MIT
---

# Research Idea Selection and Validation

This is a local adaptation of pinned upstream methods. Follow the current goal, approved plan, and file scope; put actual materials/results in the author-selected workspace, not built-in folders.

## Inputs

Broad direction, reference papers, author constraints, permitted resources, and evidence/time budgets.

## Workflow

1. Extract questions, known methods, limitations, and the desired effect from the direction/reference papers; record searched coverage.
2. Generate a bounded candidate set and filter by problem significance, differences from nearest methods, falsifiable predictions, and cost, retaining rejection reasons.
3. Search nearest prior work more deeply for leading candidates and check for renaming rather than a real distinction; report search bounds rather than absolute novelty.
4. Run minimal feasibility checks only within actual authorization/budget, retaining commands, duration, outputs, and failures; upstream default hours are not user-approved resources.
5. Deliver ranking, counterevidence, and criticism; refine the author’s chosen candidate into a question card/experiment matrix and mark absent independent review.

## Outputs

idea-candidates.md, novelty-check.md, pilot-record.md, and proposal.md with one canonical candidate record.

## Acceptance

- Candidate judgments have evidence/hypothesis labels and visible rejections/unverified points.
- Pilots are actually run or explicitly not run; unauthorized resources remain unused.

## Continue When

Proceed to experiment planning after the author selects a candidate and resources are explicit; retain undecided direction for judgment.

## Tools and Status

Reading/textual methods require no runtime installation or model API. Actual business actions are carried out by the current agent and authorized tools.

Bundled guidance does not prove installed dependencies or validated runtime. Reading/copying a skill does not enable automation, create employees, rent resources, or publish outputs.

## Sources and Changes

[SOURCE.md](<SOURCE.md>) · [LICENSE.txt](<LICENSE.txt>) · [English/mixed original](<../../../sources/aris/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/idea-discovery/SKILL.md>)

2026-10-05: retained upstream originals/licenses and added equivalent Chinese/English entrypoints, adapting default paths, authorization, and runtime guidance to this platform. Supporting material keeps its original language; raw entrypoints are not default executable workflows.

## Idea candidates and validation

1. For each candidate list nearest work, shared features and one testable difference; related work/no search hit does not prove novelty.
2. Choose a minimal feasibility test and record actual inputs, budget, success/failure criteria and observations; expectation is not a result.
3. Record critical review separately from author selection and retain rejected candidates/reasons; do not rent parallel resources by default.

Detailed reference: [references/novelty-candidates.en.md](references/novelty-candidates.en.md); working template: [assets/candidate-card.en.md](assets/candidate-card.en.md). These resources stay inside the copied package.
