# DATA QUALITY REPORT

This report measures whether the learning loop has enough structured evidence to support empirical search-policy updates.

- Search runs: **12**
- Structured outcomes: **1**
- Mean legacy/core run completeness: **91.0%**
- Runs below 70% completeness: **0**
- Structural issues detected: **0**
- Capabilities without an explicit next falsifiable test: **0**
- V4 runs: **0** (core V4 instrumentation complete: **0**)
- Runs mapped to a controlled search objective (explicit or reviewed legacy map): **11/12**
- Candidate dispositions normalized to controlled reasons (direct or reviewed alias): **17**

## Missing recommended legacy/core fields

| Field | Runs missing |
|---|---:|
| queries | 6 |
| search_surfaces | 4 |
| candidate_dispositions | 4 |

## Structural issues

- None.

## Learning bottlenecks

- Strategy evidence remains below the 5-run/20-inspection comparison threshold; use MEASUREMENT_CAMPAIGN.md rather than over-reading observational percentages.
- Query-family wording remains sparse; objective aggregation is the stable cross-domain layer.
- Exact surface labels are normalized into families, but matched comparisons are still required for causal surface claims.
- Revision debt and MASTER catalog provenance debt are tracked separately in REVISION_DEBT_REPORT.md.
- Core instrumentation is strong enough for cautious, exploration-preserving allocation.
