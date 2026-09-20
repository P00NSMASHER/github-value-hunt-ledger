# Hunt 05 R14 — SAM historical-action manifest probe and evidence-memory component

Date: 2026-09-20
Lane: Gov Evidence / CAP-011 / EXP-006

## Executive result

This run materially narrows EXP-006 but does **not** close it.

A live public no-login probe of a known stale SAM action UUID (`99efe068a9e5419cadacd8ffe4ae4d04`, solicitation `127EAX26Q0103`) succeeded on the SAM website resource endpoint with the query parameters `excludeDeleted=false&withScanResult=false`. The response was HTTP 200 `application/hal+json` and returned five resource records with stable `resourceId`, `attachmentId`, name, `deletedFlag`, access state, export-control state, `fileExists`, and type. The corresponding public SAM opportunity page is not the latest family action: its history lists newer Sep 15/16/17 actions. Therefore **at least one non-latest historical action UUID remains publicly queryable for rich attachment metadata**.

This is a meaningful positive result for the proposed EXP-006 architecture: `action history -> per-action deletion-inclusive resource manifest -> append-only observation -> packet state` is technically viable on at least one stale action without permissioned Opportunity Management access.

It is **not yet evidence that the union of every historical action manifest is lossless**. Official GSA deletion semantics still state that when a resource is deleted with `deleteAll=true`, the deleted published resource will not appear in further revisions. The official documentation does not promise that every prior action UUID remains forever publicly queryable or that old manifests retain every pre-delete resource. Until the frozen ten-family corpus passes that test, independent polling snapshots remain prudent defense-in-depth.

## Live probe details

Public endpoint probed, without login and without downloading attachment contents:

`https://sam.gov/api/prod/opps/v3/opportunities/99efe068a9e5419cadacd8ffe4ae4d04/resources?excludeDeleted=false&withScanResult=false`

Result: HTTP 200; five public, existing, non-deleted files:

- `f53c64da447a417d9f67c7eac0cd4d80` — `127EAX26Q0103 QA2.docx`
- `556303a398a0436ea0f3ad42409c9842` — `127EAX26Q0103 QA1.docx`
- `e382bfc4008a4c8bb2a07ba557c3f817` — `Attachment 1 - Statement of Work.docx`
- `d33a7141888140caabc1ab4220e9b8b6` — `127EAX26Q0103.pdf`
- `fe270c886f5046ed99b25932d2c2bae2` — `Attachment 2 - Wage Determination.pdf`

All five reported public access, `deletedFlag=0`, `exportControlled=0`, `fileExists=1`, `type=file`.

Source-boundary interpretation: this is a website/internal public surface rather than the documented public Opportunities API contract. It must be treated as an observable first-party source with schema-drift/failure gates, not as a guaranteed stable API.

## Official-source cross-check

GSA's Opportunity Management API documentation provides the authoritative semantics needed to interpret the manifest fields even though that management API itself is permissioned:

- `/resources` supports an optional `excludeDeleted` parameter.
- Resource metadata includes `attachmentId`, `resourceId`, `fileExists`, `name`, `type`, `postedDate`, `accessLevel`, `exportControlled`, `explicitAccess`, `deletedDate`, `deletedFlag`, and `accessStatus`.
- Delete Resource has a required `deleteAll` flag. GSA states that when true, the resource is deleted from all versions and the deleted published resource will not show up for further revisions.

Consequence: latest/current resource state is structurally insufficient for history. A complete product must retain older successful observations and distinguish explicit source tombstones from inferred disappearance.

## Independent implementation candidate

### DeerSpotter/samgovsearch — current-source evidence memory / deterministic attachment extraction — STRONG COMPONENT — 25/30

- URL: https://github.com/DeerSpotter/samgovsearch
- Exact revision: `14c840690e38fe3e9eb6f04c13cbd0105ebbb756`
- Date inspected: 2026-09-20
- Public attention: 1 GitHub star at inspection; no repository license was exposed by GitHub metadata.
- Concrete capability: the repository implements no-key SAM website/internal discovery plus a Contract Brain evidence layer. It identifies analyzed sources by SAM `resourceId` + SHA-256 + parser version; persists source binaries and deterministic extraction runs/rows; performs native PDF extraction before OCR; handles DOCX/PPTX/XLSX/text/one-level ZIP; preserves exact locators; and marks extraction `complete`, `failed`, or `review_required` rather than semantically promoting extracted text automatically.
- Strongest verification: its Supabase edge function independently checks that a submitted `resourceId` is indexed under the claimed notice, re-downloads the public source, recomputes SHA-256 server-side, and rejects the ingest if bytes changed during processing. The schema preserves multiple hashes for one `resourceId` via `unique(resource_id, sha256)` and versioned parser runs.
- Why unusual: most SAM search wrappers stop at discovery/download. This one already contains much of the evidence-memory pattern needed by CaptureBrief: exact source identity, byte hash, parser version, normalized source rows, extraction status, deterministic reuse, and independent server-side hash verification.
- Buyer/problem fit: GovCon capture/proposal teams need source-backed document facts and a defensible proof that extracted text came from the exact SAM artifact analyzed.
- First paid wedge: use this pattern inside the Solicitation Packet Integrity Audit to emit artifact hashes and extraction provenance for each publicly retrievable packet document.
- Build/domain compression: high for evidence ingestion/extraction, plausibly weeks to a few engineer-months versus rebuilding browser + server verification, deterministic parsers, source-row locators, persistence, and resumable evidence from scratch.
- Rights/provenance: no root license detected by GitHub metadata at this revision. Under the user's standing assertion, repository-owned public material is separately commercially authorized; SAM data and any third-party parser dependencies/assets retain their own terms.
- Score: A4 + B4 + C5 + D4 + E4 + F4 = **25/30**.
- Strongest objection / red-team: this is not a historical packet oracle. The documented evidence-memory table is keyed to current notice/resource observations and does not itself model action UUID lineage, deletion-inclusive immutable manifest observations, source failures, or disappearance transitions. No root `tests/` directory was present at the inspected revision. The internal SAM endpoints are explicitly described by the project as less stable than the official public API.
- Combination: GSA/Data Services action lineage + per-action `excludeDeleted=false` manifest observations + `samgovsearch`-style `resourceId`/SHA/parser evidence memory + FAR/deviation resolver + PIID/IDV award lineage.
- Next action: adapt only the evidence-memory/extraction pattern behind an append-only action/manifest envelope. Do not let its current-notice cache define historical completeness.

