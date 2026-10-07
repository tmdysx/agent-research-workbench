---
name: research-topic
description: "Turn a research interest or observation into a bounded, falsifiable, feasible question; use for topic selection without presenting a candidate hypothesis as a finding."
license: MIT
metadata:
  display_name: "Topic and Hypothesis"
  version: "1.0.0"
  language: en
---

# Topic and Hypothesis

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

A research interest, actual observation, or public literature; time, data, equipment, and disciplinary background. Record observation sources, units, and uncertainty. Distinguish published reports, personal observations, and conjecture.

## Workflow

1. Use [assets/选题卡.md](assets/选题卡.md) to specify the object, conditions, comparison, and outcome. A machine-learning question may compare performance and cost under a fixed budget; it must not promise improvement beforehand.
2. Read [references/问题与反证.md](references/问题与反证.md). Separate questions, candidate hypotheses, rival explanations, predictions, measurements, and evidence. Mark plans without actual observations as exploratory.
3. Search the nearest public work and retain queries, dates, read sources, and similarities. Report that this search found no match rather than claiming nobody has done it or novelty is proven. Send full-text support checks to Literature and Evidence.
4. Design the smallest check that distinguishes explanations, stating what would support, contradict, or leave them undecided. Theory needs counterexamples and proof obligations; reviews need boundaries and comparable evidence.
5. Explain tradeoffs in value, data availability, reproduction basis, resources, and difficulty. Continue within existing authorization; goal changes or direction expansion follow project change rules.

## Outputs

A topic card, nearest-work comparison, and minimal validation design. Candidate ideas remain candidates and do not overwrite the agreed goal.

## Acceptance

The person can explain the question, what previous work covers, what could contradict the explanation, and whether resources suffice. Include a falsifiable prediction and sourced or explicitly unresolved gaps. Do not retrospectively call a hypothesis prespecified after inspecting test performance.

## Gaps and stopping conditions

If lawful data, budget, or disciplinary judgment is missing, work on public literature and design. Summarize a pilot at the budget/retry limit. Preserve negative outcomes; explain a narrowed question and do not invent a mechanism.

## Continue

Once the question is clear, proceed to Literature and Evidence. With a sufficient evidence table, proceed to Data and Experiment Design.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [sci/hypothesis-generation](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/hypothesis-generation/SKILL.md)
- [aris/idea-discovery](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/idea-discovery/SKILL.md)
- [aris/novelty-check](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/novelty-check/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [idea-discovery](<../业务/paper/aris/idea-discovery/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
