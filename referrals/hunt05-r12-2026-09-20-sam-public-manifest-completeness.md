# Hunt 05 referral — SAM public manifest completeness closes EXP-006 attachment-state gap

Date: 2026-09-20
Lane: Gov Evidence / CaptureBrief
Primary graph edge: CAP-011 -> EXP-006
Radar edge: RAD-008 temporal machine-readable public authority
Search strategy: STRAT:first-party-history-manifest-triangulation

## Executive finding
This run resolves the highest-value question left by Hunt 05's frozen 10-solicitation EXP-006 corpus more sharply than the previous run:

1. **SAM public Data Services bulk/history is useful for notice/action lineage, but it is not attachment-complete.** The official Get Opportunities API says it returns only the latest active version and directs users to Data Services for all versions. GSA's own production Solicitation Review Tool backfill code independently states that the public bulk Contract Opportunities extract contains solicitation metadata but **no attachment links**, and therefore deliberately sets metadata-only records to `Cannot Evaluate (Review Required)` instead of making a document-level compliance finding.
2. **A low-attention Apache-2.0 repository, `chrisfulcher/orrery`, implements the missing public attachment-state plane.** It live-probed the same unkeyed SAM.gov web-interface endpoint used by the SAM UI:
   `GET https://sam.gov/api/prod/opps/v3/opportunities/{notice_id}/resources`
   with `Accept: application/hal+json`.
   The returned manifest carries resource IDs, names, sizes/types, posted date, `accessStatus`, `exportControlled`, `deletedFlag`, `attachmentId`, order, file-existence and link/file type. Orrery stores those states, raw manifest JSON and last-seen time; it distinguishes public, restricted/export-controlled, deleted and off-site portal links; it re-checks manifests after a notice version changes; and it fails the run if the undocumented manifest shape drifts instead of silently producing a clean empty result.
3. This combination means **CaptureBrief can build a mostly keyless solicitation-packet integrity plane from legitimately public surfaces**: Data Services for notice/version lineage + SAM public UI manifest for attachment state + public file downloads for immutable artifact hashes. A SAM API key becomes primarily a latency/description enhancement rather than the core packet-completeness dependency.

The strongest remaining objection is historical attachment-state completeness: Orrery records the latest manifest metadata per attachment and explicit `deletedFlag`, but the inspected code does not create an append-only manifest-snapshot/version table nor mark a prior attachment deleted merely because it disappears from a later manifest. `last_seen_at` makes that repair possible, but it is not yet the same as a lossless historical packet ledger. That exact gap should be the next test rather than another generic SAM wrapper search.

## Phase B result — what public Data Services can and cannot prove
Official source implementation:
- `GSA/open-gsa-redesign@494b1312e9c6436474840befe6e1964da15932b3`
- `_apidocs/get-opportunities-public-api.md`

Verified contract:
- Get Opportunities v2 returns the **latest active version** only.
- GSA directs users to SAM Data Services for all versions.
- Active Data Services notices are updated daily; archived notices weekly.
- The public API's latest row exposes `resourceLinks`, but that does not make the bulk extract attachment-complete.

Official GSA production-code falsifier:
- `GSA/srt-api@7f529d53055492ab7470585d9bbd92ddfbd1e581`
- `server/scripts/ingest_bulk_ict.js`

Verified behavior:
- The script identifies `ContractOpportunitiesFullCSV.csv` as SAM's public no-key/no-quota bulk channel.
- It explicitly inserts **metadata only**.
- It explicitly records no compliance determination and sets `reviewRec = 'Cannot Evaluate (Review Required)'` plus `undetermined = true`.
- The source comment states why: the bulk extract contains **no attachment links**, while controlling requirements such as Section 508 can live in SOW/PWS/attachments. A metadata-only conclusion could therefore confidently say the language was absent when the relevant document was simply never read.

This is stronger than an inference from a missing CSV field: GSA's own application code treats bulk-without-attachments as insufficient evidence for document-level conclusions.

## Public Data Services filenames and row semantics
Independent implementations consuming the official public files converge on these surfaces:
- active: `Contract Opportunities/datagov/ContractOpportunitiesFullCSV.csv`
- archive: `Contract Opportunities/Archived Data/FY{year}_archived_opportunities.csv`

