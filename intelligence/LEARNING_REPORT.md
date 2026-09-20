# LEARNING REPORT

Generated from prospective and benchmark search runs. Retrospective anecdotes are excluded from yield denominators.

- Measured runs: **9**
- Search-bearing runs: **8**
- Structured outcomes: **1**
- Outcome-lag window: **14 days**; recent runs are not counted as outcome failures.

## Strategy performance

| Strategy | Runs | Inspected | Retained precision | MASTER yield | New-capability run rate | Experiment run rate | Outcomes | Outcome conversion* | Evidence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| STRAT:acceptance-path-transition-inspection | 2 | 4 | 75.0% [30.1%, 95.4%] | 0.0% [0.0%, 49.0%] | 0.0% [0.0%, 65.8%] | 100.0% [34.2%, 100.0%] | 1 | — | insufficient |
| STRAT:capability-conjunction-search-claim-tracing | 2 | 6 | 100.0% [61.0%, 100.0%] | 0.0% [0.0%, 39.0%] | 0.0% [0.0%, 65.8%] | 100.0% [34.2%, 100.0%] | 0 | — | insufficient |
| STRAT:evaluation-target-independence | 2 | 4 | 75.0% [30.1%, 95.4%] | 0.0% [0.0%, 49.0%] | 0.0% [0.0%, 65.8%] | 100.0% [34.2%, 100.0%] | 0 | — | insufficient |
| STRAT:fail-open-boundary-archaeology | 1 | 4 | 50.0% [15.0%, 85.0%] | 0.0% [0.0%, 49.0%] | 0.0% [0.0%, 79.3%] | 100.0% [20.7%, 100.0%] | 0 | — | insufficient |
| STRAT:first-party-production-source-triangulation | 2 | 7 | 42.9% [15.8%, 75.0%] | 0.0% [0.0%, 35.4%] | 0.0% [0.0%, 65.8%] | 100.0% [34.2%, 100.0%] | 0 | — | insufficient |

*Outcome conversion only uses runs old enough to clear the lag window.

## Query-family performance

| Query family | Runs | Inspected | Retained precision | MASTER yield | New-capability run rate | Outcomes | Evidence |
|---|---:|---:|---:|---:|---:|---:|---|
| EXP-001 realized-recovery persistence and concurrency acceptance boundary | 1 | 0 | — | — | 0.0% [0.0%, 79.3%] | 1 | insufficient |
| SAM attachment deletedFlag excludeDeleted deleteAll disappearance historical manifest retention | 1 | 4 | 50.0% [15.0%, 85.0%] | 0.0% [0.0%, 49.0%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |
| SAM solicitation history Data Services attachment manifest deleted restricted external-link completeness | 1 | 3 | 33.3% [6.1%, 79.2%] | 0.0% [0.0%, 56.2%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |
| USECPO-v2-schema-event-id-correlation-lineage | 1 | 1 | 100.0% [20.7%, 100.0%] | 0.0% [0.0%, 79.3%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |
| event-time authority + external provider inquiry + UNKNOWN != FAILED + one-shot refund + confirmed counter-event + compensating ledger + bank realization | 1 | 3 | 100.0% [43.8%, 100.0%] | 0.0% [0.0%, 56.2%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |
| invoice-po-receipt exact-line identity + receipt-capacity conservation + service acceptance + blanket-order semantics | 1 | 3 | 100.0% [43.8%, 100.0%] | 0.0% [0.0%, 56.2%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |
| outage-outcome-independent-falsifier-rights | 1 | 3 | 66.7% [20.8%, 93.9%] | 0.0% [0.0%, 56.2%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |
| physical-action response-loss + same-action readback + UNKNOWN + retry/restart gate | 1 | 4 | 75.0% [30.1%, 95.4%] | 0.0% [0.0%, 49.0%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |
| recovery-proof completeness + expected-subject inventory + multi-engine semantic restore + fail-open validation | 1 | 4 | 50.0% [15.0%, 85.0%] | 0.0% [0.0%, 49.0%] | 0.0% [0.0%, 79.3%] | 0 | insufficient |

## Policy

- Do not claim a strategy is superior until it has at least 5 measured runs and 20 deep inspections.
- Keep explicit exploration; low-frequency strange discoveries must not be optimized away by short-run precision.
- Realized outcomes outrank predicted repository scores.
- An internal engineering or validation run with zero candidates can still strengthen a capability or experiment, but it does not enter candidate-yield denominators.
- Failed and partial outcomes remain training data.

## Realized value traced through the loop

- Revenue: **$0**
- Customer value: **$0**
- Observed engineering compression: **0–0 engineer-days**
