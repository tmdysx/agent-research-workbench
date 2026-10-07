---
name: mh-paper-aris-module-research-wiki
description: "Maintain traceable knowledge nodes and typed relationships among papers, ideas, experiments and claims."
license: MIT
---

# Research knowledge nodes and evidence relationships

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

The explicit project wiki directory/operation scope, nodes and sources, research brief, confirmed states, and the requested ingest/query/update/check task.

## Method

1. Check the existing schema, canonical node IDs and relationship store first. Manage papers, ideas, experiments and claims separately; a title string is not a unique identity.
2. Verify provenance, version and identity and deduplicate at ingestion. Preserve original abstracts separately from interpretation and do not guess missing fields.
3. Record evidence-backed typed edges such as extends, motivates, tests, supports and invalidates in the graph’s canonical store; existing mechanisms generate page Connections.
4. Separate proof/review status from empirical evidence. Create real experiment nodes before support/refutation edges; a metric must not rewrite proof status or establish an unaudited claim identity.
5. When making compact query material, retain failed ideas, critical gaps and evidence chains. Remove operational errors or permission reminders that should not become scientific facts.
6. Check orphan nodes, dead links, conflicting states, untested ideas and sparse pages and propose located repairs. Perform only the authorized update rather than creating a new private library.

## Outputs and acceptance

A node/edge change list, provenance locations, query material or lint report. Verify no dangling endpoints, retained failure memory, and distinction between empirical evidence and proof status.

## Dependencies and boundaries

The upstream runtime relies on helpers including research_wiki.py. This package installs no writer and reads neither ~/.aris nor the author’s home. Prepare change drafts from authorized text and use the project’s existing entry for writes.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [capture-antipatterns.md](references/support/skills/shared-references/capture-antipatterns.md)
- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/research-wiki/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
