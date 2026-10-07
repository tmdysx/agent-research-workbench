---
name: research-manuscript-citations
description: "Organize a manuscript from actual methods, results, and located literature, checking citations and numbers; use for drafts and revisions without inventing experiments, author declarations, or approvals."
license: MIT
metadata:
  display_name: "Manuscript and Citations"
  version: "1.0.0"
  language: en
---

# Manuscript and Citations

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

Question, actual method records, result figures, claim-evidence table, existing draft, and target writing form. Record gaps; do not invent sample counts, numbers, or ethical approval from experience.

## Workflow

1. Read [references/证据到正文.md](references/证据到正文.md). Outline according to the discipline and actual design; use [assets/论文核验表.md](assets/论文核验表.md) to map each section's purpose, claims, sources, and open questions.
2. Write from evidence: methods describe actual actions; results retain negatives, no change, and uncertainty; discussion distinguishes explanations from observations; conclusions stay within data and design. Label post-hoc exploration.
3. Link claims to existing source IDs and pages/sections/figures/tables, and numbers to runs and extraction steps. Preserve the project's full source references rather than creating a new global numbering scheme.
4. Verify citation identity/version, support, and format. DOI/BibTeX does not mean support is checked. Distinguish unavailable full text and pending author checks; do not fabricate author/year, pages, DOI, or quotation.
5. Check objects, samples, units, denominators, splits, method names, and values across title, abstract, prose, tables, figures, and attachments. Write the abstract after the main text is established. Do not claim experiments that never ran.
6. Author order, contributions, conflicts, funding, ethics, data/code availability, and AI statements must come from actual records. Leave unknowns for author confirmation, never insert false boilerplate.
7. Preserve originals and differences during revision. Make the requested preview and actually render/open it. Report unverified formatting honestly; do not require a particular toolchain.

## Outputs

Outline, manuscript and preview, citation library, consistency checklist, figures/attachments, and unresolved questions. Fluent prose is not successful evidence verification.

## Acceptance

Important claims/numbers open their sources; methods match real runs. Citation identity/support and author verification are clear. No fabricated results or statements; verify the requested preview in practice.

## Gaps and stopping conditions

Do not upload restricted content to an unauthorized service. A hosted agent reading local files does not imply local-model processing. Leave unsupported judgments/statements unverified and out of conclusions. Deliver gaps at the revision scope/budget limit; do not call an incomplete draft submission-ready.

## Continue

Send a traceable manuscript to Submission Preparation. Return experimental, statistical, and literature gaps to their corresponding stage; polished prose must not hide them.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [writer/scientific-writing](https://github.com/K-Dense-AI/claude-scientific-writer/blob/529b9f73ab4b48925027145800d7b49e96ccfd3c/scientific_writer/.claude/skills/scientific-writing/SKILL.md)
- [sci/citation-management](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/citation-management/SKILL.md)
- [aris/paper-claim-audit](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/paper-claim-audit/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [paper-writing](<../业务/paper/aris/paper-writing/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
