---
name: research-revision
description: "Map reviews of this manuscript to edits, additional experiments, revised-text locations, and evidence-based replies; preserve original comments and do not send automatically."
license: MIT
metadata:
  display_name: "Revision and Response"
  version: "1.0.0"
  language: en
---

# Revision and Response

Any agent able to read Markdown can follow this skill; the platform does not need another model API. Copy templates into the authorized business-output directory before filling them in, and preserve original evidence. This package primarily addresses computational and machine-learning research. Adjust evidence types for reviews or theory; it does not authorize clinical, animal, or wet-lab experiments.

## Inputs

Authorized reviews of this manuscript, the submitted version, editor instructions/deadline, existing evidence, and budget. Do not read or save third-party confidential reviewing files without authorization.

## Workflow

1. Preserve original comments completely and read-only. Break them down by reviewer/original numbering, including editor comments. Map questions, actions, evidence, and revised locations in [assets/返修矩阵.md](assets/返修矩阵.md).
2. Classify wording, method/evidence, statistical comparison, figure/citation, and out-of-scope issues. Inspect actual records; distinguish already done but undocumented, new work needed, impossible work, and evidence-based disagreement.
3. Order work and budget it. Send extra experiments to design and label them as proposed after review, never rewrite the original plan. Report results only after running; proposed work is not completed work.
4. Preserve draft versions/differences and check text, figures, and attachments together. New claims need evidence. Do not remove negative results or invent compliance.
5. Respond with the issue, action or reasoned disagreement, evidence, and new page/line/section. Verify locations after final rendering; provisional draft line numbers do not suffice.
6. Prepare marked manuscript, clean manuscript, response, and attachments under current venue rules. Address every original comment; mark unresolved decisions for the author, never impersonate editorial decisions or acceptance.
7. Third-party confidential reviewing differs from revising one's own paper and needs editor/author authorization and policy permission. A hosted agent reading a local manuscript may be external processing. This package covers one's own revision or a public exercise.

## Outputs

Read-only original comments, revision matrix, versioned manuscripts, experiment records, response draft, local revision package, and gaps.

## Acceptance

Each comment maps to a reply, revised location, and actual evidence. New experiments actually ran; disagreement has reasons. Clean/marked texts, response, and attachments share versions, with unmet items visible.

## Gaps and stopping conditions

Record confidentiality permission, critical-evidence, budget, and dispute gaps specifically. Hand off at deadline/budget; do not automatically request an extension, send a response, or upload. Decomposing comments does not authorize changing/deleting their source file.

## Continue

Hand off for author confirmation and submission by their authorized operator, without automatic email/submission. Return substantive issues to the corresponding stage and recheck the entire matrix.

## Sources and license

This existing skill folder's adaptations, templates, and references retain their independent MIT license; see [LICENSE.txt](LICENSE.txt). This English translation preserves that scope and does not relicense the rest of the project or upstream materials. See [references/来源与改编.md](references/来源与改编.md) for the original adaptation record. Supporting references and templates currently retain their original Chinese filenames and language; this English entrypoint is complete, not an English summary linking to a Chinese workflow. Upstream pinned originals remain in the project's 技能库/业务/paper/sources/legacy-research as source snapshots, not executable entrypoints. Do not automatically run their agents, schedulers, paid services, or commands.

- [aris/rebuttal](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/rebuttal/SKILL.md)
- [aris/resubmit-pipeline](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/2132036060e03e8d0df69a4b21e5971819c0c2d6/skills/resubmit-pipeline/SKILL.md)
- [sci/peer-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/peer-review/SKILL.md)


The legacy source snapshots retain their original pins and bytes. In a clean business template, consult `技能库/业务/paper/sources/legacy-research/path-map.json` for the old-to-bundled path mapping. The original Chinese skill and source lock remain unchanged; snapshots are not executable installations.

## Optional ARIS method detail

Choose existing detail for the current problem. These are optional links to project sources; report a missing package and never infer installation/execution from a link.

- [rebuttal](<../业务/paper/aris/rebuttal/SKILL.en.md>) · unchanged canonical ID/source pin `2132036060e03e8d0df69a4b21e5971819c0c2d6`
