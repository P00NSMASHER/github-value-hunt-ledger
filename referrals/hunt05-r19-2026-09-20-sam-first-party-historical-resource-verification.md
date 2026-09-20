# Hunt 05 R19 — first-party historical SAM resource membership verified while semantic identity/bytes remain unresolved

Date: 2026-09-20
Lane: Gov Evidence / CAP-011 / EXP-006
Strategy: `STRAT:first-party-history-manifest-triangulation`

## Executive result

This run revisited the unresolved historical object in SAM Notice ID `N6600126Q6264 — KVM MOUNT FABRICATION` and improved the evidence state without overclaiming the filename.

The public unauthenticated SAM resource-manifest surface for historical action UUID `936993aa0dc94d7f832dbdcf634023d9`, queried with explicit deletion inclusion, directly returned resource ID `e0cca665190b4d15b31497aadd362e25` as a member of that historical action. The response exposed at least:

- `opportunityId = 936993aa0dc94d7f832dbdcf634023d9`
- `attachmentId = 1a1b36917cd144e18a0dc28a506667d3`
- `resourceId = e0cca665190b4d15b31497aadd362e25`
- `attachmentOrder = 29`
- `accessStatus = public`
- `effectiveDeletedDate = 2026-08-05T21:59:53.206+00:00`

This independently upgrades the object from the prior run's **inferred historical source object** to **VERIFIED historical action membership/source object**.

However, the extracted public response available in this run did not expose the object's complete `name` field in a way that could be independently retained, and a direct unauthenticated public download request for the resource ID returned HTTP 400. Therefore the exact semantic identity `e0cca... == C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0001` remains **INFERRED**, not VERIFIED, and the artifact bytes remain `BYTES_UNAVAILABLE_AT_OBSERVATION`.

The current first-party SAM notice still instructs offerors to review `C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0001` while also identifying Amend 0004 as the source of current award evaluation factors. The current named attachment inventory does not expose a named Amend 0001 file. No first-party source inspected in this run established that Amend 0004 completely incorporates/supersedes all requirements from Amend 0001.

The safe packet state therefore remains:

`VERIFIED_ACTION_MEMBERSHIP + SEMANTIC_IDENTITY_INFERRED + BYTES_UNAVAILABLE + REFERENCE_UNRESOLVED`

not `complete_public`.

## First-party evidence inspected

### Current notice and family history
Current public action: `4f722ea79ce74faea16eec7a764dae3b`.

The public SAM page exposes Notice ID `N6600126Q6264` and links to historical actions including `936993aa0dc94d7f832dbdcf634023d9`, which itself displays a stale-action warning pointing to a newer action.

The current notice text continues to name Amend 0001 in the review list and separately identifies Amend 0004 for current award evaluation factors. Its current visible named attachments omit Amend 0001.

### Historical action resource manifest
Public read-only request used:

`https://sam.gov/api/prod/opps/v3/opportunities/936993aa0dc94d7f832dbdcf634023d9/resources?excludeDeleted=false&withScanResult=false`

The response directly associated `e0cca665190b4d15b31497aadd362e25` with action `936993...` and exposed public/deletion-state metadata listed above.

This is stronger than the prior R18 evidence, which inferred the source object from a historical five-document packet after four other resources were mapped to Attachments 1–4.

### Artifact byte check
Public read-only request used:

`https://sam.gov/api/prod/opps/v3/opportunities/resources/files/e0cca665190b4d15b31497aadd362e25/download`

Observed result: HTTP 400. No login, credentials, controlled/restricted artifact, or paid access was used.

### Official schema/contract boundary
GSA's documented Opportunity Management API defines attachment metadata fields including `resourceId`, `name`, `fileExists`, deletion state and access state and documents download by resource ID, but that documented management surface requires authorization/API credentials. The unauthenticated `/api/prod/opps/v3/.../resources` surface used above is therefore useful first-party observational evidence but must not be treated as a stable public API contract.

## Interpretation discipline

### VERIFIED
1. `e0cca665190b4d15b31497aadd362e25` is a first-party SAM source object associated with historical action `936993aa0dc94d7f832dbdcf634023d9`.
2. That object was exposed as public-access metadata in the observed historical-action manifest.
3. The observed manifest exposed `attachmentId = 1a1b36917cd144e18a0dc28a506667d3`, `attachmentOrder = 29`, and `effectiveDeletedDate = 2026-08-05T21:59:53.206+00:00` for the object.
4. The current public SAM notice continues to reference Amend 0001 while the current named attachment inventory does not provide a named Amend 0001 file.
5. The direct public download route for `e0cca...` returned HTTP 400 at observation time.

