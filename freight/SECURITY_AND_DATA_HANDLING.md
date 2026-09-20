# Freight Recovery — Security and Data Handling

Updated: 2026-09-20

This document describes the current **controlled-pilot security posture** and the controls that remain required before a shared production SaaS deployment.

## What the current pilot model enforces in code

- **Buyer + business-unit scope is carried through proof objects.** Findings, authority, truth, incumbent submissions, settlements, recovery certificates and pilot reports must remain in one buyer/BU scope.
- **Shipment-level finding identity is explicit.** A finding must bind to the exact frozen invoice + shipment row; matching only an invoice number is not sufficient.
- **Incumbent output is sealed before truth is opened.** The incumbent source SHA-256, buyer/BU scope and frozen population hash are sealed first; opening the output later binds that sealed submission to buyer-owned truth.
- **Pilot source manifests are machine-checkable.** Sources must be authorized, read-only for the controlled pilot, scope-matched, SHA-256 identified, retention-bounded and marked secret-free.
- **Credentials/secrets are not evidence.** A source explicitly marked as containing secrets is rejected from the evidence room.
- **Unsupported or ambiguous money remains $0.** Existing truth/settlement/recovery gates continue to fail closed.
- **Pre-parser input guard exists for PDF/CSV/XML/EDI/X12.** Oversized files, archives, path-traversal names, XML DTD/entity constructs, invalid text encodings, unrecognized EDI headers and overlong EDI segments are rejected before domain parsing.
- **Spreadsheet export formula cells are neutralized.** Source evidence remains immutable; derived spreadsheet exports can neutralize formula-leading text.
- **Release provenance is reproducible from the checkout.** Control-file hashes and the exact component-rights inventory are generated deterministically in CI.
- **Data lifecycle state is fail-closed.** Pilot sources become lifecycle census entries; retention defines deletion scope; only explicit external confirmation may produce `DELETE_CONFIRMED`; unresolved delete outcomes remain `DELETE_UNKNOWN`.
- **Source observation has three states.** `PRESENT`, `VERIFIED_EMPTY`, and `UNAVAILABLE` are distinct; `VERIFIED_EMPTY` requires completeness evidence.
- **Application audit records are append-only/hash chained.** Buyer/BU-scoped records detect mutation/reordering inside the supplied audit set.
- **Standards-shaped supply-chain artifacts are deterministic.** CI produces a CycloneDX 1.6-shaped SBOM and unsigned in-toto/DSSE-shaped payload for later external signing.

## What this does NOT claim

The current repository does **not** by itself prove:
- a deployed shared multi-tenant production database is isolated correctly;
- parsers run in a hardened OS/container sandbox;
- transport/storage encryption for a specific buyer environment;
- externally signed release provenance;
- a complete transitive deployment SBOM (the repository now emits a deterministic partial CycloneDX 1.6-shaped SBOM);
- independent external timestamp attestation;
- SOC 2 / ISO 27001 / other certification.

Those are deployment or external-assurance facts and must not be inferred from repository tests.

## Pilot data minimization

For a controlled pilot:
1. define one buyer and business unit;
2. request only the historical population and authority/evidence needed for the agreed test;
3. use read-only exports or read-only access where possible;
4. do not request passwords, API secrets, private keys or unrelated customer records;
5. record source SHA-256 and authorization/retention metadata;
6. keep incumbent output sealed until buyer-owned truth is frozen;
7. delete/return pilot data according to the agreed retention plan.

## File-ingestion boundary

Accepted pre-parser formats are currently limited to:
- PDF
- CSV
- XML
- EDI / X12

Archives are rejected rather than recursively unpacked. This is an intentional fail-closed choice for the first pilot.

The pre-parser guard is not a substitute for later parser isolation. Before annual/shared service deployment, document parsers should execute with low privilege, no ambient production credentials, bounded CPU/memory/time and no unintended network access.

## Tenant/business-unit isolation

Current proof-layer controls reject:
- authority from another buyer/BU;
- findings from another buyer/BU;
- findings attached to the wrong shipment row;
- incumbent submission/output from another buyer/BU;
- settlement events from another buyer/BU.

This is necessary but not sufficient for a shared data service. Cross-tenant negative tests must also run against the actual database/object-store/API authorization layer used for real customer data.

## Release and component provenance

`freight/release_provenance.py` deterministically emits:
- SHA-256 for the committed Freight control files;
- component inventory from `COMPONENT_RIGHTS_REGISTRY.json`;
- exact 40-character upstream revisions;
- public-license and commercial-use basis fields where recorded;
- an aggregate provenance hash.

This is a reproducible component/provenance inventory, **not a signed attestation** and not a legal opinion.

## Buyer-facing security statement

For an initial pilot, Freight Recovery should be represented as a **controlled, read-only, human-reviewed acceptance engagement** using scope-bound evidence and fail-closed proof rules.

Do not represent it as an already-certified enterprise SaaS security platform until the deployment-specific controls above are implemented and independently evidenced.


## Retention, deletion and source-observation semantics

`freight/data_lifecycle.py` applies the research-derived **CENSUS / SCOPE / PROOF** separation:

- data-room manifest = CENSUS of in-scope pilot source objects;
- retention days / delete-after = SCOPE;
- explicit external deletion confirmation = PROOF.

A source disappearing, a delete call timing out, or a follow-up read failing does **not** prove deletion. The state remains `DELETE_UNKNOWN` until explicit confirmation evidence exists.

Source observations separately record:
- `PRESENT`;
- `VERIFIED_EMPTY` with completeness evidence;
- `UNAVAILABLE`.

This prevents an unavailable settlement or document source from becoming a false “nothing happened” conclusion.

## Audit and release evidence

`freight/audit_ledger.py` provides application-level buyer/BU-scoped append-only hash-chain evidence. It detects mutation and reordering of the supplied record set but is not external trusted timestamping.

`freight/sbom.py` creates a deterministic CycloneDX 1.6-shaped document covering pinned Freight repository components and direct pinned CI Python dependencies.

`freight/release_attestation.py` creates an in-toto Statement v1-shaped payload in an **unsigned** DSSE envelope. Repository-generated signatures are intentionally forbidden so this payload cannot be mistaken for independently signed provenance.

A production release may later send the deterministic payload to an approved external signing identity/key and record signer/verifier evidence separately.
