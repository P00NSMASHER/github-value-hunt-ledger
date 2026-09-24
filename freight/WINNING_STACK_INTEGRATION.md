# RecoveryOS winning-stack integration

## Outcome

RecoveryOS now has a pinned, deterministic integration plane for:

- `docx-redline-js` contract amendments;
- the SLA Penalty Settlement Engine as an independent comparator;
- AgentLedger-style evidence, replay and side-effect boundaries;
- Duroxide-style durable recovery workflows;
- Fleetbase read-only operational evidence;
- Yale tariff-rate data for landed-cost exposure.

The integration is implemented in `freight/recovery_stack.py`. It does not give
any external component authority to create findings, assert recovered dollars,
post settlements, send carrier actions, or overwrite source contracts.

## Authority model

RecoveryOS remains authoritative for:

1. controlling contract/rate authority;
2. validated findings;
3. buyer review;
4. recovery claims;
5. external-action authorization;
6. settlement allocation and reversal;
7. fee eligibility and recovery certificates.

External systems receive immutable jobs with pinned repository revisions,
canonical payload hashes, idempotency keys and explicit execution boundaries.

## Business improvements

### Contract recovery

Confirmed claims can produce localized, fingerprint-bound Word redline jobs.
Jobs require atomic validation and never overwrite the source document.

### Settlement assurance

Claim batches produce an independent settlement-comparator job. Comparator
output is evidence for review; it cannot post money or change RecoveryOS state.

### Reliable AI operations

Every case receives an evidence-ledger job with explicit no-replay rules for
external side effects and an `UNKNOWN` outcome state that must be reviewed
before retry. Retry requires a hash-bound review receipt, and execution events
cannot move backwards in time.

### Durable execution

Every case receives a resumable workflow job covering evidence intake through
recovery certificate. Execution state is stored in an append-only SQLite event
chain with immutable job definitions.

### Freight operations

Fleetbase events enter only as read-only, hash-bound observations. They may
strengthen shipment and proof-of-delivery evidence but cannot mutate Fleetbase
or independently validate a claim.

### Landed-cost expansion

Effective-dated tariff observations calculate signed exposure in integer cents.
Exposure is explicitly classified as non-claim intelligence until controlling
authority and buyer review promote it through the normal RecoveryOS workflow.

## Deployment sequence

1. Run the new integration plane in shadow mode against the synthetic pilot.
2. Enable the MIT/Apache adapters one at a time after dependency/SBOM review.
3. Keep the AGPL settlement engine and Fleetbase behind isolated API or
   comparator boundaries until the intended deployment model is approved.
4. Reconcile each adapter result against RecoveryOS and record false positives,
   missed findings, analyst minutes and recovery lift.
5. Promote an adapter only when it improves measured outcomes without weakening
   the existing authority, security, rights or external-action gates.
