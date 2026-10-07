---
name: mh-paper-aris-module-dse-loop
description: "Organize tunable parameters and objective constraints into baseline, candidate trials and bounded evidence-driven search."
license: MIT
---

# Bounded design-space exploration

This is an English method adaptation equivalent to the Chinese entry; neither entry is a full translation of upstream. Status: `runtime_enabled=false` means upstream runtime facilities are not enabled. Local textual methods remain usable for the currently authorized single task, while external MCP/API, GPU or robotics readiness is not implied. Read and write only within the task scope; import no automatic permissions, fixed models or endless review. Do not automatically upload, notify, schedule, rent GPUs or scan the author’s home. Record actual evidence, independent review and unverified status separately.

## Inputs

Authorized program/configuration scope, parameters and valid values, metric extraction, optimization direction, hard constraints, and trial/time/resource budget.

## Method

1. Determine parameter types, defaults and limits from authorized source/configuration. Record provenance and reasons for inferred ranges; do not silently enlarge the authorized search space.
2. Freeze metric extraction and constraint checks and validate the default baseline first. If not executed, keep it as a baseline plan rather than presenting predicted values as measurements.
3. Choose diverse initial points, such as a structured sweep or Latin hypercube. Bind each candidate to its full configuration, command, raw output and constraint status.
4. Use measured results to choose the next batch: fine grids near good low-dimensional regions, coordinate descent for more dimensions, categorical enumeration, or a Pareto frontier for multiple objectives. Avoid unjustified duplicate evaluations.
5. Deliver one candidate batch as the currently authorized task. Stop on time/trial limits, patience or success criteria; record range expansion as a proposal. The platform does not loop on the agent’s behalf.
6. Report the best feasible configuration, baseline-relative change, sensitivity and unexplored regions. Retain failures, timeouts and constraint violations; say best in the searched range rather than globally optimal.

## Outputs and acceptance

A candidate-trial table, linked baseline/configurations/raw outputs, stop reason and next-batch proposal. Verification must distinguish planned from executed, feasible from infeasible, and scalar objectives from Pareto trade-offs.

## Dependencies and boundaries

The task selects gem5, synthesis, compilers or performance programs; the method package does not install or control them. Upstream’s inner loop is algorithmic reference, not authorization to create a background runner, schedule, endless review or GPU rental.

Read the following archived support when relevant; commands therein are reference material, not installation or execution authorization:

- [external-cadence.md](references/support/skills/shared-references/external-cadence.md)

## Sources

- [Full upstream method](references/upstream.md)
- [Source and version record](SOURCE.md)
- [MIT license and attribution](LICENSE.txt)

Adapted from upstream `skills/dse-loop/SKILL.md`. The archived original remains the place to inspect full detail; this entry changes execution assumptions to the project’s current authorization boundary.
