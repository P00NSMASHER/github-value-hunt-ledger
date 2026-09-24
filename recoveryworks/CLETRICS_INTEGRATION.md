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

## Remediation executor dry-run boundary (step 7a)

A separate provider-neutral executor boundary now validates the exact remediation plan, approval, NOT_EXECUTED envelope, verified read-only resource snapshot, expected resource state hash, allowlisted action type, and required action parameters.

The current allowlist defines contracts for resize_instance and remove_idle_resource. The output is a hash-bound DRY_RUN_VALIDATED plan containing no provider API operation, sets live_execution_allowed=false, and records mutation_performed=false. There is no AWS SDK, shell command, provider credential handling, or live mutation function in this half-step.

## Governed remediation handoff and receipt (step 7b)

The remediation boundary now supports a credential-free handoff to a named separate executor. The handoff binds the exact dry-run plan, remediation approval, customer authorization id, executor id, authorizer id, expected resource-state hash, issuance/expiry window, and mandatory pre-execution recheck. It embeds neither credentials nor provider operations.

Before a downstream executor can consume the handoff, a fresh independently verified resource snapshot must still match the dry-run state. Any drift requires a new review. After an external execution, RecoveryOS can verify a supplied execution receipt against the handoff/gate and a verified post-state snapshot. This repository still contains no provider mutation implementation.

## Authorized real-account diagnostic path (step 8)

A customer diagnostic can now be run locally from an explicit intake JSON and customer authorization artifact. Before creating any RecoveryOS state, the runner verifies authorization timing/purposes and preflights every FOCUS row against the authorized provider, billing account, currency, and service period. A mismatch or expired authorization fails before the private diagnostic directory is created.

The command is: python -m recoveryworks.cloud_diagnostic --intake diagnostic.json --base-dir . --run-at <UTC timestamp>. Authorization grants analysis scope only; it never promotes source verification, permits remediation, or permits external recovery actions. Real customer data is not bundled with the repository and must be supplied under authorization.

## Governed remediation handoff and receipt validation (step 7b)

RecoveryOS can now prepare a hash-bound handoff for a separately authorized executor, but it still contains no provider mutation implementation. The handoff requires a second explicit execution authorization that binds the customer authorization, exact dry-run proof, named executor, and expiration window. Immediately before handoff, a fresh independently verified resource snapshot must still match the dry-run resource state and satisfy a configurable maximum age.

Downstream execution receipts are accepted only when they bind the exact handoff, executor, action, before-state hash, execution window, and a verified post-state snapshot. APPLIED receipts must show a changed state and a provider request id; NOOP receipts must show unchanged state. This provides a receipt/proof protocol without giving RecoveryOS any cloud SDK or live mutation path.

## Commercial pilot package configuration (step 9a)

An internal configurable commercial package now defines the initial AWS pilot scope, deliverables, pricing hypotheses, exclusions, assumptions, and customer acceptance criteria. Recovery success fees are explicitly defined against verified recovered cash only; prospective savings and anomaly exposure are not recovery-fee bases.

The package is marked INTERNAL_PILOT_CONFIGURATION and hard-fails if cloud mutation or external recovery actions are put in scope. It also records that pricing is a hypothesis to test. This half-step creates no contract, invoice, outreach, payment request, customer acceptance, or external commitment.

## Authorized real-account diagnostic intake hardening (step 8)

The real-account runner now requires the customer authorization to bind the exact SHA-256 of every focus, meter, rate, and optional signal file before processing. A separate evidence-review object binds the exact money-bearing focus/meter/rate hashes plus the three verification flags. Customer permission to process therefore cannot promote unreviewed evidence to VALIDATED recovery.

After scope and hash checks, the authorized source bytes are copied into verified private snapshots and the pilot runs only from those snapshots. Changed bytes, symlinks, expired/unverified authorization, out-of-scope FOCUS rows, or evidence-review hash mismatches fail before the diagnostic ledger is created.

## Proposal and SOW draft bundle (step 9b)

The commercial package can now render private proposal/SOW-ready Markdown drafts plus a hash-bound manifest. Draft fee scenarios calculate configured diagnostic/success/assurance arithmetic but are explicitly marked as pricing hypotheses and not revenue forecasts.

The generated artifacts are deliberately nonbinding: they cannot be marked signed, accepted, invoiced, paid, or committed. A separately finalized agreement would still be required.

## Customer onboarding and intake readiness (step 10)

A customer onboarding validator now checks the diagnostic authorization, required FOCUS/meter/reviewed-rate files, required CSV columns, diagnostic period, and Cletrics exporter identity. Optional anomaly/reconciliation/savings files are tracked without blocking the base diagnostic.

