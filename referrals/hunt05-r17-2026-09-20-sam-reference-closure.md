# Hunt 05 R17 — SAM packet reference-closure / missing-required-artifact check

Date: 2026-09-20
Lane: Gov Evidence / CAP-011 / EXP-006
Strategy: `STRAT:first-party-history-manifest-triangulation`

## Executive result

This run repeated EXP-006 work on a second frozen solicitation family, `N6600126Q6264 — KVM MOUNT FABRICATION`, and found a **new packet-integrity failure mode distinct from latest-vs-history loss**:

> A current first-party SAM notice can explicitly instruct offerors to review a named attachment that is not present as a named file in the current deletion-inclusive resource manifest.

The current SAM action is `4f722ea79ce74faea16eec7a764dae3b` (Sep 17 2026 10:34 PDT). Its description says award evaluation is defined in `C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0004`, and under **REVIEW ALL OF THE FOLLOWING ATTACHMENTS** it still names `C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0001` plus Attachments 1–6.

The current visible SAM Attachments/Links table contains eight file rows: Amend 0004; Amend 0003 marked Deleted; Attachments 1–6. It does **not** contain Amend 0001.

A direct public resource-manifest probe of the current action using:

`GET https://sam.gov/api/prod/opps/v3/opportunities/4f722ea79ce74faea16eec7a764dae3b/resources?excludeDeleted=false&withScanResult=false`

with `Accept: application/hal+json` returned HTTP 200 and **12 resources**: the same eight named file rows plus four unnamed `type=link` objects posted Jul 28. No named resource for Amend 0001 was present. The four blank links all predate the Jul 30 amendment-reference state and therefore cannot safely be assumed to resolve the named Amend 0001 requirement without further source evidence.

This means `complete_public` needs a **reference-closure gate**, not merely successful manifest enumeration.

## Current manifest probe — direct first-party metadata

Observed 2026-09-20. No attachment content was downloaded.

| resourceId | name | bytes | postedDate | deletedFlag | deletedDate | access | exportControlled | fileExists | type |
|---|---|---:|---|---:|---|---|---:|---:|---|
| `5b7326d6bf8149d59f387e39ffa8aad6` | C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0004.docx | 68152 | 2026-09-17T17:34:04.732Z | 0 | — | public | 0 | 1 | file |
| `38a71d4c40b94b76b6d45cb48de9ce7e` | C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0003.docx | 61516 | 2026-08-05T21:59:53.206Z | 1 | 2026-09-17T17:34:04.732Z | public | 0 | 1 | file |
| `5ce44ec810d548f8bb087127460801ee` | C2.1 Attachment (1)_KVM_Mount Specifications.docx | 28638 | 2026-07-30T22:19:48.647Z | 0 | — | public | 0 | 1 | file |
| `772b07cde74b42d3a5029cf2ec0e5fdd` | C2.1 Attachment (2)_Brackets Drawings.pdf | 108568 | 2026-07-30T22:19:48.647Z | 0 | — | public | 0 | 1 | file |
| `8a53fc89cae64576a321bdae278972c7` | C2.1 Attachment (3)_Brackets CAD files.zip | 525257 | 2026-07-30T22:19:48.647Z | 0 | — | public | 0 | 1 | file |
| `f2fd408b293f4c469d7502103b88c322` | C2.1 Attachment (4)_Similar Mount Reference Photos.zip | 676180 | 2026-07-30T22:19:48.647Z | 0 | — | public | 0 | 1 | file |
| `54758299415f47e7b1c06793fab93573` | C2.1 Attachment (5)_Drawings with amplifying Information.pdf | 183446 | 2026-08-05T21:59:53.206Z | 0 | — | public | 0 | 1 | file |
| `4a3c22dca72e43dc8607609cb5189b30` | C2.1 Attachment (6)_Amendment Clarification and Guidance.docx | 49669 | 2026-09-17T17:34:04.732Z | 0 | — | public | 0 | 1 | file |
| `54a5da7e021e4c478745727cbe565476` | *(blank)* | 0 | 2026-07-28T23:10:10.024Z | 0 | — | public | 0 | 1 | link |
| `bcfbcb7006054289936487ce06a02dfa` | *(blank)* | 0 | 2026-07-28T23:10:10.024Z | 0 | — | public | 0 | 1 | link |
| `e80c616c62e14acfa2104051be176c3a` | *(blank)* | 0 | 2026-07-28T23:10:10.024Z | 0 | — | public | 0 | 1 | link |
| `3cd22979213d46a6b7826dca766b467c` | *(blank)* | 0 | 2026-07-28T23:10:10.024Z | 0 | — | public | 0 | 1 | link |

