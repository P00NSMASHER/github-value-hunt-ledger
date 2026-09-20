# Hunt 05 R18 — SAM historical resource identity can outlive public artifact retrieval

Date: 2026-09-20
Lane: Gov Evidence / CAP-011 / EXP-006
Strategy: `STRAT:first-party-history-manifest-triangulation`

## Executive result

This run continued the frozen solicitation family `N6600126Q6264 — KVM MOUNT FABRICATION` and narrowed the unresolved Amend 0001 question.

The current first-party SAM notice still explicitly instructs offerors to **REVIEW ALL** listed attachments and names `C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0001`, while simultaneously stating that current award evaluation factors are in Amend 0004. The current attachment inventory does not supply a named Amend 0001 file. No first-party source inspected in this run established that Amend 0004 completely supersedes/incorporates every requirement from Amend 0001. Therefore the machine-safe state remains `referenced_artifact_unresolved`, not `complete_public` and not `superseded`.

A historical SAM-directory observation for action UUID `936993aa0dc94d7f832dbdcf634023d9` exposed five document download links. Four can be independently associated with the known Attachment 1–4 resources because the SAM redirect paths identify the same resource IDs observed in the current manifest:

- `5ce44ec810d548f8bb087127460801ee` — Attachment 1
- `772b07cde74b42d3a5029cf2ec0e5fdd` — Attachment 2
- `8a53fc89cae64576a321bdae278972c7` — Attachment 3
- `f2fd408b293f4c469d7502103b88c322` — Attachment 4

The fifth historical download link points to SAM resource ID:

- `e0cca665190b4d15b31497aadd362e25`

That fifth object is a **strong inferred candidate** for the historically referenced solicitation/amendment artifact because it is the only unmatched document in a five-document historical packet whose notice text names Amend 0001 plus Attachments 1–4. However, this run did **not** directly recover a first-party filename or artifact bytes for `e0cca665...`, so the exact identity must remain `INFERRED`, not `VERIFIED`.

Direct public retrieval of `https://sam.gov/api/prod/opps/v3/opportunities/resources/files/e0cca665190b4d15b31497aadd362e25/download` returned HTTP 400 during this run. The historical source object/reference therefore survives as an observable identifier while the bytes were not publicly retrievable through that download path at observation time.

This creates a new evidence state distinct from deleted/restricted/external/missing:

> `historical_source_object_observed_or_inferred + artifact_bytes_unavailable`

For evidence-grade solicitation reconstruction, retaining historical source identity is not enough. Public bytes and their hashes should be captured when lawfully available because later source retrieval may fail even while historical action/document references remain discoverable.

## External evidence inspected

### First-party current SAM notice
Current action: `4f722ea79ce74faea16eec7a764dae3b`.

Verified from the current public SAM page:
- Notice ID `N6600126Q6264` is active.
- Updated published date is 2026-09-17 10:34 PDT.
- The description states that award evaluation factors are in `... Amend 0004`.
- The same description still explicitly tells offerors to review `... Amend 0001` plus Attachments 1–6.
- Current named document inventories exposed by public mirrors omit Amend 0001.

### Historical chronology corroboration
A dated 2026-07-30 SAM Daily/FBO archive reproduces the solicitation notice at that time and shows that Amend 0001 plus Attachments 1–4 were part of the required packet.

A historical SAM-directory observation for action UUID `936993aa0dc94d7f832dbdcf634023d9` exposed five document links. Four resolve by resource identity to current-known Attachments 1–4; the remaining resource ID is `e0cca665190b4d15b31497aadd362e25`.

### Public byte retrieval check
The direct public SAM download path for `e0cca665190b4d15b31497aadd362e25` returned HTTP 400. No credentials, account access, controlled artifact, or restricted file was used.

## Interpretation discipline

### VERIFIED
1. The current first-party notice still names Amend 0001 as a document offerors should review.
2. The current notice separately identifies Amend 0004 as the source of current evaluation factors.
3. Current public document inventories do not expose a named Amend 0001 file.
4. Historical notice text shows that Amend 0001 was genuinely part of the solicitation requirements, not a newly introduced typo in the current notice.
5. A historical five-document observation contains four document resources that map to Attachments 1–4 and one unmatched source resource ID `e0cca665...`.
6. The public SAM download URL for `e0cca665...` returned HTTP 400 during this run.

