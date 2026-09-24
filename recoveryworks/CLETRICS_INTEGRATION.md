# Cletrics -> RecoveryOS Phase 1 integration

## Scope

This integration keeps Cletrics upstream of RecoveryOS. Cletrics collects and normalizes cloud billing/meter data; CloudRecovery performs deterministic contract-backed expected-vs-actual math; RecoveryOS remains the only money-bearing proof and lifecycle authority.

Phase 1 implements the first six integration steps:

1. Freeze the Cletrics evidence-bundle schema.
2. Load the bundle with ZIP, file-set, SHA-256, size, identity, and provenance checks.
3. Map normalized provider billing rows to the existing InvoiceCharge model.
4. Map independent meter rows to the existing UsageRecord model with duplicate-meter fail-closed behavior.
5. Continue loading reviewed contract pricing only through the existing rates_csv -> ContractRate path.
6. Feed the imported objects unchanged through audit_cloud_billing() and RecoveryEngine.

## Trust boundary

The bundle never contains a field that can mark RecoveryOS evidence verified. Scan 360 supplies charge_source_verified and meter_source_verified separately. Both default to false. A valid Cletrics ZIP therefore proves artifact integrity and lineage, not commercial authority.

Cletrics pricing estimates, anomaly scores, savings estimates, recommendations, and inferred prices are not controlling contract authority in Phase 1.

## Bundle schema

The ZIP contains exactly manifest.json plus the files declared by manifest entries. Every non-directory file must be declared; unmanifested files fail closed.

Required manifest fields:

    schema: 1
    bundle_type: CLETRICS_RECOVERYOS_CLOUD_EVIDENCE
    client_id
    provider
    billing_account_id
    currency
    period_start
    period_end
    exported_at
    cletrics.release
    cletrics.commit and/or cletrics.image_digest
    entries[]

Each entry contains:

    role
    path
    sha256
    size_bytes
    transformation_id (optional)
    source.kind
    source.locator
    source.sha256
    source.acquired_at

Required roles are invoice_charges and meter_usage.

### invoice_charges CSV

Required columns:

    Charge_ID
    Counterparty
    Account_ID
    Service_ID
    Service_Date
    Actual_Amount

Charge_ID should be an immutable provider billing-line identity. Additional Cletrics/provider columns are retained as provider_fields metadata but do not participate in money math.

### meter_usage CSV

Required columns:

    Charge_ID
    Meter_Record_ID
    Usage_Units

Rows are aggregated by Charge_ID. Duplicate (Charge_ID, Meter_Record_ID) pairs fail closed so replayed meter records cannot inflate expected usage.

## Scan 360

Existing CSV mode remains supported. Cletrics mode replaces charges_csv plus meter_csv/usage_csv, while rates_csv remains mandatory and separately reviewed:

    {
      "client_id": "client-1",
      "currency": "USD",
      "cloud": {
        "cletrics_bundle": "cletrics-export.zip",
        "rates_csv": "reviewed-cloud-rates.csv",
        "charge_source_verified": true,
        "meter_source_verified": true,
        "rate_source_verified": true
      }
    }

The manifest client_id and currency must exactly match the surrounding Scan 360 job.

## Deliberately deferred

CloudSignal/anomaly ingestion, contract-discount authority, commitment allocation, continuous bundle ingestion, separate recovery-vs-savings dashboards, and remediation remain later phases. None is silently approximated here.


## Phase 2: signals, discounts, and commitments

Phase 2 adds steps 7-12 without weakening the Phase-1 proof boundary.

### Non-money signal roles

Two optional manifest roles are supported: anomaly_signals and reconciliation_signals.

Anomaly normalized columns:

    Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,Region,
    Severity,Detection_Method,Metric_Name,Z_Score,Baseline_Value,Actual_Value,
    Estimated_Cost_Impact,Confidence

Reconciliation normalized columns:

    Signal_ID,Detected_At,Provider,Account_ID,Service_ID,SKU_Key,
    Estimated_Cost,Actual_Cost,Error_Pct,Drift_Direction

These rows become immutable CloudSignal objects. estimated_impact_cents is explicitly non-authoritative. CloudSignal has no conversion path to RecoveryObservation, and Scan 360 returns signals separately from Recovery Ledger/report totals.

### Reviewed contract discount mode

The cloud_discount Scan 360 section requires a Cletrics bundle, reviewed base rates, and reviewed discount authority.

Discount authority CSV columns:

    Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,
    Discount_BPS,Applies_To

Applies_To is VARIABLE or ALL. A validated discount finding requires the base rate, discount authority, invoice, and load-bearing usage to be verified. Missing or overlapping authority fails closed.

### Reviewed commitment-benefit mode

The cloud_commitment Scan 360 section requires a Cletrics bundle, reviewed base/on-demand rates, reviewed commitment rates, and independently reviewed per-charge allocations.

Commitment authority CSV:

    Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,
    Commitment_Type,Committed_Unit_Rate

Allocation CSV:

    Charge_ID,Allocation_ID,Entitled_Units

Only min(billable units, independently evidenced entitled units) receives the committed rate. Unused entitlement is recorded as context and is never counted as recoverable money. A committed rate above the reviewed base rate fails closed.