Orrery's `src/orrery/ingest/bulk.py` enumerates 47 bulk columns including `NoticeId`, `Sol#`, `PostedDate`, `Type`, `BaseType`, archive fields, agency/office identifiers, deadline, NAICS/PSC, set-aside, award metadata, contacts, link and description. It does **not** contain attachment/resource-link columns.

The implementation stores raw JSON and a SHA-256 hash, creates a `notice_versions` row only when the raw row changes, and keys fiscal-year archives through the official Data Services path. It also protects negative evidence: an active notice is deactivated only after a complete pass of the active extract and only relative to the extract's own source-generated cut time. If the cut time is unavailable, it clears nothing.

Its tests verify:
- changed raw rows create a new notice version while exact reruns do not;
- an API row wins conflicting bulk metadata while bulk may safely fill a missing description;
- mid-batch failure leaves committed rows/cursor recoverable and marks the run failed;
- active deactivation does not run on a partial pass or without a source cut time;
- deep API office hierarchy cannot always be reproduced from shallow bulk codes, and this limitation is explicitly tested.

## Frozen-corpus triangulation
The frozen EXP-006 Phase A corpus already showed that the SAM UI maintains multiple actions per business solicitation and attachment states such as Deleted, Controlled and external PIEE links.

This run cross-checked public bulk-derived publication lineage against live SAM history for representative corpus members:

### `127EAX26Q0103`
Live SAM page observed Sep 20:
- displayed action was Sep 14 and explicitly warned newer actions existed;
- History contained six actions: Sep 3, 9, 14, 15, 16, 17.
- attachment table on the Sep 14 action showed Q&A 1/2, SOW, solicitation PDF and wage determination.

A public processor built from SAM Data Services grouped six publication rows for the same solicitation number, matching the six-action history count. Its attachment projection, however, did not represent the complete UI packet/history.

### `127EAX26Q0105`
Phase A recorded five SAM History actions and an evolving packet with Q&A, manuals and site photos. The bulk-derived publication grouping exposed five publication rows, again supporting notice/action lineage, while its attachment projection was materially thinner than the live SAM packet.

### `FA524026Q0041`
Live SAM page observed Sep 20:
- four History actions;
- current revised solicitation plus Q&A and supporting files;
- a similarly named earlier revision explicitly marked `(Deleted)`.

Bulk-derived publication grouping exposed four publication rows, matching notice/action count, but its attachment projection did not reproduce the deleted/current attachment state.

Conclusion from these sampled cases: **Data Services is a credible public version/action source, not a complete attachment-state oracle.** The phase-B architecture should treat the two planes separately.

## Best new repository — `chrisfulcher/orrery`
- URL: https://github.com/chrisfulcher/orrery
- Exact revision inspected: `89ae2218c031c2c46720783acfb44cea22e48636`
- Created: 2026-09-08
- Public attention at inspection: 1 star / 0 forks
- Public license: Apache-2.0
- Status: **STRONG / MASTER referral**
- Score: **28/30**
  - A Speed to first revenue: 4/5
  - B Customer value / ceiling: 5/5
  - C Build/domain compression: 5/5
  - D Rarity / advantage: 5/5
  - E Evidence quality / reproducibility: 5/5
  - F Rights / deployment / operational clarity: 4/5

### What it contains
A self-hosted federal BD intelligence system combining:
- current SAM opportunities from API and public bulk/archive files;
- keyless attachment discovery/download;
- attachment text extraction/search;
- USAspending award history;
- SAM entity registrations/exclusions;
- Federal Hierarchy resolution;
- pursuit/workflow state and provenance.

The commercially important discovery for this lane is not the dashboard. It is the **manifest/currentness and fail-closed ingestion machinery**.

### Public SAM attachment manifest probe
`docs/notes/sam-manifest-probe.md` records a live probe on 2026-09-09 of:

`GET https://sam.gov/api/prod/opps/v3/opportunities/{notice_id}/resources`

with `Accept: application/hal+json`.

Observed behavior:
- notice with attachments: HTTP 200 with `_embedded.opportunityAttachmentList[].attachments[]`;
- notice with none: HTTP 200 with no `_embedded` key;
- unknown notice: HTTP 400 `Record not found`;
- file download: public 303 redirect to a short-lived S3 URL then 200;
- no API key and no SAM keyed-quota accounting for the manifest/download path.

