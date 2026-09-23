# Freight Recovery — Release, Security and Diligence Gate

Updated: 2026-09-23

This checklist separates **research architecture** from a buyer-deployable Freight Recovery release.

## Release identity

Every buyer-facing release must include:
- product version;
- source commit;
- dependency/component manifest with exact revisions;
- component-rights registry version;
- test command and captured result;
- SHA-256 checksums / deterministic provenance for committed controls;
- component inventory;
- release notes;
- known limitations;
- deployment model.

Do not treat chat/sandbox ZIPs as the canonical release unless they are reproduced from committed source and tied to a release/provenance record.

## Deployment evidence addendum — 2026-09-20

Live connected-provider evidence for `freightleak-audit` is recorded in:
- `freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json`
- `freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.md`
- `freight/INCIDENT_TABLETOP_2026-09-20.md`

Current deployment facts:
- Netlify SSO team login required for **all** visitors: **CONFIG PROVEN**.
- Netlify Forms: **0**.
- Netlify environment variables: **0**.
- Netlify team members: **1**.
- Netlify team MFA enforcement: **not enforced**.
- No Freight backend/data plane was discovered in Vercel, Render, Floot, Replit, AppDeploy, or Supabase.
- Cross-tenant isolation: **UNPROVEN / not testable yet** because no Freight multi-tenant customer data plane was discovered.
- Parser sandboxing: **UNPROVEN / not testable yet** because no production Freight parser runtime was discovered.
- Deployment-specific incident tabletop: **completed — PASS WITH MATERIAL GAPS**, not a live incident.

These findings do not upgrade missing tenant/parser controls to PASS.

- [x] Deployment evidence is freshness-bounded: the 2026-09-20 Netlify snapshot
  expires after 2026-09-27 and must be recollected earlier after relevant
  configuration changes.
- [x] VERIFIED separate-environment evidence requires SHA-256 receipts,
  configuration fingerprinting, verifier metadata and a validity window of no
  more than 90 days.

The **final pilot launch decision is machine-enforced** by
`freight/pilot_launch_gate.py`, which composes buyer readiness, pilot rights
operability, rights-evidence consistency and the chosen data-handling path.

## P0 — before a paid pilot with confidential buyer data

### Repository/supply-chain
- [x] Every repository GitHub Action reference is pinned to a full immutable
  commit SHA, with a repository-wide regression test that rejects floating refs.
- [x] Technology Intelligence validation workflow uses immutable Action SHAs + read-only contents permission; only the main-only persistence job receives contents:write.
- [x] Workflow payload writers reject absolute paths and parent traversal.
- [x] Workflow writers can touch only explicit allowed files/prefixes.
- [x] Deployment and separate-environment freshness gates evaluate the real UTC
  workflow date; CI can no longer keep expired evidence green with a frozen date.
- [x] CI dependencies are version-pinned.
- [x] Commercial/runtime/comparator components are represented in the rights registry with exact revisions.
- [x] Rights status promotion is fail-closed: separately licensed components cannot be used by the pilot launch gate without verified executed evidence, a confirmed-allowed commercial-use scope, diligence-room metadata and SHA-256; hosted/SaaS/assignment/change-of-control claims also require verified scope evidence.
- [x] Deterministic control-file hashes + component inventory can be regenerated in CI via `freight/release_provenance.py`.
- [x] Release/evidence text inputs are pinned to LF in `.gitattributes`, so
  Windows and Linux checkouts hash the same committed bytes.
- [x] Deterministic CycloneDX 1.6-shaped SBOM is generated for pinned Freight repository components + direct pinned CI Python dependencies.
- [x] Deterministic unsigned in-toto/DSSE-shaped attestation payload is generated and verified in CI; repository output intentionally contains no signature.
- [ ] Separate executed permission/license documents are stored in the actual buyer/acquirer diligence room.

