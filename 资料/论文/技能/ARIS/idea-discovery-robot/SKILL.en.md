---
name: mh-paper-aris-module-idea-discovery-robot
description: "Screen ideas by embodiment, sensing, task and benchmark constraints, prioritizing simulation or existing offline evidence."
license: MIT
---

# Robotics idea discovery and simulation validation planning

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

Task family, embodiment/actuation, sensors, control/policy interfaces, available simulators/benchmarks/offline data and resource constraints.

## Method

1. Write a robotics problem frame covering embodiment, task, perception–action bottleneck, timing/safety constraints, data and sim-to-real risks. State assumptions for missing fields.
2. Build a literature matrix with embodiment, sensing, task, control paradigm, benchmark and success/failure metrics; verify that similarly named settings are actually comparable.
3. Ground each candidate in an available benchmark/simulator and explicit baseline and identify the failure mode addressed. Applying a VLM or diffusion model to a robot is not automatically a contribution.
4. Design simulation-first or offline-replay pilots with collision, intervention, latency, energy or other relevant failure metrics alongside success rate.
5. Check novelty jointly across embodiment, task, benchmark, sensing and policy class. Compare simulation differences without presenting simulation performance as physical-hardware reliability.
6. Execute the current pilot only in an available authorized environment; otherwise deliver a concrete pilot plan. Mark hardware-dependent candidates as needing physical validation and retain the not-reviewed status when no independent review occurred.

## Outputs and acceptance

Robotics candidate cards, benchmark/baseline matrix, pilot protocol and sim-to-real/hardware evidence gaps. Every candidate needs an embodiment, failure metrics and testable environment; an unrun plan is not validation.

## Dependencies and boundaries

Verify actual readiness of simulators, robotics software, data, external models and GPUs. This entry does not launch robots, hardware experiments, downloads or cloud rentals; physical operations must already be authorized for the current task.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [output-language.md](references/support/skills/shared-references/output-language.md)
- [output-versioning.md](references/support/skills/shared-references/output-versioning.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/idea-discovery-robot/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