## Third-party historical corroboration

Independent public procurement mirrors currently preserve multiple SAM action IDs under the same solicitation family. For `N4215826Q0036`, public mirrors show the Sep 14 action `dedde183bf2e4977a7afb963bf9f92a9` with one document and a later Sep 17 action `f23f6db8ffc94e8e92d40abe3fe8d8ce` with additional document state. This is useful corroboration that action-level attachment sets evolve, but third-party mirrors are not authoritative and cannot establish SAM completeness.

For `W50S8B-26-Q-A016`, current SAM evidence explicitly shows `Attachment 2 - Product Description.pdf` as `(Deleted)` on a non-latest Sep 17 action, while later mirrored family views contain a larger six-document packet. This remains an excellent EXP-006 tombstone fixture.

## Claims tested

### Supported
1. **A stale/non-latest action UUID can remain publicly queryable for rich attachment metadata.** Verified for `99efe068a9e5419cadacd8ffe4ae4d04` on 2026-09-20.
2. **Deletion-inclusive retrieval must be explicit.** Official schema exposes `excludeDeleted`; independent implementations/public examples intentionally use `excludeDeleted=false`.
3. **Current/latest manifests cannot be historical authority.** Official `deleteAll` semantics explicitly allow a resource to stop appearing in future revisions.
4. **Source-byte provenance can be made independently checkable.** `DeerSpotter/samgovsearch` verifies notice/resource linkage and server-side SHA before persisting extracted evidence.

### Not yet proven
1. Every historical action UUID remains publicly queryable indefinitely.
2. Historical action manifests retain resources after a later `deleteAll` operation.
3. Unioning all action UUID manifests reconstructs every attachment ever publicly visible for all ten frozen families.
4. The public website/internal resource endpoint is a stable contractual API surface.

## Commercial implication

The strongest near-term CaptureBrief wedge remains **Solicitation Packet Integrity Audit**, but the implementation can now be more concrete:

`family/action history -> deletion-inclusive manifest observation -> immutable raw manifest/body hash -> resourceId -> source-byte SHA -> deterministic extraction rows -> completeness state -> compliance/decision layer`

That creates proof for both **which files controlled** and **which exact bytes were analyzed**. The remaining moat-building test is historical losslessness.

## CAP / OPP / EXP / RAD handoff

- CAPABILITY DELTA: CAP-011 gains direct evidence that stale action UUIDs can be queried on the public manifest surface; source-byte proof can be layered underneath with the independently verified `samgovsearch` pattern.
- GRAPH EDGE: `DeerSpotter/samgovsearch@14c840690e...` STRENGTHENS CAP-011 evidence ingestion but CHALLENGES no historical completeness claim; stale SAM action manifest access STRENGTHENS EXP-006 feasibility.
- RADAR SIGNAL: reinforces RAD-008 qualitatively: authoritative state is multi-plane and temporal; artifact-byte provenance is a separate layer from action/manifest provenance.
- EXPERIMENT IMPACT: EXP-006 advances from hypothetical per-action access to one verified stale-action success. Keep status READY/PARTIAL, not PASS.
- COMMERCIAL IMPACT: higher confidence that packet-integrity proof can be built without forcing an official API key for every attachment-manifest check, subject to instability/fail-closed handling.
- NEGATIVE KNOWLEDGE: current notice caches and current resource inventories cannot define packet history; successful one-action retrieval does not establish historical retention guarantees.

## Search policy update

Continue `STRAT:first-party-history-manifest-triangulation`, but narrow the next run to a **deleteAll retention fixture** rather than broad SAM wrappers. Prefer one family where a resource is explicitly deleted and where at least one predecessor and one successor action UUID are known. Query both action manifests with explicit deletion inclusion, compare stable resource IDs, and distinguish: predecessor retains resource / successor explicit tombstone / successor disappearance / source failure.

## Next highest-value question

**For one frozen family with an explicit deleted resource, does querying the predecessor action UUID after deletion still return that resource with `excludeDeleted=false`, and does the successor return an explicit tombstone or simply omit it?**
