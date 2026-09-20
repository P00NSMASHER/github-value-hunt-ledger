# Hunt 05 R15 — SAM attachment replacement identity / stale-view temporal-state finding

Date: 2026-09-20
Lane: Gov Evidence / CAP-011 / EXP-006

## Executive result

This run did not close the remaining `deleteAll` predecessor-retention question, but it produced a material EXP-006 design correction from a live frozen solicitation fixture: **attachment filename is not a stable identity, and a historical/stale SAM opportunity view can display attachment state that changed after that action's own published timestamp.**

The fixture is solicitation `W50S8B-26-Q-A016` (Electronic Lockers).

### First-party stale-action evidence

Official public SAM page:

`https://sam.gov/opp/03dbaaf6edd44b32ab961dab0bf6ec86/view`

The page identifies itself as a non-latest action and says newer actions exist. Its own action metadata is `Updated Published Date: Sep 17, 2026 10:18 am EDT`, while the History section lists later Sep 18 actions at 08:50 and 12:48 EDT.

Yet the attachment table on this Sep 17 action currently shows:

- `Attachment 2 - Product Description.pdf (Deleted)`
- size: **140 KB**
- access: Public
- **Updated Date: Sep 18, 2026**

That is a later attachment-state timestamp than the action's Sep 17 published timestamp. Therefore the rendered historical/stale page cannot be assumed to be an immutable snapshot of the packet exactly as it existed at that action time. The UI may expose resource state that was updated subsequently.

The same official page currently lists six family history entries:
- Sep 18 12:48 EDT — Updated
- Sep 18 08:50 EDT — Updated
- Sep 17 10:18 EDT — Updated
- Sep 17 07:21 EDT — Updated
- Sep 16 15:39 EDT — Updated
- Sep 16 11:06 EDT — Original

## Independent temporal corroboration

Two public procurement mirrors captured materially different attachment sets for the same solicitation family.

### Earlier mirrored state (Sep 17)
Civic AI snapshot:
`https://www.civiccontracts.com/contract/new-jersey-electronic-lockers-3eggk5nqfl2`

Documents (3):
- Attachment 1 — `W50S8B26QA016.pdf` — 3.2 MB
- Attachment 2 — `Product Description.pdf` — **140 KB**
- Attachment 3 — `Price Schedule.xlsx` — 21 KB

A separate Rule of Two snapshot shows an intermediate five-document set including Amendment 0001 and Questions/Clarifications while retaining the same 140 KB Product Description.

### Later mirrored state (Sep 18)
Civic AI snapshot:
`https://www.civiccontracts.com/contract/new-jersey-electronic-lockers-1drizzw6axg`

Documents (6):
- Attachment 6 — `W50S8B26QA0160002.pdf` — 3.8 MB
- Attachment 3 — `Price Schedule.xlsx` — 21 KB
- Attachment 5 — `Questions and Clarifications 2.pdf` — 170 KB
- Attachment 2 — `Product Description.pdf` — **272 KB**
- Attachment 4 — `Amendment W50S8B26QA0160001.pdf` — 3.8 MB
- Attachment 1 — `W50S8B26QA016.pdf` — 3.2 MB

The later mirror's `View on SAM.gov` link resolves to the current SAM workspace action URL:
`https://sam.gov/workspace/contract/opp/901ddb2a6f6f40979dca8ab26cbc5c39/view`

The mirrors are not authority and cannot establish completeness, deletion semantics, or exact resource IDs. They are useful independent temporal observations showing that the same filename, `Attachment 2 - Product Description.pdf`, existed first as a 140 KB artifact and later as a 272 KB artifact while the official stale action UI marks the 140 KB artifact deleted.

## Design consequence

This fixture rules out filename as an attachment identity key.

The evidence model must distinguish at least:

`solicitation family -> action UUID -> manifest observation -> resourceId -> content hash -> filename -> source state`

and must separately encode transitions such as:

- `ADDED`
- `UNCHANGED`
- `REPLACED_SAME_FILENAME`
- `EXPLICITLY_DELETED`
- `DISAPPEARED_AFTER_COMPLETE_OBSERVATION`
- `RESTRICTED_OR_ACCESS_CHANGED`
- `UNKNOWN_SOURCE_FAILURE`

A replacement with the same filename must not be collapsed into an in-place overwrite. The old resource and the new resource must remain independently addressable through stable source identity (`resourceId` where available) and immutable byte hash.

## Why this matters commercially

CaptureBrief's proposed Solicitation Packet Integrity Audit should not report only a current file list. It should be able to say, for example:

> the earlier 140 KB Product Description was deleted/replaced; the controlling later packet contains a different 272 KB Product Description plus Amendment 0002 and revised Q&A.