### Important interpretation

This is **not yet proof that Amend 0001 is legally/control-wise missing**. A later amendment may incorporate or supersede earlier text. The correct machine state is therefore not `missing_required_file` as a final conclusion; it is `referenced_artifact_unresolved` until one of these is proven:

1. the referenced artifact is recovered from a historical action/resource observation;
2. the controlling amendment explicitly incorporates/supersedes it in a way that makes the old byte artifact unnecessary; or
3. the source explicitly withdraws the reference.

Absent that proof, a successful latest-manifest read cannot justify `complete_public`.

## First-party history UUID map

The current SAM page exposes ten action states. By extracting the first-party history anchors and aligning them with the public History timestamps shown on the current action, the family is:

1. `4f722ea79ce74faea16eec7a764dae3b` — Sep 17 2026 10:34 am PDT — Updated/current
2. `adb89ec24d7a48c5865840887310d5d1` — Sep 17 2026 10:25 am PDT — Updated
3. `5f168289a5ad48abb511fe6c9eed3224` — Aug 11 2026 10:07 pm PDT — Updated
4. `936993aa0dc94d7f832dbdcf634023d9` — Aug 05 2026 02:57 pm PDT — Updated
5. `edb1089a377d4a9abc50b25d98e6e9d5` — Aug 05 2026 07:55 am PDT — Updated
6. `10c981e53de4486c9f90ae24b8e22640` — Aug 05 2026 07:49 am PDT — Updated
7. `7314f32bdba84115ad4e85bdbf407113` — Jul 30 2026 03:19 pm PDT — Updated
8. `c00bea2428e44ebf85efb129394aeb79` — Jul 30 2026 03:06 pm PDT — Updated
9. `44056457bc9e4653b18db3f5ec48807f` — Jul 28 2026 04:15 pm PDT — Updated
10. `76ba6ea8efd9449e974e53ac5ae93cae` — Jul 28 2026 04:10 pm PDT — Original

The stale `44056457...` first-party SAM page itself points forward to `4f722...` as the most recent action, independently confirming family continuity rather than requiring filename/date inference.

## Independent temporal corroboration

A dated SAMDaily/FBO archive for the Jul 30 action links directly to SAM action UUID `7314f32bdba84115ad4e85bdbf407113` and records the notice description at that time as explicitly requiring `C2.1 Combined_Synopsis_Solicitation_KVM_Mount Amend 0001` plus Attachments 1–4.

`natdexterra/spotcheck@2ace0d1a74c006f738a80e5f7a96249586ec6999` independently states that its synthetic sample package was built from the real Jul 30 public SAM RFQ `N6600126Q6264`; the real specification text and drawing sheet were derived from the public Attachment 1 and Attachment 2. This is useful corroboration that the Jul 30 public packet was harvestable, but it is **not** treated as SAM history authority and does not prove the missing Amend 0001 resource identity.

## New acceptance invariant — REFERENCE CLOSURE

Before `complete_public`, CaptureBrief must validate not only source-manifest completeness but **document-reference closure**:

For every named artifact, attachment, exhibit, amendment, schedule, drawing, external system, or incorporated-by-reference object that the controlling notice or controlling artifact instructs the offeror to review/use:

- resolve it to a stable source object + observation + bytes; **or**
- resolve an explicit supersession/incorporation edge to the controlling successor; **or**
- emit `referenced_artifact_unresolved` / `external_dependency_unresolved` and withhold packet completeness.

The closure check must run recursively inside downloaded/public artifacts as well as on notice text; otherwise a complete manifest can still represent an incomplete decision packet.