When structurally ready, it emits a diagnostic request that materializes directly into the current step-8 CustomerDiagnosticAuthorization and DiagnosticEvidenceReview API. Processing authorization is bound to exact input hashes, while financial evidence verification remains a separate reviewer decision. Checklist and request outputs use private writes.

## Read-only pilot operations console (step 11a)

The first operations-console layer is a private read-only snapshot rather than an interactive control surface. It shows diagnostic status, active evidence readiness, supersession holds, recovery lifecycle totals, savings/diagnostic totals, and remediation-plan state.

All mutation controls are explicitly false: the console cannot approve findings, authorize recovery, execute remediation, mutate cloud infrastructure, or perform external actions. JSON and Markdown snapshots are written privately for operational review.

## Azure and GCP shared FOCUS proof contract (planned step 10)

The Cletrics FOCUS exporter, local pilot deployment contract, and authorized diagnostic boundary now accept AWS, Azure, and GCP. The pilot fails closed if the declared provider does not match the provider normalized from the FOCUS bundle.

Azure and GCP use the same RecoveryOS InvoiceCharge, UsageRecord, ContractRate, discount authority, commitment authority/allocation, verification flags, and expected-vs-actual arithmetic as AWS. Provider-specific rehearsals independently prove the base contracted-rate, reviewed discount, and commitment-benefit paths. Each rehearsal also includes an unsupported service that remains NO_CONTRACT_RATE and a savings signal that stays outside recovery dollars.

## Multi-cloud orchestration dry-run planner (planned step 11a)

A separate planning-only orchestrator now composes two or three AWS/Azure/GCP pilot deployment plans for one client and currency. It requires unique providers and deployment ids and rejects any shared evidence-bundle, ledger, receipt-registry, or report path.

The plan explicitly keeps provider isolation required, cross-provider authority reuse prohibited, shared ledgers/receipt registries prohibited, combined financial rollup disabled, and execution disabled. This half-step does not run the provider jobs or sum recovery/savings dollars across clouds; it only produces a private hash-bound JSON/Markdown orchestration plan.

### Provider identity and authority-isolation hardening

FOCUS provider identity is now canonicalized at the proof boundary: common Amazon Web Services aliases map to AWS, Microsoft/Microsoft Azure aliases map to Azure, and Google/Google Cloud Platform aliases map to GCP. The original FOCUS ProviderName is still preserved on invoice evidence for counterparty/rate matching; only the bundle/provider scope is canonicalized.

The multi-cloud planner now enforces its cross-provider authority-isolation claim in code: provider jobs cannot reuse the same FOCUS, meter, signal, rate, discount, commitment, or allocation input file. Separate provider outputs were already mandatory. This prevents a single reviewed authority file from being silently reused across cloud providers.

## Multi-cloud local execution with isolated truth planes (step 11b)

The multi-cloud orchestrator can now execute the validated AWS/Azure/GCP provider jobs locally through the existing one-command pilot runner. Each provider retains its own evidence bundle, ledger, receipt registry, state head, and assurance report proof hash.

The execution result deliberately contains no combined financial totals and performs no cloud mutation or external action. Provider assurance report hashes are verified after each run and become the only inputs allowed into the later executive-rollup layer.

## Proof-bound multi-cloud executive rollup (step 12)

A reviewed executive rollup can now be built only from the verified provider assurance reports emitted by step 11b. It verifies each report proof hash and required financial-boundary controls before reading summary values.

Only a fixed allowlist of same-currency, same-semantic cent categories is aggregated: recovery lifecycle dollars, prospective savings, verified realized savings, anomaly exposure, and reconciliation drift. Case counts, individual findings, rules, evidence packets, recommendations, confidence scores, and resource identities are never merged across providers. Every provider report proof hash and state head remains visible in the rollup.

## Production deployment packaging and preflight (step 13a)

Production packaging now has a hash-bound container/service contract, explicit config/input/state/report volume roles, health/readiness checks, and a Docker Compose batch manifest. The image must be pinned by sha256 digest and run as a numeric non-root user with read-only root filesystem, network disabled, all capabilities dropped, no-new-privileges enabled, and no provider-write/remediation/external-action capability.

Config and input mounts are read-only. State and report mounts must be separate private writable directories; readiness verifies them with private sentinels and revalidates the exact pilot spec and mounted source files. The generated Compose shape runs a preflight job before the pilot batch job and uses network_mode none. Step 13a does not build images, start containers, provision infrastructure, or contact external services.

## Reproducible production container and CI smoke (step 13b)

