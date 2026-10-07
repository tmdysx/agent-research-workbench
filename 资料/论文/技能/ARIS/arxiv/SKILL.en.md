---
name: mh-paper-aris-module-arxiv
description: "Retrieve arXiv metadata by query or paper ID and save original papers within the authorized scope."
license: MIT
---

# Search and retrieve arXiv papers

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

A query or exact arXiv ID, year/category constraints, result limit, and whether metadata or original-paper download is needed.

## Method

1. Distinguish ID lookup from topic search. Check an exact ID directly; use reproducible keywords and filters for a topic without treating one ranked result set as exhaustive.
2. Read Atom metadata through an available retrieval route and retain title, authors, abstract, publication/update dates, version, abs link and PDF link.
3. Screen for relevance and distinguish preprint versions from separately published versions. Record invalid IDs, empty results and network limits truthfully.
4. Only if download is requested and authorized, save selected PDFs to an explicit directory and verify their existence and readability. Do not bulk-fetch unrequested papers or private libraries.
5. Summarize the acquired text’s problem, method, evidence and limitations, distinguishing abstract-only reading from original-paper reading. Use an existing authorized project entry for knowledge-base updates.

## Outputs and acceptance

A search record and paper-identity table; the download branch also has an actual file list. Reading notes state their depth. Verify IDs, versions, sources and actual download count; a link or empty file is not a retrieved paper.

## Dependencies and boundaries

Online retrieval needs arXiv and network tools. Upstream arxiv_fetch.py/research_wiki.py are not installed in the method package. Supplied papers can be handled using the local reading steps.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/arxiv/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