Observed attachment-entry fields include:
`resourceId`, `name`, `mimeType`, `size`, `postedDate`, `accessStatus`, `exportControlled`, `deletedFlag`, `attachmentId`, `attachmentOrder`, `fileExists`, `type`.

The probe explicitly notes that `exportControlled` and `deletedFlag` arrive as string flags (`"0"` / `"1"`). It also explicitly classifies the endpoint as an **undocumented SAM web-UI interface**, not a published API contract, and responds conservatively: pin v3, parse strictly, retain raw entries, and fail on a shape the release cannot understand.

### Implemented state model
Migration `0015_attachment_manifest.sql` adds:
- notice-level `manifest_status`: `pending | checked | unknown | failed`;
- `manifest_checked_at`;
- attachment discovery source;
- declared size/type;
- `access_status`;
- `export_controlled`;
- `deleted_upstream`;
- raw `manifest_json`;
- `last_seen_at`.

The migration comment explicitly states that `resourceLinks` are only a first observation and are not the source of record, because amendments add files after a notice was initially ingested.

`src/orrery/fetch/queue.py` then implements the operational contract:
- manifests are re-read every seven days for active/open notices;
- a newer `notice_versions` observation makes the manifest due immediately;
- explicit unknown notices are terminal, while transient failures are eligible for later retry;
- manifest metadata refreshes on every sighting;
- a pending file becomes skipped without a request if the manifest declares it unfetchable;
- unexpected manifest shape closes the ingestion run failed instead of silently writing a partial/empty state.

### Tests verified beyond README
`tests/test_fetch_queue.py` verifies that:
- a bulk-backfilled notice with no `resourceLinks` can discover attachments through the manifest stage;
- a legitimate no-attachment 200 is recorded as `checked` rather than retried forever;
- an unknown notice becomes an explicit terminal state;
- malformed manifest shape raises `ManifestShapeError` and marks the run failed;
- HTTP 429 stops the manifest stage after the first rate-limit response;
- oversized, export-controlled and restricted files are skipped without attempting download;
- a newer notice version forces a manifest recheck;
- a second sighting refreshes metadata without re-queueing an already fetched file;
- an off-site `type=link` entry such as PIEE is preserved as an external procurement dependency and deliberately not fetched as if it were a SAM file;
- attachment failures distinguish at least gone/404, transport, store and size-policy outcomes.

`tests/test_sam_client.py` separately verifies:
- the manifest request is keyless and sends `Accept: application/hal+json`;
- no-attachment vs unknown-notice semantics;
- strict manifest shape validation;
- string access flags map correctly: export-controlled and restricted entries are non-public, and `deletedFlag=1` is recorded as deleted;
- public attachment downloads do not receive the SAM API key and are SHA-256 hashed on disk;
- keyed credentials are refused for off-host URLs and removed from request logs.

### Why this is rare / undernoticed
The repository has essentially no public attention, but it solves the exact edge EXP-006 exposed: public solicitation document state after the latest-only API and metadata-only bulk plane. It also does so with unusually mature negative-state semantics for a project created less than two weeks before inspection.

### Commercial path
Smallest paid wedge: **Solicitation Packet Integrity Audit**.

Input: a SAM solicitation number/notice family.
Output:
- business solicitation ID + action/version IDs;
- Data Services publication lineage;
- current manifest inventory per action;
- public/restricted/export-controlled/deleted/external states;
- content hashes for retrievable public artifacts;
- explicit completeness state and blocking reason;
- current packet used for downstream compliance analysis.

This can be sold before full CaptureBrief automation because the customer pain is independent of AI: proposal teams can waste hours or submit against stale/incomplete amendment packets.

### Build compression
Very high. Orrery supplies tested implementations for the two hard parts that were still open in CAP-011:
1. fail-closed public Data Services bulk/history ingestion with source-cut semantics and version hashes;
2. recurring keyless attachment-manifest acquisition with tombstone/access/external-link states.

A clean independent implementation would still be reasonable if product architecture differs, but this repository likely saves months of API/source-behavior discovery and negative-test design.

### Strongest objection / red-team result
The current implementation is **not yet a lossless historical attachment ledger**.