Recommended proof edge:

`controlling_notice/artifact -> REFERENCES -> named_artifact -> RESOLVES_TO(resourceId, observation_id, artifact_hash)`

or

`named_artifact -> SUPERSEDED_BY -> successor_artifact` with source evidence.

## Claims tested

### VERIFIED
1. Current SAM description explicitly tells offerors to review Amend 0001.
2. Current visible SAM attachment table has Amend 0004, deleted Amend 0003, and Attachments 1–6, but no Amend 0001.
3. Current deletion-inclusive resource endpoint returns 12 resources: eight named files + four unnamed links; no named Amend 0001 file is present.
4. All ten action UUIDs for the family can be recovered from first-party SAM history links, including the original `76ba6...` action.
5. Jul 30 archived notice text independently names Amend 0001 as part of the RFQ requirements.

### NOT YET PROVEN
1. Whether a historical action manifest still returns the exact Amend 0001 resourceId.
2. Whether Amend 0004 explicitly and completely incorporates/supersedes Amend 0001, such that the earlier byte artifact is no longer necessary to interpret requirements.
3. Whether any of the four blank current `type=link` objects semantically resolves an old named dependency; their Jul 28 timestamps make that unlikely for the Jul 30 amendment but this was not dereferenced.
4. The full `UNION(all action manifests) - latest` resourceId delta for this second family; the current run exhausted the dynamic-browser extraction budget after recovering the current manifest and all action UUIDs.

## Capability / experiment / commercial impact

### CAPABILITY DELTA
`CAP-011` needs **reference closure** in addition to action-union and immutable observation history. Manifest completeness and packet semantic completeness are separate proof obligations.

### GRAPH EDGE
Add:

`notice/artifact -> REFERENCES -> artifact/dependency -> RESOLVES_TO source object OR SUPERSEDED_BY source-backed successor`

Unresolved references block `complete_public`.

### RADAR SIGNAL
`RAD-008` strengthens qualitatively: machine-readable public authority can be internally self-inconsistent across narrative references and enumerated resources, so authority-aware software must reconcile source semantics, not merely enumerate source objects.

### EXPERIMENT IMPACT
Add planted/real case to `EXP-006`:

`NOTICE_REFERENCES_ARTIFACT_ABSENT_FROM_CURRENT_DELETION_INCLUSIVE_MANIFEST`

Expected state: `referenced_artifact_unresolved` until historical recovery or source-backed supersession is proven.

### COMMERCIAL IMPACT
The Solicitation Packet Integrity Audit gains a buyer-facing check that ordinary scrapers miss: **“the agency tells you to review a document that the current attachment list does not supply.”** That is directly actionable before compliance review or proposal drafting.

### NEGATIVE KNOWLEDGE
- complete manifest enumeration != semantic packet completeness;
- current attachment table != closure of named dependencies;
- later amendment number does not automatically prove earlier amendment is safely irrelevant;
- blank external link objects cannot be assumed to resolve a named missing artifact;
- unresolved reference must not be silently treated as superseded.

## Search policy update

Continue `STRAT:first-party-history-manifest-triangulation`, but extend each frozen-family pass with a **reference-closure phase**:

1. freeze current description + current deletion-inclusive manifest;
2. extract all named attachments/exhibits/amendments/external systems from notice text;
3. compare names/identities against the current and historical manifest union;
4. if absent, search source-backed supersession/incorporation evidence;
5. only then classify the packet as complete or unresolved.

Do not resume generic SAM wrapper hunting.

## Score / disposition

**29/30 capability/experiment finding. No new repository promotion.**

A5 speed-to-revenue relevance + B5 buyer value + C5 architecture/build compression + D5 rarity + E5 direct current first-party page/manifest evidence + F4 operational clarity. F stays below 5 because the resource endpoint remains an undocumented public-web interface and this run did not finish the second family's historical-manifest union.

## Next highest-value question

**For `N6600126Q6264`, which historical action manifest contains the exact source object for Amend 0001, and does Amend 0004 contain explicit source-backed language that fully incorporates/supersedes it—or must CaptureBrief keep the packet unresolved?**
