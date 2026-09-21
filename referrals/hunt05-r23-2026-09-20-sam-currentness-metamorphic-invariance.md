# Hunt 05 R23 — SAM currentness requires metamorphic invariance

Date: 2026-09-20
Lane: Gov Evidence / CaptureBrief
Status: STRONG CAP-011 / EXP-006 evidence; no new MASTER repository promotion
Primary graph edge: CAP-011 -> EXP-006
Radar edge: RAD-008 temporal machine-readable public authority
Search strategy: STRAT:first-party-history-manifest-triangulation + metamorphic falsification
Repository HEAD observed before write: `722fde548bd6284778ecd281610b5c29b60391ea`

## Executive finding

The prior EXP-006 row-permutation adversary is necessary but **not sufficient** to detect unsafe current-action selection from SAM bulk/history rows.

A deterministic selector can be perfectly invariant to row order and still be wrong if it treats an opaque `NoticeId`/action UUID as chronology. Cross-family evidence now provides a concrete counterexample: lexical UUID order happens to agree with currentness on two same-day families, but fails on a third frozen family where first-party SAM identifies a lexically smaller UUID as the most recent current action.

Therefore CaptureBrief should require two independent metamorphic properties before any derived history selector is trusted:

1. **ROW_PERMUTATION_INVARIANCE** — shuffling the same history rows must not change the selected current action.
2. **OPAQUE_ID_RENAMING_INVARIANCE** — replacing action/notice UUID strings with arbitrary bijective opaque labels, while preserving every authoritative temporal/semantic fact, must not change which underlying action is selected.

If either transformation changes the answer, the selector is using representation artifacts rather than source authority.

This materially tightens CAP-011 and EXP-006 because naive heuristics can look correct on multiple real solicitations by accident.

## Three materially different discovery passes

### A. Direct frozen-family pass — `127EAX26Q0105`

Public current/history evidence:
- SAM Directory currently shows five notices and identifies `fd8a53223a054ff3a7315815e1f11fab` as the latest Notice ID.
- Public SAM-derived history reproductions show same-day updates on **Sep 16, 2026 at 07:17 am PDT and 09:47 am PDT**, with 09:47 as the current updated publication time.
- Abierto/Data-Services-derived grouping lists the two Sep 16 action IDs in historical order as:
  - `b4f8640aecf44cb2a5f3bdf3b9f7c0a9`
  - `fd8a53223a054ff3a7315815e1f11fab`

Sources:
- https://sam.directory/opportunities/greenhouse-building-control-system-repairs-127eax26q0105
- https://www.governmentcontracts.us/government-contracts/opportunity-details/42639717142000159.htm
- https://abierto.us/opportunities/127eax26q0105

Result: lexical maximum of the two same-day UUIDs is `fd8...`, which **happens to agree** with the current action. This is an accidental-pass fixture for a bad lexical tie-break.

Evidence label: **CURRENT/CHRONOLOGY CORROBORATED; UUID-to-time mapping inferred from ordered history across independent public views.**

### B. Frozen counterexample — `FA524026Q0041`

First-party SAM currently serves action URL:
- `https://sam.gov/opp/0f367577ad68477b947384888441974e/view`
- Updated Published Date: **Sep 17, 2026 05:21 pm AEST**.

The same family has three Sep 17 action UUIDs:
- `0f367577ad68477b947384888441974e`
- `a9d281564bc540ab8ef09af4c64c2a53`
- `cf21df787f6d480897b037d1af47aa7d`

The first-party page's history reports Sep 17 actions at 05:21, 05:17 and 05:02 pm AEST, plus the Sep 15 original. Prior R21/R22 evidence already established that Abierto and SAM Directory label `cf21...` as `LATEST`, while the first-party SAM current action page is `0f...` at 05:21.

Source:
- https://sam.gov/opp/0f367577ad68477b947384888441974e/view
- durable prior evidence: `referrals/hunt05-r21-2026-09-20-sam-current-action-ordering-divergence.md`
- durable prior evidence: `referrals/hunt05-r22-2026-09-20-sam-bulk-currentness-boundary.md`