Verified from the inspected code:
- `deleted_upstream` is refreshed when the manifest explicitly marks a named attachment deleted;
- `last_seen_at` advances when the attachment is named again;
- but there is no inspected append-only `manifest_versions`/manifest-snapshot table;
- and no inspected sweep that converts “was present in an earlier manifest, absent from a later successful complete manifest” into an explicit disappearance/tombstone state.

This matters because a source can remove an item without returning that prior item with `deletedFlag=1`. CaptureBrief must not assume the explicit flag is exhaustive until tested on real action chains.

The second objection is operational: the manifest endpoint is undocumented. Orrery mitigates this correctly by failing closed on schema drift, but a commercial service should maintain a current live canary and a fallback path rather than treat the endpoint as contractual.

## Capability delta
CAP-011 can be strengthened from “solicitation packet/history reconstruction from first-party sources” into a concrete public-surface design:

`Data Services notice/action lineage -> public web-UI manifest state -> public artifact hash -> external/restricted dependency -> downstream authority decision`.

This makes “complete public packet” technically plausible without requiring permissioned Opportunity Management API access, subject to the historical-manifest caveat above.

## Graph edge
- `chrisfulcher/orrery@89ae...` -> IMPLEMENTS the missing attachment-state edge in CAP-011.
- GSA public API/Data Services -> authoritative notice/version plane.
- GSA SRT bulk backfill code -> independently proves bulk metadata alone is insufficient for document-level conclusions.
- Orrery manifest state -> TESTS and materially advances EXP-006.
- explicit restricted/deleted/external states -> strengthens RAD-008 and RAD-001 proof-carrying operational software.

## Radar signal
**RAD-008 is strengthened, score unchanged.** The new signal is that machine-readable public authority can require multiple first-party planes from the same government system: current API, bulk/version files, UI manifest, artifact downloads and source-health state. A single “official API” endpoint is not automatically the full authority surface.

**RAD-001 is also strengthened, score unchanged.** The packet itself can carry evidence of why a downstream answer was permitted or withheld: artifact hash, action/version, manifest check, access/deletion status and unresolved dependency.

## Experiment impact — EXP-006
The experiment should now split into two falsifiable questions:

### EXP-006A — notice/action lineage
For each of the frozen ten solicitation families:
1. enumerate public Data Services rows across active + relevant FY archive;
2. normalize business solicitation number separately from action NoticeId;
3. compare ordered rows to the frozen SAM History actions;
4. require no silent deduplication by solicitation number;
5. source lag/failure must produce `history_unresolved`, never `complete_public`.

### EXP-006B — packet/attachment lineage
For each public action NoticeId:
1. fetch the public manifest with the pinned Accept header;
2. store raw manifest + hash + observation time;
3. normalize each entry by stable resource/attachment identity;
4. preserve `accessStatus`, export control, deleted flag, file existence and link-vs-file type;
5. download only permitted public files and hash bytes;
6. compare successive successful manifests for additions, explicit deletions, changed metadata and **disappearances**;
7. mark off-site portal links as explicit external dependencies;
8. only emit `complete_public` when version/history and manifest checks both completed successfully and all required public artifacts are accounted for.

A planted negative should remove a previously seen manifest item without setting `deletedFlag`; the engine must emit a disappearance/tombstone or unresolved transition rather than silently forgetting it.

## Commercial impact
Buyer: small/midsize federal primes, capture/proposal teams, outsourced proposal shops and consultants.

Painful problem: teams routinely download one current SAM page or forwarded solicitation packet and can miss a later action, revised file, deleted/superseded attachment, controlled dependency or off-SAM PIEE package.

First paid wedge: fixed-price `Solicitation Packet Integrity Audit` with evidence manifest and change timeline.

Money path: reduced wasted proposal labor, prevented stale-packet submissions/compliance misses, and a defensible foundation for higher-value automated compliance/capture intelligence.

Build compression: likely several engineer-months of source discovery, failure-state design, public attachment acquisition and regression-case construction.

Moat: long-lived observed manifest/version histories and buyer-specific packet-change/outcome data, not the underlying public endpoints themselves.

