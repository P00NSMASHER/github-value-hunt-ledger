# CloudRecovery and MerchantFeeRecovery ingestion contract

These branches extend Recovery Scan 360 without changing the common
RecoveryWorks proof, review, authorization, or outcome model.

## CloudRecovery

CloudRecovery compares provider invoice charges to reviewed effective-dated
contract pricing using an independent usage quantity.

Typical supported billing units include compute-hours, storage GB-months,
requests, vCPU-hours, bandwidth units, or another reviewed commercial unit.
The contract rate and usage export must use the same unit.

### Contract rate CSV

CloudRecovery reuses the common recurring-service contract schema:

- `Counterparty`
- `Service_ID`
- `Effective_From`
- `Effective_To`
- `Fixed_Fee`
- `Included_Units`
- `Unit_Rate`

Expected amount:

`fixed fee + max(independent usage - included usage, 0) * unit rate`

### Invoice charge CSV

- `Charge_ID`
- `Counterparty`
- `Account_ID`
- `Service_ID`
- `Service_Date`
- `Actual_Amount`

### Raw cloud meter CSV

Instead of a pre-aggregated generic usage file, CloudRecovery can aggregate:

- `Charge_ID`
- `Meter_Record_ID`
- `Usage_Units`

Duplicate Meter_Record_ID values within one Charge_ID fail closed so replayed
meter records cannot inflate expected usage.

### Cloud Scan 360 config

```json
{
  "cloud": {
    "charges_csv": "cloud_charges.csv",
    "rates_csv": "cloud_rates.csv",
    "meter_csv": "cloud_meter.csv",
    "charge_source_verified": true,
    "rate_source_verified": true,
    "meter_source_verified": true
  }
}
```

A generic `usage_csv` plus `usage_source_verified` may be used instead of
`meter_csv`. The two quantity inputs are mutually exclusive.

### Cletrics evidence bundle

CloudRecovery also accepts a hash-bound Cletrics evidence bundle as an alternative to charges_csv plus meter_csv/usage_csv:

```json
{
  "cloud": {
    "cletrics_bundle": "cletrics-export.zip",
    "rates_csv": "reviewed-cloud-rates.csv",
    "charge_source_verified": true,
    "meter_source_verified": true,
    "rate_source_verified": true
  }
}
```

The bundle imports only provider billing rows and independent meter quantities. Contract rates continue to come from the separately reviewed rates_csv authority path. Bundle integrity/provenance never self-verifies evidence: charge_source_verified and meter_source_verified remain explicit RecoveryOS inputs and default false.

See `recoveryworks/CLETRICS_INTEGRATION.md` for the frozen phase-1 bundle contract.

CloudRecovery does not attempt to reconstruct public on-demand pricing,
reserved-instance optimization, commitment utilization, tax, credits, or
provider-specific discount programs unless those commercial terms have first
been normalized into a reviewed effective contract rate.

## MerchantFeeRecovery

MerchantFeeRecovery intentionally audits only **processor-controlled commercial
fees**.

In-scope primitives:

- fixed/monthly processor fee
- processor markup in basis points against independent gross sales volume
- processor per-transaction fee

Explicitly outside this first calculation surface:

- interchange
- card-network assessments
- taxes
- chargeback losses
- pass-through third-party charges
- any fee whose commercial classification has not been reviewed

This boundary prevents a blended processing statement from being treated as
though every dollar were contract-controlled processor markup.

### Merchant agreement CSV

- `Processor`
- `Fee_Plan_ID`
- `Effective_From`
- `Effective_To`
- `Fixed_Fee`
- `Markup_BPS`
- `Per_Transaction_Fee`

Expected processor-controlled fee:

`fixed fee + gross sales * markup bps / 10,000 + transaction count * per-tx fee`

All percentage math uses integer basis points and integer cents with explicit
half-up rounding.

### Reviewed processor-fee statement CSV

- `Statement_ID`
- `Processor`
- `Account_ID`
- `Fee_Plan_ID`
- `Statement_Date`
- `Processor_Controlled_Fees`
- `Scope_Reviewer_ID`

When `statement_source_verified=true`, `Scope_Reviewer_ID` is mandatory.
This reviewer is attesting that `Processor_Controlled_Fees` excludes
interchange/network/tax/pass-through amounts from the recovery calculation.

### Independent transaction summary CSV

- `Statement_ID`
- `Gross_Sales`
- `Transaction_Count`

Variable markup/per-transaction agreements require this independent quantity
evidence. A fixed-only commercial fee can be audited without a transaction
summary.

### Merchant Fee Scan 360 config

```json
{
  "merchant_fee": {
    "statements_csv": "merchant_statements.csv",
    "agreements_csv": "merchant_agreements.csv",
    "transactions_csv": "merchant_transactions.csv",
    "statement_source_verified": true,
    "agreement_source_verified": true,
    "transaction_source_verified": true
  }
}
```

## Failure modes

CloudRecovery inherits common recurring-contract exceptions including:

- `DUPLICATE_CHARGE_ID`
- `NO_CONTRACT_RATE`
- `OVERLAPPING_CONTRACT_RATES`
- `MISSING_USAGE`
- `CONFLICTING_USAGE_RECORDS`

MerchantFeeRecovery surfaces:

- `DUPLICATE_STATEMENT_ID`
- `NO_FEE_AGREEMENT`
- `OVERLAPPING_FEE_AGREEMENTS`
- `MISSING_TRANSACTION_SUMMARY`
- `CONFLICTING_TRANSACTION_SUMMARIES`

Exceptions do not create validated recovery dollars.

## External-action boundary

Neither branch sends disputes, refund requests, processor notices, or provider
communications.

The common RecoveryWorks lifecycle remains:

1. ingest and hash source records
2. calculate expected vs actual deterministically
3. separate REVIEW from VALIDATED dollars
4. human reviewer approval
5. explicit customer authorization
6. external recovery action
7. outcome and fee recording


### Cletrics signal plane

Optional anomaly_signals and reconciliation_signals bundle roles are returned by Scan 360 as cloud_signals. They do not enter the Recovery Ledger and cannot increase potential, validated, authorized, claimed, recovered, or fee totals.

### Contract discount recovery

The cloud_discount Scan 360 section combines Cletrics invoice/meter evidence with separately reviewed base rates and discount authority. Missing or overlapping discount authority fails closed.

### Commitment benefit recovery

The cloud_commitment Scan 360 section requires separately reviewed commitment terms and a per-charge allocation file. It detects a missed benefit only on units proven allocated to the charge. Unused commitments, coverage gaps, utilization, recommendations, and Monte Carlo savings remain outside recovery math.
