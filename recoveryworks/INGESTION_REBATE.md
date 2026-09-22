# RebateRecovery ingestion contract

RebateRecovery finds supplier/customer rebate underpayments by reconstructing the
rebate earned from a versioned program and comparing it with settlement evidence.

It is an **underpayment** branch:

`potential recovery = expected rebate - actual rebate received`

## Required inputs

### Program JSON

The file can be a list or `{"programs": [...]}`.

Each program requires:

- `supplier_id`
- `program_id`
- `period_start` / `period_end`
- `tier_mode`
- `measurement_basis`
- `tiers`

There is deliberately **no default tier mode**.

Supported modes:

- `retroactive` — the rate reached by total period volume applies to the full
  qualifying spend.
- `incremental` — each portion of qualifying volume/spend is rebated at the
  rate of the tier band it occupies.

Supported measurement bases:

- `units`
- `spend` (currency dollars)

Tier bands must start at zero, be contiguous, and end with an open-ended final
tier.

Example:

```json
{
  "programs": [{
    "supplier_id": "Supplier A",
    "program_id": "2026-Q3",
    "period_start": "2026-07-01",
    "period_end": "2026-09-30",
    "tier_mode": "incremental",
    "measurement_basis": "units",
    "tiers": [
      {"min_measure": 0, "max_measure": 100, "rate_pct": 0},
      {"min_measure": 100, "max_measure": 200, "rate_pct": 5},
      {"min_measure": 200, "max_measure": null, "rate_pct": 10}
    ]
  }]
}
```

Rates may be supplied as integer `rate_bps` instead of `rate_pct`.
Percentage rates must resolve exactly to basis points.

## Purchase CSV

Default columns:

- `Purchase_ID`
- `Supplier`
- `Program_ID`
- `Purchase_Date`
- `Quantity`
- `Net_Spend`

The program ID is explicit: RecoveryWorks does not guess which rebate program
an invoice belongs to.

Duplicate purchase IDs block the affected program from recovery math.
Purchases outside the program period are surfaced as
`OUT_OF_PERIOD_PURCHASE` exceptions and are not included.

## Settlement CSV

Default columns:

- `Settlement_ID`
- `Supplier`
- `Program_ID`
- `Amount_Received`
- `Settlement_Date`

A settlement row with amount `0` is valid evidence that no cash/credit was
received. If no settlement evidence is supplied for a program,
RebateRecovery returns `NO_SETTLEMENT_EVIDENCE` instead of assuming zero.

Duplicate settlement IDs block the affected program.

## Calculation controls

### Retroactive

For the achieved tier:

`expected rebate = total qualifying spend * achieved tier rate`

### Incremental spend tiers

Qualifying spend is split across contiguous spend bands and each band is
multiplied by its own rebate rate.

### Incremental unit tiers

Purchase lines are ordered by purchase date and ID. Each line's spend is
allocated across unit bands at that line's unit price, then the rebate rate for
each band is applied.

A purchase with positive spend and zero quantity is rejected when unit-based
incremental math requires a unit price.

## Scan 360 config

```json
{
  "rebate": {
    "programs_json": "rebate_programs.json",
    "purchases_csv": "purchases.csv",
    "settlements_csv": "rebate_settlements.csv",
    "program_source_verified": true,
    "purchase_source_verified": true,
    "settlement_source_verified": true
  }
}
```

## Verification and action

All three evidence classes must be verified before a finding can become
VALIDATED:

- controlling rebate program/version
- qualifying purchase population
- settlement/remittance evidence

Detection is not permission to demand payment. Human review and explicit
customer authorization remain mandatory before any external recovery action.