The production container definition is now pinned to a specific Python 3.12.14 slim-bookworm image digest. RecoveryWorks' current cloud runtime has no third-party Python runtime dependencies, so requirements.production.lock is intentionally empty except for comments; any future dependency requires an exact lock/build-manifest update.

ContainerBuildManifest binds the full Git commit, base-image digest, Dockerfile SHA-256, dependency-lock SHA-256, and runtime dependency list. RecoveryWorks CI now generates that manifest, builds the actual container, verifies the OCI source-revision label, and smoke-runs the image with network disabled, read-only root filesystem, all capabilities dropped, no-new-privileges, and only a tmpfs for /tmp. CI does not publish or deploy the image.

## Production observability and auditable run history (step 14)

Production observability now has structured hash-chained run events, a stable failure taxonomy, provider/job health metrics, recovery/savings/diagnostic metric snapshots, alert-ready records, immutable run manifests, and a private hash-chained run-history store.

Successful pilot observability verifies the assurance-report proof hash before recording it. Alerts are emitted for supersession review, recovery evidence review, and fail-closed scan exceptions; they do not mutate cases or infrastructure. The history store rejects duplicate run ids, sequence gaps, previous-hash breaks, entry tampering, and head-hash mismatches.

## Immutable release and promotion gates (step 15a)

Release control now binds the full source commit, source-build manifest proof, exact digest-pinned container image, and production-deployment proof into one immutable release candidate. A rollback manifest binds the candidate to a previous verified release/image/source commit.

Environment promotion gates require passing health/readiness checks for the exact deployment proof plus release approvals bound to the exact release/environment. Production requires two distinct approvers and a rollback manifest. The resulting gate is READY_FOR_SEPARATE_PROMOTION_ACTION but promotion_execution_enabled and deployment_performed remain false. Private release manifest, approval, rollback, and gate artifacts can be written for a later external promotion workflow.

### Production runtime closure

The reproducible container manifest now records the two source roots required by the current RecoveryWorks runtime: recoveryworks and freight. The production Dockerfile copies both roots, compiles both, and smoke-imports the pilot, deployment, observability, and release-control entrypoints. The container still has no third-party Python runtime dependencies beyond the digest-pinned Python base image.

## Governed release deployment handoff (step 15b)

A production-ready promotion gate can now be converted into a credential-free handoff for a named separate deployer. The handoff binds the exact release, promotion-gate proof, environment, digest-pinned image, source commit, deployment proof, deployer identity, and authorization window. RecoveryOS still cannot perform or claim the deployment itself.

A downstream deployment receipt is accepted only when it binds that exact handoff and proves the exact release/image/source/deployment proof within the authorization window. A separately verified post-deployment environment snapshot must confirm the same release plus passing health/readiness receipts. The result is DEPLOYMENT_VERIFIED, not an internal deployment action.

## Production backup/restore and DR rehearsal (step 16)

Production resilience now freezes four private state surfaces into one deterministic private backup archive: the RecoveryOS ledger, Cletrics receipt registry, assurance report, and tamper-evident production run history. The backup manifest binds every artifact hash/size, archive hash, source checkpoint, retention expiry, and configured RPO/RTO objectives.

A restore is not considered DR-valid after extraction alone. The rehearsal reloads the RecoveryOS bundle, verifies the Cletrics registry, re-verifies the assurance report proof hash, replays the production run-history chain, and enforces the configured RPO/RTO. Passing rehearsals emit a hash-bound DR_REHEARSAL_PASSED artifact; archive tampering, incomplete state, stale backups, or slow restores fail closed.

## Supply-chain and release security gate (step 17a)

Release security now has a deterministic component inventory/SBOM over the digest-pinned Python base image plus the exact RecoveryWorks and freight runtime source roots. Source-root components carry deterministic tree hashes and file counts and are bound to the exact release/source commit/build-manifest proof.

A container attestation-input artifact binds the release, image digest, source commit, build proof, and SBOM proof to a SLSA provenance predicate type while explicitly recording that signing and publication have not occurred. A separate external vulnerability-scan receipt contract binds the exact image digest, scanner/version, vulnerability-database identity/digest, scan time, severity counts, and verified source receipt.

The release security gate requires a verified scan for the exact image and enforces configured critical/high severity thresholds. Passing yields SECURITY_GATE_READY while signing_performed, attestation_published, and image_published remain false.

## External security evidence verification bridge (step 17b)

The internal RecoveryWorks component inventory can now be exported as deterministic CycloneDX 1.5 JSON bound to the exact release and SBOM proof. External signature-verification and provenance-verification receipts are modeled as separate verified artifacts and must bind the exact release proof, image digest, source commit, build-manifest proof, and SBOM proof.