### Customer data
- [ ] Buyer authorization is documented for the actual engagement.
- [x] Current Netlify customer-data path is machine-classified as **BLOCKED** until deployment security evidence changes.
- [x] Separate controlled/manual pilot path is machine-classified as **BLOCKED** until both executed component-rights evidence and a separately controlled data environment have verified evidence.
- [x] Separate/manual pilot route cannot be self-attested: launch requires a structured VERIFIED environment manifest with evidence references for all applicable controls.
- [ ] Netlify team MFA is enforced before confidential buyer data is accepted.
- [x] Pilot data-room code rejects sources not marked read-only.
- [x] Buyer/business-unit scope is carried through source manifests, findings, authority, truth, incumbent submission/output, settlement events, recovery certificates and buyer reports.
- [x] Proof-layer cross-buyer/BU/shipment negative tests exist.
- [ ] Cross-tenant negative tests pass against the **actual production database/object-store/API authorization layer** used for customer data. Current evidence: no Freight multi-tenant data plane was discovered, so this remains unproven rather than passed.
- [x] Source manifests require positive retention days; buyer-specific retention/deletion/export terms still must be agreed per engagement.
- [x] CENSUS/SCOPE/PROOF lifecycle entries derive from the source manifest and retention scope.
- [x] Delete attempts cannot become `DELETE_CONFIRMED` without explicit external confirmation evidence; ambiguous outcomes remain `DELETE_UNKNOWN`.
- [x] Source observations distinguish `PRESENT`, `VERIFIED_EMPTY`, and `UNAVAILABLE`; `VERIFIED_EMPTY` requires completeness evidence.
- [x] Buyer/BU-scoped append-only audit records are hash chained and detect
  mutation/reordering within the supplied record set; event time is canonical
  UTC and cannot move backward in the chain.
- [x] A file-backed scope-bound SQLite audit reference store persists the chain, serializes concurrent appends and blocks direct UPDATE/DELETE mutations.
- [x] Sources explicitly marked as containing credentials/secrets are rejected from the evidence room.

### Parsing/untrusted inputs
- [x] PDF/EDI/X12/XML/CSV inputs pass through a fail-closed pre-parser guard.
- [x] File-size, text-line and EDI-segment limits are enforced before parsing.
- [x] Archives are rejected rather than recursively unpacked.
- [x] XML DTD/entity constructs are rejected before downstream parsing.
- [x] Spreadsheet formula-leading text can be neutralized on derived exports without mutating source evidence.
- [ ] Downstream parser CPU/time/memory limits are enforced in the actual deployment runtime. Current evidence: no production Freight parser runtime was discovered.
- [ ] Downstream parsers execute in a low-privilege sandbox with no ambient production credentials or unintended network access. Current evidence: no production Freight parser runtime was discovered.
- [ ] Untrusted document text is proven unable to grant tool/control-plane authority in the deployed workflow.

### Blind pilot / proof chain
- [x] Incumbent source SHA-256 is sealed against buyer/BU + frozen population before truth opens.
- [x] Finding identity includes exact invoice + shipment, not invoice number alone.
- [x] Controlling authority is buyer/BU scoped and source-identified.
- [x] Expected charge remains deterministic and independently falsifiable.
- [x] Physical truth remains independent of commercial entitlement.
- [x] Blind order is enforced: source/data room -> population -> sealed incumbent -> truth -> opened incumbent.
- [x] Unsupported findings remain REVIEW / $0.
- [x] Settlement readback has source hash + allocation lineage.
- [x] Settlement claim/event/counter evidence requires canonical lowercase
  SHA-256; allocation and reversal times are canonical UTC and chronological at
  both the application and direct-SQL trigger layers.
- [x] Duplicate/preexisting/automatic credits cannot become fee-eligible.
- [x] Recovery certificate cannot exceed validated or realized amounts and remains buyer/BU scoped.
- [x] Final pilot-package hash binds data-room manifest, population, truth, sealed incumbent and opened incumbent output.

## P1 — before annual continuous assurance

