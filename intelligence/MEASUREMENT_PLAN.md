# MEASUREMENT DEBT PLAN

This report answers a different question from SEARCH_POLICY.md: not **where might value be**, but **what evidence is still missing before the system can credibly compare search strategies**.

- Active strategies: **14**
- Strategies with sufficient evidence: **0**
- Sufficiency threshold: **5 measured discovery runs + 20 deep inspections** per strategy.
- Explicit fixture, artifact-verification, waiting and unclassified actions do not satisfy discovery thresholds. Legacy records without an action remain observational evidence.

## Strategy measurement debt

| Strategy | Runs | Inspected | More runs needed | More inspections needed | Instrumentation debt | Policy allocation |
|---|---:|---:|---:|---:|---:|---:|
| STRAT:bidirectional-money-evidence-invariant-tracing | 0 | 0 | 5 | 20 | 0% | 4.8% |
| STRAT:cross-source-emergence-triangulation | 0 | 0 | 5 | 20 | 0% | 4.8% |
| STRAT:decision-claim-runtime-side-effect-trace | 0 | 0 | 5 | 20 | 0% | 4.8% |
| STRAT:ingestion-invariant-triad-intersection | 0 | 0 | 5 | 20 | 0% | 4.8% |
| STRAT:nested-authority-and-post-review-invariant-audit | 0 | 0 | 5 | 20 | 0% | 4.8% |
| STRAT:paper-research-artifact-production-descendant | 0 | 0 | 5 | 20 | 0% | 4.8% |
| STRAT:authority-origin-invariant-set-consistency | 1 | 1 | 4 | 19 | 0% | 4.7% |
| STRAT:protocol-regression-archaeology-for-pre-fat-systems | 1 | 3 | 4 | 17 | 0% | 6.9% |
| STRAT:fail-open-boundary-archaeology | 1 | 4 | 4 | 16 | 0% | 7.8% |
| STRAT:first-party-production-source-triangulation | 2 | 7 | 3 | 13 | 100% | 9.9% |
| STRAT:capability-conjunction-search-claim-tracing | 3 | 9 | 2 | 11 | 11% | 10.7% |
| STRAT:evaluation-target-independence | 4 | 6 | 1 | 14 | 50% | 8.4% |
| STRAT:rule-period-authority-version-audit | 4 | 9 | 1 | 11 | 0% | 10.1% |
| STRAT:acceptance-path-transition-inspection | 5 | 10 | 0 | 10 | 7% | 13.0% |

## Operating rule

- Spend part of the exploration budget on reducing measurement debt, especially for zero-run strategies.
- Do not manufacture deep inspections merely to hit 20; a bounded no-find run is valid evidence if the search was genuinely executed and logged.
- Prefer prospective runs with complete literal queries, search surfaces and candidate dispositions so strategy comparisons remain interpretable.
- Once a strategy clears the evidence threshold, additional runs should be justified by information value, active experiment gaps or outcome follow-through—not by quota.
