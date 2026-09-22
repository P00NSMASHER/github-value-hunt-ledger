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
- **SaaSRecovery** — subscription, seat, and contracted-rate billing leakage.
- **TelecomRecovery** — recurring service and CDR/usage billing leakage.
- **RebateRecovery** — earned supplier/volume rebates not fully settled.
- **LeaseRecovery** — rent, CAM, operating-expense, and area-based lease billing leakage.
- **TaxRecovery** — professionally reviewed sales/use-tax and transaction-tax overpayments.
- **InsuranceRecovery** — professionally reviewed commercial/property claim underpayments.

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

## Operational ingestion

APRecovery and UtilityRecovery file schemas, deterministic tariff primitives,
verification flags, and failure modes are documented in
`recoveryworks/INGESTION_AP_UTILITY.md`.

SaaSRecovery and TelecomRecovery contract, invoice, seat, usage, and CDR schemas
are documented in `recoveryworks/INGESTION_SAAS_TELECOM.md`.

RebateRecovery tier modes, purchase/settlement schemas, and calculation controls
are documented in `recoveryworks/INGESTION_REBATE.md`.

LeaseRecovery landlord-charge, lease-rate, and area/allocation schemas are
documented in `recoveryworks/INGESTION_LEASE.md`.

## Portfolio readiness

Operational-vs-foundation status for all RecoveryWorks divisions is tracked in
`recoveryworks/PORTFOLIO.md`.

ConstructionRecovery entitlement, schedule-version, CPM, event-mapping,
qualified-causation, and settlement schemas are documented in
`recoveryworks/INGESTION_CONSTRUCTION.md`.

TaxRecovery invoice-tax, reviewed-assessment, rule-snapshot, and professional-review
schemas are documented in `recoveryworks/INGESTION_TAX.md`.

InsuranceRecovery claim, policy-assessment, settlement, and qualified-review schemas
are documented in `recoveryworks/INGESTION_INSURANCE.md`.
