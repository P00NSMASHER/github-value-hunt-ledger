# MATCHED STRATEGY MEASUREMENT CAMPAIGN

This campaign reduces strategy-measurement debt using frozen benchmark tasks. It is deliberately separate from commercial opportunity search.

- Active strategies needing more evidence: **12**
- Suggested matched comparison groups: **5**
- Protocol: `benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md`
- **Do not read `BENCHMARK_GOLD.md` before a result is frozen.**

## Highest-leverage matched groups

| Comparison group | Task | Strategies |
|---|---|---|
| CMP:authority-currentness:task-09 | 09 — Find an official first-party machine-readable U.S. federal acquisition-rule source that preserves clause/provision structure, fill-ins and revision/change provenance. | STRAT:authority-origin-invariant-set-consistency, STRAT:first-party-production-source-triangulation, STRAT:rule-period-authority-version-audit |
| CMP:verification-boundaries:task-12 | 12 — Find a real restore-verification platform that executes recoveries across heterogeneous data systems and emits independently checkable evidence rather than trusting backup-success status. | STRAT:acceptance-path-transition-inspection, STRAT:evaluation-target-independence, STRAT:fail-open-boundary-archaeology |
| CMP:operational-conjunctions:task-16 | 16 — Find a deep airline-disruption/recovery engine covering constrained optimization, passenger/crew recovery, legality, uncertainty, simulation and deterministic replay. | STRAT:capability-conjunction-search-claim-tracing, STRAT:decision-claim-runtime-side-effect-trace, STRAT:evaluation-target-independence |
| CMP:agent-lineage-governance:task-28 | 28 — Find a persistent self-improving agent harness that can turn repeated failures/tactics into durable memories, skills and subagents with rollback or refinement history. | STRAT:acceptance-path-transition-inspection, STRAT:cross-source-emergence-triangulation, STRAT:paper-research-artifact-production-descendant |
| CMP:ingestion-protocol:task-37 | 37 — Find a permit/property ingestion plane with connectors across municipal data systems, immutable permit versions/diffs and explicit semantic field-mapping QA. | STRAT:first-party-production-source-triangulation, STRAT:ingestion-invariant-triad-intersection, STRAT:protocol-regression-archaeology-for-pre-fat-systems |

## Per-strategy next measurement

| Strategy | More runs needed | More inspections needed | Evaluation set | Suggested task | Comparison group |
|---|---:|---:|---|---|---|
| STRAT:acceptance-path-transition-inspection | 0 | 10 | EVAL:verification-boundaries | 12 | CMP:verification-boundaries:task-12 |
| STRAT:authority-origin-invariant-set-consistency | 5 | 20 | EVAL:authority-currentness | 09 | CMP:authority-currentness:task-09 |
| STRAT:capability-conjunction-search-claim-tracing | 3 | 14 | EVAL:operational-conjunctions | 16 | CMP:operational-conjunctions:task-16 |
| STRAT:cross-source-emergence-triangulation | 5 | 20 | EVAL:agent-lineage-governance | 28 | CMP:agent-lineage-governance:task-28 |
| STRAT:decision-claim-runtime-side-effect-trace | 5 | 20 | EVAL:operational-conjunctions | 16 | CMP:operational-conjunctions:task-16 |
| STRAT:evaluation-target-independence | 3 | 16 | EVAL:verification-boundaries | 12 | CMP:verification-boundaries:task-12 |
| STRAT:fail-open-boundary-archaeology | 4 | 16 | EVAL:verification-boundaries | 12 | CMP:verification-boundaries:task-12 |
| STRAT:first-party-production-source-triangulation | 3 | 13 | EVAL:authority-currentness | 09 | CMP:authority-currentness:task-09 |
| STRAT:ingestion-invariant-triad-intersection | 5 | 20 | EVAL:ingestion-protocol | 37 | CMP:ingestion-protocol:task-37 |
| STRAT:paper-research-artifact-production-descendant | 5 | 20 | EVAL:agent-lineage-governance | 28 | CMP:agent-lineage-governance:task-28 |
| STRAT:protocol-regression-archaeology-for-pre-fat-systems | 5 | 20 | EVAL:ingestion-protocol | 37 | CMP:ingestion-protocol:task-37 |
| STRAT:rule-period-authority-version-audit | 5 | 20 | EVAL:authority-currentness | 09 | CMP:authority-currentness:task-09 |

## Why this is stronger than ordinary telemetry

- The same frozen task is assigned to multiple strategies, reducing domain/task-difficulty confounding.
- Conditions should be run independently and frozen before sibling results are visible.
- No-find and correct reject outcomes count; only returning a candidate is not success.
- These comparisons estimate search-method performance. Real customer outcomes still decide long-run commercial allocation.
