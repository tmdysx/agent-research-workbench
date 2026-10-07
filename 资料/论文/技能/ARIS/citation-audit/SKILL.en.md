---
name: mh-paper-aris-module-citation-audit
description: "Citation identity and support audit; a local ARIS method adaptation; upstream runtime is not installed by this package."
license: MIT
---

# Citation identity and support audit

This is a method adaptation, not a word-for-word translation. The complete original is retained separately. Use the current authorized workspace, goal, plan, applicable rules and latest handoff.

## Inputs

Manuscript, bibliography, search permission and bibliography-freeze constraint.

## Method

1. Locate every citation occurrence in its claim context rather than auditing only the bibliography.
2. Check existence, author/title/year/DOI consistency, and support from the relevant full-text location separately.
3. Report KEEP/FIX/REPLACE/REMOVE proposals with evidence; a failed lookup means unknown, not nonexistent.
4. If the bibliography is frozen, propose prose/candidate changes without editing bib files; recheck affected citations after revision.

## Outputs and acceptance

Citation-context-source-verdict ledger and unresolved identities/full-text gaps.

Every conclusion/completion traces to actual files, sources and checks. Report missing inputs, missing independence and unperformed checks; creating an artifact does not replace platform delivery acceptance.

## Dependencies and boundary

`runtime_enabled=false`.

This package installs method text/references. Scripts, MCP, model APIs, cloud GPUs, uploads, messages and timers are not enabled. Perform actions only when currently authorized and actually available; a model label does not establish independent review and a score cannot grant permissions.

See [SOURCE.md](SOURCE.md) for actual upstream dependencies and excluded attachments. Required support text is retained under package-local `references/support/`; historic tool paths/actions remain upstream background.

## Sources

[完整上游原文 / Complete original](references/upstream.md) · [SOURCE.md](SOURCE.md) · [MIT](LICENSE.txt)

Upstream: wanshuiyin/Auto-claude-code-research-in-sleep, archive commit `0472e530251cdbd3364c33b110063c58f819edd7`. Copyright (c) 2026 wanshuiyin. Local adaptation: tmdysx (agent-assisted), 2026-10-06. Third-party MIT rights remain unchanged.