The bridge also reuses the exact vulnerability-scan receipt from step 17a. A verified security-evidence bundle is produced only when the security gate, CycloneDX export, vulnerability scan, signature receipt, and SLSA provenance receipt all bind the same release. RecoveryOS does not perform signing, scanning, registry publication, or attestation publication itself.

## Unified production admission gate (step 18)

Production deployment now has a single admission choke point. The admission gate requires the exact PRODUCTION promotion gate, externally verified release-security evidence, a current passing DR rehearsal, and the exact container-build manifest bound to the release source commit and image digest.

A configurable DR-age limit prevents an old restore rehearsal from satisfying a new production admission. The gate itself cannot deploy anything. Release deployment handoffs now require the production-admission proof in addition to the promotion gate, preventing the older promotion-only path from bypassing security/DR/build controls.

## Governed incident detection and rollback handoff (step 19a)

Post-deployment incident assessment now requires a verified environment snapshot and detects health/readiness failures plus release, image, source-commit, and deployment-contract drift. A healthy snapshot that matches the expected release does not create an incident artifact.

Rollback uses the already-bound release rollback manifest and target release, then requires distinct approvals (two in production) before producing a credential-free handoff for a separate deployer. RecoveryOS contains no rollback executor. A downstream rollback receipt is accepted only when it binds the exact handoff/target and a verified healthy post-rollback environment snapshot confirms the target release/image/source/deployment proof. Passing yields ROLLBACK_VERIFIED.

## Incident lifecycle and post-incident review (step 19b)

Production incidents now have a private hash-chained lifecycle journal covering DETECTED, ACKNOWLEDGED, ESCALATED, rollback approval/handoff/verification, RECOVERY_CONFIRMED, CLOSED, and REVIEWED states. Invalid transitions, sequence gaps, previous-hash breaks, event tampering, and journal state-hash changes fail closed.

Closure evidence binds the original incident, verified rollback receipt, recovered environment snapshot proof, closing actor/time, and closure reason. A separate post-incident review records root cause, contributing factors, corrective/preventive actions, follow-up owner, and due date while explicitly not claiming that those actions have already been executed.

## Production launch/readiness dossier (step 20)

A single private launch/readiness dossier now binds the exact release, production admission, externally verified security evidence, passing DR rehearsal, successful production-style observability run, rollback readiness, and commercial pilot package. It presents separate CFO, CTO, security, and operations sections and preserves proof hashes for every upstream control plane.

The CFO section exposes pricing only as the existing internal hypothesis and success-fee basis of verified recovered cash. The dossier explicitly cannot claim a signed customer contract, verified customer revenue/traction, external production deployment, or guaranteed economics. JSON and Markdown outputs use private writes.

## Provider-neutral activation simulation (step 21a)

The external-environment activation boundary now has provider-neutral contracts for AWS, Azure, and GCP. A verified credential-scope attestation records only principal identity, account scope, and read/discovery permissions; credentials themselves cannot be embedded and mutation-capable permissions fail closed.

A separate verified environment-state discovery binds the current release/image and summarized environment state. The adapter supports only DISCOVER_STATE, VALIDATE_CREDENTIAL_SCOPE, and SIMULATE_DEPLOYMENT. It stores no credentials, exposes no mutation operation, and records no provider API call. Simulation compares the discovered state with the exact ProductionAdmissionGate/release and returns SIMULATION_ONLY with the proposed release/image transition; no external environment is changed.

## External activation handoff and receipt verification (step 21b)

A SIMULATION_ONLY activation can now be converted into a short-lived credential-free handoff for a named separate deployer, but only after a second fresh verified environment discovery proves the environment has not drifted since simulation. The handoff binds the exact simulation, release, ProductionAdmissionGate, credential-scope proof, provider/account/environment, current state, target image/source commit, deployer, and expiry window.

A downstream activation receipt is accepted only when it binds that exact handoff and a verified post-activation environment discovery proves the target release/image. RecoveryWorks still contains no provider deployment operation and stores no credentials; verified completion yields ACTIVATION_VERIFIED.

## Continuous production assurance/currentness (step 22)

A read-only continuous assurance evaluation now checks the admitted release against verified environment state, exact external security evidence and its age, DR rehearsal freshness, private-backup RPO/retention/freshness, tamper-evident run-history integrity/currentness, Cletrics processing-evidence freshness/verification, unresolved incident lifecycle state, and outstanding cloud supersession candidates.

Results are PASS, REVIEW_REQUIRED, or BLOCKED. Release/image drift, stale security/DR/backups/history/cloud evidence, or unresolved incidents block assurance. Unverified cloud evidence, closed-but-unreviewed incidents, and supersession candidates require review. The snapshot is alert-ready and can be written privately as JSON/Markdown, but automatic remediation and external actions remain disabled.

