---
name: mh-paper-aris-module-research-lit
description: "Retrieve and verify candidate papers within a defined scope and synthesize agreement, disagreement and gaps by method and evidence."
license: MIT
---

# Multi-source literature retrieval, verification and synthesis

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

The research question, search scope and screening criteria, supplied material, explicitly selected external sources and whether original-paper download is needed.

## Method

1. Start with supplied local material and authorized knowledge bases and record each source’s scope. Select external databases explicitly: upstream all excludes S2/DeepXiv/Exa/Gemini/OpenAlex opt-in sources and does not authorize every service.
2. Use reproducible keywords, time scope, queries and screening reasons. Retain missing-source/network failures and coverage gaps; top-ranked papers are not an exhaustive systematic-review evidence set.
3. Verify every candidate’s title, authors, ID/DOI and version, retaining links when merging preprints with publication records. Keep unverified papers visible but separate from citable evidence.
4. Extract problem, method, results, assumptions, limitations and reusable mechanisms. Locate scientific claims and numbers in original text; model summaries are not final evidence.
5. Group by research question and distinguish consensus, contradictions, incomparable settings and real gaps. Compare methods and evaluation conditions rather than accumulating a paper list.
6. Deliver a sourced synthesis and next-reading list. Perform downloads or existing knowledge-base writes only within authorization and do not claim unavailable routes succeeded.

## Outputs and acceptance

Search/screening records, verified and unverified paper tables, a method/evidence matrix and synthesis. Key conclusions require sources; retain coverage limits and abstract-only items explicitly.

## Dependencies and boundaries

Use MCP/API/helpers only according to actual availability and current authorization. The method package does not scan private paper repositories, bulk-download, write Obsidian/Zotero, call extra models or start sub-pipelines automatically.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [citation-discipline.md](references/support/skills/shared-references/citation-discipline.md)
- [fan-out-pattern.md](references/support/skills/shared-references/fan-out-pattern.md)
- [output-composition.md](references/support/skills/shared-references/output-composition.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/research-lit/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
