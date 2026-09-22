# Parcel, Procurement, Warranty/Credit, and Payroll/Benefit ingestion

These four RecoveryWorks branches use the common proof, calculation, review,
authorization, and durable-ledger model. Detection never authorizes external
contact, refund demands, claims, or money movement.

## ParcelRecovery

ParcelRecovery finds parcel carrier invoice overpayments by comparing an actual
shipment charge to a **reviewed expected-rate assessment** bound to the same:

- shipment
- carrier
- ship date
- service code
- zone
- billed weight

The first operational adapter deliberately does not infer carrier contract rates,
dimensional weight, or accessorial eligibility from invoice text alone. A parcel
rating engine, reviewed carrier contract, or other authorized upstream process
can produce the expected assessment.

### Parcel invoice CSV

- `Shipment_ID`
- `Invoice_ID`
- `Shipper_ID`
- `Carrier_ID`
- `Ship_Date`
- `Service_Code`
- `Zone`
- `Billed_Weight`
- `Actual_Total`

`Shipper_ID` must match the Scan 360 client.

### Reviewed parcel assessment CSV

- `Assessment_ID`
- `Shipment_ID`
- `Carrier_ID`
- `Ship_Date`
- `Service_Code`
- `Zone`
- `Billed_Weight`
- `Expected_Total`
- `Rate_Basis`
- `Rate_Snapshot_Date`
- `Rate_Reviewer_ID`

A verified assessment requires both the rate snapshot date and reviewer ID.

Identity differences fail closed instead of being treated as an overcharge.

## ProcurementRecovery

ProcurementRecovery reconstructs the amount an invoice line should have billed
from two independent sources:

`expected line = contracted unit price × approved billable quantity`

The controlling price comes from an effective PO/contract authority. The
quantity comes from a separate receipt, three-way match, or reviewed billable
quantity record.

### Supplier invoice line CSV

- `Invoice_Line_ID`
- `Invoice_ID`
- `Purchaser_ID`
- `Supplier_ID`
- `PO_Line_ID`
- `SKU`
- `Invoice_Date`
- `Invoiced_Quantity`
- `Actual_Line_Amount`

### Price authority CSV

- `Authority_ID`
- `Supplier_ID`
- `PO_Line_ID`
- `SKU`
- `Effective_From`
- `Effective_To`
- `Contracted_Unit_Price`
- `Price_Basis`

### Approved quantity CSV

- `Invoice_Line_ID`
- `Approved_Billable_Quantity`
- `Quantity_Basis`

Missing or conflicting quantity evidence creates an exception, not recovery.

This first adapter treats the supplied invoice line amount as the product/service
line being reconciled. Tax, freight, duties, and unrelated ancillary charges
should be supplied to their appropriate RecoveryWorks branches rather than
silently mixed into the procurement line.

## Warranty/CreditRecovery

Warranty/CreditRecovery is an **underpayment** branch for approved supplier
credits that have not been fully issued or applied.

Examples include reviewed:

- warranty credits
- RMA/return credits
- supplier allowances
- approved pricing credits
- other documented supplier credit entitlements

### Credit entitlement CSV

- `Entitlement_ID`
- `Client_ID`
- `Supplier_ID`
- `Reference_ID`
- `Credit_Category`
- `Entitled_Amount`
- `Effective_Date`
- `Entitlement_Basis`
- `Entitlement_Reviewer_ID`

Verified entitlements require a reviewer.

### Credit settlement CSV

- `Settlement_ID`
- `Entitlement_ID`
- `Amount_Received`
- `Settlement_Date`
- `Settlement_Kind`

Multiple unique credit memos/refunds/remittances are summed.

A zero-dollar settlement row is valid evidence that no credit was received.
If there is no settlement evidence, the branch returns
`NO_CREDIT_SETTLEMENT_EVIDENCE`; it does **not** assume zero.

## Payroll/BenefitBillingRecovery

This branch is strictly for **employer-side vendor/carrier billing
reconciliation**.

In scope examples:

- payroll processor per-employee/per-pay-run service fees
- benefit administration fees
- carrier premium/service billing when modeled as a reviewed rate × independent
  billable units
- other employer-paid service charges under an effective contract

Explicitly outside this branch:

- employee wage calculations
- payroll tax calculations or tax claims
- employee deductions
- benefits eligibility decisions
- individual employee/member claims
- employee-facing recovery or collection

### Rate and charge CSVs

The branch reuses the common recurring-service contract schema:

Rate:
- `Counterparty`
- `Service_ID`
- `Effective_From`
- `Effective_To`
- `Fixed_Fee`
- `Included_Units`
- `Unit_Rate`

Charge:
- `Charge_ID`
- `Counterparty`
- `Account_ID`
- `Service_ID`
- `Service_Date`
- `Actual_Amount`

Expected amount:

`fixed fee + max(independent units - included units, 0) × unit rate`

Use separate Service_ID values for different benefit plans, coverage tiers,
payroll services, or pricing units.

### Deidentified unit CSV

- `Charge_ID`
- `Record_ID`
- `Units`

`Record_ID` must be an opaque/surrogate identifier. The loader rejects common
direct-identifier headers including names, SSN, DOB, email, phone, and address.

Duplicate surrogate records within one charge fail closed.

## Scan 360 configuration

```json
{
  "parcel": {
    "charges_csv": "parcel_charges.csv",
    "assessments_csv": "parcel_assessments.csv",
    "charge_source_verified": true,
    "assessment_source_verified": true
  },
  "procurement": {
    "invoice_lines_csv": "procurement_invoice_lines.csv",
    "authorities_csv": "procurement_authorities.csv",
    "quantities_csv": "approved_quantities.csv",
    "invoice_source_verified": true,
    "authority_source_verified": true,
    "quantity_source_verified": true
  },
  "warranty_credit": {
    "entitlements_csv": "credit_entitlements.csv",
    "settlements_csv": "credit_settlements.csv",
    "entitlement_source_verified": true,
    "settlement_source_verified": true
  },
  "payroll_benefit": {
    "charges_csv": "employer_vendor_charges.csv",
    "rates_csv": "employer_vendor_rates.csv",
    "units_csv": "deidentified_billable_units.csv",
    "charge_source_verified": true,
    "rate_source_verified": true,
    "unit_source_verified": true
  }
}
```

## External-action boundary

All four branches stop at the Recovery Ledger. Existing RecoveryWorks controls
still require:

1. proof-bound source ingestion
2. deterministic expected-vs-actual calculation
3. REVIEW/VALIDATED separation
4. human reviewer approval
5. explicit customer authorization
6. external recovery action
7. outcome and fee recording