## Enterprise control/evidence map (step 23a)

Buyer diligence now has a machine-readable/private control map covering read-only access control, private state/backups, secure SDLC/release admission, software supply chain, DR/continuity, incident response, auditability/continuous assurance, deterministic financial integrity, and separation of authorization from external mutation.

Every internally evidenced control points to exact proof hashes plus explicit limitations. SOC 2 and ISO 27001 labels may appear only as questionnaire/reference mappings; the artifact hard-fails on certification claims and explicitly records third_party_audit_completed=false. It does not claim SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other certifications/attestations that have not actually been obtained.

## Customer-safe enterprise diligence package (step 23b)

The enterprise control map can now be packaged into questionnaire-ready customer-safe responses, an evidence-room proof index, and an explicit gap/remediation register with internal owner and due date. Customer exports redact internal actor identifiers and omit internal paths, source locators, and raw metadata while preserving proof hashes, control ids, evidence descriptions, and limitations.

The package includes a direct certification answer stating that no SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other third-party certification is claimed. Controls lacking event-specific or external validation evidence become explicit gaps rather than being silently represented as complete.

## Customer data governance controls (step 24)

Managed customer data now has a per-customer private data-space inventory with exact file hashes, classification, allowed purposes, collection time, retention deadline, and source kind. Raw credential/secret material is explicitly rejected. Paths cannot escape the customer root, and customer inventories cannot mix customers.

Purpose-limited access decisions are recorded in a private hash-chained access history, including denied attempts. Customer export creates a deterministic private archive and receipt. Logical deletion validates the exact file hash, retention/early-deletion authorization, and active legal holds before removing the managed file; deletion receipts explicitly state logical_deletion_only=true and never claim forensic secure wipe. Active legal holds override deletion.

## Provider connector readiness contracts (step 25a)

AWS, Azure, and GCP now have provider-neutral read-only connector contracts using verified credential references (workload identity, managed identity, role reference, or service-account impersonation) rather than persisted credentials. The contract exposes only DESCRIBE_IDENTITY, DISCOVER_BILLING_EXPORTS, and DISCOVER_RESOURCES and records live_calls_enabled=false, write_operations_enabled=false, and secret_persistence_enabled=false.

Provider discovery can be tested through exact request-bound verified replay fixtures for deterministic offline/replay validation. Replay results prove provider/account/operation scope and explicitly record provider_api_called=false and secrets_persisted=false. A stable connector error taxonomy covers RATE_LIMITED, AUTHORIZATION_FAILED, TIMEOUT, TRANSIENT_PROVIDER_ERROR, MALFORMED_RESPONSE, SCOPE_MISMATCH, and FIXTURE_MISS. No live AWS/Azure/GCP calls are implemented in this half-step.

## Separate-runner provider discovery handoff (step 25b)

Read-only provider discovery can now be handed to a named separate connector runner through a short-lived credential-free artifact that binds the exact connector contract, credential-reference proof, provider/account, request, operation, runner, and expiry window. RecoveryWorks itself still does not call AWS/Azure/GCP.

A returned discovery receipt is accepted only when it is externally verified, binds the exact handoff/request/runner, occurs inside the authorization window, carries a hash-bound response payload and provider request id, and explicitly records that no provider mutation or credential material was returned. Successful verification yields EXTERNAL_READONLY_DISCOVERY_VERIFIED.

## End-to-end tenant binding registry (step 26)

Managed pilot execution now derives a canonical tenant identity from tenant_id (defaulting to client_id), client_id, and the execution namespace. Before any private pilot artifact is written, a shared private tenant registry reserves the bundle, ledger, Cletrics receipt registry, assurance JSON, and assurance Markdown paths. A path already bound to another tenant fails before overwrite.

After execution, the ledger is checked for cross-client findings, the Cletrics registry for cross-client receipts, and the assurance report for exact client/proof integrity. Their semantic/file proofs are then tenant-bound; the same proof cannot be rebound to another tenant. The registry exposes the same binding API for backups, continuous-assurance snapshots, run-history/diligence artifacts, and customer exports so managed production workflows can fail closed on cross-customer path/proof reuse without changing every underlying artifact schema.

## Production job control and dry-run scheduling (step 27a)

Internal production work now has deterministic tenant-bound job schedules and occurrence identities for CONTINUOUS_ASSURANCE, PRIVATE_BACKUP, and CLOUD_DIAGNOSTIC. Schedules support one-time or fixed intervals of at least one hour and explicitly keep execution_enabled=false and external_actions_enabled=false.

