# LeaseRecovery and RebateRecovery ingestion contract

These branches use the shared RecoveryOS proof, review, authorization, durable ledger, and Scan 360 reporting layers. Ingestion never authorizes external action.

## LeaseRecovery

LeaseRecovery uses the shared effective-dated contract-billing engine.

### Landlord charges CSV

Default columns: Charge_ID, Counterparty, Account_ID, Service_ID, Service_Date, Actual_Amount.
Counterparty is normally the landlord/property manager. Service_ID identifies the governed charge family, such as BASE-RENT, CAM-2026, OPEX-2026, or TAX-ESCALATION.

### Lease rate CSV

Default columns: Counterparty, Service_ID, Effective_From, Effective_To, Fixed_Fee, Included_Units, Unit_Rate.
The rate must already be normalized to the invoice period. RecoveryOS does not guess annual-to-monthly conversions.
Fixed-only rent lines do not require quantity evidence. Area/allocation-based lines require independent quantity evidence.

### Area CSV

Columns: Charge_ID, Area_SqFt.
The area file is source-hashed and row-located independently from the landlord invoice and lease rate schedule.

Scan 360 lease config fields: charges_csv, rates_csv, area_csv, charge_source_verified, rate_source_verified, area_source_verified.
A generic usage_csv using Charge_ID and Units may be supplied instead of area_csv, but not both.
If an effective rate requires quantity evidence and none is supplied, the charge fails closed with MISSING_USAGE.
Lease interpretation and CAM/operating-expense entitlement remain subject to qualified human review before authorization.

## RebateRecovery

RebateRecovery detects earned rebate amounts that exceed explicit recorded rebate credits.
It does not infer nonpayment from silence. Every audited agreement/period must have at least one explicit credit-ledger row. A verified zero-dollar row represents: credit ledger checked; nothing was paid.

### Rebate agreements CSV

Default columns: Agreement_ID, Vendor, Basis, Effective_From, Effective_To, Threshold_Amount, Threshold_Units, Rate_BPS, Rate_Per_Unit, Fixed_Bonus.

Supported basis spend_bps:
expected rebate = eligible spend × Rate_BPS / 10,000 + Fixed_Bonus.
Threshold_Amount is expressed in currency units. 200 basis points = 2%.

Supported basis unit_cents:
expected rebate = eligible units × Rate_Per_Unit + Fixed_Bonus.
Threshold_Units controls eligibility.

### Rebate activity CSV

Columns: Agreement_ID, Period_ID, Period_End, Eligible_Spend, Eligible_Units.
This first production slice expects one summarized activity row per agreement/period. Duplicate summaries fail closed rather than being summed implicitly.

### Rebate credits CSV

Columns: Credit_ID, Agreement_ID, Period_ID, Amount.
Multiple distinct credits for a period are summed. Duplicate Credit_ID values are excluded and emitted as DUPLICATE_CREDIT_ID.
An agreement/period with no accepted credit rows emits MISSING_CREDIT_LEDGER_ROW and cannot create a recovery finding.

Scan 360 rebate config fields: agreements_csv, activity_csv, credits_csv, agreement_source_verified, activity_source_verified, credit_source_verified.

## Shared lifecycle

1. ingest and hash sources
2. select effective controlling rule/agreement
3. deterministic expected-vs-actual calculation
4. REVIEW or VALIDATED classification
5. human reviewer approval
6. explicit customer authorization
7. external recovery action
8. recovered-cash and fee tracking

No ingestion setting is permission to contact a landlord or supplier.
