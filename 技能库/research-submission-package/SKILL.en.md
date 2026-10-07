---
name: research-submission-package
description: "Check the target venue's current official requirements and prepare a local submission package and missing-declarations list; do not log in, upload, pay, or submit automatically."
license: MIT
metadata:
  display_name: "Submission Preparation"
  version: "1.0.0"
  language: en
---

# Submission Preparation

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

Target journal/conference, article type, latest manuscript, figures/attachments, citation checks, and actual author details. If the target is undecided, produce a general checklist rather than choosing a venue and pretending the package is complete.

## Workflow

1. Check current official author guidance and the applicable round; record URL/access date. Check length, anonymity, formats, citations, attachments, reporting guidelines, and AI policy. Experience is not the current rule.
2. Map materials in [assets/投稿清单.md](assets/投稿清单.md). Use reporting standards appropriate to the actual discipline/design instead of applying a medical template to every paper.
3. Build an independent local package and preserve source drafts. When anonymity is required, make a separate anonymous copy and check names, acknowledgments, links, properties, and attachments. Do not delete draft history.
4. Draft cover letter, contributions, conflicts, funding, ethics, data/code, and AI-use statements from actual records. Do not invent identities, reviewer suggestions, or reasons; leave unknowns for the author.
5. Actually open/render files and check figure clarity, main-text/attachment consistency, evidence, and citation status. Keep a final version/fingerprint inventory.
6. Separate a locally complete package, pending author confirmation, and missing files. This stage does not log in, pay, upload, email, formally submit, or publicly release anything. A skill name does not authorize an external action.

## Outputs

Local package, official-requirement/date comparison, cover-letter and declaration drafts, author-confirmation/gap list, and version inventory.

## Acceptance

The person opens final text and attachments and sees official requirements with actual checks. Distinguish formatting, unverified items, and author confirmation. Ready to submit is not submitted or guaranteed acceptance.

## Gaps and stopping conditions

Mark an undecided target, missing identity/evidence, or necessary materials as not ready while continuing local organization. Record specific policy conflicts for decision. No automatic submission script or active connection.

## Continue

Hand the package to the author and their explicitly authorized submission operator. Return author feedback to writing; begin revision only when reviews arrive, preserving versions.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [writer/scientific-writing](https://github.com/K-Dense-AI/claude-scientific-writer/blob/529b9f73ab4b48925027145800d7b49e96ccfd3c/scientific_writer/.claude/skills/scientific-writing/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [paper-writing](<../业务/paper/aris/paper-writing/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
- [research-review](<../业务/paper/aris/research-review/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
