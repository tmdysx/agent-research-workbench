---
name: mh-paper-aris-module-comm-lit-review
description: "Search and synthesize communications research by system layer, scenario, metrics and failure modes."
license: MIT
---

# Layered communications literature review

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

The communications problem, system layer and scenario, time/database scope, explicitly supplied literature collection, and venue restrictions.

## Method

1. Locate the problem in PHY/MAC, networking, transport or systems, and in wireless, cellular, satellite/NTN, Wi-Fi or another scenario. State the optimization target and constraints.
2. Search only the supplied local material or authorized Zotero/Obsidian collections first, preserving ownership and source labels, then fill gaps with external primary literature.
3. Search the communications database tiers and broaden from priority venues within each tier. Venue quality is a ranking signal unless the user explicitly requests a top-only hard filter.
4. For each paper, record scenario, protocol/channel assumptions, method, controls, throughput/latency/reliability metrics and limitations; separate theoretical, simulated and measured evidence.
5. Synthesize mechanism differences, incomparable settings and recurring failures into sourced gaps. Blogs and summaries are discovery clues.

## Outputs and acceptance

A communications literature matrix and tiered search record with scenarios, evidence types, comparability, disagreements and gaps. Verification must not merely rank headline metrics or present simulation as hardware measurement.

## Dependencies and boundaries

Zotero/Obsidian MCP are optional material sources; online search needs available services. With only supplied material, produce a bounded review and disclose coverage gaps; do not scan the author’s home or real paper repository.

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/comm-lit-review/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
