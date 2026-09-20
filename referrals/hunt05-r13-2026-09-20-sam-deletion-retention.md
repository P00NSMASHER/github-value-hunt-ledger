# Hunt 05 referral — SAM deletion retention boundary and lossless packet-history requirement

Date: 2026-09-20
Lane: Gov Evidence / CaptureBrief
Primary graph edge: CAP-011 -> EXP-006
Radar edge: RAD-008 temporal machine-readable public authority
Search strategy: STRAT:first-party-history-manifest-triangulation

## Executive finding
The highest-value open question from the previous run is now materially narrower: **SAM does expose explicit attachment tombstones, but a latest/current manifest cannot be assumed to preserve every historically removed attachment forever.**

Three independent evidence layers converge:

1. **Official GSA Opportunity Management documentation exposes `excludeDeleted` on attachment-metadata reads and `deleteAll` on resource deletion.** The documentation states that when `deleteAll=true`, deleted published resources **will not show up for any further revisions that will be created**. Therefore a successor action/revision can legitimately omit an attachment that existed on an earlier action even though the logical solicitation family still needs that attachment recorded as historical/superseded evidence.
2. **Current public SAM pages sometimes preserve explicit deleted entries in the current action.** On 2026-09-20, `W50S8B-26-Q-A016` publicly listed `Attachment 2 - Product Description.pdf (Deleted)` while later amendment/Q&A files remained current; `N6600126Q6264` listed `Amend 0003` as Deleted beside current `Amend 0004`; and `FA524026Q0041` listed a prior solicitation revision as Deleted beside the current revised solicitation. This proves explicit tombstones are real and commercially important, but not that they are exhaustive across later revisions.
3. **Independent implementations show the public resource endpoint is deliberately queried with `excludeDeleted=false`.** Govly's recorded SAM test traffic used `/resources?excludeDeleted=false&withScanResult=false`; `quirkyllama/sam_gov_scraper@2da380308be88ea9b57695f2809b22040821b25a` hard-codes the same parameter. By contrast, `chrisfulcher/orrery@89ae2218c031c2c46720783acfb44cea22e48636` calls `/resources` without an explicit `excludeDeleted` parameter and its live probe did not establish the endpoint default.

The architecture implication is decisive: **CaptureBrief needs an append-only per-action/per-observation manifest ledger. Explicit `deletedFlag=1` is useful evidence, but absence from a later successful manifest must never erase prior state or be interpreted as “never existed.”**

## Primary implementation challenged — `chrisfulcher/orrery`
- URL: https://github.com/chrisfulcher/orrery
- Exact revision: `89ae2218c031c2c46720783acfb44cea22e48636` (still repository HEAD when checked 2026-09-20)
- Public license: Apache-2.0
- Prior score: 28/30
- Revised score after red-team: **26/30 STRONG component**
  - A Speed to first revenue: 4/5
  - B Customer value / ceiling: 5/5
  - C Build/domain compression: 5/5
  - D Rarity / technical advantage: 5/5
  - E Evidence quality / completeness: 4/5
  - F Rights / deployment / operational clarity: 3/5

### What remains strong
`orrery` is still the best low-attention implementation found for the public SAM attachment plane. It:
- uses the keyless SAM web-interface resource endpoint;
- distinguishes manifest `checked`, `unknown`, and `failed` states;
- parses `accessStatus`, export control, `deletedFlag`, file existence and link/file type;
- preserves raw per-attachment manifest JSON and `last_seen_at`;
- rechecks after notice-version change or age interval;
- fails the ingestion run on unknown manifest shape;
- does not fetch restricted/export-controlled items;
- preserves off-site portal links as explicit dependencies;
- hashes downloaded public artifacts.

Those are unusually mature negative-state semantics for such a young repository.

### Newly verified gap 1 — deletion inclusion is implicit, not pinned
`src/orrery/sam/client.py` builds the manifest URL as:

`/api/prod/opps/v3/opportunities/{notice_id}/resources`

and sends only `Accept: application/hal+json`. It does **not** pin `excludeDeleted=false` or `withScanResult=false`.

That matters because official GSA schema exposes `excludeDeleted` as an optional parameter but does not define a safe default in the inspected documentation, while independent SAM consumers explicitly request `excludeDeleted=false` when they want the full attachment metadata plane. A commercial evidence system should not let an undocumented default decide tombstone visibility.

### Newly verified gap 2 — successful recheck does not sweep absent rows
`src/orrery/fetch/queue.py` upserts only items returned by the current successful manifest. On conflict, it refreshes metadata, `deleted_upstream`, raw manifest JSON and `last_seen_at`. After the loop it marks the notice `manifest_status='checked'`.

