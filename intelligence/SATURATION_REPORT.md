# SEARCH SATURATION REPORT

Saturation is a soft redirect, not a ban. A neighborhood is never marked saturated from attention alone; it requires enough measured runs plus evidence of low novelty or rising duplication.

- Measured runs: **12**
- Research neighborhoods: **22**
- Sufficient-evidence neighborhoods: **0**
- Saturating: **0**
- Saturated: **0**

## Neighborhood health

| Neighborhood | Type | Status | Runs | Inspected | Retained | MASTER | New-cap run rate | Duplicate ratio | Trailing no-delta | Action |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| NBR:cap:cap-001 | capability | INSUFFICIENT | 1 | 3 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:cap:cap-006 | capability | INSUFFICIENT | 1 | 0 | 0 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:cap:cap-007 | capability | INSUFFICIENT | 1 | 3 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:cap:cap-010 | capability | INSUFFICIENT | 1 | 4 | 2 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:cap:cap-011 | capability | INSUFFICIENT | 2 | 7 | 3 | 0 | 0% | — | 2 | MEASURE_MORE |
| NBR:cap:cap-015 | capability | INSUFFICIENT | 2 | 4 | 3 | 0 | 0% | — | 2 | MEASURE_MORE |
| NBR:cap:cap-016 | capability | INSUFFICIENT | 4 | 9 | 9 | 0 | 0% | — | 4 | MEASURE_MORE |
| NBR:cap:cap-017 | capability | INSUFFICIENT | 3 | 7 | 6 | 0 | 0% | — | 3 | MEASURE_MORE |
| NBR:cap:cap-018 | capability | INSUFFICIENT | 1 | 3 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:cap:cap-019 | capability | INSUFFICIENT | 1 | 3 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:approved-measurement-exact-work-order-contract-line-ownership-bill-period-cutoff-cumulative-authority-unbilled-claim-alt | query_family | INSUFFICIENT | 1 | 3 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:event-time-authority-external-provider-inquiry-unknown-failed-one-shot-refund-confirmed-counter-event-compensating-ledge | query_family | INSUFFICIENT | 1 | 3 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:exp-001-realized-recovery-persistence-and-concurrency-acceptance-boundary | query_family | INSUFFICIENT | 1 | 0 | 0 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:invoice-po-receipt-exact-line-identity-receipt-capacity-conservation-service-acceptance-blanket-order-semantics | query_family | INSUFFICIENT | 1 | 3 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:outage-outcome-independent-falsifier-rights | query_family | INSUFFICIENT | 1 | 3 | 2 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:physical-action-ambiguity-external-run-identity-restart-persistent-positive-readback-negative-reissue-proof | query_family | INSUFFICIENT | 1 | 2 | 2 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:physical-action-response-loss-same-action-readback-unknown-retry-restart-gate | query_family | INSUFFICIENT | 1 | 4 | 3 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:physical-action-restart-identity-continuity-local-cancelled-unknown-retry-gate | query_family | INSUFFICIENT | 1 | 1 | 1 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:recovery-proof-completeness-expected-subject-inventory-multi-engine-semantic-restore-fail-open-validation | query_family | INSUFFICIENT | 1 | 4 | 2 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:sam-attachment-deletedflag-excludedeleted-deleteall-disappearance-historical-manifest-retention | query_family | INSUFFICIENT | 1 | 4 | 2 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:sam-solicitation-history-data-services-attachment-manifest-deleted-restricted-external-link-completeness | query_family | INSUFFICIENT | 1 | 3 | 1 | 0 | 0% | — | 1 | MEASURE_MORE |
| NBR:qf:usecpo-v2-schema-event-id-correlation-lineage | query_family | INSUFFICIENT | 1 | 1 | 1 | 0 | 0% | — | 1 | MEASURE_MORE |

## Guardrails

- Insufficient telemetry is never interpreted as saturation.
- Saturation cannot override an active experiment-specific search need.
- A saturated same-domain neighborhood may still justify cross-domain positive-DNA transfer.
- Duplicate ratio is ignored until at least 10 structured candidate dispositions exist.
- First-seen rate is ignored until at least 10 explicit first-seen observations exist.
- Three consecutive no-delta runs are necessary but not sufficient for SATURATED.
- Manual review should inspect false-negative rescues before any hard prefilter is created.