A private hash-verified job registry provides leases, active-lease concurrency exclusion, expired-lease retry attempts, and idempotent completion by exact result proof hash. Retry decisions are bounded by max attempts/backoff and only retry transient classes such as rate limiting, timeouts, transient provider errors, state conflicts, or temporary I/O failures; authorization and other permanent failures stop. This half-step plans and coordinates jobs only—no scheduler daemon or autonomous external action is installed.

### Downstream tenant inheritance

The managed tenant registry now propagates beyond pilot execution. Production run-history recording automatically binds the history path/proof to the manifest client tenant when a registry is present. Production backups require every managed source path to resolve to the same tenant before writing, reserve backup archive/manifest paths before creation, and bind both resulting proofs. Customer data exports likewise inherit the customer tenant registry when present and reserve/bind the export archive. Assurance/diligence and other proof artifacts can use bind_existing_tenant_output / bind_managed_tenant_artifact so customer-specific exports cannot reuse another tenant's path or proof.

## Local production job worker execution (step 27b)

The tenant-bound job registry now supports lease heartbeat/renewal, cancellation, structured failure receipts, and restart recovery through later lease attempts. Local execution is implemented only for CONTINUOUS_ASSURANCE, PRIVATE_BACKUP, and previously authorized CLOUD_DIAGNOSTIC jobs; each runtime payload must hash to the preplanned job payload proof before any work begins.

The worker calls the existing local assurance evaluator/writer, private backup creator, or authorized diagnostic runner, records the exact result proof in the job registry, and remains idempotent after completion. It contains no provider API, cloud mutation, claim submission, or other external-action path.

## Chaos/recovery production acceptance (step 28)

A deterministic production acceptance suite now injects and verifies six failure/recovery scenarios: stale worker lease recovery, corrupted private job-registry state, atomic write failure, cross-tenant path collision, semantic restore after simulated process loss, and isolated multi-provider jobs. The tests exercise the actual lease registry, private atomic writer failure path, tenant registry, backup/restore verifier, and multi-cloud local execution.

A proof-bound acceptance report can only be created when every required scenario has a passing evidence result and records external_actions_performed=false. Corrupted state, partial-write risk, tenant collisions, or failed semantic restore therefore cannot be papered over by the report layer.

## Internal performance/capacity envelope (step 29a)

A deterministic capacity harness now generates exact FOCUS billing rows, matching independent meter rows, and reviewed contract-rate data, then runs them through the real local Cletrics export and RecoveryOS pilot path. Workload source hashes are deterministic across directories/runs for the same row count.

The internal envelope measures end-to-end runtime, billing-row throughput, peak Python traced memory, evidence-bundle ZIP size, validated recovery cents, and state-head creation. A capacity artifact is emitted only when every configured limit/minimum passes and is explicitly labeled INTERNAL_CAPACITY_ENVELOPE_PASSED with external_sla_claimed=false. This is engineering capacity evidence, not a customer SLA or external performance certification.

## Measured multi-dimensional capacity matrix (step 29b)

Capacity evidence can now be combined into an explicit matrix across billing-row, provider-count, and tenant-count dimensions. Every matrix cell requires proof hashes from an actual passing measurement/execution; the derived internal operating envelope uses only observed maxima/minima and records extrapolation_used=false and external_sla_claimed=false.

Admission checks compare requested billing rows/providers/tenants against those measured limits. Requests beyond any measured dimension return ADMISSION_REJECTED_CAPACITY before execution and do not trigger automatic scaling.

## Internal production service-level controls (step 30)

Production job control now has an internal SLO/pressure evaluator over planned tenant jobs and the private lease registry. It measures backlog depth, oldest queued-job age, maximum schedule lateness, missed-schedule count, and utilization of the measured capacity envelope.

The evaluator returns HEALTHY, PRESSURE, THROTTLED, or BLOCKED with proof-bound alerts. Over-capacity demand, excessive backlog/age, or missed schedules block new internal-job admission; high measured utilization can throttle admission before overload. It never performs automatic scaling or external actions.

## Simulated one-command operator rehearsal (step 31a)

A one-command local operator rehearsal now creates an isolated synthetic tenant, synthetic FOCUS/meter/rate inputs, validates onboarding/authorization/evidence-review readiness, materializes the authorized diagnostic call, schedules and executes it through the tenant-bound local job worker, and verifies the resulting private Cloud Assurance output.

The rehearsal also emits a private customer-safe diligence index plus an operator runbook/checklist covering tenant setup, intake validation, job scheduling/lease execution, report verification, review boundaries, and confirmation that no customer contact, provider mutation, claim submission, or external action occurred. The state is SIMULATED_OPERATOR_REHEARSAL_PASSED and is not real customer onboarding.

