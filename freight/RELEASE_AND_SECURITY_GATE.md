# Freight Recovery — Release, Security and Diligence Gate

Updated: 2026-09-20

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

## P0 — before a paid pilot with confidential buyer data

### Repository/supply-chain
- [x] Freight GitHub Actions are pinned to full immutable commit SHAs.
- [x] Workflow payload writers reject absolute paths and parent traversal.
- [x] Workflow writers can touch only explicit allowed files/prefixes.
- [x] CI dependencies are version-pinned.
- [x] Commercial/runtime/comparator components are represented in the rights registry with exact revisions.
- [x] Deterministic control-file hashes + component inventory can be regenerated in CI via `freight/release_provenance.py`.
- [ ] Separate executed permission/license documents are stored in the actual buyer/acquirer diligence room.

### Customer data
- [ ] Buyer authorization is documented for the actual engagement.
- [x] Pilot data-room code rejects sources not marked read-only.
- [x] Buyer/business-unit scope is carried through source manifests, findings, authority, truth, incumbent submission/output, settlement events, recovery certificates and buyer reports.
- [x] Proof-layer cross-buyer/BU/shipment negative tests exist.
- [ ] Cross-tenant negative tests pass against the **actual production database/object-store/API authorization layer** used for customer data.
- [x] Source manifests require positive retention days; buyer-specific retention/deletion/export terms still must be agreed per engagement.
- [x] Sources explicitly marked as containing credentials/secrets are rejected from the evidence room.

### Parsing/untrusted inputs
- [x] PDF/EDI/X12/XML/CSV inputs pass through a fail-closed pre-parser guard.
- [x] File-size, text-line and EDI-segment limits are enforced before parsing.
- [x] Archives are rejected rather than recursively unpacked.
- [x] XML DTD/entity constructs are rejected before downstream parsing.
- [x] Spreadsheet formula-leading text can be neutralized on derived exports without mutating source evidence.
- [ ] Downstream parser CPU/time/memory limits are enforced in the actual deployment runtime.
- [ ] Downstream parsers execute in a low-privilege sandbox with no ambient production credentials or unintended network access.
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
- [x] Duplicate/preexisting/automatic credits cannot become fee-eligible.
- [x] Recovery certificate cannot exceed validated or realized amounts and remains buyer/BU scoped.
- [x] Final pilot-package hash binds data-room manifest, population, truth, sealed incumbent and opened incumbent output.

## P1 — before annual continuous assurance

- [ ] isolated production database/control plane;
- [ ] immutable/versioned evidence object storage;
- [ ] independent verifier identity with read-only evidence permission;
- [ ] sandbox/isolation for untrusted code and parsers;
- [ ] central kill switch/budget limit;
- [ ] signed release/provenance;
- [ ] full SPDX/CycloneDX-equivalent SBOM if required by buyer diligence;
- [ ] backup/restore drill;
- [ ] audit logging and alerting;
- [ ] customer-specific integration secrets held outside source;
- [ ] incident-response and breach-notification runbook;
- [ ] completed security questionnaire / external diligence package.

## Current claim boundary

The repository now proves **scope-bound proof objects, pre-parser rejection controls, machine-checkable pilot source/package manifests and deterministic release/component provenance**.

It does **not** prove a deployed shared multi-tenant SaaS is isolated, parser sandboxing is production-grade, transport/storage encryption is configured for a specific buyer, provenance is signed, or any external security certification exists.

## Commercial launch rule

A pilot may be sold before the full enterprise platform exists **only** when it is run as a controlled, read-only, human-reviewed acceptance engagement and every unsupported dollar fails closed.

Do not market the research-agent production architecture as already deployed Freight Recovery infrastructure. They are separate systems until integrated and proven.
