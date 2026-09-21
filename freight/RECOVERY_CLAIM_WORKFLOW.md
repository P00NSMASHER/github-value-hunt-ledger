# Recovery Claim Workflow

The recovery-claim workflow is the deterministic bridge between proof-bound buyer decisions and persistent settlement attribution.

A recovery claim can be issued only when:

- the buyer-review batch re-verifies against the current review packet, routing, and frozen truth;
- buyer review is complete for the buyer-review-ready case set;
- the individual finding disposition is `CONFIRMED`;
- the finding remains a positive `VALIDATED` finding;
- the exact finding proof still matches the buyer-review proof;
- claim issuance is not timestamped before the buyer review;
- the incumbent output is valid and bound to the same truth/population.

`FALSE_POSITIVE` and `UNRESOLVED` reviews never create recovery claims.

## Automatic fee eligibility boundary

The caller does not set `fee_disqualified`.

If the sealed incumbent output already identified a confirmed finding, the workflow marks that recovery claim fee-disqualified automatically. Challenger-only confirmed findings remain potentially fee-eligible; actual fee eligibility still depends on later settlement attribution and the commercial agreement.

## Claim proof

Each claim is generated with:

- deterministic claim ID based on the frozen finding proof;
- invoice reference;
- carrier as payer and customer as payee;
- exact finding currency;
- exact validated cents;
- canonical issue timestamp;
- the finding proof hash as claim source hash;
- explicit one-to-one `ClaimFindingBinding`;
- buyer review hash and incumbent attribution in the claim record proof.

This artifact represents an issued recovery claim. It is not settlement proof and does not assert realized savings.


## Atomic persistence

`persist_recovery_claim_batch` re-verifies the claim batch and store scope, then writes the full claim set through one SQLite transaction.

The persistence layer:
- pre-validates every claim before opening the batch transaction;
- rejects duplicate claim IDs or source hashes in the submitted batch;
- commits all new claims together;
- rolls back earlier inserts if a later claim conflicts;
- treats an exact replay as idempotent instead of duplicating claims;
- returns a deterministic receipt with attempted, created, and already-present counts.

A persistence receipt proves that the claim batch was accepted by the reference settlement store. It still does not prove external settlement or recovery.
