# Recovery Scan 360 runner

The runner is the first operational surface for the RecoveryWorks umbrella. It
combines supported branch adapters into one proof-bound, durable client ledger.

Current executable branches:

- FreightRecovery
- APRecovery
- PayerRecovery
- UtilityRecovery

## Run

```bash
python -m recoveryworks.cli \
  --config /private/client-scan.json \
  --state /private/recoveryworks-state.json \
  --report /private/recoveryworks-report.json
```

The state and report files are atomically written with mode `0600`. Operational
state must live on private storage, not in the public repository.

## Example config

```json
{
  "client_id": "client-001",
  "currency": "USD",
  "freight": {
    "truth_manifest_json": "truth-manifest.json"
  },
  "ap": {
    "payments_csv": "Payments.csv",
    "obligations_csv": "AP_Invoices.csv",
    "default_effective_from": "2026-01-01",
    "payment_source_verified": false,
    "obligation_source_verified": false
  },
  "payer": {
    "lines_csv": "payer_lines.csv",
    "rates_csv": "payer_rates.csv",
    "default_effective_from": "2026-01-01",
    "line_source_verified": false,
    "rate_source_verified": false,
    "jurisdiction": "US"
  },
  "utility": [
    {
      "bills_csv": "Bills.csv",
      "tariffs_json": "utility-a-tariffs.json",
      "utility_id": "Utility A",
      "default_effective_from": "2026-01-01",
      "bill_source_verified": false,
      "tariff_source_verified": false,
      "jurisdiction": "NY"
    }
  ]
}
```

Paths are resolved relative to the config file.

Verification booleans default to false and must be JSON booleans. Marking a
source verified means the operating workflow has independently established that
the file/source is the relevant, authentic source. Merely receiving or hashing a
file does not make its contents verified.

## Freight input

FreightRecovery is imported from its existing proof artifacts; Scan 360 does not
recompute freight pricing. Each freight job must provide exactly one of:

- `truth_manifest_json` — an existing FreightRecovery `truth-manifest.json`; or
- `audit_bundle_zip` — a FreightRecovery `AUDIT_RESULT` bundle.

The importer verifies individual finding proof hashes and the truth-manifest hash.
For audit bundles it also verifies the bundle manifest hash and size for
`truth-manifest.json`. The freight buyer ID and currency must match the Scan 360
client scope.

## AP input

Default payment headers:

- `Payment_Number`
- `Vendor`
- `Invoice_Number`
- `Amount`
- `Payment_Date`

Default obligation headers:

- `Vendor`
- `Invoice_Number`
- `Amount`
- `Invoice_Date`

Repeated payment export lines are deduplicated per vendor + normalized invoice +
payment ID. A single ACH/check number may legitimately span several invoices.
Conflicting repeated lines are quarantined as exceptions. Duplicate-looking
payments without a verified obligation or corroborating vendor-statement credit
remain REVIEW.

## Payer input

Payer inputs must already be de-identified and use a claim surrogate ID. The
common-ledger CSV loader rejects direct identifier headers such as patient name,
member ID, patient ID, DOB/date of birth, SSN, and subscriber ID.

Default remittance-line headers:

- `Line_ID`
- `Claim_Surrogate_ID`
- `Payer`
- `Service_Date`
- `Billed_Procedure`
- `Paid_Procedure`
- `Units`
- `Paid_Amount`
- `Modifier`
- `Place_Of_Service`

Default rate headers:

- `Payer`
- `Procedure_Code`
- `Allowed_Amount_Per_Unit`
- `Effective_From`
- `Effective_To`
- `Modifier`
- `Place_Of_Service`

Missing or ambiguous effective rates are reported as exceptions and do not
produce recoverable dollars.

## Utility input

Default bill headers:

- `Bill_ID`
- `Utility`
- `Account_ID`
- `Service_Class`
- `Bill_Date`
- `Bill_Amount`
- `Billed_kWh`
- `Billed_Demand_kW`
- `Billed_rkVA`
- `Days_Used`
- optional `Service_Start` + `Service_End`

Time-of-use quantities use `Billed_kWh_<Period>` columns such as
`Billed_kWh_On_Peak`.

When both service-period columns are supplied, they control tariff-version
selection. Bill date is only the fallback when service dates are unavailable.
A service period that crosses a tariff change is returned as an exception rather
than priced under one version.

The tariff importer supports explicit deterministic `logic_steps` for:

- `fixed_fee`
- `daily_fixed_fee`
- `per_kwh` / `energy_charge`
- `tiered_kwh` with strictly increasing cumulative tiers and a final open tier
- `tou_kwh` with an explicit period
- `per_kw` / `demand_charge`
- `per_rkva` / `reactive_demand_fee`
- `minimum_charge` / `minimum_bill`

It deliberately rejects executable conditions, Python/free-form formulas,
unknown charge types, malformed tiers, and ambiguous unsupported structures.

## Lifecycle boundary

A Scan 360 run may discover and validate findings. It does not:

- approve findings;
- authorize recovery activity;
- contact a counterparty;
- submit a claim, appeal, dispute, or demand;
- mark a case recovered.

Those remain separate human-controlled RecoveryLedger transitions.
