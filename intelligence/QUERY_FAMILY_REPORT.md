# QUERY FAMILY REPORT

Query families are canonicalized independently from literal search strings so the system can learn reusable search patterns without collapsing distinct hypotheses too early.

- Measured query families: **11**
- One-run families: **11**
- Families with sufficient evidence (>=5 runs and >=20 deep inspections): **0**

## Family measurements

| Query family | Runs | Inspected | Retained | MASTER | Capability runs | Experiment runs | Evidence |
|---|---:|---:|---:|---:|---:|---:|---|
| QF:physical-action-response-loss-same-action-readback-unknown-retry-restart-gate — physical-action response-loss + same-action readback + UNKNOWN + retry/restart gate | 1 | 4 | 3 | 0 | 0 | 1 | insufficient |
| QF:recovery-proof-completeness-expected-subject-inventory-multi-engine-semantic-restore-fail-open-validation — recovery-proof completeness + expected-subject inventory + multi-engine semantic restore + fail-open validation | 1 | 4 | 2 | 0 | 0 | 1 | insufficient |
| QF:sam-attachment-deletedflag-excludedeleted-deleteall-disappearance-historical-manifest-retention — SAM attachment deletedFlag excludeDeleted deleteAll disappearance historical manifest retention | 1 | 4 | 2 | 0 | 0 | 1 | insufficient |
| QF:approved-measurement-exact-work-order-contract-line-ownership-bill-period-cutoff-cumulative-authority-unbilled-claim-alt — approved measurement + exact work-order/contract-line ownership + bill-period cutoff + cumulative authority + unbilled claim + alternate mutate endpoint | 1 | 3 | 3 | 0 | 0 | 1 | insufficient |
| QF:event-time-authority-external-provider-inquiry-unknown-failed-one-shot-refund-confirmed-counter-event-compensating-ledge — event-time authority + external provider inquiry + UNKNOWN != FAILED + one-shot refund + confirmed counter-event + compensating ledger + bank realization | 1 | 3 | 3 | 0 | 0 | 1 | insufficient |
| QF:invoice-po-receipt-exact-line-identity-receipt-capacity-conservation-service-acceptance-blanket-order-semantics — invoice-po-receipt exact-line identity + receipt-capacity conservation + service acceptance + blanket-order semantics | 1 | 3 | 3 | 0 | 0 | 1 | insufficient |
| QF:outage-outcome-independent-falsifier-rights — outage-outcome-independent-falsifier-rights | 1 | 3 | 2 | 0 | 0 | 1 | insufficient |
| QF:sam-solicitation-history-data-services-attachment-manifest-deleted-restricted-external-link-completeness — SAM solicitation history Data Services attachment manifest deleted restricted external-link completeness | 1 | 3 | 1 | 0 | 0 | 1 | insufficient |
| QF:physical-action-restart-identity-continuity-local-cancelled-unknown-retry-gate — physical-action restart + identity continuity + local CANCELLED/UNKNOWN + retry gate | 1 | 1 | 1 | 0 | 0 | 1 | insufficient |
| QF:usecpo-v2-schema-event-id-correlation-lineage — USECPO-v2-schema-event-id-correlation-lineage | 1 | 1 | 1 | 0 | 0 | 1 | insufficient |
| QF:exp-001-realized-recovery-persistence-and-concurrency-acceptance-boundary — EXP-001 realized-recovery persistence and concurrency acceptance boundary | 1 | 0 | 0 | 0 | 0 | 1 | insufficient |

## Interpretation

- A one-off query family is a hypothesis, not a learned policy.
- Reuse the same family ID when the underlying conjunction/invariant is the same even if literal queries change.
- Use `query_family_aliases.json` to merge wording variants only after manual review; never auto-merge families by text similarity alone.
- Literal queries remain preserved in search runs for reproducibility.
