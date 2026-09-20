# DATA QUALITY REPORT

This report measures whether the learning loop has enough structured evidence to support empirical search-policy updates.

- Search runs: **15**
- Structured outcomes: **1**
- Mean legacy/core run completeness: **89.7%**
- Runs below 70% completeness: **1**
- Structural issues detected: **1**
- Capabilities without an explicit next falsifiable test: **0**
- V4 runs: **3** (core V4 instrumentation complete: **2**)
- Runs mapped to a controlled search objective (explicit or reviewed legacy map): **14/15**
- Candidate dispositions normalized to controlled reasons (direct or reviewed alias): **20**

## Missing recommended legacy/core fields

| Field | Runs missing |
|---|---:|
| queries | 7 |
| candidate_dispositions | 5 |
| search_surfaces | 4 |
| candidate_count | 1 |
| deep_inspected | 1 |
| retained_count | 1 |
| master_promoted_count | 1 |

## Structural issues

- RUN:20260920T202725Z:hunter11:recovery-identity-lifecycle — **unregistered_strategy_variant**: STRAT:identity-lifecycle-contradiction-archaeology

## Learning bottlenecks

- Strategy evidence remains below the 5-run/20-inspection comparison threshold; use MEASUREMENT_CAMPAIGN.md rather than over-reading observational percentages.
- Query-family wording remains sparse; objective aggregation is the stable cross-domain layer.
- Exact surface labels are normalized into families, but matched comparisons are still required for causal surface claims.
- Revision debt and MASTER catalog provenance debt are tracked separately in REVISION_DEBT_REPORT.md.
- Core instrumentation is strong enough for cautious, exploration-preserving allocation.