### Evidence-size capacity axis and internal SLO report

The measured capacity matrix now requires an explicit EVIDENCE_BYTES dimension in addition to billing rows, provider count, and tenant count. The conservative envelope records the maximum measured evidence bytes separately from the generated bundle size, and admission/service-level utilization accounts for evidence volume as a fourth capacity axis. Requests beyond the measured evidence-size limit fail with ADMISSION_REJECTED_CAPACITY before work begins.

Internal service-level snapshots now have private JSON/Markdown reporting with queue depth, job age, lateness, missed schedules, measured capacity utilization, throttle state, and alert details. The report explicitly identifies itself as an internal engineering control, not a customer SLA, and does not enable autonomous external actions.

### Real multi-axis capacity runner

The capacity matrix now has an executable measured runner rather than only accepting preconstructed matrix cells. It performs real local RecoveryWorks pilots for multiple billing-row counts, AWS/Azure/GCP provider counts, isolated tenant counts, and evidence-size scenarios; each cell records measured runtime, traced peak memory, aggregate evidence/bundle bytes, throughput, and exact pilot deployment proof hashes. The conservative operating envelope is derived only from those observed cells, with measured_only=true, extrapolation_used=false, and external_sla_claimed=false.

## Authoritative pilot prelaunch gate and brief (step 31b)

RecoveryWorks now has a proof-bound commercial prelaunch gate that directly binds the exact internal commercial package, simulated operator rehearsal, customer-safe diligence package, internal service-level snapshot, measured capacity envelope, and proposed capacity demand. READY means only that a buyer-safe prelaunch handoff may be prepared; customer data, kickoff, outreach, cloud mutation, recovery claims, and external actions remain unauthorized.

The derived launch brief stores the authoritative gate id/proof hash and cannot override the gate. Capacity overload, blocked/throttled service state, high diligence gaps, unsupported commercial scope, or failed operator boundaries block the handoff; pressure/medium diligence gaps remain explicit conditions. This avoids the older pattern where a downstream packet could be built from an unproven caller-supplied decision.

## Buyer-safe pilot activation packet (step 32)

A non-blocked authoritative prelaunch decision can now produce a buyer-safe activation packet that binds the exact launch-gate proof, launch-brief proof, and commercial-pilot proof. The packet carries pricing only as the existing hypothesis, exact buyer data requests, buyer/RecoveryWorks responsibilities, pilot stages, report surfaces, and financial integrity invariants.

The packet hard-codes customer_data_authorized=false, kickoff_authorized=false, outreach_authorized=false, external_action_authorized=false, and contract_created=false. Editing or recreating the packet cannot bypass a blocked gate because the packet verifies the authoritative decision/brief proof chain.

## Machine-checkable prelaunch charter (step 33a)

The buyer-safe activation packet can now be bound to a machine-checkable prelaunch charter that freezes the proposed buyer/business-unit scope, population/date range, billing accounts/providers, pricing hypotheses, named operating roles, and explicit acknowledgments. Runtime parsing requires every acknowledgment to be a literal boolean; strings such as false cannot be treated as truthy authorization.

Even PRELAUNCH_ACCEPTED hard-codes customer_data_authorized=false, kickoff_authorized=false, outreach_authorized=false, external_action_authorized=false, and contract_created=false. Fee values must exactly match the activation packet. This half-step is an operational scope-freeze/acknowledgment artifact only; actual customer-data and kickoff authorization remain a later separate proof.

## Verified pilot kickoff authorization (step 33b)

A PRELAUNCH_ACCEPTED charter can now advance only when RecoveryWorks receives a separately verified buyer authorization receipt for the exact frozen engagement, buyer, billing-account/provider/date scope, read-only pilot purpose, authorization window, and retention deadline. The authorization receipt is externally sourced; RecoveryWorks does not manufacture buyer consent.

The resulting kickoff gate can authorize read-only customer-data processing and pilot kickoff, but still hard-codes outreach, external recovery action, provider mutation, invoicing, and payment collection as unauthorized. Scope drift, expired/unverified authorization, or mismatch against the charter fails closed.

## Governed pilot execution lifecycle (step 34)

Authorized pilots now have a private tamper-evident execution journal with a fixed internal sequence: KICKOFF_AUTHORIZED, INTAKE_FROZEN, DIAGNOSTIC_COMPLETE, EVIDENCE_REVIEW_COMPLETE, BUYER_REVIEW_READY, CLOSEOUT_READY, and CLOSED. Every transition requires proof hashes and remains bound to the exact kickoff-gate proof and engagement id.

