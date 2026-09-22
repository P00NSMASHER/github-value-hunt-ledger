# LeaseRecovery ingestion contract

LeaseRecovery audits landlord charges against effective-dated lease pricing using the shared deterministic contract-billing engine.

## Charges CSV

Default columns: Charge_ID, Counterparty, Account_ID, Service_ID, Service_Date, Actual_Amount.
Counterparty is normally the landlord or property manager. Service_ID identifies the governed charge family such as BASE-RENT, CAM-2026, OPEX-2026, or TAX-ESCALATION.

## Lease rate CSV

Default columns: Counterparty, Service_ID, Effective_From, Effective_To, Fixed_Fee, Included_Units, Unit_Rate.
Rates must already be normalized to the invoice period. RecoveryOS does not infer annual-to-monthly or quarterly-to-monthly conversions.
Fixed-only charges do not require quantity evidence. Unit-priced charges require independent quantity evidence.

## Area CSV

Columns: Charge_ID, Area_SqFt.
Area_SqFt is independently hashed and row-located and is multiplied by the effective Unit_Rate for the matching charge.
A generic usage_csv with Charge_ID and Units may be supplied instead of area_csv, but never both.

If a unit-priced lease rate has no independent area/usage record, the candidate fails closed with MISSING_USAGE rather than assuming a quantity.
Duplicate charge IDs, missing effective rates, and overlapping rate versions inherit the shared contract-billing fail-closed controls.

## Scan 360 configuration fields

lease.charges_csv
lease.rates_csv
lease.area_csv or lease.usage_csv
lease.charge_source_verified
lease.rate_source_verified
lease.area_source_verified or lease.usage_source_verified

## Operational boundary

LeaseRecovery ingestion can identify REVIEW or VALIDATED billing variances. It cannot approve a case, contact a landlord, send a demand, interpret legal entitlement autonomously, or authorize recovery activity.
Qualified human review remains required for lease interpretation and CAM/operating-expense entitlement before the existing explicit customer-authorization gate.
