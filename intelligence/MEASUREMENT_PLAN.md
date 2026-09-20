# MEASUREMENT DEBT PLAN

This report answers a different question from SEARCH_POLICY.md: not **where might value be**, but **what evidence is still missing before the system can credibly compare search strategies**.

- Active strategies: **12**
- Strategies with sufficient evidence: **0**
- Sufficiency threshold: **5 measured runs + 20 deep inspections** per strategy.

## Strategy measurement debt

| Strategy | Runs | Inspected | More runs needed | More inspections needed | Instrumentation debt | Policy allocation |
|---|---:|---:|---:|---:|---:|---:|
| STRAT:authority-origin-invariant-set-consistency | 0 | 0 | 5 | 20 | 0% | 5.2% |
| STRAT:cross-source-emergence-triangulation | 0 | 0 | 5 | 20 | 0% | 5.2% |
| STRAT:decision-claim-runtime-side-effect-trace | 0 | 0 | 5 | 20 | 0% | 5.2% |
| STRAT:ingestion-invariant-triad-intersection | 0 | 0 | 5 | 20 | 0% | 5.2% |
| STRAT:paper-research-artifact-production-descendant | 0 | 0 | 5 | 20 | 0% | 5.2% |
| STRAT:protocol-regression-archaeology-for-pre-fat-systems | 0 | 0 | 5 | 20 | 0% | 5.2% |
| STRAT:rule-period-authority-version-audit | 1 | 1 | 4 | 19 | 0% | 5.5% |
| STRAT:fail-open-boundary-archaeology | 1 | 4 | 4 | 16 | 0% | 9.8% |
| STRAT:evaluation-target-independence | 2 | 4 | 3 | 16 | 100% | 9.5% |
| STRAT:capability-conjunction-search-claim-tracing | 2 | 6 | 3 | 14 | 17% | 13.4% |
| STRAT:first-party-production-source-triangulation | 2 | 7 | 3 | 13 | 100% | 13.0% |
| STRAT:acceptance-path-transition-inspection | 5 | 10 | 0 | 10 | 7% | 17.5% |

## Operating rule

- Spend part of the exploration budget on reducing measurement debt, especially for zero-run strategies.
- Do not manufacture deep inspections merely to hit 20; a bounded no-find run is valid evidence if the search was genuinely executed and logged.
- Prefer prospective runs with complete literal queries, search surfaces and candidate dispositions so strategy comparisons remain interpretable.
- Once a strategy clears the evidence threshold, additional runs should be justified by information value, active experiment gaps or outcome follow-through—not by quota.
