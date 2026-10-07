---
name: research-route
description: "Identify the current research stage and plan the route, budget, and handoff from topic to submission and revision; use when starting a project or taking it over."
license: MIT
metadata:
  display_name: "Research Route"
  version: "1.0.0"
  language: en
---

# Research Route

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

The person's original request, approved goals and plans, latest handoff, existing artifacts within the authorized scope, deadline, and resources. Mark unknowns as unresolved; do not scan a private paper repository to fill them in.

## Workflow

1. Read this project's AGENTS.md, handoff skill, and applicable module rules. Preserve existing requirement sources and identifiers. Read [references/路线与阶段.md](references/路线与阶段.md); determine the stage from actual artifacts, and distinguish a finished file from a supported scientific conclusion.
2. Use [assets/路线卡.md](assets/路线卡.md) to record the stage, dependencies, artifact paths, acceptance checks, and gaps. Reproduction, methods research, reviews, and theory follow different branches; explain substitute artifacts for any skipped stage.
3. Choose the first currently feasible task. Record total time, run count, resources per run, cost ceiling, retry limit, and stopping conditions. Without a budget, organize files, design, and public literature before starting a long experiment.
4. Load only the relevant stage skill, perform authorized work, verify actual artifacts, and record delivery and handoff in the project. The skill does not launch other agents or platform model APIs. A blocked dependency pauses only work that needs it.
5. End the work item when its budget or failure limit is reached, or the user stops it. Preserve evidence and recommendations. A negative result does not permit changing goals, deleting records, or bypassing acceptance.

## Outputs

A research route card, current-stage work plan, existing-artifact/gap inventory, and handoff. Existing literature, experiment, paper, presentation, and media modules carry business materials. Machine records stay separate from the person's notes.

## Acceptance

Without reading code, the person can identify the current stage, its evidence, the next task, and its check. Every verified status opens a real artifact; unrun work, unresolved claims, and missing inputs are not completed. A replacement agent can resume the same route.

## Gaps and stopping conditions

Record specific unresolved data rights, scientific judgment, resources, and submission authorization. A route card does not authorize payment, public upload, or formal submission. Keep construction acceptance, source verification, claim support, and author confirmation as distinct states.

## Continue

If the research question is unclear, use Topic and Hypothesis first. Otherwise, load the stage whose inputs are ready. Do not load the whole skill library at once.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [aris/research-pipeline](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/research-pipeline/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [research-pipeline](<../业务/paper/aris/research-pipeline/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
