# SEARCH OBJECTIVE REPORT

Objectives are broader than query families. They let multiple domain-specific queries teach the same reusable research question while preserving each literal query and QF identity.

- Defined objectives: **12**
- Objectives touched by measured runs: **9**
- Unclassified measured runs: **1**

| Objective | Runs | Inspected | Retained | MASTER | Capability-touch runs | Experiment runs | Outcome eq. |
|---|---:|---:|---:|---:|---:|---:|---:|
| OBJ:independent-evaluation — Independent evaluation | 13 | 15 | 7 | 0 | 11 | 12 | 3.00 |
| OBJ:current-rule-authority — Current rule authority | 6 | 10 | 5 | 0 | 6 | 3 | 0.00 |
| OBJ:completeness-proof — Completeness proof | 5 | 11 | 5 | 0 | 5 | 5 | 0.00 |
| OBJ:runtime-side-effect — Runtime side-effect trace | 4 | 0 | 0 | 0 | 4 | 4 | 1.00 |
| OBJ:authority-lineage — Authority lineage | 3 | 7 | 7 | 0 | 3 | 3 | 0.00 |
| OBJ:protocol-regression — Protocol regression | 3 | 6 | 5 | 0 | 3 | 3 | 1.00 |
| OBJ:ambiguity-reconciliation — Ambiguity reconciliation | 3 | 5 | 4 | 0 | 3 | 3 | 0.00 |
| OBJ:identity-lineage — Identity and correlation lineage | 2 | 5 | 3 | 0 | 2 | 2 | 0.00 |
| OBJ:exactly-once-settlement — Exactly-once settlement | 2 | 3 | 3 | 0 | 2 | 2 | 1.00 |
| OBJ:unclassified — Unclassified | 1 | 2 | 2 | 0 | 1 | 1 | 0.00 |

## Interpretation

- Objective-level aggregation is descriptive; it does not replace matched strategy experiments.
- A query family should map to one primary objective only when the hypothesis is clear. Ambiguous families stay unclassified rather than being force-fit.
- Future V4 prospective runs persist `search_objective_id` directly; legacy runs are mapped through `query_objective_map.json`.