## Rights / provenance
- Orrery repository code: Apache-2.0 at inspected revision.
- SAM/GSA source data: first-party public government source; preserve exact source URL/version/observation time.
- Permissioned/controlled files: do not access without authorization; preserve only public metadata and explicit access-required state.
- Off-site portal dependencies such as PIEE retain their own access/terms. An external link is evidence of dependency, not permission to fetch protected content.
- The user-provided standing commercial authorization for public GitHub repository-owned code does not extend to third-party data/standards/external services.

## Negative knowledge
- **Do not use Data Services alone for solicitation packet completeness.** Official GSA code says the bulk extract has no attachment links.
- **Do not use one current SAM action as the solicitation family.** Frozen corpus proves business IDs and action UUIDs are separate layers.
- **Do not infer no attachments from zero attachment rows.** A successful manifest check is a distinct fact.
- **Do not infer deletion only from absence.** Preserve explicit source deletion separately from derived disappearance; both need evidence.
- **Do not trust an undocumented endpoint fail-open.** Unexpected manifest shape must taint the run and completeness state.
- **Do not fetch restricted/export-controlled or authenticated external content without authorization.** Keep access state explicit.
- **Do not keep hunting generic SAM wrappers** unless the frozen corpus reveals a new authority/currentness gap.

## Cross-agent referral
MASTER Integrator / CaptureBrief owner:
- Consider `chrisfulcher/orrery@89ae2218c031c2c46720783acfb44cea22e48636` as a 28/30 strong CAP-011 component and potential MASTER entry because it closes the exact missing public attachment-state edge exposed by EXP-006 rather than duplicating a known wrapper.
- Amend EXP-006 to separate notice/action completeness from packet/attachment completeness and add a missing-without-deletedFlag adversarial case.

Data/provenance specialist:
- Generalize an append-only `manifest_observation` envelope: `{source, family_id, action_id, observed_at, raw_hash, source_health, complete_response, entries[]}` and derive add/change/delete/disappear events without overwriting evidence.

SLED specialist:
- Apply the same design to Bonfire/OpenGov/PlanetBids: source-level posting history and attachment manifest are separate evidence planes; disappearance, restriction and off-site dependency must remain first-class states.

Exact unanswered technical question: **Across the frozen ten solicitation families, do SAM's public manifests return every prior attachment as an explicit `deletedFlag` tombstone when it leaves the live packet, or do some files simply disappear between successful action/manifest observations?**

## Search policy update
Prefer searches that close a concrete authority edge in EXP-006. For SAM-like systems, query for implementation evidence around `resources`, `manifest`, `deletedFlag`, `accessStatus`, `fileExists`, `last_seen`, `history`, `archive`, `source_generated_at`, `complete pass` and `shape error`. Stop generic opportunity/MCP wrappers unless they implement one missing state better than the current stack.

Reusable skill refinement: **first-party history + public manifest triangulation**
- use official docs to identify current-vs-history boundary;
- find first-party production code that states what a bulk/export plane omits;
- inspect the public UI's machine-readable document manifest separately;
- require explicit no-data vs failed vs unknown vs restricted vs deleted semantics;
- compare live/frozen examples before promoting completeness claims;
- store raw version/manifest observations so later parser improvements can replay exact source state.

## VALUE HANDOFF
1. **Capability delta:** mostly keyless solicitation packet integrity from Data Services history + public SAM attachment manifest + immutable file hashes.
2. **Graph edge:** directly strengthens CAP-011 and materially advances EXP-006; contributes evidence to RAD-008 and RAD-001.
3. **Radar signal:** temporal public authority increasingly consists of multiple machine-readable source planes, not one canonical API response.
4. **Experiment impact:** EXP-006 can now test notice/action lineage and attachment lineage separately, with explicit disappearance-vs-deletion negatives.
5. **Commercial impact:** fixed-price packet-integrity audits can be sold before full CaptureBrief SaaS; downstream compliance becomes safer because analysis is gated on packet evidence.
6. **Negative knowledge:** public bulk history is metadata/version evidence, not an attachment-complete packet; explicit source deletion and derived disappearance must not be conflated.

## Next highest-value question
Across the frozen ten solicitation families, do SAM's public manifests return every prior attachment as an explicit `deletedFlag` tombstone when it leaves the live packet, or do some files simply disappear between successful action/manifest observations?