# ALLOCATOR LEARNING REPORT

- Portfolio policy: **PORTFOLIO:00ad73e21071**
- Mode: **baseline_insufficient_evidence**
- Attributed assignment runs: **0**
- Attribution-debt runs: **0**
- Roles with sufficient evidence: **0**

V10 changes portfolio capacity only from executed assignment telemetry. Generated plans that were never run receive no learning credit.

## Slot-role evidence

| Role | Runs | Inspected | Retained precision | New-cap run rate | MASTER/run | Experiment-touch rate | Outcome-run rate | Duplicate ratio | Signal | Evidence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| adjacency | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |
| coverage | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |
| experiment | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |
| measurement | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |
| verification | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |
| wildcard | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |

## Effective portfolio

| Role | Baseline slots | Effective slots |
|---|---:|---:|
| adjacency | 2 | 2 |
| coverage | 3 | 3 |
| experiment | 6 | 6 |
| measurement | 1 | 1 |
| verification | 1 | 1 |
| wildcard | 1 | 1 |

## Adaptation decision

- Shift: **none**
- At most one slot can move per generation.
- Measurement, verification and wildcard remain protected roles.
- Experiment, coverage and adjacency cannot move outside configured minimum/maximum slot bounds.
- Manual overrides are measured separately and never silently treated as generated allocator success.
- Allocation signal is a scheduling heuristic; realized outcomes remain the strongest downstream evidence.
