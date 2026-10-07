---
name: mh-paper-aris-module-semantic-scholar
description: "Semantic Scholar literature search; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Semantic Scholar literature search

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Scholarly query, year/field scope and actual network access.

## Method

1. Specify query and coverage; retrieve title/author/year, venue and available identifiers.
2. Fetch details for relevant papers, distinguish arXiv/published versions and deduplicate by identity/DOI.
3. Treat citation counts/TLDR as discovery signals; substantive claims require full-text support.
4. The original fetch helper is not bundled; use a real authorized query tool and record failed lookups as unknown.

## Outputs and acceptance

Search log, identity/version checks and full-text gaps.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