Result: lexical maximum of the same-day UUID set is `cf21...`, but the current first-party action is `0f...`. A deterministic lexical UUID tie-break therefore fails this real frozen fixture even though it can pass other same-day fixtures.

Evidence label: **FIRST-PARTY CURRENT ACTION VERIFIED; normalized latest-pointer disagreement previously verified.**

### C. Analog same-day family — `SP060025R0800`

A separate DLA solicitation provides a useful control. Public SAM-derived history reports two Sep 9, 2026 updates at approximately **01:54 pm EDT** and **02:22 pm EDT**, with the 02:22 update current. Data-derived publication listings associate the same-day action set with UUIDs:
- `454559379d1346cc86e9abb934f8bd72`
- `9a189f14bc504628a2e8ce5bf4185954`

Public mirrors identify `9a189...` as latest/current.

Sources:
- https://governmentbidhub.com/bid-opportunities/bid-detail/18694516930015976
- https://governmentbidders.com/government_bids/detail/NBD00159765169318694.htm
- https://abierto.us/opportunities/sp060025r0800

Result: lexical maximum `9a189...` again **happens to agree** with currentness. Together with Q0105 this shows why a heuristic can survive a small regression suite and still be invalid.

Evidence label: **CORROBORATED ANALOG, not first-party authority.**

## Code-level negative comparator — `EthanHNguyen/rfp-map`

Repository: https://github.com/EthanHNguyen/rfp-map
Exact revision inspected: `7e16e62fae99c1a0c0bd1e0aed45cbb862b091d9`
Public license: MIT
Attention at inspection: 0 stars / 0 forks
Status: NEGATIVE/COMMODITY COMPARATOR, **18/30**

`script/ingest-sam.py` / `scripts/ingest-sam.py` consumes the official SAM bulk CSV from the public S3 Data Services path, normalizes `NoticeId` as an opaque record ID and retains `PostedDate`, but it is a current active-opportunity visualization pipeline rather than a source-authoritative intra-family chronology/currentness engine. Its value here is as a clean example of how easy it is to ingest the source correctly without acquiring the semantics needed to prove which same-family revision controls.

Verified beyond README from source:
- direct public S3 bulk URL;
- `NoticeId` retained as normalized record identity;
- `PostedDate` retained as a field;
- deterministic current-map generation and daily refresh artifacts;
- no inspected authoritative intra-family revision/currentness receipt.

This is not a criticism of the map's purpose; it is negative evidence against treating ordinary bulk ingestion as CAP-011 temporal authority.

## Claim tested

### Claim: row permutation alone is sufficient to expose unsafe current-action derivation

**FALSIFIED.**

A selector can sort same-day rows lexically by opaque UUID, so row permutation leaves its result unchanged. Such a selector would pass:
- `127EAX26Q0105`;
- `SP060025R0800`;

and fail:
- `FA524026Q0041`.

The stronger invariant is **representation independence**: currentness must not depend on source-row order or opaque identifier spelling.

Important boundary: I did **not** obtain Abierto's private selection code. The observed results are compatible with several deterministic tie-breaks. This run does **not** claim Abierto uses lexical-max UUID. The finding is that lexical/identity-based tie-breaks are unsafe and that the current acceptance test would not necessarily catch them.

## Recommended EXP-006 metamorphic suite

For every same-day multi-action family:

1. **ROW_PERMUTATION_INVARIANCE**
   - randomly permute row order;
   - expected selected underlying action unchanged.

2. **OPAQUE_ID_RENAMING_INVARIANCE**
   - replace every action UUID/NoticeId with a random one-to-one opaque label;
   - preserve all non-ID facts and relationships;
   - expected selected underlying action unchanged.

3. **TIME_TRUNCATION_FAIL-CLOSED**
   - remove sub-day source-effective ordering so two or more candidate actions share only a calendar date;
   - without an independent first-party current receipt, expected state is `HISTORY_SET_COMPLETE / CURRENT_UNKNOWN`, not a guessed current action.

4. **CURRENT_RECEIPT_DOMINANCE**
   - plant a bulk/mirror-derived pointer that conflicts with a fresh first-party current assertion;
   - expected state `CURRENT_ACTION_SOURCE_DISAGREEMENT` with buyer-facing analysis bound to the first-party current receipt while the disagreement remains visible.

