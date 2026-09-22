# SaaSRecovery and TelecomRecovery ingestion contract

These branches use the shared deterministic recurring contract-billing engine.
They compare actual invoice charges to an effective-dated contract rate and,
when pricing is quantity based, an independent quantity source.

No invoice quantity is trusted merely because it appears on the invoice.

## Shared rate CSV

Default columns:

| Field | Column |
|---|---|
| counterparty/vendor/carrier | `Counterparty` |
| service/SKU/plan | `Service_ID` |
| effective start | `Effective_From` |
| effective end | `Effective_To` |
| fixed recurring fee | `Fixed_Fee` |
| included units | `Included_Units` |
| unit/overage rate | `Unit_Rate` |

At least one of fixed fee or unit rate must be non-zero. Effective date ranges
must not overlap for the same counterparty + service at the charge date.

Expected amount:

`fixed fee + max(independent units - included units, 0) * unit rate`

All calculations use Decimal arithmetic and integer cents/micros.

## Shared invoice-charge CSV

Default columns:

- `Charge_ID`
- `Counterparty`
- `Account_ID`
- `Service_ID`
- `Service_Date`
- `Actual_Amount`

Duplicate `Charge_ID` values are all excluded from recovery math.

## Generic quantity CSV

If the customer already has an independently generated usage/licensing
aggregation:

| Field | Column |
|---|---|
| invoice charge | `Charge_ID` |
| independent quantity | `Units` |

## SaaSRecovery

SaaSRecovery targets contracted subscription/seat billing leakage such as:

- charged seat counts exceeding independently verified billable seats
- invoice rates above the effective contract rate
- recurring platform fees above the contracted fixed fee
- incorrect included-seat thresholds

### Seat snapshot CSV

Instead of a pre-aggregated quantity file, Scan 360 can count a raw seat/license
snapshot:

- `Charge_ID`
- `Seat_ID`
- `Billable`

Accepted billable flags include true/false, yes/no, 1/0, active/inactive, and
billable/nonbillable.

Duplicate Seat_ID values inside the same Charge_ID fail closed.

### SaaS Scan 360 config

```json
{
  "saas": {
    "charges_csv": "saas_charges.csv",
    "rates_csv": "saas_rates.csv",
    "seat_snapshot_csv": "saas_seats.csv",
    "charge_source_verified": true,
    "rate_source_verified": true,
    "seat_source_verified": true
  }
}
```

Use `usage_csv` + `usage_source_verified` instead of `seat_snapshot_csv`
when the independent quantity is already aggregated. The two inputs are mutually
exclusive.

## TelecomRecovery

TelecomRecovery targets recurring-service and usage leakage such as:

- monthly recurring charges above contract
- usage charged above independently aggregated CDR quantities
- wrong included-minute/data/message allowance
- wrong per-unit overage rate

The first implementation is deliberately unit-agnostic: minutes, messages,
megabytes, gigabytes, events, or other contract units can all be used as long as
the contract rate and usage file use the same unit.

### Raw CDR usage CSV

Scan 360 can aggregate raw CDR-style usage:

- `Charge_ID`
- `CDR_ID`
- `Usage_Units`

Usage is summed by Charge_ID. Duplicate CDR_ID values within a Charge_ID fail
closed so replayed CDR rows cannot inflate expected usage.

### Telecom Scan 360 config

```json
{
  "telecom": {
    "charges_csv": "telecom_charges.csv",
    "rates_csv": "telecom_rates.csv",
    "cdr_csv": "cdr.csv",
    "charge_source_verified": true,
    "rate_source_verified": true,
    "cdr_source_verified": true
  }
}
```

Use `usage_csv` + `usage_source_verified` instead of `cdr_csv` when usage
is already independently aggregated.

## Failure modes

The shared engine produces explicit exceptions instead of guesses:

- `DUPLICATE_CHARGE_ID`
- `NO_CONTRACT_RATE`
- `OVERLAPPING_CONTRACT_RATES`
- `MISSING_USAGE`
- `CONFLICTING_USAGE_RECORDS`

An exception does not create validated recovery dollars.

## Verification and action controls

Each input has an explicit boolean source-verification flag. File hashing proves
what bytes were ingested; it does not itself mean the source was verified.

The normal RecoveryWorks lifecycle remains mandatory:

1. ingest
2. detect
3. verify evidence/rule
4. human review
5. explicit customer authorization
6. external recovery action
7. outcome recording

Neither SaaSRecovery nor TelecomRecovery contacts vendors/carriers or submits a
dispute automatically.
