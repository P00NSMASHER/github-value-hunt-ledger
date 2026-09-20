# Hunt 05 R16 — SAM historical-action manifest union / resource-identity verification

Date: 2026-09-20
Lane: Gov Evidence / CAP-011 / EXP-006
Strategy: `STRAT:first-party-history-manifest-triangulation`

## Executive result

This run closes the two highest-value questions left by Hunt 05 R15 for one frozen EXP-006 solicitation family and establishes a stronger failure mode than the prior hypothesis.

For SAM Notice ID `W50S8B-26-Q-A016`:

1. The old 143,690-byte `Attachment 2 - Product Description.pdf` and its replacement 278,832-byte file have **different SAM `resourceId` values** despite having the exact same filename.
2. The current deletion-inclusive manifest contains both the old tombstone and the replacement, proving filename is not source-object identity.
3. More importantly, another deleted resource (`Attachment 5 - Questions and Clarifications.pdf`, resourceId `00a43d7e02184a02950290925d972b1e`) is present in historical action manifests but is **absent from the latest action manifest even when queried with `excludeDeleted=false`**.
4. Therefore a latest deletion-inclusive manifest is **not lossless historical attachment authority**. For this live family, the union of historical action manifests contains one resourceId that the latest manifest no longer returns.
5. Historical action manifest responses are also not immutable publication-time snapshots: querying the Sep 16 action on Sep 20 returns the old Product Description with a Sep 18 deletion timestamp. Action membership and current resource state must therefore be modeled separately from what was observed at the action's publication time.

This materially advances `EXP-006`: the required architecture is now empirically justified as **action-history union + deletion-inclusive per-action observations + append-only local observation history**, not merely current manifest + tombstones.

## First-party action history

Live SAM.gov history for `W50S8B-26-Q-A016` was inspected on 2026-09-20. The solicitation-family history contained:

1. `bdd8de7d21074ac7bf54d9dbdd1d6049` — Sources Sought (Original), Sep 04 2026 08:56 pm EDT
2. `8b5632ccc61143c2a1524bfa1771064c` — Solicitation (Original), Sep 16 2026 11:06 am EDT
3. `de2a58ef32f841eb80ad6df5a3508c0b` — Solicitation (Updated), Sep 16 2026 03:39 pm EDT
4. `901ddb2a6f6f40979dca8ab26cbc5c39` — Solicitation (Updated), Sep 17 2026 07:21 am EDT
5. `03dbaaf6edd44b32ab961dab0bf6ec86` — Solicitation (Updated), Sep 17 2026 10:18 am EDT
6. `740398b03fdc4eb3afad685884d6f3f4` — Solicitation (Updated), Sep 18 2026 08:50 am EDT
7. `c799a091e7d649388583d224d67032cc` — Solicitation (Updated/current), Sep 18 2026 12:48 pm EDT

All six solicitation action UUID resource endpoints were queried directly from the public SAM web API with explicit:

`?excludeDeleted=false&withScanResult=false`

No login was used. No controlled/export-restricted file contents were accessed or downloaded.

## Manifest progression observed on 2026-09-20

### Action `8b5632...` — 3 resources
- `d5d2dd35dfae44f78665d30d172f38d9` — Attachment 1 — 3,312,440 bytes — current
- `53901ef77baa40da88ff1a8cfa1b71db` — Attachment 2 Product Description — 143,690 bytes — `deletedFlag=1`, deletion timestamp `2026-09-18T16:48:14.059Z`
- `2553df4e790c4eb59c7396d22a25d2d6` — Attachment 3 Price Schedule — 21,139 bytes — current

### Action `de2a58...` — 3 resources
Same three `resourceId` values as `8b5632...`, including the old Product Description now returned with the later Sep 18 tombstone.

### Action `901ddb...` — 3 resources
Same three `resourceId` values again, including the old Product Description tombstone.

### Action `03dbaaf...` — 5 resources
Adds:
- `00a43d7e02184a02950290925d972b1e` — Attachment 5 Questions and Clarifications — 161,270 bytes; current `deletedFlag=0` in this action response but `effectiveDeletedDate=2026-09-18T12:50:46.692Z`
- `d26e9a3074cb4c18a833f67a8ffea3c2` — Amendment 0001 — 3,999,705 bytes

The old 143,690-byte Product Description is still returned as deleted.

### Action `740398...` — 6 resources
Adds:
- `fdb2c8a64170488abddc0138c56a9082` — Questions and Clarifications 1 — 173,415 bytes — later `deletedFlag=1` at `2026-09-18T16:48:14.059Z`

