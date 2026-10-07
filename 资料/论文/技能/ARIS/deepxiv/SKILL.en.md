---
name: mh-paper-aris-module-deepxiv
description: "Answer focused literature questions through DeepXiv brief, structure and section-level reading."
license: MIT
---

# Progressive paper retrieval and section reading

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

A topic query or paper ID, the question to answer, and the requested brief, head, section or trending mode.

## Method

1. Choose the mode matching the question. Begin explanation with a brief and evidence location with the head/section map; do not default to full retrieval or all trending papers.
2. Check search-result identities and sources, select method, experiments or limitations from the section map, and record the content actually available.
3. Deepen abstract-level judgments into body passages. Locate evidence using title, ID, section and source version, preserving changes in interpretation across tiers.
4. Treat trending and web-search results as discovery clues. When necessary, verify venue, citations and other metadata against original publication pages or available structured sources.
5. Disclose unavailable routes or sections and the unread scope. If a knowledge-base update is requested, deliver identity-checked reading cards without installing the CLI automatically.

## Outputs and acceptance

A progressive reading record, read-section list and evidence cards with unread sections and source limits. Each answer must be traceable to its retrieval tier.

## Dependencies and boundaries

Actual online access depends on deepxiv-sdk/DeepXiv CLI and upstream deepxiv_fetch.py, whose availability is not guaranteed. Apply the same method to supplied section text.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)
- [wiki-helper-resolution.md](references/support/skills/shared-references/wiki-helper-resolution.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/deepxiv/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
