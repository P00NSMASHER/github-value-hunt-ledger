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
automatically. RecoveryLedger requires both human approval and an explicit
customer authorization ID before a case can become CLAIMED.

## Universal model

Client -> Counterparty -> Transaction -> Governing Rule -> Expected Amount ->
Actual Amount -> Variance -> Evidence -> Recovery Case -> Outcome.

The two common financial modes are:

- OVERPAYMENT: recoverable = max(actual - expected, 0)
- UNDERPAYMENT: recoverable = max(expected - actual, 0)

## Existing FreightRecovery integration

recoveryworks.branches.freight.from_freight_finding() bridges the existing
proof-bound freight/ findings into RecoveryOS. It intentionally downgrades a
freight finding to review if the matching verified authority object is absent.

## Test

From repository root:

    python -m unittest recoveryworks.test_recoveryworks

The foundation intentionally uses only Python's standard library.

## Multibranch adapter status

RecoveryOS now has concrete normalization adapters for all six initial branches:

- FreightRecovery bridges existing proof-bound freight findings.
- PayerRecovery accepts deterministic expected reimbursement vs paid amounts.
- UtilityRecovery accepts effective-dated tariff recalculation results.
- APRecovery accepts deterministic payment/reconciliation variances.
- ConstructionRecovery accepts reviewed entitlement amounts and paid amounts.
- DutyRecovery accepts deterministic tariff/fee expected-vs-paid results.

Every non-freight adapter is date-scoped. If the proposed controlling rule is
outside its effective window for the transaction/event date, the rule remains
visible for review but its controlling flag is revoked and the finding cannot
become VALIDATED.

## Fulfillment packets

`build_recovery_packet()` converts a ledger record into a deterministic,
hash-addressed fulfillment packet containing the money calculation, rule
provenance, evidence locators, case state, and readiness gates.

`submission_ready(packet)` is true only when all of the following are true:

- the finding is VALIDATED;
- the controlling rule is verified;
- every load-bearing evidence item is verified;
- a human reviewer approved the case;
- explicit customer authorization exists; and
- the case is currently in AUTHORIZED state.

`build_client_portfolio_packet()` produces a client-isolated, hash-addressed
rollup across branches without leaking records belonging to another client.

## Audit trail

RecoveryLedger now emits an append-only SHA-256 event chain for add, approval,
authorization, claim, rejection, and recovery transitions. Duplicate ingestion,
identical repeated approval, and identical repeated authorization are idempotent.
The ledger exposes an audit head and snapshot hash so a delivered portfolio can
be tied back to the exact case state used to produce it.
