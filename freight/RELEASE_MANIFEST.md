# Freight Recovery v15.8 — Canonical Release Manifest

Release checkpoint: **v15.8-persistent-audit-restore-diligence-2026-09-20**

## Freight source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Freight v15.8 merge commit: `7ce74d4106645682a82200ec1eec0738c8da8d65`
- v15 commercialization PR: **#7**
- v15.1 machine-gates PR: **#8**
- v15.2 readiness/gap-control PR: **#10**
- v15.3 proof-derived reporting PR: **#11**
- v15.4 commercial-ops/outcome-learning PR: **#12**
- v15.5 adaptive-authorization/commercial-learning PR: **#17**
- v15.6 pilot-security/provenance PR: **#20**
- v15.7 lifecycle/audit/SBOM/attestation PR: **#22**
- v15.8 persistent-audit/restore/diligence PR: **#25**
- Note: repository `main` continues to advance independently as hunters/integrators commit. The Freight merge commit above is the canonical v15.8 code checkpoint.

## Verified CI checkpoint

### Freight Commercial Contracts
- v15.8 successful PR-head run: `35526130920`
- Result: **success**
- Freight commercial proof tests: **129 passed**
- Controlled-pilot rights gate: **success**
- Canonical Freight gap gate: **success**
- Ready-pilot diagnostic fixture: **success**
- Full synthetic commercial rehearsal: **success**
- Deterministic release provenance generation + verification: **success**
- Component inventory generation: **success**
- CycloneDX SBOM generation + verification: **success**
- Unsigned DSSE attestation generation + verification: **success**
- Deterministic diligence ZIP generation + verification: **success**

An earlier v15.8 CI run failed only because `BackupRestoreResult` accidentally received the internal `schema` key used in its proof-hash body. The semantic restore comparison itself had already passed. The constructor was corrected without weakening the restore criteria.

## New v15.8 operational-diligence controls

### Persistent buyer/BU-scoped audit reference store

`freight/audit_store.py` provides file-backed SQLite reference persistence for the v15.7 audit chain:
- buyer + business unit fixed at store construction;
- monotonic per-scope sequence;
- full hash-chain replay before append;
- `BEGIN IMMEDIATE` serialized append transactions;
- retry on transient database lock;
- direct SQL UPDATE and DELETE blocked by immutable triggers;
- scope-bound reads and semantic summary.

This is a reference application persistence boundary, not a hosted external WORM logging service.

### Semantic backup/restore proof

`freight/backup_restore.py` backs up both:
- the scoped audit store; and
- the scoped settlement store.

The drill:
1. freezes the source semantic summary;
2. uses SQLite's backup API;
3. restores into fresh database files;
4. reopens both stores under the same buyer/BU scope;
5. re-verifies the complete audit chain;
6. computes a deterministic content hash over all scoped settlement tables;
7. re-checks recovery/review/event/allocation/counter/reversal counts;
8. re-checks realized cents and fee-eligible cents;
9. requires the complete source/restored semantic summaries to match.

Backup-file existence or a matching file checksum alone is **not** considered restore proof.

### Deterministic zero-customer-data diligence bundle

`freight/diligence_bundle.py` creates a byte-deterministic ZIP containing:
- commercial operating/qualification/learning documents;
- pilot/readiness/data-room/report/audit-lifecycle documents;
- security/release gates;
- rights registry;
- release manifest;
- deterministic release provenance;
- exact component inventory;
- partial CycloneDX 1.6 SBOM;
- unsigned DSSE release payload.

`BUNDLE_MANIFEST.json` records each entry's:
- path;
- byte size;
- SHA-256.

The bundle explicitly states:
- `customer_data_included=false`;
- unsigned evidence remains unsigned;
- SBOM coverage remains partial;
- no certification/deployed-control claim is implied.

The verifier rejects entry tampering or divergence from the current checkout.

### Expanded deterministic provenance

`freight/release_provenance.py` now covers the persistent-audit, semantic-restore and diligence-bundle control code in addition to the existing Freight control plane.

## Current commercial / learning state

Freight Recovery v15.8 is **commercially specified, machine-gated, internally rehearsed, scope-bound, lifecycle-aware, persistently audit-capable, semantically restore-tested, pre-parser hardened and reproducibly diligence-packaged; EXP-001 remains externally unproven**.

Structured external Freight evidence remains:
- directly evidenced Freight revenue: **$0**
- directly evidenced Freight customer value: **$0**
- paid diagnostic/pilot/annual conversion: **none recorded**
- Freight ACTIVE_SEARCH gaps: **0**

No internal v15.8 operational/diligence improvement changes those external facts.

## Current claim boundary

The repository now demonstrates internally:
- scoped proof and blind-incumbent binding;
- source/data-room package manifests;
- pre-parser hostile-input rejection;
- lifecycle/delete/source-observation semantics;
- application audit hash chaining;
- persistent scoped reference audit storage;
- semantic audit + settlement backup/restore proof;
- deterministic component/control provenance;
- partial CycloneDX 1.6 SBOM;
- deliberately unsigned in-toto/DSSE payload;
- deterministic zero-customer-data diligence packaging.

It still does **not** prove:
- real storage-provider deletion execution;
- deployed backup scheduling or geographic redundancy;
- measured production RPO/RTO;
- externally trusted time;
- production external/WORM audit-log authorization and alerting;
- deployed shared database/object-store/API tenant isolation;
- production parser CPU/memory/time/network sandboxing;
- buyer-specific encryption configuration;
- external signing identity or valid signature;
- complete transitive deployment SBOM;
- incident-response operating evidence;
- SOC 2 / ISO 27001 or other certification.

## Remaining high-value blockers

1. first authorized real buyer population and later settlement;
2. executed Trenova/Opstrax hosted/SaaS/change-of-control rights where unresolved;
3. deployment-specific customer data-service cross-tenant isolation;
4. production parser process isolation/resource/network controls;
5. real storage-provider deletion receipts;
6. deployed backup schedule/geographic redundancy/RPO/RTO;
7. production audit-service external immutability/authorization/alerting;
8. external signing/trusted timestamp and complete deployment SBOM if required;
9. incident-response operating evidence/security certification.

## Engineering / search freeze

Do not cut another Freight version for repository novelty alone.

Reopen internal Freight work only for:
- a paying-customer/EXP-001 named gap;
- deployment/security diligence;
- rights diligence;
- a reproduced money-bearing disagreement;
- a measured reviewer bottleneck whose automation preserves the false-dollar ceiling.

The global adaptive search model cannot override the Freight domain gate.

## Next canonical milestone

**Externally evidenced paid diagnostic/pilot → authorized scoped data room → bounded parser execution → frozen population + sealed incumbent → buyer-owned truth → challenger-only validated finding or defensible clean result → buyer-approved action → issued credit/refund/remittance → unambiguous settlement → lifecycle/audit/restore evidence → externally evidenced outcome → annual assurance conversion.**

That external chain remains the primary path to materially increasing Freight Recovery's defensible value.
