---
name: mh-paper-aris-module-alphaxiv
description: "Understand one specified paper through AlphaXiv overview, full-text access and original-source fallback."
license: MIT
---

# Tiered single-paper reading

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

One explicit arXiv ID, AlphaXiv/arXiv link or supplied paper text, plus the question and desired reading depth.

## Method

1. Normalize the paper ID and check title and authors. Handle the specified paper; topic discovery and multi-paper synthesis belong to literature-review methods.
2. If sources are available and networking is in scope, start with the overview, deepen to abs Markdown when needed, then fall back to arXiv LaTeX or the supplied PDF. Record which tier actually succeeded.
3. Extract the problem, mechanism, main evidence, limitations and answers to the reader’s question. Label overview claims as secondary summaries and locate important claims in the original.
4. Record missing sections, retrieval failures and unverifiable numbers instead of completing them from model memory. Name the next section and question for deeper reading.
5. Only when the task requests an existing knowledge-base update, pass the identity-checked paper and evidence locations to its established entry. Do not create or scan a private library.

## Outputs and acceptance

A single-paper reading card with identity, actual source tier, mechanism, evidence locations, limitations and next reading questions. Verification must distinguish original evidence, summary paraphrases and unread material.

## Dependencies and boundaries

Online tiers depend on AlphaXiv/arXiv and retrieval tools; the reading method also works on supplied local text. Upstream research_wiki.py is optional bookkeeping and is not installed by this package.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/alphaxiv/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