The prior Questions and Clarifications resource `00a43...` is now explicit `deletedFlag=1`, deletion timestamp `2026-09-18T12:50:46.692Z`.

### Current action `c799a09...` — 8 resources
Adds three resources posted at `2026-09-18T16:48:14.059Z`:
- `1986563642894cf190012310a0669232` — Amendment 0002 — 4,002,898 bytes
- `4bcfa0317ccc4c9cb6463e100a1ffa05` — Questions and Clarifications 2 — 173,594 bytes
- `c819c7c5e96e4c71b76eb4856b851627` — Attachment 2 Product Description — 278,832 bytes — current

Also returns the earlier Product Description tombstone:
- `53901ef77baa40da88ff1a8cfa1b71db` — same filename — 143,690 bytes — `deletedFlag=1` — deleted at `2026-09-18T16:48:14.059Z`

But **does not return**:
- `00a43d7e02184a02950290925d972b1e` — Attachment 5 Questions and Clarifications — 161,270 bytes, despite that resource being present in `03dbaaf...` and explicitly tombstoned in `740398...`.

## Same-filename replacement identity — VERIFIED

Exact filename in both records:

`Attachment 2 - Product Description.pdf`

Old resource:
- `resourceId`: `53901ef77baa40da88ff1a8cfa1b71db`
- size: 143,690 bytes
- posted: `2026-09-16T15:06:53.145Z`
- deleted: `2026-09-18T16:48:14.059Z`
- `deletedFlag=1`
- public / `exportControlled=0` / `fileExists=1`

Replacement resource:
- `resourceId`: `c819c7c5e96e4c71b76eb4856b851627`
- size: 278,832 bytes
- posted: `2026-09-18T16:48:14.059Z`
- `deletedFlag=0`
- public / `exportControlled=0` / `fileExists=1`

This definitively falsifies filename-as-identity and validates stable source-object identity + content hash as the correct attachment key.

## Historical-union losslessness — ONE-FAMILY RESULT

Across the six solicitation action manifests, nine unique `resourceId` values were observed.

The latest `c799...` manifest contains eight.

Exactly one resource exists in the historical union but not in the latest deletion-inclusive manifest:

`00a43d7e02184a02950290925d972b1e` — `Attachment 5 - Questions and Clarifications.pdf`

Therefore, for this family:

`UNION(historical action manifests, excludeDeleted=false) > latest manifest, excludeDeleted=false`

The latest deletion-inclusive manifest is provably not a lossless historical packet ledger.

This is consistent with GSA's documented resource-deletion boundary from prior runs (`excludeDeleted` / `deleteAll` semantics), but the present result is stronger because it is an independently observed live fixture rather than documentation-only reasoning.

## Manifest-default behavior — current live probe

The current `c799...` endpoint was queried three ways on 2026-09-20:

- omit `excludeDeleted` -> 8 resources, including the two tombstones currently retained
- `excludeDeleted=false` -> same 8 resources
- `excludeDeleted=true` -> 6 resources, tombstones removed

Thus current live default behavior is equivalent to `excludeDeleted=false` for this endpoint. Engineering should still pin `excludeDeleted=false` explicitly because a default is not a contractual historical-completeness guarantee and can change independently of the client.

This corrects an overstatement in earlier Orrery criticism: failure to explicitly pin `excludeDeleted=false` is robustness debt, but **under the currently observed SAM behavior it does not by itself cause deleted resources to be omitted**. Orrery's real historical-authority gap remains its mutable current-row UPSERT model and lack of an immutable per-manifest observation ledger/disappearance transition history.

## `chrisfulcher/orrery@89ae2218c031c2c46720783acfb44cea22e48636` — revised interpretation, score unchanged 26/30

Deep source inspection confirms:

- `ManifestItem.resource_id` is a first-class field parsed from SAM's `resourceId`.
- File download URLs are built from `resource_id`, not filename.
- The attachment upsert key is `(notice_id, url)`; for SAM file entries that URL is derived from resourceId, so same-filename replacement resource IDs can coexist rather than collide on filename.
- `deletedFlag` is parsed and preserved.
- Current code calls `/resources` without explicitly passing `excludeDeleted=false`; current live SAM default includes tombstones, so this is presently functional but still fragile.
- The UPSERT refreshes one current attachment row and `last_seen_at`; it does not create an immutable child record for every complete manifest observation and does not sweep or type a resource that disappears from a later complete manifest.

