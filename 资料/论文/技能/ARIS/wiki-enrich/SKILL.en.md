---
name: mh-paper-aris-module-wiki-enrich
description: "Fill missing interpretation on existing paper pages while preserving identity, original abstracts and graph relationships."
license: MIT
---

# Faithful enrichment of existing paper pages

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

Authorized existing paper pages, explicit TODO sections, original text/abstracts and project context; replacing existing interpretation must be in the current task scope.

## Method

1. Check node_id, title and original source per page and select only TODO sections. Skip existing prose by default and do not create a wiki when none exists.
2. Use available overview, full text/brief and deeper sources, falling back to arXiv or the page’s original abstract last. Record the actual source and limits of secondary or abstract-only reading.
3. Fill the one-line mechanism, problem/gap, method, results, assumptions, limitations, reusable ingredients and open questions separately. Preserve source numbers and units; use “not stated in source” for absent information.
4. Claims may reference only existing graph relations; project relevance must use the supplied brief/gaps. Mark missing context rather than inventing claim nodes or project direction.
5. Replace only uniquely matched heading-plus-TODO blocks and preserve YAML, Connections and Abstract (original). Log each page’s actual source and filled/skipped sections.

## Outputs and acceptance

Per-page enrichment records and reviewable differences, source/reading depth and remaining gaps. Verify unchanged metadata, original abstracts and graph-generated relations, with no default replacement of existing interpretation.

## Dependencies and boundaries

AlphaXiv/arXiv/DeepXiv and research_wiki.py are upstream retrieval/bookkeeping dependencies whose readiness is not guaranteed. No cron is created; enrich authorized pages from supplied text in the current task.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [output-language.md](references/support/skills/shared-references/output-language.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)
- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/wiki-enrich/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
