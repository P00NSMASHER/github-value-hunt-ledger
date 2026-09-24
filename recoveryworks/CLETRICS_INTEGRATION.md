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

## Phase 3: continuous ingestion, savings, and remediation

### Continuous processing receipts

Use recoveryworks.integrations.cletrics_continuous.run_continuous_cletrics_scan with a private registry_path. The receipt fingerprint binds:

- Cletrics bundle and manifest SHA-256;
- processing mode (cloud, cloud_discount, or cloud_commitment);
- reviewed authority-file hashes;
- verification flags;
- client and currency scope.

An exact repeat is omitted from financial reprocessing. A changed bundle, rate, discount, commitment, allocation, or verification flag produces a new fingerprint. If that fingerprint targets a cloud billing scope already processed for the same provider/account/period/mode, continuous ingestion returns supersession_required instead of silently creating a second finding. The private receipt registry is independently hash-verified and does not modify Recovery Ledger history.

### Separate financial surfaces

Scan 360 now emits financial_surfaces.recovery and financial_surfaces.savings.

Recovery is the existing proof-bound RecoveryOS ledger. Savings only sums explicit savings_signals rows. Anomaly estimated exposure and reconciliation drift remain separate diagnostics and are never included in estimated savings.

Savings signal normalized columns:

    Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,Region,
    Savings_Category,Estimated_Savings,Confidence,Recommendation,Remediation_Action

realized_savings_cents remains zero in this integration because realized savings require a separate before/after evidence model that is not inferred from recommendations.

### Governed remediation

cloud_remediation.enabled=true creates a DRAFT plan from explicit savings opportunities that contain both Recommendation and Remediation_Action. RecoveryOS does not execute provider changes.

approve_cloud_remediation_plan requires both a reviewer_id and customer_authorization_id and binds the exact plan/action IDs. prepare_cloud_remediation_envelopes produces immutable envelopes whose execution_status is NOT_EXECUTED.

cloud_remediation.execute=true fails closed. Provider mutation belongs in a separately authorized downstream control plane.

### Remaining explicit boundaries

Phase 3 is intentionally not a cloud-change executor. Same-period changed authority or bundle scope is surfaced for explicit supersession review rather than replacing a live RecoveryOS case. Combined discount-plus-commitment pricing is not inferred. Realized savings remains zero until a separate before/after evidence model exists. Provider mutations require a separately authorized downstream control plane.

## Operational Cletrics FOCUS exporter

`recoveryworks.integrations.cletrics_exporter` now creates the frozen evidence
bundle directly from Cletrics-shaped operational exports. The billed-cost side
is a FOCUS Cost and Usage CSV (`ProviderName`, `BillingAccountId`,
`ServiceName`, `ChargePeriodStart`, `BilledCost`, `BillingCurrency`).
Independent quantity evidence remains a separate meter CSV and is never
silently sourced from the same billing row.

Meter rows may bind by explicit `Charge_ID`, by `FOCUS_Row_Hash`, or by the
unique resource/service/date natural key. Ambiguous natural-key joins fail
closed. Optional anomaly, reconciliation, and savings exports are validated and
carried into their existing non-money signal roles.

The CLI entry point is:

`python -m recoveryworks.integrations.cletrics_exporter --focus ... --meter ... --output ... --client-id ... --cletrics-release ... --cletrics-commit ... --exported-at ... --period-start ... --period-end ...`

The ZIP writer uses deterministic entry metadata so identical source bytes and
manifest inputs produce identical bundle bytes.

## AWS end-to-end rehearsal

`recoveryworks.cletrics_aws_rehearsal.run_aws_cletrics_rehearsal()` now
exercises the complete read-only AWS-shaped path using synthetic FOCUS billing,
independent meter evidence, reviewed rate authority, discount authority,
commitment authority/allocation, anomalies, reconciliation drift, and explicit
savings opportunities.

The rehearsal deliberately proves three independent recovery theories:

- base contracted-rate mismatch: 1000 validated cents;
- contractual variable-discount omission: 1200 validated cents;
- commitment-benefit omission: 1600 validated cents.

A second AWS service with no reviewed contract authority produces
`NO_CONTRACT_RATE` and no recovery case. Two savings recommendations, two
anomalies, and reconciliation drift remain on the non-money financial surface.
The acceptance function raises rather than returning success if any signal
estimate leaks into RecoveryOS validated dollars.

## Supersession candidate boundary (step 3a)

Continuous ingestion now materializes a hash-bound
`CloudSupersessionCandidate` whenever a same-provider/account/period/mode
scope has already been processed and the bundle, manifest, reviewed authority,
or verification flags change.