The lifecycle intentionally contains no claim-submission/provider-mutation state. Invalid transition skips, kickoff/scope replacement, sequence gaps, previous-hash breaks, or journal tampering fail closed. This provides pilot-operating accountability without converting internal progress into external-action authorization.

## Pilot closeout/economics review snapshot (step 35a)

A completed diagnostic/buyer-review path can now produce a proof-bound pilot closeout snapshot that keeps recovery, prospective savings, verified realized savings, anomaly exposure, and reconciliation drift on separate surfaces. Commercial arithmetic is derived only from the frozen charter hypotheses.

Recovered-cash success-fee arithmetic uses recovered_cents only; validated/potential recovery, prospective savings, anomaly exposure, and drift cannot increase it. The snapshot is only PILOT_CLOSEOUT_REVIEW_READY and hard-codes continuation_authorized=false, invoice_created=false, payment_due_asserted=false, payment_received=false, and external_action_authorized=false. It is not an invoice, payment claim, or renewal commitment.

## Verified buyer closeout acknowledgment (step 35b)

Pilot closeout can now advance only with a separately sourced, verified buyer receipt that binds the exact closeout/charter/engagement/buyer and repeats the exact recovered cash, validated recovery, prospective savings, realized savings, anomaly exposure, and reconciliation drift surfaces. Any amount drift, unverified receipt, unaccepted outcome surface, or unresolved dispute fails closed.

The resulting PILOT_CLOSEOUT_ACKNOWLEDGED artifact may record only a continuation interest such as REVIEW_MONTHLY_ASSURANCE; it hard-codes continuation_authorized=false, invoice_authorized=false, payment_due_asserted=false, and external_action_authorized=false. Buyer acknowledgment therefore cannot silently become billing or renewal authority.

## Finalized agreement and fee-draft readiness (step 36)

A closeout acknowledgment can now be paired with a separately sourced, externally finalized commercial agreement receipt. The agreement—not the earlier pricing hypothesis—becomes the commercial arithmetic authority and may explicitly differ from the charter hypothesis; any such variance is surfaced in the readiness artifact.

COMMERCIAL_FEE_DRAFT_READY calculates diagnostic and recovered-cash success-fee arithmetic only when those fee types are applicable in the finalized agreement. Success-fee math is recovered_cash_cents × finalized_agreement_bps and cannot use validated/potential recovery, prospective savings, anomaly exposure, or drift. Monthly assurance is separately tracked as accepted/not accepted. The gate allows draft preparation only and hard-codes invoice_issuance_performed=false, payment_due_asserted=false, payment_collected=false, and external_action_performed=false.

## Unissued billing/payment draft (step 37a)

COMMERCIAL_FEE_DRAFT_READY can now produce a private human-review billing draft whose line items are limited to agreement-supported closeout charges: the finalized diagnostic fee and success fee on verified recovered cash. Validated/potential recovery, prospective savings, anomaly exposure, reconciliation drift, and unaccepted monthly assurance cannot become payable line items.

The monthly assurance amount is displayed only as a separately tracked option and is not included in the closeout draft total. The artifact is always DRAFT_NOT_ISSUED and hard-codes issued=false, sent=false, payment_due_asserted=false, payment_received=false, payment_instructions_included=false, and external_commitment_created=false. The proposed due date is informational and only applies if a later separately governed issuance step occurs.

## Verified external invoice issuance (step 37b)

An unissued billing draft can now be converted into a short-lived credential-free handoff for a named separate billing issuer. The handoff freezes the exact agreement/readiness/draft proofs, line-item proofs, total, currency, and agreed due date while keeping RecoveryWorks unable to issue, send, collect, or embed payment instructions.

Payment due becomes verified only after a separately sourced external billing receipt proves the exact handoff was issued and delivered to the buyer inside the authorization window with the same line items/total/currency/due date. The resulting state is ISSUED_INVOICE_VERIFIED and remains unpaid. RecoveryWorks still performs no invoice sending or payment collection.

## Independent payment settlement reconciliation (step 38)

Issued-invoice payment state now requires separately verified external cash-settlement evidence; an invoice/billing provider's own paid flag is explicitly insufficient. Settlement receipts bind the exact issued invoice/buyer/currency, external settlement reference, observed time, gross amount, merchant fee, net cash, invoice-applied amount, and independent source evidence.

Reconciliation supports partial payments, duplicate-settlement rejection, exact invoice over-allocation prevention, and externally observed reversals/chargebacks that reopen a previously paid balance. Invoice state is UNPAID, PARTIALLY_PAID, or PAID solely from the net applied settlement events. RecoveryWorks does not collect payment and provider_accounting_only receipts fail closed.
