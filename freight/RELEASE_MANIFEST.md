# Freight Recovery v15.6 — Canonical Release Manifest

Release checkpoint: **v15.6-pilot-security-provenance-2026-09-20**

## Freight source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Freight v15.6 merge commit: `76fde9f9ad6fb1183acea7eb60dbef0fac24da37`
- v15 commercialization PR: **#7**
- v15.1 machine-gates PR: **#8**
- v15.2 readiness/gap-control PR: **#10**
- v15.3 proof-derived reporting PR: **#11**
- v15.4 commercial-ops/outcome-learning PR: **#12**
- v15.5 adaptive-authorization/commercial-learning PR: **#17**
- v15.6 pilot-security/provenance PR: **#20**
- Note: repository `main` continues to advance independently as hunters/integrators commit. The Freight merge commit above is the canonical v15.6 code checkpoint.

## Verified CI checkpoint

### Freight Commercial Contracts
- v15.6 successful PR-head run: `35524672964`
- Result: **success**
- Hunter/model contract suite: **success**
- Freight commercial proof suite: **success**
- Controlled-pilot rights gate: **success**
- Canonical Freight gap-register gate: **success**
- Ready-pilot diagnostic fixture: **success**
- Full synthetic commercial rehearsal: **success**
- Deterministic release-provenance generation: **success**
- Deterministic provenance verification: **success**
- Component-inventory generation: **success**

An earlier v15.6 run failed because a new EDI-limit regression test created a custom policy but did not pass it to the tested function. Only the test invocation was corrected; the production input-limit rule was not weakened.

## New v15.6 pilot-security controls

### Scope-bound proof chain
Money-bearing proof objects now bind:
- buyer ID;
- business unit;
- invoice ID;
- shipment ID;
- customer;
- carrier;
- currency;
- controlling authority.

Cross-buyer, cross-BU, wrong-shipment and frozen-row identity mismatches fail closed before a validated dollar is created.

Settlement events, settlement allocations, recovery certificates and pilot reports retain buyer/BU scope.

### Sealed incumbent protocol
The incumbent source is represented as a `SealedIncumbentSubmission`:
1. freeze buyer/BU + population;
2. seal incumbent source SHA-256 against that population;
3. build/freeze buyer-owned truth;
4. open the incumbent output from the previously sealed source;
5. bind opened output to source hash, sealed-submission hash, truth hash and population hash.

This proves deterministic application ordering/content binding. It is **not** independent external timestamp attestation.

### Pilot data-room/package integrity
`freight/pilot_package.py` now provides machine-checkable:
- source authorization;
- buyer/BU scope;
- source type;
- SHA-256;
- read-only pilot status;
- secret/credential exclusion flag;
- retention days;
- final package binding across data room, population, truth, sealed incumbent and opened incumbent.

Unauthorized, cross-scope, secret-bearing or non-read-only pilot sources fail closed.

### Hostile-input pre-parser boundary
`freight/input_guard.py` adds conservative pre-parser checks for:
- PDF;
- CSV;
- XML;
- EDI;
- X12.

It rejects:
- archives / archive magic;
- path-traversal filenames;
- non-allowlisted extensions;
- empty/oversized files;
- invalid UTF-8 text;
- XML DTD/entity constructs;
- NUL text;
- unrecognized EDI headers;
- overlong EDI segments.

Derived spreadsheet exports can neutralize formula-leading strings without mutating original evidence.

This is a **pre-parser boundary**, not an OS/container sandbox.

### Deterministic release/component provenance
`freight/release_provenance.py` deterministically produces:
- SHA-256 for committed Freight control files;
- exact component inventory from `COMPONENT_RIGHTS_REGISTRY.json`;
- full pinned 40-character upstream revisions;
- public-license/commercial-use-basis/runtime-status fields;
- aggregate component-inventory hash;
- aggregate provenance hash.

CI regenerates and verifies the snapshot deterministically.

This is not:
- a signed attestation;
- a legal opinion;
- a full SPDX/CycloneDX SBOM;
- proof of runtime/deployment configuration.

## Commercial control plane

- `freight/BUSINESS_MODEL.md` — ICP, offer ladder, pricing and fixed-fee margin rules.
- `freight/COMMERCIAL_QUALIFICATION.md` / `deal_economics.py` — deal routing and analyst-hour budget.
- `freight/COMMERCIAL_LEARNING.md` / `commercial_learning.py` — buyer-cohort anti-overfit calibration.
- `freight/DATA_READINESS_DIAGNOSTIC.md` / `readiness.py` — BLOCKED / CONDITIONAL / READY.
- `freight/PILOT_DATA_ROOM.md` / `pilot_package.py` — pilot source/package manifests.
- `freight/PILOT_PROTOCOL.md` — sealed incumbent + blind truth protocol.
- `freight/contracts.py` — scoped proof objects.
- `freight/input_guard.py` — pre-parser hostile-input boundary.
- `freight/settlement_store.py` — durable settlement attribution/reversal handling.
- `freight/pilot_reporting.py` — scoped proof-derived buyer metrics.
- `freight/release_provenance.py` — deterministic control/component provenance.
- `freight/SECURITY_AND_DATA_HANDLING.md` — buyer-facing current posture/non-claims.
- `freight/GAP_REGISTER.json` — deny-by-default Freight research authorization.
- `intelligence/domain_search_policies.json` — adaptive global policy binding to Freight gate.
- `freight/COMPONENT_RIGHTS_REGISTRY.json` — exact rights-operability inventory.
- `freight/RELEASE_AND_SECURITY_GATE.md` — controlled-pilot vs annual-deployment gates.

## Commercial / learning state

Freight Recovery v15.6 is **commercially specified, machine-gated, internally rehearsed, scope-bound, pre-parser hardened and deterministically provenance-checkable; EXP-001 remains externally unproven**.

Structured external Freight evidence remains:
- directly evidenced Freight revenue: **$0**
- directly evidenced Freight customer value: **$0**
- paid diagnostic/pilot/annual conversion: **none recorded**
- Freight ACTIVE_SEARCH gaps: **0**

No internal v15.6 security or engineering improvement changes those external facts.

## Current claim boundary

The repository now supports a controlled pilot with:
- explicit buyer/BU scope;
- machine-checkable source authorization/retention metadata;
- read-only source requirement;
- secret-bearing source rejection;
- exact shipment identity;
- sealed incumbent content binding;
- fail-closed proof/money semantics;
- fail-closed pre-parser checks;
- deterministic release/component provenance.

It does **not** yet prove:
- shared production database/object-store/API tenant isolation;
- production parser CPU/memory/time/network sandboxing;
- buyer-specific encryption configuration;
- signed release provenance;
- full buyer-required SBOM;
- incident-response/backup/audit operation;
- SOC 2 / ISO 27001 or other security certification.

## Remaining high-value blockers

1. first authorized real buyer population and later settlement;
2. executed Trenova/Opstrax hosted/SaaS/change-of-control rights where unresolved;
3. deployment-specific customer data-service cross-tenant isolation;
4. production parser sandbox/resource/network controls;
5. signed provenance/full buyer-required SBOM and deployment artifact;
6. backup/restore, logging/alerting and incident-response evidence for annual assurance.

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

**Externally evidenced paid diagnostic/pilot → authorized scoped data room → frozen population + sealed incumbent → buyer-owned truth → challenger-only validated finding or defensible clean result → buyer-approved action → issued credit/refund/remittance → unambiguous settlement → outcome record → annual assurance conversion.**

That external chain remains the primary path to materially increasing Freight Recovery's defensible value.
