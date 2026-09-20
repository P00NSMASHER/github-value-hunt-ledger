# DATA QUALITY REPORT

This report measures whether the learning loop has enough structured evidence to support empirical search-policy updates.

- Search runs: **17**
- Structured outcomes: **1**
- Mean legacy/core run completeness: **87.8%**
- Runs below 70% completeness: **2**
- Structural issues detected: **1**
- Capabilities without an explicit next falsifiable test: **0**
- V4 runs: **5** (core V4 instrumentation complete: **3**)
- Runs mapped to a controlled search objective (explicit or reviewed legacy map): **16/17**
- Candidate dispositions normalized to controlled reasons (direct or reviewed alias): **23**

## Missing recommended legacy/core fields

| Field | Runs missing |
|---|---:|
| queries | 8 |
| candidate_dispositions | 6 |
| search_surfaces | 5 |
| candidate_count | 2 |
| deep_inspected | 2 |
| retained_count | 2 |
| master_promoted_count | 2 |

## Structural issues

- RUN:20260920T202725Z:hunter11:recovery-identity-lifecycle — **unregistered_strategy_variant**: STRAT:identity-lifecycle-contradiction-archaeology

## Learning bottlenecks

- Strategy evidence remains below the 5-run/20-inspection comparison threshold; use MEASUREMENT_CAMPAIGN.md rather than over-reading observational percentages.
- Query-family wording remains sparse; objective aggregation is the stable cross-domain layer.
- Exact surface labels are normalized into families, but matched comparisons are still required for causal surface claims.
- Revision debt and MASTER catalog provenance debt are tracked separately in REVISION_DEBT_REPORT.md.
- Core instrumentation is strong enough for cautious, exploration-preserving allocation.
