# QUERY FAMILY REPORT

Query families preserve reusable search hypotheses while broader search objectives aggregate related hypotheses across domains.

- Measured query families: **12**
- One-run families: **12**
- Families mapped to a controlled search objective: **11/12**
- Objective conflicts requiring review: **0**
- Families with sufficient evidence (>=5 runs and >=20 deep inspections): **0**

## Family measurements

| Query family | Objective | Runs | Inspected | Retained | MASTER | Capability runs | Experiment runs | Evidence |
|---|---|---:|---:|---:|---:|---:|---:|---|
| QF:physical-action-response-loss-same-action-readback-unknown-retry-restart-gate — physical-action response-loss + same-action readback + UNKNOWN + retry/restart gate | OBJ:ambiguity-reconciliation | 1 | 4 | 3 | 0 | 0 | 1 | insufficient |
| QF:recovery-proof-completeness-expected-subject-inventory-multi-engine-semantic-restore-fail-open-validation — recovery-proof completeness + expected-subject inventory + multi-engine semantic restore + fail-open validation | OBJ:completeness-proof | 1 | 4 | 2 | 0 | 0 | 1 | insufficient |
| QF:sam-attachment-deletedflag-excludedeleted-deleteall-disappearance-historical-manifest-retention — SAM attachment deletedFlag excludeDeleted deleteAll disappearance historical manifest retention | OBJ:completeness-proof | 1 | 4 | 2 | 0 | 0 | 1 | insufficient |
| QF:approved-measurement-exact-work-order-contract-line-ownership-bill-period-cutoff-cumulative-authority-unbilled-claim-alt — approved measurement + exact work-order/contract-line ownership + bill-period cutoff + cumulative authority + unbilled claim + alternate mutate endpoint | OBJ:authority-lineage | 1 | 3 | 3 | 0 | 0 | 1 | insufficient |
| QF:event-time-authority-external-provider-inquiry-unknown-failed-one-shot-refund-confirmed-counter-event-compensating-ledge — event-time authority + external provider inquiry + UNKNOWN != FAILED + one-shot refund + confirmed counter-event + compensating ledger + bank realization | OBJ:exactly-once-settlement | 1 | 3 | 3 | 0 | 0 | 1 | insufficient |
| QF:invoice-po-receipt-exact-line-identity-receipt-capacity-conservation-service-acceptance-blanket-order-semantics — invoice-po-receipt exact-line identity + receipt-capacity conservation + service acceptance + blanket-order semantics | OBJ:authority-lineage | 1 | 3 | 3 | 0 | 0 | 1 | insufficient |
| QF:outage-outcome-independent-falsifier-rights — outage-outcome-independent-falsifier-rights | OBJ:independent-evaluation | 1 | 3 | 2 | 0 | 0 | 1 | insufficient |
| QF:sam-solicitation-history-data-services-attachment-manifest-deleted-restricted-external-link-completeness — SAM solicitation history Data Services attachment manifest deleted restricted external-link completeness | OBJ:completeness-proof | 1 | 3 | 1 | 0 | 0 | 1 | insufficient |
| QF:physical-action-ambiguity-external-run-identity-restart-persistent-positive-readback-negative-reissue-proof — physical-action ambiguity + external run identity + restart-persistent positive readback + negative reissue proof | unclassified | 1 | 2 | 2 | 0 | 0 | 1 | insufficient |
| QF:physical-action-restart-identity-continuity-local-cancelled-unknown-retry-gate — physical-action restart + identity continuity + local CANCELLED/UNKNOWN + retry gate | OBJ:ambiguity-reconciliation | 1 | 1 | 1 | 0 | 0 | 1 | insufficient |
| QF:usecpo-v2-schema-event-id-correlation-lineage — USECPO-v2-schema-event-id-correlation-lineage | OBJ:identity-lineage | 1 | 1 | 1 | 0 | 0 | 1 | insufficient |
| QF:exp-001-realized-recovery-persistence-and-concurrency-acceptance-boundary — EXP-001 realized-recovery persistence and concurrency acceptance boundary | OBJ:exactly-once-settlement | 1 | 0 | 0 | 0 | 0 | 1 | insufficient |

## Interpretation

- A one-off query family is a hypothesis, not a learned policy.
- The objective layer is intentionally broader: related queries can teach the same research objective without being merged into one QF.
- Reuse a QF only when the implementation conjunction/hypothesis is genuinely the same.
- Literal queries remain preserved in search runs for reproducibility.
