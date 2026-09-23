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
- **CloudRecovery** — contracted cloud/hosting rate and metered-usage billing leakage.
- **MerchantFeeRecovery** — processor-controlled markup, per-transaction, and fixed-fee leakage.
- **ParcelRecovery** — parcel carrier rate/zone/weight billing leakage.
- **ProcurementRecovery** — PO/contract price and approved-quantity invoice leakage.
- **Warranty/CreditRecovery** — approved supplier/warranty credits not fully received.
- **Payroll/BenefitBillingRecovery** — employer-side payroll-service and benefit-carrier billing leakage.

## Non-negotiable invariant

A model may help extract or classify evidence, but it never invents controlling
rules and never performs money arithmetic. RecoveryEngine receives normalized
expected/actual values with versioned source references. A finding is VALIDATED
only when the controlling rule and all load-bearing evidence are verified.

No branch submits a claim, appeal, dispute, demand, or counterparty communication
automatically. RecoveryLedger requires both human approval and an explicit
customer authorization ID before a case can become CLAIMED.

RECOVERED is a separate evidence boundary. A case can become RECOVERED only
from a verified `SettlementEvidence` object that binds positive integer cents,
currency, an external source locator, a SHA-256 source digest, and an observed
time that does not predate the claim. The evidence is bound to one finding, and
the ledger refuses reuse of a settlement ID or source line across findings in
the same client scope. Fees cannot exceed that evidenced amount.

Proof-bearing source references, scan manifests, calculation inputs/traces, and
build artifacts require full lowercase SHA-256 digests. High-value calculation
and build provenance also requires the full 40-hex Git commit identifier;
abbreviations and descriptive placeholders fail closed.

## Durable-state integrity

Durable-ledger schema 2 authenticates a canonical UTC time on every hash-chained
lifecycle event and preserves that time during replay. Transitions cannot move
backward, repeat an approval/authorization, or rewrite review evidence after a
case progresses. Nested proof metadata and journal payloads are detached and
immutable after acceptance.

Schema 1 bundles did not authenticate lifecycle times. They are intentionally
rejected instead of being replayed with a new timestamp that could imply old
analysis was freshly performed. Recreate them from source evidence or use a
separately reviewed migration that preserves this limitation.

The local bundle adapter serializes compare-and-swap writes with a private
cross-process lock. State and report writes use `0600` on POSIX and a private
current-user plus SYSTEM DACL on Windows, and fail if those permissions cannot
be independently verified. This is a local reference adapter, not a claim of
external WORM storage or production database authorization.

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

CloudRecovery metering and MerchantFeeRecovery processor-fee scope schemas are
documented in `recoveryworks/INGESTION_CLOUD_MERCHANT.md`.

ParcelRecovery, ProcurementRecovery, Warranty/CreditRecovery, and
Payroll/BenefitBillingRecovery schemas and scope boundaries are documented in
`recoveryworks/INGESTION_PARCEL_PROCUREMENT_CREDIT_PAYROLL.md`.

## Seven-figure assurance

The mandatory proof, dual-control, source-authentication, deadline, and outbound-artifact controls for seven-figure findings are documented in `recoveryworks/HOSTILE_EXAMINATION_STANDARD.md`.