Disposition remains **STRONG component / 26/30**, not historical authority. The direct live fixture validates its resource-ID design but also proves the missing append-only observation layer matters commercially.

## Claims tested

### VERIFIED
1. Same filename can represent two distinct SAM source resources in one solicitation family.
2. `resourceId`, not filename, is the stable source-object discriminator for this fixture.
3. A current `excludeDeleted=false` manifest can include both an old tombstone and its same-named replacement.
4. A deleted resource can be absent from a later manifest even when the later manifest is requested with `excludeDeleted=false`.
5. Historical action-union retrieval recovers at least one resource lost from the latest manifest in this family.
6. Historical action endpoints queried later can carry resource state/deletion timestamps later than the action's own publication time; they are not immutable publication-time snapshots.
7. Current live SAM behavior when `excludeDeleted` is omitted is equivalent to `excludeDeleted=false` for this fixture.

### NOT YET PROVEN
1. Historical action-union retrieval is lossless across all ten frozen EXP-006 families.
2. Every historical action UUID remains queryable indefinitely.
3. A `deleteAll` resource will always remain recoverable from at least one historical action endpoint forever.
4. The exact byte hashes of the two Product Description versions were not computed in this run; distinct source IDs and byte sizes prove distinct source objects, while byte-level identity remains a separate evidence field.

## Capability / experiment / commercial impact

### CAPABILITY DELTA
`CAP-011` can now state a stronger falsifiable rule: **latest deletion-inclusive attachment state is insufficient historical authority**. Historical action membership and locally immutable observation history are both required.

### GRAPH EDGE
Required proof graph becomes:

`Notice family -> Action UUID -> Manifest observation -> resourceId -> source state -> byte hash -> parser version -> extracted fact`

where action membership and observation-time state remain distinct.

### RADAR SIGNAL
`RAD-008` strengthens qualitatively: machine-readable government authority is not only versioned; source APIs can expose **retroactively updated state on historical objects plus later omission of prior tombstones**, making observation time first-class.

### EXPERIMENT IMPACT
`EXP-006` now has a live planted-real-world fixture for:
- `SAME_FILENAME_DIFFERENT_RESOURCE_ID`
- `HISTORICAL_ACTION_RETROACTIVE_TOMBSTONE_STATE`
- `DELETED_RESOURCE_ABSENT_FROM_LATEST_EXCLUDEDELETED_FALSE`
- `HISTORICAL_UNION_RECOVERS_LATEST_OMISSION`
- `OMITTED_EXCLUDEDELETED_DEFAULT_CURRENTLY_INCLUDES_TOMBSTONES`

PASS still requires the ten-family corpus, but the architecture choice is no longer hypothetical.

### COMMERCIAL IMPACT
The Solicitation Packet Integrity Audit can make a concrete differentiated claim: it can identify a document that was once part of the official packet even when the latest SAM manifest no longer returns that resource, and can distinguish a same-named replacement from the superseded artifact.

### NEGATIVE KNOWLEDGE
- filename is not attachment identity;
- latest manifest is not complete history even with deleted records requested;
- historical action endpoint state is not necessarily frozen at action publication time;
- a present tombstone does not guarantee permanent tombstone retention;
- source failure still cannot create disappearance;
- polling snapshot and action-history union are complementary, not substitutes.

## Search policy update

Do not resume generic SAM-wrapper discovery. Repeat this exact per-action deletion-inclusive manifest-union test across the remaining frozen EXP-006 families, prioritizing families with known explicit tombstones, same-name replacements, restricted/off-site resources and multiple action UUIDs.

For each family record:
- action UUID sequence;
- per-action query and observation timestamp;
- full response/body hash if feasible;
- all `resourceId`s and source states;
- `union(all actions) - latest`;
- resources whose deletion state is retroactively visible on older actions;
- resources absent after a previously explicit tombstone;
- source failures separately from successful empty responses.

## Score / disposition

**29/30 capability/experiment finding.** No new repository promotion.

A5 speed-to-revenue impact + B5 buyer value + C5 architecture/build compression + D5 rarity + E5 direct live-source evidence + F4 operational clarity. F remains below 5 because the resource endpoint is an undocumented/public-web interface and long-term retention behavior is not guaranteed.

## Next highest-value question

**Across the remaining nine frozen EXP-006 solicitation families, how often does `UNION(historical action manifests, excludeDeleted=false)` contain resourceIds absent from the latest deletion-inclusive manifest, and can any previously observed resource disappear from every still-queryable historical action endpoint?**