The candidate binds the prior receipt and proposed processing fingerprint and
records explicit reason codes: `BUNDLE_CHANGED`, `MANIFEST_CHANGED`,
`AUTHORITY_CHANGED`, and/or `VERIFICATION_CHANGED`. Its review state is
`REVIEW_REQUIRED` and it explicitly carries `ledger_mutation_allowed=false`.

This is intentionally only the first half of the supersession workflow. No
candidate can yet reject the incumbent finding, admit a replacement finding,
or change report counting. Those review/ledger transitions remain behind the
next approval gate.

## Reviewed supersession workflow (step 3b)

Supersession now preserves historical proof instead of deleting old findings.
A reviewer approves a hash-bound set of per-charge bindings. Each binding may
represent incumbent -> replacement, incumbent -> no-longer-recoverable, or
newly-recoverable -> replacement-only.

Only REVIEW and VALIDATED incumbents are eligible. AUTHORIZED, CLAIMED, and
RECOVERED cases fail closed and require a separate case-management process.
Approved incumbents transition to SUPERSEDED with the exact approval hash and
optional replacement finding id. Recovery Scan 360 excludes SUPERSEDED amounts
from active potential/validated totals while retaining superseded_cents and the
historical case record.

### Supersession apply semantics

`prepare_cloud_supersession_preview` recalculates the proposed job in an
isolated temporary ledger and compares active cloud references in the exact
provider/account/period scope. Review bindings support replacement, retirement
with no replacement, and newly recoverable findings.

`approve_cloud_supersession_preview` binds the candidate, every before/after
finding proof, reviewer, note, and approval time. Only REVIEW/VALIDATED
incumbents are eligible.

`apply_cloud_supersession` rechecks the live incumbent proofs/states, records
SUPERSEDE events in the durable journal, admits exact approved replacement
findings, CAS-saves the ledger, and replaces the old continuous-processing
receipt with the approved proposed fingerprint.

## Verified realized-savings evidence (step 4)

Prospective savings and realized savings are now separate proof surfaces.
`measure_realized_cloud_savings` requires:

1. the exact SAVINGS_OPPORTUNITY signal;
2. its exact remediation action and plan;
3. plan approval containing that action;
4. the exact NOT_EXECUTED authorization envelope;
5. independent evidence that the approved change was actually implemented;
6. a verified pre-change cost baseline;
7. a verified post-change cost observation; and
8. a reviewed normalization method.

Two normalization modes are supported. `FIXED_SCOPE` requires a reviewer to
attest the comparison scope is unchanged. `ACTIVITY_RATIO` normalizes
baseline cost by comparable workload units. Baseline and post windows must
have equal duration and must fall before/after implementation respectively.

A measurement may calculate an indicative delta while remaining REVIEW, but
only VERIFIED measurements roll into `realized_savings_cents`.

## Pilot deployment dry-run contract (step 5a)

The first half of the pilot deployment is now executable as a validation-only
CLI:

`python -m recoveryworks.pilot_deployment --spec pilot.json --base-dir . --dry-run`

The contract currently targets the first AWS pilot and hard-fails unless cloud
access is declared READ_ONLY, RecoveryOS has no provider write credentials,
remediation execution is disabled, external actions are disabled, and private
state is required. All referenced input files must exist before a plan is
produced.

The dry-run emits deterministic argv for the Cletrics FOCUS exporter and the
future pilot runner plus private bundle/ledger/receipt/report paths. It does not
start containers, provision infrastructure, contact AWS, run external recovery
actions, or mutate cloud resources. Those execution/startup pieces are the
remaining half of step 5 and stay behind the next approval gate.

## Local one-command pilot launcher (step 5b)

The local pilot is now runnable with one command:

`python -m recoveryworks.pilot_runner --spec pilot.json --base-dir .`

The launcher revalidates the step-5a deployment contract, exports the Cletrics
FOCUS + independent-meter bundle, re-seals that ZIP under verified private
permissions, runs continuous RecoveryOS ingestion, and writes private ledger,
receipt-registry, and report JSON files.

Verification remains explicit in `recoveryos.verification`; the launcher never
promotes rates, invoice rows, or meter rows to verified simply because the
pipeline ran. It also forces cloud remediation disabled and performs no AWS API
calls, provisioning, external recovery actions, or cloud mutations.

## Customer-facing Cloud Assurance report (step 6)

The pilot now emits private JSON and Markdown Cloud Recovery & Savings Assurance reports. The report keeps five surfaces separate: recoverable cash, prospective savings, verified realized savings, anomaly exposure, and reconciliation drift.

Every active VALIDATED cloud recovery has an evidence packet containing the exact expected-vs-actual calculation, finding proof hash, controlling rule id/hash/source locator/effective dates, every load-bearing evidence hash and locator, verification flags, calculation metadata, and current lifecycle state. SUPERSEDED and REJECTED findings remain historical but are not emitted as active validated recovery packets.

The report itself never authorizes cloud mutation or external recovery action.
