# TaxRecovery ingestion contract

TaxRecovery detects transaction-tax overpayments by comparing actual tax charged
on invoice lines with separately reviewed expected tax assessments.

It does **not** autonomously decide taxability, exemption status, nexus, sourcing,
refund eligibility, or filing procedure.

## Tax line CSV

Default columns:

- `Tax_Line_ID`
- `Invoice_ID`
- `Purchaser_ID`
- `Vendor_ID`
- `Transaction_Date`
- `Jurisdiction`
- `Tax_Category`
- `Taxable_Basis`
- `Actual_Tax`

Each row is source-hashed and retains its CSV row locator.

`Purchaser_ID` must match the Scan 360 `client_id`. A mixed-client tax export
is rejected before any recovery math.

Duplicate `Tax_Line_ID` values are excluded rather than deduplicated
heuristically.

## Reviewed assessment CSV

Default columns:

- `Assessment_ID`
- `Tax_Line_ID`
- `Transaction_Date`
- `Jurisdiction`
- `Tax_Category`
- `Expected_Tax`
- `Taxability_Basis`
- `Rule_Snapshot_Date`
- `Professional_Reviewer_ID`

A verified assessment requires both:

- a named `Professional_Reviewer_ID`
- a `Rule_Snapshot_Date`

The reviewed assessment must match the invoice line on transaction date,
jurisdiction, and tax category. Conflicts fail closed.

Typical `Taxability_Basis` values can describe the reviewer-supported basis,
for example a reviewed exemption, sourcing treatment, statutory rate, product
classification, or tax-engine result. RecoveryWorks stores that basis but does
not independently declare it legally correct.

## Recovery calculation

For a matched line:

`potential recovery = actual tax charged - reviewed expected tax`

Only positive differences become recovery candidates.

Verified invoice evidence plus a verified professionally reviewed assessment can
produce VALIDATED dollars. Otherwise the finding remains REVIEW.

## Explicit exception states

- `DUPLICATE_TAX_LINE_ID`
- `PURCHASER_SCOPE_MISMATCH`
- `NO_REVIEWED_TAX_ASSESSMENT`
- `CONFLICTING_TAX_ASSESSMENTS`
- `TAX_ASSESSMENT_IDENTITY_MISMATCH`
- `ASSESSMENT_WITHOUT_TAX_LINE`

Exceptions do not create validated recovery amounts.

## Scan 360 config

```json
{
  "tax": {
    "lines_csv": "tax_lines.csv",
    "assessments_csv": "tax_assessments.csv",
    "line_source_verified": true,
    "assessment_source_verified": true
  }
}
```

## External recovery actions

A validated TaxRecovery finding is not authorization to request a refund,
self-adjust a return, claim an exemption, or contact a taxing authority/vendor.

The common RecoveryWorks controls still require:

1. human finding review
2. explicit customer authorization
3. appropriate tax-professional review of the chosen recovery route
4. outcome recording in the Recovery Ledger