- [ ] isolated production database/control plane;
- [ ] immutable/versioned evidence object storage;
- [ ] independent verifier identity with read-only evidence permission;
- [ ] sandbox/isolation for untrusted code and parsers;
- [ ] central kill switch/budget limit;
- [ ] externally signed release/provenance using an approved signing identity/key;
- [x] deterministic CycloneDX-shaped SBOM for current pinned repo components + direct CI dependencies;
- [ ] complete deployment/transitive SBOM if required by buyer diligence;
- [x] semantic reference backup/restore drill restores scoped audit + settlement SQLite stores and re-verifies audit chain, full settlement content hash, realized cents and fee-eligible cents;
- [ ] deployed backup scheduling/retention/geographic redundancy plus measured RPO/RTO;
- [x] file-backed scoped reference audit persistence with immutable SQL triggers;
- [ ] production audit-store service authorization, external immutability/WORM controls and alerting;
- [ ] customer-specific integration secrets held outside source;
- [x] documented incident-response / breach-decision runbook with machine-checked containment, recovery, exposure-resolution and notification-authorization closure rules;
- [x] deployment-specific incident tabletop completed against the discovered Netlify Freight deployment;
- [ ] deployed contact tree/on-call/alerting plus live-environment incident exercise evidence;
- [x] deterministic zero-customer-data technical/commercial diligence ZIP with per-entry SHA-256 and generated provenance/SBOM/unsigned attestation;
- [x] deterministic controlled synthetic pilot ZIP with exact fictional inputs,
  generated review/report outputs, per-entry SHA-256, duplicate/path rejection,
  byte-for-byte replay verification and explicit no-customer-value boundaries;
- [x] public marketing build uses an exact 33-file allowlist (page, local
  scripts/styles, responsive imagery, licensed local fonts and demo), requires
  an operator-attested business inbox plus two distinct operator-attested live
  Stripe Payment Links, embeds the controlled-demo SHA-256 and contains no
  upload, analytics, backend request or customer-data intake;
- [x] checkout configuration accepts only canonical HTTPS `buy.stripe.com`
  destinations, rejects test links/query/fragment values, requires separate
  readiness/audit links and leaves deployment fail-closed when configuration is
  absent;
- [x] GitHub Pages validation/deployment workflow is least-privilege and pins
  every third-party Action to a full commit; pull requests cannot deploy and
  main deployment requires owner-configured contact and checkout variables;
- [ ] both exact-price live links are created in a Freight Recovery-branded
  Stripe account, with the correct business identity, one-time prices, receipt,
  terms/cancellation link and no adjustable quantity/subscription/add-on;
- [ ] a controlled end-to-end live checkout/refund receipt check is completed
  against both links without using customer freight data;
- [ ] the checkout-enabled public URL, download, contact, calculator and both
  payment destinations are independently checked after deployment;
- [ ] buyer-specific completed security questionnaire and externally supplied diligence artifacts.

## Current claim boundary

The repository now proves **scope-bound proof objects, pre-parser rejection controls, machine-checkable pilot source/package manifests, CENSUS/SCOPE/PROOF lifecycle semantics, persistent tamper-evident reference audit records, semantic reference backup/restore, deterministic release/component provenance, a standards-shaped CycloneDX SBOM, an unsigned in-toto/DSSE payload, a deterministic zero-customer-data diligence bundle, a deterministic controlled synthetic buyer demo, an exact static-site publication boundary, rights evidence consistency gates, a documented fail-closed incident-response decision model, Netlify deployment access-control configuration evidence, and a completed deployment-specific tabletop**.

It does **not** prove executed rights documents have been supplied/reviewed; the launch gate now treats that absence as a blocker. It also does not prove the checkout-enabled site has been deployed, the Payment Links belong to the correct Freight Recovery account, a payment/refund was completed, the public inbox works, a customer outcome occurred, a deployed shared multi-tenant SaaS is isolated, parser sandboxing is production-grade, Netlify team MFA is enforced, deletion was executed by a real storage provider, deployed backups meet an RPO/RTO or geographic-redundancy policy, production audit logs have external WORM/alerting controls, transport/storage encryption is configured for a specific buyer, live on-call/alerting incident operations exist, provenance is externally signed, the SBOM covers all transitive deployment dependencies, or any external security certification exists.

## Commercial launch rule

A pilot may be sold before the full enterprise platform exists **only** when it is run as a controlled, read-only, human-reviewed acceptance engagement and every unsupported dollar fails closed.

Do not market the research-agent production architecture as already deployed Freight Recovery infrastructure. They are separate systems until integrated and proven.
