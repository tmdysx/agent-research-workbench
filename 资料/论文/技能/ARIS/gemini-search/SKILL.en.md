---
name: mh-paper-aris-module-gemini-search
description: "Broaden literature candidates using Gemini-style discovery, then verify paper identity and evidential support."
license: MIT
---

# AI-assisted literature discovery and verification

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

The research question, date/discipline scope, keywords and exclusions, plus supplied AI discovery results or an authorized search route.

## Method

1. Break a broad question into mechanisms, scenarios, synonymous terms and counterexamples, requesting titles, authors, years and traceable links.
2. Use an actually available Gemini CLI/MCP within the task scope, or organize supplied results. Record the prompt and actual response; a tool declaration is not invocation evidence.
3. Verify that title, ID and DOI identify the same paper and check version, venue and original text. Retain verification failures as unverified candidates.
4. Compare newly covered directions with duplicates from existing searches and organize methods, limitations and gaps by relevance rather than the model’s ranking alone.
5. Return important numbers and citation support to primary papers. Use a reliable structured source for citation counts rather than Gemini-reported counts.

## Outputs and acceptance

An AI-discovery record, verified/unverified candidate table and coverage gaps. Each paper must have a traceable source and model output must be separated from paper facts.

## Dependencies and boundaries

Upstream depends on Gemini CLI/MCP, Google services and installable packages. This package pins no model and installs no npm package, account or API key. External content remains material to verify.

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/gemini-search/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
