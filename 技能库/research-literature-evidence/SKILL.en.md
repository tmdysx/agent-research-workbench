---
name: research-literature-evidence
description: "Build a search record, literature comparisons, and claim-evidence table for reviews, gaps, and arguments; distinguish a source existing from it actually supporting a claim."
license: MIT
metadata:
  display_name: "Literature and Evidence"
  version: "1.0.0"
  language: en
---

# Literature and Evidence

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

The research question, discipline, search cutoff date, claims needing support, and authorized literature. Read the literature-module skill first. External materials enter through the project's external intake; for unapproved materials retain only a search list.

## Workflow

1. Choose official databases or search entrypoints suited to the question. Record queries, dates, filters, and coverage limits. Browser access or public APIs are options; paid search is not compulsory.
2. Read [references/证据核验.md](references/证据核验.md). Check title, authors, year, identifier, and version, and obtain full text lawfully. Abstracts, search snippets, and finding a DOI do not count as reading the source.
3. Use [assets/文献证据表.md](assets/文献证据表.md) to extract population/object, method, data, evaluation, limitations, and exact page/section/figure/table. Record support or contradiction. Link versions of one study without counting them as separate evidence.
4. Synthesize by questions and disagreements instead of accumulating article summaries. Keep counterevidence, negative results, corrections/retractions, and uncovered scope.
5. Only a requested systematic review requires prespecified inclusion/exclusion, screening reasons, and record/report/study counts. Label ordinary background searching narrative; do not claim exhaustive coverage.
6. Record discovered, located, agent-checked, and author-verified states with checker and date. Separate metadata checks from claim support; agent checks do not replace author responsibility.

## Outputs

Search log, thematic comparison, claim-source-location table, missing-full-text/unverified list, and a citation library when needed.

## Acceptance

The person can open a source at the cited location and see the claim's conditions, support, and counterevidence. Verify author, year, and version; preserve numeric units and context. The search boundary is reviewable.

## Gaps and stopping conditions

Mark restricted access, unclear rights, identity conflicts, and unlocatable passages unresolved. Do not invent DOIs, quotations, or findings, or bulk copy unauthorized full text. At the search limit, deliver existing evidence and limitations.

## Continue

With the gap defined, proceed to experiment design. At the writing stage, hand off directly to Manuscript and Citations. Missing key evidence requires more checking or a narrower claim.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [sci/literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/literature-review/SKILL.md)
- [sci/citation-management](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/citation-management/SKILL.md)
- [sci/scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-critical-thinking/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [idea-discovery](<../业务/paper/aris/idea-discovery/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