5. **ID-SORT NEGATIVE CONTROL**
   - construct a fixture where lexical minimum, lexical maximum, insertion order and true current are all different where possible;
   - no identity/order heuristic may produce `CURRENT_VERIFIED` without an authority receipt.

### Acceptance law

`CURRENT_VERIFIED` is admissible only when currentness is supported by an explicit source-authoritative receipt or by a source-backed chronology whose semantics independently establish ordering. Passing opaque-ID and row-order metamorphic tests is necessary defensive evidence, but is not itself authority.

## Capability delta

CAP-011 now gains a concrete **currentness representation-invariance contract**:

`HISTORY_SET_RECEIPT` + `CURRENT_ACTION_RECEIPT` + optional source-backed `ACTION_ORDER_RECEIPT`, with currentness invariant under row permutation and opaque-ID renaming.

This is stronger than merely saying “do not sort UUIDs”; it is a reusable falsifiable property for any government version/history feed using opaque record identifiers.

## Graph edge

- same-day SAM families -> CHALLENGE heuristic temporal inference in CAP-011.
- `FA524026Q0041` -> REAL-WORLD COUNTEREXAMPLE to identity-based currentness.
- `127EAX26Q0105` and `SP060025R0800` -> ACCIDENTAL-PASS controls demonstrating why positive fixtures alone are insufficient.
- representation-invariance suite -> STRENGTHENS EXP-006.

## Radar signal

RAD-008 strengthened qualitatively, numeric score unchanged.

The emerging pattern is that evidence-grade government data needs **semantic authority independent of transport representation**. Opaque source identifiers are identity, not time. A robust evidence system should survive harmless representational transformations while failing closed when authoritative temporal facts are removed.

## Commercial impact

Buyer: federal capture/proposal teams and proposal-service firms.

Painful problem: a tool can ingest every amendment and still silently bind analysis to the wrong controlling action when several revisions share a date and the data plane lacks a source-authoritative current/sequence field.

First paid wedge remains the Solicitation Packet Integrity / FAR-Deviation Readiness audit, but the QA story is stronger: CaptureBrief can prove its amendment selector is not dependent on incidental row order or opaque UUID spelling.

This reduces a difficult-to-detect class of false confidence where an implementation passes ordinary examples because identifier order happened to align with chronology.

## Negative knowledge

- Two or even several fixtures where lexical UUID order matches chronology do **not** validate UUID sorting.
- Row-permutation tests do not catch deterministic identity-based tie-breaks.
- Opaque `NoticeId`/action UUID values have no inspected chronological ordering contract.
- Day-level `PostedDate` is insufficient when multiple actions occur on the same day.
- A complete action set plus a deterministic selector is still not source authority.
- Currentness must fail closed when the authority receipt is unavailable.

## Cross-lane referral

Provenance/data lane: make `OPAQUE_ID_RENAMING_INVARIANCE` a generic acceptance test for version-selection systems. Exact question: can the common evidence envelope prove that subject identity labels are semantically opaque while preserving a separate source-effective/currentness receipt?

This generalizes beyond SAM to any registry/API where UUIDs identify revisions but do not order them.

## VALUE HANDOFF

1. **Capability delta:** CAP-011 gains a representation-invariant currentness contract.
2. **Graph edge:** same-day SAM action families challenge any history-to-current edge not backed by a separate authority receipt.
3. **Radar signal:** temporal authority should be invariant to harmless transport/identifier representation changes.
4. **Experiment impact:** EXP-006 must add UUID-renaming metamorphic tests in addition to row permutation.
5. **Commercial impact:** CaptureBrief can defensibly test for a wrong-controlling-amendment class that ordinary positive examples miss.
6. **Negative knowledge:** accidental agreement on multiple families is not evidence that lexical or row-derived currentness is valid.

## Next highest-value question

Across the remaining frozen EXP-006 same-day multi-action families and active/cancelled/archived status classes, how often do common deterministic heuristics (`last row`, `lexical max UUID`, day-date + lexical tie-break) disagree with a fresh first-party current assertion, and can the resulting corpus define one status-aware `CURRENT_ACTION_RECEIPT` contract without guessing?