### INFERRED, NOT VERIFIED
1. `e0cca665...` is likely the historical source object for Amend 0001 because it is the sole unmatched resource in the relevant five-document packet. Exact filename/bytes were not recovered, so do not promote this to verified identity.

### NOT VERIFIED
1. The exact filename, content hash, or bytes of `e0cca665...`.
2. Whether another first-party historical manifest surface still exposes richer metadata for this resource.
3. Whether Amend 0004 explicitly and completely supersedes/incorporates every requirement from Amend 0001.
4. Whether the HTTP 400 is permanent removal, endpoint behavior, a required query/header difference, or another public-delivery issue.

## New acceptance invariant — HISTORICAL BYTE AVAILABILITY

Reference closure needs separate source-object and artifact-byte states.

Recommended model:

`reference -> source_object_state -> artifact_byte_state -> parser/evidence state`

Where source-object state is one of:
- `VERIFIED_SOURCE_OBJECT`
- `INFERRED_SOURCE_OBJECT`
- `UNRESOLVED_SOURCE_OBJECT`

And byte state is separately:
- `BYTES_VERIFIED_HASHED`
- `BYTES_RESTRICTED`
- `BYTES_EXTERNAL_DEPENDENCY`
- `BYTES_UNAVAILABLE_AT_OBSERVATION`
- `BYTES_NOT_YET_CHECKED`

`complete_public` requires every controlling referenced artifact either to have verified bytes/hash, an authoritative source-backed supersession/incorporation edge, or an explicit non-public blocker that prevents a false completeness claim.

Historical source identity alone does not prove analyzable packet completeness.

## Commercial / capability impact

### CAPABILITY DELTA
CAP-011 gains a separate **historical byte-availability** dimension. Action membership, resource identity, observation-time source state and artifact bytes are all independent evidence axes.

### GRAPH EDGE
Extend the packet graph:

`notice/artifact -> REFERENCES -> historical_source_object -> OBSERVED_AT -> artifact_bytes/hash`

If source object exists but bytes cannot be recovered, retain the object and emit `artifact_bytes_unavailable` rather than deleting history or pretending the reference is resolved.

### RADAR SIGNAL
RAD-008 strengthens qualitatively: official public-source systems can retain historical references/identifiers while no longer serving the historical byte artifact through the observed public delivery path. Proof-carrying public-data systems therefore need proactive immutable artifact capture when lawful and available.

### EXPERIMENT IMPACT
Add EXP-006 adversary:

`HISTORICAL_REFERENCE_AND_RESOURCE_ID_SURVIVE_BUT_ARTIFACT_BYTES_UNAVAILABLE`

Expected state: packet cannot become `complete_public` solely from the surviving resource ID/reference; require prior immutable byte receipt or authoritative supersession.

### COMMERCIAL IMPACT
The Solicitation Packet Integrity Audit can distinguish a subtle but consequential risk ordinary opportunity scrapers miss: **the government record proves a required historical document existed, but today's public packet no longer lets the analyst retrieve the bytes needed to reconstruct what governed at that time.**

### NEGATIVE KNOWLEDGE
- historical resource ID != historical artifact availability;
- historical action/page existence != downloadable historical bytes;
- current later amendment number != proof of full supersession;
- current notice continuing to name an old amendment must be treated as a live unresolved dependency until source-backed closure exists;
- an inferred one-to-one mapping from packet cardinality must remain labeled inference until filename/metadata/bytes independently confirm it.

## Score / disposition

**29/30 capability/experiment finding. No new repository promotion.**

A5 speed-to-revenue relevance + B5 buyer value + C5 architecture/build compression + D5 rarity + E4 evidence quality + F5 operational clarity. E remains 4 because exact `e0cca665...` filename/bytes are not recovered and the causal meaning of HTTP 400 is unresolved.

## Search policy update

Continue the frozen-family EXP-006 work. For every historical action union, record not only resource presence/deletion but whether each resource's public bytes remain retrievable and hashable. Preserve public artifacts at first lawful observation rather than assuming historical endpoints will remain byte-complete later.

Do not spend external money or use authenticated/controlled access to chase an unavailable public artifact. First exhaust free first-party metadata/history surfaces and independent public observations.

## Next highest-value question

**Can a first-party public historical resource/manifest surface independently verify that `e0cca665190b4d15b31497aadd362e25` is Amend 0001, and if so does any public route still return its bytes—or must this packet remain permanently `referenced_artifact_unresolved / bytes_unavailable` absent a preserved earlier snapshot?**
