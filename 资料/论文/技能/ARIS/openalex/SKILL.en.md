---
name: mh-paper-aris-module-openalex
description: "Query papers, institutions and citation relationships using OpenAlex metadata while preserving provenance and query definitions."
license: MIT
---

# Open scholarly metadata and citation-relationship queries

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

A topic, DOI/OpenAlex ID or institution/author scope, year/type filters, result limit and relationship question.

## Method

1. Choose works, author/institution lookup or citation relationships and record reproducible keywords and filters. Disambiguate names before using author or institution identities.
2. If online access is available, retrieve structured metadata and retain title, DOI, year, authors, institutions, publication source, open-access status and update time.
3. Deduplicate with DOI or explicit identifiers and retain links between versions. Do not complete missing funding, institution or venue fields from model memory.
4. Organize citations, references and topic/institution distributions for the question, stating collection time and database coverage. Citation counts are database metrics, not proof of quality or claim support.
5. Return to original papers for scientific evidence and deliver a screening-oriented metadata table with coverage limitations.

## Outputs and acceptance

Metadata/relationship tables with query definitions and collection time, deduplication rules and missing fields. Verification requires traceable identities, distinct versions and separation of database metrics from textual evidence.

## Dependencies and boundaries

Upstream depends on the OpenAlex API, requests and openalex_fetch.py. An API key is optional configuration rather than a model API. This package does not guarantee current service policy or environment readiness.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [integration-contract.md](references/support/skills/shared-references/integration-contract.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/openalex/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