There is no inspected step that:
- snapshots the complete manifest body;
- records the set of resource/attachment IDs observed in each successful check;
- marks a previously seen resource as missing/disappeared when absent from a later complete response;
- distinguishes “explicit source deletion” from “not returned in this action/revision.”

A small independent SQLite replay of the exact UPSERT semantics was run as a falsifiable test:
- observation 1 returned `r1` and `r2`, both `deleted_upstream=0`;
- observation 2 successfully returned only `r2`;
- result: `r1` remained in the table with `deleted_upstream=0` and its old `last_seen_at`, while the notice-level manifest could still become `checked`.
- when a later observation explicitly returned `r1` with `deletedFlag=1`, the same UPSERT correctly changed `deleted_upstream` to 1.

Therefore Orrery handles **explicit tombstones**, but it does not currently convert **absence-after-success** into a typed historical state.

### Why official deletion semantics make this more than a hypothetical
GSA's documented resource deletion contract says `deleteAll=true` deletes a resource from all versions and that deleted published resources will not show up for future revisions. This creates a real family-level history problem:

`action A manifest: resource X exists -> deleteAll -> action B manifest: resource X may not appear`

A collector that stores only action B, or overwrites the family with action B's manifest, loses evidence that X ever existed. Even a collector that preserves a current attachment row but does not bind observations to action/version IDs cannot prove *which packet state controlled when*.

The correct state is not automatically `deletedFlag=1`; it can be a historical relation such as `superseded_or_removed_before_successor_action`, supported by the prior immutable observation and the action transition.

## Independent implementation evidence

### `govly/prompt_vcr@fe1db1ae01b453e1b5cacf974b74b020083c0c2c` — historical protocol evidence / 23/30 component
Govly's VCR cassettes preserve real SAM HTTP request/response fixtures from 2024. Multiple recorded requests call:

`/api/prod/opps/v3/opportunities/{id}/resources?excludeDeleted=false&withScanResult=false`

and returned self links preserve the same parameter. This is valuable because it independently shows that SAM consumers intentionally request deleted resources rather than relying on an unspecified default.

Commercial/build value is limited because this repository is test-recording infrastructure, not a turnkey ingestion engine, but it is strong protocol archaeology and a useful regression fixture.

### `quirkyllama/sam_gov_scraper@2da380308be88ea9b57695f2809b22040821b25a` — 18/30 negative comparator
The scraper hard-codes `excludeDeleted=false&withScanResult=false`, which is the correct retrieval instinct, but then persists only attachment ID/resource ID/name/type/extension/URL. It does not persist `deletedFlag`, `deletedDate`, access state or a manifest observation identity. It also skips an opportunity entirely if a contract row already exists, so it is not a temporal amendment/manifest ledger.

Use it as evidence for the request parameter, not as evidence-grade packet history.

### `Yazan-O/biddesk@8676b420e33dd7c8155fe9c6c9e5b3580778d127` — 18/30 negative comparator
`fetch_resource_links()` reads the same public manifest endpoint but deliberately returns only public, existing, undeleted files. It filters out any row where `fileExists != 1`, `deletedFlag` is nonzero, or access is not public. That is reasonable for a downloader but unsafe as the authority layer for packet completeness because tombstones and restricted dependencies vanish before normalization.

Its saved snapshot layer also merges new active notices into a prior snapshot while keeping old records, which is useful for demo continuity but does not create an attachment-state event ledger.

## Current public corpus confirmation
Fresh public SAM pages inspected 2026-09-20 independently confirm explicit deleted states are not theoretical:
- `W50S8B-26-Q-A016`: current public page lists `Attachment 2 - Product Description.pdf (Deleted)` along with current amendment/Q&A artifacts.
- `N6600126Q6264`: current public page lists `C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0003.docx (Deleted)` beside current `Amend 0004` and supporting attachments.
- `FA524026Q0041`: current page lists the current revised solicitation plus a prior same-family revision explicitly marked `(Deleted)`.

These examples show explicit tombstones survive at least some current-action presentations. They do **not** establish that every removed resource survives every later revision, and the official `deleteAll` rule is affirmative contrary evidence.

## EXP-006B revised acceptance contract
The attachment-lineage benchmark should now require all of the following:

1. **Explicit deletion-inclusive read:** request `excludeDeleted=false` on any surface that supports it; do not depend on endpoint defaults.
2. **Manifest observation identity:** every successful or failed check gets an immutable observation row carrying action/notice ID, source URL + query semantics, observed time, HTTP/source state, full-body hash, parser/schema version and complete-response flag.
3. **Per-entry observation rows:** bind `attachmentId`, `resourceId`, name, order, posted/deleted dates, `deletedFlag`, file existence, access/export-control state, type and raw entry to the observation.
4. **No destructive reconciliation:** a newer successful manifest never deletes old evidence rows.
5. **Typed transition logic:** compare successive successful manifests for additions, metadata changes, explicit tombstones and disappeared IDs. A disappeared prior resource becomes `disappeared_unexplained` or a version-transition state, not `never existed`.
6. **Action-aware carry-forward:** if a new SAM action/revision is created, historical attachments from predecessor actions remain linked to that action even if the successor manifest omits them.
7. **Failure quarantine:** 429/5xx/shape failure/transport failure creates no disappearance events because the manifest is not known complete.
8. **Completeness gate:** `complete_public` requires resolved action lineage + a successful deletion-inclusive manifest for every relevant action + all required public artifacts hashed + restricted/external dependencies explicitly represented.

### Planted regression cases
- resource explicitly returns `deletedFlag=1`;
- resource is present in action A but absent in successor action B after `deleteAll` semantics;
- resource is absent after a transient 429/5xx (must **not** create deletion/disappearance);
- legitimate 200/no-attachments response;
- restricted/export-controlled resource;
- off-site PIEE link;
- same business Notice ID across multiple action UUIDs;
- newer notice version triggers a new manifest observation before downstream analysis.

## Commercial impact
The product wedge becomes stronger, not weaker: **Solicitation Packet Integrity Audit** should sell proof of packet lineage rather than “download all current files.”

Buyer: federal capture/proposal teams and outsourced proposal shops.
Pain: a team can analyze or submit against a packet that silently lost a prior requirement, deleted attachment, amendment or controlled/external dependency.
First paid deliverable: one opportunity-family report with action graph, manifest observation ledger, explicit additions/deletions/disappearances, content hashes for public artifacts, restricted/external blockers and a fail-closed completeness state.
Money path: reduced proposal rework, avoided nonresponsive submissions, lower analyst labor, defensible compliance evidence.
Moat: historical source-state corpus + deterministic event reconciliation + failure semantics; the LLM summary itself is not the moat.

## Capability delta
CAP-011 should now specify **deletion-inclusive, append-only manifest observations** as part of evidence-grade solicitation authority. Current-state manifest parsing alone is insufficient.

## Graph edge
- GSA attachment metadata/deletion semantics -> DEFINES the authoritative resource-state boundary for CAP-011.
- `orrery@89ae...` -> IMPLEMENTS most current-state manifest acquisition but is CHALLENGED on deletion inclusion/default pinning and historical absence reconciliation.
- Govly VCR fixtures -> independently SUPPORT explicit `excludeDeleted=false` request semantics.
- EXP-006 -> strengthened with a concrete tombstone-recall and disappearance-negative benchmark.

## Radar signal
RAD-008 strengthens qualitatively, score unchanged: temporal public authority is not merely “versioned records.” It requires **non-destructive evidence retention across source revisions**, because an authoritative successor revision may legitimately stop returning an artifact that existed in the predecessor.

## Negative knowledge
- `deletedFlag` existence does not prove tombstone exhaustiveness.
- A successful latest manifest is not a historical packet ledger.
- Optional `excludeDeleted` must be pinned explicitly; undocumented defaults cannot support a proof claim.
- “Public existing undeleted files only” is a download policy, not an evidence model.
- A manifest recheck may be successful while a prior resource silently remains stale in a current-state table unless absence is explicitly reconciled.
- Source failure must never emit disappearance events.

## Cross-agent referrals
- Data/provenance lane: generalize an append-only `manifest_observation -> resource_observation -> transition` model usable across SAM and SLED procurement portals.
- SLED lane: search whether Bonfire/OpenGov/PlanetBids successor postings omit deleted/replaced files and whether current UI manifests expose tombstones; transplant the same disappearance negative fixture.
- CaptureBrief integrator: do not promote `complete_public` until EXP-006B passes with explicit deletion-inclusive reads and action-aware historical retention.

## Search policy update
Stop searching for additional generic SAM wrappers. Search only for:
- explicit deleted-resource/history semantics;
- per-action attachment snapshots;
- `excludeDeleted`/tombstone behavior;
- immutable manifest archives or VCR fixtures;
- source-generated action lineage;
- exact failure modes exposed by the frozen ten-family corpus.

## Next highest-value question
**If every historical action UUID in the frozen ten-family corpus is queried with `excludeDeleted=false`, can the union reconstruct every attachment ever publicly listed, including resources removed with `deleteAll`, or are there still family-level gaps requiring independent polling snapshots?**
