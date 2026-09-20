# MEASUREMENT DEBT PLAN

This report answers a different question from SEARCH_POLICY.md: not **where might value be**, but **what evidence is still missing before the system can credibly compare search strategies**.

- Active strategies: **12**
- Strategies with sufficient evidence: **0**
- Sufficiency threshold: **5 measured runs + 20 deep inspections** per strategy.

## Strategy measurement debt

| Strategy | Runs | Inspected | More runs needed | More inspections needed | Instrumentation debt | Policy allocation |
|---|---:|---:|---:|---:|---:|---:|
| STRAT:authority-origin-invariant-set-consistency | 0 | 0 | 5 | 20 | 0% | 5.4% |
| STRAT:cross-source-emergence-triangulation | 0 | 0 | 5 | 20 | 0% | 5.4% |
| STRAT:decision-claim-runtime-side-effect-trace | 0 | 0 | 5 | 20 | 0% | 5.4% |
| STRAT:ingestion-invariant-triad-intersection | 0 | 0 | 5 | 20 | 0% | 5.4% |
| STRAT:paper-research-artifact-production-descendant | 0 | 0 | 5 | 20 | 0% | 5.4% |
| STRAT:rule-period-authority-version-audit | 1 | 1 | 4 | 19 | 0% | 5.4% |
| STRAT:protocol-regression-archaeology-for-pre-fat-systems | 1 | 3 | 4 | 17 | 0% | 8.3% |
| STRAT:fail-open-boundary-archaeology | 1 | 4 | 4 | 16 | 0% | 9.4% |
| STRAT:evaluation-target-independence | 2 | 4 | 3 | 16 | 100% | 9.0% |
| STRAT:capability-conjunction-search-claim-tracing | 2 | 6 | 3 | 14 | 17% | 12.5% |
| STRAT:first-party-production-source-triangulation | 2 | 7 | 3 | 13 | 100% | 12.2% |
| STRAT:acceptance-path-transition-inspection | 5 | 10 | 0 | 10 | 7% | 16.2% |

## Operating rule

- Spend part of the exploration budget on reducing measurement debt, especially for zero-run strategies.
- Do not manufacture deep inspections merely to hit 20; a bounded no-find run is valid evidence if the search was genuinely executed and logged.
- Prefer prospective runs with complete literal queries, search surfaces and candidate dispositions so strategy comparisons remain interpretable.
- Once a strategy clears the evidence threshold, additional runs should be justified by information value, active experiment gaps or outcome follow-through—not by quota.
