# MEASUREMENT DEBT PLAN

This report answers a different question from SEARCH_POLICY.md: not **where might value be**, but **what evidence is still missing before the system can credibly compare search strategies**.

- Active strategies: **12**
- Strategies with sufficient evidence: **0**
- Sufficiency threshold: **5 measured discovery runs + 20 deep inspections** per strategy.
- Explicit fixture, artifact-verification, waiting and unclassified actions do not satisfy discovery thresholds. Legacy records without an action remain observational evidence.

## Strategy measurement debt

| Strategy | Runs | Inspected | More runs needed | More inspections needed | Instrumentation debt | Policy allocation |
|---|---:|---:|---:|---:|---:|---:|
| STRAT:authority-origin-invariant-set-consistency | 0 | 0 | 5 | 20 | 0% | 5.5% |
| STRAT:cross-source-emergence-triangulation | 0 | 0 | 5 | 20 | 0% | 5.5% |
| STRAT:decision-claim-runtime-side-effect-trace | 0 | 0 | 5 | 20 | 0% | 5.5% |
| STRAT:ingestion-invariant-triad-intersection | 0 | 0 | 5 | 20 | 0% | 5.5% |
| STRAT:paper-research-artifact-production-descendant | 0 | 0 | 5 | 20 | 0% | 5.5% |
| STRAT:protocol-regression-archaeology-for-pre-fat-systems | 1 | 3 | 4 | 17 | 0% | 7.9% |
| STRAT:fail-open-boundary-archaeology | 1 | 4 | 4 | 16 | 0% | 8.9% |
| STRAT:evaluation-target-independence | 2 | 4 | 3 | 16 | 100% | 8.4% |
| STRAT:rule-period-authority-version-audit | 2 | 5 | 3 | 15 | 0% | 9.8% |
| STRAT:capability-conjunction-search-claim-tracing | 2 | 6 | 3 | 14 | 17% | 11.6% |
| STRAT:first-party-production-source-triangulation | 2 | 7 | 3 | 13 | 100% | 11.3% |
| STRAT:acceptance-path-transition-inspection | 5 | 10 | 0 | 10 | 7% | 14.8% |

## Operating rule

- Spend part of the exploration budget on reducing measurement debt, especially for zero-run strategies.
- Do not manufacture deep inspections merely to hit 20; a bounded no-find run is valid evidence if the search was genuinely executed and logged.
- Prefer prospective runs with complete literal queries, search surfaces and candidate dispositions so strategy comparisons remain interpretable.
- Once a strategy clears the evidence threshold, additional runs should be justified by information value, active experiment gaps or outcome follow-through—not by quota.
