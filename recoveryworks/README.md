# RecoveryWorks / RecoveryOS Foundation

RecoveryWorks is the umbrella recovery business. RecoveryOS is the shared proof,
calculation, review, and lifecycle layer used by all recovery branches.

## Initial branches

- **FreightRecovery** — carrier overcharges and contract/rate leakage.
- **PayerRecovery** — provider underpayments and downcoding.
- **UtilityRecovery** — commercial utility billing/tariff errors.
- **APRecovery** — duplicate payments, unapplied credits, and vendor-statement leakage.
- **ConstructionRecovery** — change-order and delay entitlement preflight.
- **DutyRecovery** — customs-duty and tariff inconsistencies for professional review.

## Non-negotiable invariant

A model may help extract or classify evidence, but it never invents controlling
rules and never performs money arithmetic. RecoveryEngine receives normalized
expected/actual values with versioned source references. A finding is VALIDATED
only when the controlling rule and all load-bearing evidence are verified.

No branch submits a claim, appeal, dispute, demand, or counterparty communication
automatically. RecoveryLedger requires human review plus an ACTIVE, scope-bound
RecoveryActionAuthorization before a case can become CLAIMED. The authorization
is bound to the reviewed finding proof, customer engagement, branch-allowed action,
counterparty, recipient/routing hash, action-payload hash, currency, dollar ceiling,
validity window, and revocation state.

## Universal model

Client -> Counterparty -> Transaction -> Governing Rule -> Expected Amount ->
Actual Amount -> Variance -> Evidence -> Recovery Case -> Outcome.

The two common financial modes are:

- OVERPAYMENT: recoverable = max(actual - expected, 0)
- UNDERPAYMENT: recoverable = max(expected - actual, 0)

## Customer engagement boundary

RecoveryEngagementCharter defines which client, recovery branches, source-data
kinds, report generation, and customer approver roles are authorized. A charter
is immutable and hash-bound. It explicitly sets external_action_authorized=false
and requires a separate customer approval for any external recovery action.

Recovery Scan 360 is bound to the engagement ID/hash and refuses branches or
source kinds outside that charter.

## Scope-bound external action authorization

RecoveryActionAuthorization is intentionally narrower than the engagement charter.
It can authorize only one reviewed finding and an enumerated branch-allowed action.
It cannot authorize money movement, settlement acceptance, account changes,
credential use, general contact authority, or automatic execution. It expires,
can be revoked, and cannot outlive its engagement charter.

The ledger records authorized_cents and claimed_cents separately. Realized recovery
cannot exceed the exact amount that was claimed.

## Durable Recovery Ledger

SQLiteRecoveryLedger persists the same guarded lifecycle as RecoveryLedger and
adds an append-only per-case event chain. Every event is chained to the previous
event hash; startup replays the chain and verifies the persisted snapshot against
the replayed economic/lifecycle state. A modified event payload, sequence gap,
previous-hash mismatch, proof mismatch, or snapshot mismatch fails closed.

Operational timestamps are deliberately excluded from record_hash so deterministic
replay across process restarts preserves the same state identity. SQLite write
serialization rejects stale concurrent writers, and recovery-event rows are guarded
as append-only. Startup also rejects orphan snapshots and event/snapshot population
mismatches.

Money rollups are partitioned by currency; RecoveryOS never silently adds USD,
EUR, or other currencies into one meaningless "cents" total.

## Tenant isolation

ClientRecoveryLedger is the customer-facing facade for a shared RecoveryOS ledger.
It filters reads and blocks lifecycle mutations for cases belonging to another
client. Other-client and nonexistent case IDs intentionally return the same
"unknown recovery case" behavior.

## Branch adapter registry

Every branch has a stable RuleBackedAdapter entry point. Vertical engines own
domain parsing and deterministic expected-amount logic; the registry only
normalizes those proof-bound results into RecoveryObservation. This prevents a
new vertical from bypassing the shared evidence, arithmetic, review, and
authorization controls.

## Existing FreightRecovery integration

recoveryworks.branches.freight.from_freight_finding() bridges the existing
proof-bound freight findings into RecoveryOS. It intentionally downgrades a
freight finding to review if the matching verified authority object is absent.

## Test

From repository root:

    python -m unittest recoveryworks.test_recoveryworks

The foundation intentionally uses only Python's standard library.