### INFERRED, NOT VERIFIED
1. `e0cca665...` is likely the historical source object for `C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0001`. The inference remains strong because the prior historical five-document observation contained Amend 0001 plus Attachments 1–4, four resource IDs map to those four numbered attachments, and `e0cca...` was the unmatched fifth source object. Exact first-party filename/bytes were not independently recovered this run.

### NOT VERIFIED
1. Exact filename, MIME type, size, content hash or bytes for `e0cca665...`.
2. Whether HTTP 400 represents permanent deletion, delivery-route behavior, or another public delivery limitation.
3. Whether a separate first-party historical metadata route still exposes the exact filename without authenticated management access.
4. Whether Amend 0004 fully and explicitly incorporates/supersedes every requirement from Amend 0001.

## Capability / experiment consequence

The packet model needs three separately governed facts:

1. **Action/source membership** — did this resource belong to this solicitation/action family?
2. **Semantic identity** — what exact named artifact does this resource represent?
3. **Byte availability/evidence** — can the exact artifact bytes be lawfully retrieved and hashed at this observation time?

A source object can be VERIFIED on axis 1 while remaining INFERRED on axis 2 and UNAVAILABLE on axis 3. CaptureBrief must not collapse these into one boolean `attachment_exists` field.

Recommended evidence tuple:

`(notice_family, action_uuid, observation_id, resource_id, attachment_id, source_state, semantic_identity_state, byte_state, observed_at, raw_manifest_hash, artifact_hash_if_any)`

## Commercial / value handoff

### CAPABILITY DELTA
CAP-011 gains a stricter tri-state identity boundary: verified action membership does not imply verified semantic filename/content identity, and neither implies retrievable evidence bytes.

### GRAPH EDGE
Strengthen the packet graph to preserve:

`ACTION --CONTAINS_OBSERVED_SOURCE_OBJECT--> RESOURCE_ID --MAY_REPRESENT--> NAMED_ARTIFACT --HAS_BYTES_AT_OBSERVATION--> ARTIFACT_HASH`

The `MAY_REPRESENT` edge must remain inferred until first-party metadata or preserved bytes prove it.

### RADAR SIGNAL
RAD-008 strengthens qualitatively: first-party public authority can expose durable source-object identity/state while the human-readable artifact identity and bytes become harder or impossible to recover later. This increases the value of append-only lawful observation capture.

### EXPERIMENT IMPACT
EXP-006 gains an explicit adversary:

`VERIFIED_HISTORICAL_RESOURCE_MEMBERSHIP_BUT_FILENAME_UNVERIFIED_AND_BYTES_UNAVAILABLE`

Expected state: packet stays non-green unless an earlier immutable snapshot or authoritative supersession closes the dependency.

### COMMERCIAL IMPACT
The Solicitation Packet Integrity Audit can distinguish three buyer-relevant outcomes ordinary scrapers flatten together:
- the government record proves an object belonged to the packet;
- the system can or cannot prove what exact document that object was;
- the system can or cannot reproduce the bytes that governed the historical decision.

This prevents false confidence when metadata survives longer than document evidence.

### NEGATIVE KNOWLEDGE
- resource membership != semantic document identity;
- semantic identity != byte availability;
- HTTP 400 is not proof of permanent deletion unless source semantics establish it;
- an undocumented first-party UI endpoint is observational evidence, not a contractual integration guarantee;
- current later amendment number is not automatic proof that an older still-referenced amendment can be ignored.

## Score / disposition

**27/30 capability/experiment finding. No new repository promotion.**

A5 speed-to-revenue relevance + B5 buyer value + C5 architecture/build compression + D4 rarity + E4 evidence quality + F4 operational clarity.

Evidence quality remains 4 because the key historical source membership is now first-party verified but the exact semantic filename and bytes remain unresolved.

## Search policy update

Do not spend another full run repeatedly guessing public metadata routes for `e0cca...` unless a new first-party surface appears. The unresolved identity has been narrowed enough to become a planted acceptance state rather than an open-ended search sink.

Move the next frozen-family pass to `FA524026Q0041`, whose current first-party SAM page exposes both a current `Solicitation - FA524026Q0041 Rev 1 (17SEP26).pdf` and a similarly named prior `Solicitation - FA524026Q0041 Rev 1.pdf` marked Deleted across a four-action history. Test whether those rows have distinct source-object IDs, whether the historical action union retains both after successor changes, and whether a historical action response retroactively reflects later deletion state.

## Next highest-value question

**Across the four historical actions for `FA524026Q0041`, do the current and deleted same-family solicitation revisions have distinct SAM resource IDs, and does `UNION(historical action manifests)` preserve any source object absent from the latest deletion-inclusive manifest?**
