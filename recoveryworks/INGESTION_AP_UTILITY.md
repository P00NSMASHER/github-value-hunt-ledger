# APRecovery and UtilityRecovery ingestion contract

These adapters are deterministic ingestion paths for Recovery Scan 360. They do
not send claims, contact counterparties, approve findings, or authorize recovery
actions.

Every source file is SHA-256 hashed. Evidence and rules retain row/object
locators so a finding can be traced back to the exact supplied source.

## APRecovery

### Payments CSV

Default columns:

| Logical field | Column |
|---|---|
| payment ID | `Payment_Number` |
| vendor | `Vendor` |
| invoice | `Invoice_Number` |
| amount | `Amount` |
| payment date | `Payment_Date` |

Amounts must be positive. Payment dates, when present, must be ISO `YYYY-MM-DD`.

Duplicate `Payment_Number` values are excluded from recovery math and emitted
as `DUPLICATE_PAYMENT_ID` exceptions. This prevents a duplicated export row
from manufacturing a false overpayment.

### Obligations / invoice CSV

Default columns:

| Logical field | Column |
|---|---|
| vendor | `Vendor` |
| invoice | `Invoice_Number` |
| expected invoice amount | `Amount` |
| invoice/effective date | `Invoice_Date` |

If `Invoice_Date` is blank, Scan 360 requires `default_effective_from`.

A verified obligation plus verified payment records can support a validated
`AP_OBLIGATION_OVERPAYMENT` finding.

### Vendor statement CSV

Default columns:

| Logical field | Column |
|---|---|
| vendor | `Vendor` |
| invoice | `Invoice_Number` |
| statement balance | `Balance` |
| statement date | `Statement_Date` |

Statement balances are signed. Credits can be represented as `-100.00` or
`(100.00)`.

A negative verified invoice-level statement balance can support
`VENDOR_STATEMENT_CREDIT`. A matching credit can also promote an exact
duplicate-payment cluster from REVIEW to validated evidence.

If a statement conflicts with ledger math, the adapter fails closed:

- `STATEMENT_CONTRADICTS_OVERPAYMENT`
- `STATEMENT_CREDIT_MISMATCH`
- `CONFLICTING_VENDOR_STATEMENT_LINES`

Conflicting candidates do not get silently promoted to validated recovery.

### Scan 360 AP config

```json
{
  "ap": {
    "payments_csv": "Payments.csv",
    "obligations_csv": "AP_Invoices.csv",
    "vendor_statements_csv": "Vendor_Statement.csv",
    "default_effective_from": "2026-01-01",
    "default_statement_date": "2026-08-31",
    "payment_source_verified": true,
    "obligation_source_verified": true,
    "vendor_statement_source_verified": true
  }
}
```

Verification flags must be actual booleans. They represent an explicit
source-verification decision; hashing a file does not by itself mark it verified.

## UtilityRecovery

### Bills CSV

Required default columns:

- `Bill_ID`
- `Utility`
- `Account_ID`
- `Service_Class`
- `Bill_Date`
- `Bill_Amount`

Quantity columns are required only when the selected tariff uses them:

- `Billed_kWh`
- `Billed_Demand_kW`
- `Billed_rkVA`
- `Days_Used`

Time-of-use quantities are discovered from columns beginning with
`Billed_kWh_`. Examples:

- `Billed_kWh_On_Peak` -> period `ON_PEAK`
- `Billed_kWh_Off_Peak` -> period `OFF_PEAK`

If a selected tariff references a quantity that is missing from the bill, the
bill is not approximated with zero. It produces
`MISSING_OR_INVALID_BILL_QUANTITY` and no recovery finding.

### Tariff JSON

Tariff definitions must be a list or `{"tariffs": [...]}`.

Each tariff requires a service class and `logic_steps`. Effective dates can be
provided per tariff; otherwise `default_effective_from` is used.

Supported deterministic charge types:

#### Fixed monthly/customer charge

```json
{"step_name":"Customer","charge_type":"fixed_fee","value":5.00}
```

#### Daily charge

```json
{"step_name":"Daily","charge_type":"daily_fixed_fee","value":0.50}
```

Requires `Days_Used`.

#### Flat energy charge

```json
{"step_name":"Energy","charge_type":"per_kwh","value":0.10}
```

#### Tiered energy

```json
{
  "step_name": "Energy",
  "charge_type": "tiered_kwh",
  "tiers": [
    {"up_to_kwh": 1000, "rate": 0.10},
    {"up_to_kwh": null, "rate": 0.20}
  ]
}
```

Thresholds are cumulative, strictly increasing, and the final tier must be
open-ended.

#### Time-of-use energy

```json
{"step_name":"Peak","charge_type":"tou_kwh","period":"on_peak","value":0.20}
```

Requires the corresponding `Billed_kWh_On_Peak` bill quantity.

#### Demand

```json
{"step_name":"Demand","charge_type":"per_kw","value":5.00}
```

#### Reactive demand

```json
{"step_name":"Reactive","charge_type":"per_rkva","value":1.50}
```

#### Minimum bill

```json
{"step_name":"Minimum","charge_type":"minimum_bill","value":50.00}
```

### Unsupported tariff logic

The adapter deliberately rejects:

- Python formulas
- free-form formulas
- executable conditions
- unknown charge types
- malformed/non-open-ended tier schedules

It does not use `eval`.

If no effective tariff covers a bill, or overlapping versions both cover it,
the bill is returned as an exception rather than rated using a guess.

### Scan 360 Utility config

```json
{
  "utility": {
    "bills_csv": "Bills.csv",
    "tariffs_json": "tariffs.json",
    "utility_id": "Utility A",
    "default_effective_from": "2026-01-01",
    "bill_source_verified": true,
    "tariff_source_verified": true,
    "jurisdiction": "PA"
  }
}
```

## Recovery state

Ingestion only detects and records candidates. Existing RecoveryWorks controls
still apply:

1. source/rule verification
2. human reviewer approval
3. explicit customer authorization
4. claim/action execution
5. outcome/recovery recording

No ingestion flag is permission to contact a vendor, utility, payer, carrier, or
other counterparty.