That is decision-relevant because a proposal team using a stale same-named attachment could comply with the wrong technical requirements while believing the filename was unchanged.

## Existing component impact

### chrisfulcher/orrery@89ae2218c031c2c46720783acfb44cea22e48636
Status remains **STRONG component / 26/30**, not historical authority.

Its public SAM manifest path and rich resource metadata remain useful, but this fixture increases the importance of two already identified gaps:
1. explicit deletion-inclusive reads must be pinned;
2. manifest/resource observations must be append-only and action-bound so later state cannot overwrite earlier truth.

### DeerSpotter/samgovsearch@14c840690e38fe3e9eb6f04c13cbd0105ebbb756
Status remains **STRONG component / 25/30** for artifact-byte provenance. Its `resourceId + SHA-256 + parser version` pattern is a good complement to action-bound manifest history, especially for same-filename replacement cases.

## Claims tested

### Supported
1. A stale official SAM action page can display an attachment state timestamp later than the action's own published timestamp; therefore the rendered stale page is not safely assumed to be a frozen historical packet snapshot.
2. The same solicitation family can present two materially different byte-size artifacts under the same filename across temporal observations (140 KB vs 272 KB Product Description).
3. Filename-only identity/diff logic is unsafe for solicitation packet history.
4. The correct packet model needs both stable source identity and byte identity, bound to a specific observation/action.

### Still not proven
1. The exact `resourceId` of the 140 KB deleted Product Description and the 272 KB replacement.
2. Whether the current action manifest (`901ddb2a6f6f40979dca8ab26cbc5c39`) returns both the old tombstone and the new replacement or only the replacement.
3. Whether a predecessor action manifest retains the deleted resource after a later `deleteAll` operation.
4. Whether unioning every historical action manifest is lossless for the frozen 10-family EXP-006 corpus.

## Tool/source limitation this run

The public SAM resource-manifest JSON could not be read directly through the available non-interactive HTTP/search surfaces in this run, and metered interactive browser automation was unavailable due its connected-wallet balance. No login, controlled files, credentials, or restricted artifacts were accessed. This limitation affects only the still-unproven resource-ID transition details above; the first-party stale-page and independent mirrored observations are public.

## Search methods used

1. **First-party source-state inspection:** live/indexed official SAM stale-action page + history + attachment table.
2. **Independent temporal mirror triangulation:** Civic AI and Rule of Two snapshots from distinct capture times.
3. **Code/protocol archaeology:** retained Orrery/public-SAM manifest semantics and the established official `excludeDeleted`/`deleteAll` boundary from the prior runs.

## Score / disposition

**26/30 — STRONG experiment/capability finding, no new repository promotion.**

A4 speed-to-revenue impact + B4 buyer value + C5 architecture/build compression + D4 rarity + E4 evidence + F5 rights/operational clarity.

Evidence is strong enough to change the packet identity model, but not strong enough to close historical resource retention because direct predecessor/successor manifest resource IDs were not obtained this run.

## CAP / OPP / EXP / RAD handoff

- **CAPABILITY DELTA:** CAP-011 now needs explicit attachment identity separate from filename and must treat stale UI pages as observations, not immutable historical truth.
- **GRAPH EDGE:** `resourceId + content hash + action UUID + observation ID` becomes the required edge for packet evidence; Orrery and samgovsearch complement each other but neither alone establishes full history.
- **RADAR SIGNAL:** RAD-008 strengthens qualitatively: temporal authority must separate source object identity from presentation labels and current UI rendering.
- **EXPERIMENT IMPACT:** add `SAME_FILENAME_DIFFERENT_RESOURCE_OR_BYTES` and `STALE_ACTION_UI_SHOWS_LATER_RESOURCE_STATE` fixtures to EXP-006. PASS requires correct replacement/deletion transition without overwriting the predecessor artifact.
- **COMMERCIAL IMPACT:** the Packet Integrity Audit gains a concrete high-value warning: same-named solicitation documents may be materially different controlling artifacts.
- **NEGATIVE KNOWLEDGE:** filename, stale action URL, and current rendered attachment table are each insufficient alone to establish historical attachment identity/currentness.

## Search policy update

Keep `STRAT:first-party-history-manifest-triangulation`, but the next run should target exact source-object identity rather than broad discovery. Obtain predecessor and successor action UUID manifests for `W50S8B-26-Q-A016`, explicitly request deleted resources, and compare `resourceId`, size/hash, deletion state, and observation time for the two Product Description artifacts.

## Next highest-value question

**Do the 140 KB deleted Product Description and the 272 KB successor Product Description have distinct SAM `resourceId` values, and what do the predecessor versus current action manifests return for each when queried with explicit deletion inclusion?**
