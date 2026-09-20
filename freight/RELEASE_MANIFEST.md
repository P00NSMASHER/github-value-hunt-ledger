# Freight Recovery v15.7 — Canonical Release Manifest

Release checkpoint: **v15.7-lifecycle-audit-sbom-attestation-2026-09-20**

## Freight source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Freight v15.7 merge commit: `a6a1ad18ab95fb8706dc4297f2355f7dc8d2cdb5`
- v15 commercialization PR: **#7**
- v15.1 machine-gates PR: **#8**
- v15.2 readiness/gap-control PR: **#10**
- v15.3 proof-derived reporting PR: **#11**
- v15.4 commercial-ops/outcome-learning PR: **#12**
- v15.5 adaptive-authorization/commercial-learning PR: **#17**
- v15.6 pilot-security/provenance PR: **#20**
- v15.7 lifecycle/audit/SBOM/attestation PR: **#22**
- Note: repository `main` continues to advance independently as hunters/integrators commit. The Freight merge commit above is the canonical v15.7 code checkpoint.

## Verified CI checkpoint

### Freight Commercial Contracts
- v15.7 PR-head run: `35525286692`
- Result: **success**
- Hunter/model contracts: **success**
- Freight commercial proof contracts: **success**
- Controlled-pilot rights gate: **success**
- Canonical Freight gap gate: **success**
- Ready-pilot diagnostic fixture: **success**
- Full synthetic commercial rehearsal: **success**
- Deterministic release provenance generation + verification: **success**
- Component inventory generation: **success**
- Deterministic CycloneDX SBOM generation + verification: **success**
- Unsigned DSSE attestation generation + verification: **success**

## New v15.7 diligence controls

### CENSUS / SCOPE / PROOF data lifecycle

`freight/data_lifecycle.py` applies the reusable recovery-proof pattern:

- **CENSUS** — the machine-checkable pilot data-room manifest defines the source objects under management.
- **SCOPE** — retention days define when each source becomes due for deletion.
- **PROOF** — only explicit external deletion confirmation can create `DELETE_CONFIRMED`.

Lifecycle states:
- `PRESENT`
- `DELETE_REQUESTED`
- `DELETE_UNKNOWN`
- `DELETE_CONFIRMED`

A timeout, disappearance or failed read never proves deletion. Ambiguous deletion stays `DELETE_UNKNOWN`.

### Source-observation receipts

Source observations distinguish:
- `PRESENT`
- `VERIFIED_EMPTY`
- `UNAVAILABLE`

`VERIFIED_EMPTY` requires completeness evidence. This prevents a failed/partial settlement, document or authority source read from becoming a false “nothing happened” conclusion.

### Scope-bound append-only audit evidence

`freight/audit_ledger.py` provides:
- buyer/business-unit scope;
- monotonic sequence;
- previous-record hash;
- event hash;
- timezone-aware event timestamp;
- optional SHA-256 evidence reference;
- mutation/reorder detection.

This is an **application-level tamper-evidence chain** over the supplied record set. It is not an external trusted timestamp or immutable external log-service claim.

### CycloneDX-shaped SBOM

`freight/sbom.py` deterministically emits a CycloneDX 1.6-shaped document covering:
- exact repository/revision components in `COMPONENT_RIGHTS_REGISTRY.json`;
- direct pinned Python CI dependencies in `production/requirements-ci.txt`.

The document self-checks:
- unique component references;
- content digest;
- deterministic UUID serial.

Coverage is explicitly **partial**. It does not claim every transitive runtime/OS/cloud/API/data/model/deployment dependency.

### in-toto / DSSE-shaped release attestation

`freight/release_attestation.py` creates:
- an in-toto Statement v1-shaped payload;
- subjects for deterministic Freight control provenance and the SBOM;
- an unsigned DSSE envelope with `signatures: []`.

The repository verifier rejects non-empty/fake signatures. This deliberately prevents repository-generated evidence from masquerading as externally signed provenance.

A future deployment may submit the deterministic payload to an approved external signing identity/key and preserve the signer/verifier evidence separately.

### Expanded deterministic provenance

`freight/release_provenance.py` now hashes the broader Freight control plane, including:
- audit ledger;
- commercial-learning controls;
- scoped proof contracts;
- data lifecycle;
- deal economics;
- gap authorization;
- input guard;
- outcome adapter;
- pilot package/reporting;
- readiness;
- release attestation/gate/provenance;
- SBOM generator;
- settlement store;
- synthetic rehearsal;
- rights/gap/domain-policy files;
- pinned CI dependencies and Freight CI workflow.

## Current commercial / learning state

Freight Recovery v15.7 is **commercially specified, machine-gated, internally rehearsed, scope-bound, lifecycle-aware, application-audit-chain capable, pre-parser hardened and reproducibly supply-chain documented; EXP-001 remains externally unproven**.

Structured external Freight evidence remains:
- directly evidenced Freight revenue: **$0**
- directly evidenced Freight customer value: **$0**
- paid diagnostic/pilot/annual conversion: **none recorded**
- Freight ACTIVE_SEARCH gaps: **0**

No v15.7 internal diligence improvement changes those external facts.

## Current claim boundary

The repository now demonstrates internally:
- buyer/BU/shipment scope-bound proof;
- sealed-incumbent blind protocol;
- source/data-room package manifests;
- fail-closed pre-parser input checks;
- explicit deletion/unknown/confirmed lifecycle semantics;
- present/verified-empty/unavailable source receipts;
- application-level audit hash chaining;
- deterministic control/component provenance;
- deterministic partial CycloneDX 1.6-shaped SBOM;
- deterministic unsigned in-toto/DSSE-shaped payload.

It still does **not** prove:
- real storage-provider deletion execution;
- externally trusted time;
- deployed persistent audit-store access control/immutability/alerting;
- deployed shared database/object-store/API tenant isolation;
- production parser CPU/memory/time/network sandboxing;
- buyer-specific encryption configuration;
- external signing identity or valid signature;
- complete transitive deployment SBOM;
- backup/restore operations for the deployed service;
- incident-response operating evidence;
- SOC 2 / ISO 27001 or other certification.

## Remaining high-value blockers

1. first authorized real buyer population and later settlement;
2. executed Trenova/Opstrax hosted/SaaS/change-of-control rights where unresolved;
3. deployment-specific customer data-service cross-tenant isolation;
4. production parser sandbox/resource/network controls;
5. real storage-provider deletion receipts and persistent audit-store controls;
6. external signing/trusted timestamp and complete deployment SBOM if required;
7. backup/restore, logging/alerting and incident-response evidence for annual assurance.

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

**Externally evidenced paid diagnostic/pilot → authorized scoped data room → frozen population + sealed incumbent → buyer-owned truth → challenger-only validated finding or defensible clean result → buyer-approved action → issued credit/refund/remittance → unambiguous settlement → lifecycle/audit receipts → externally evidenced outcome → annual assurance conversion.**

That external chain remains the primary path to materially increasing Freight Recovery's defensible value.
