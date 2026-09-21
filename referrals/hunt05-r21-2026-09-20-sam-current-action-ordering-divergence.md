# Hunt 05 R21 — FA524026Q0041: complete action set can still select the wrong current action

Date: 2026-09-20
Lane: Node 05 — Gov Evidence
Strategy: `STRAT:first-party-history-manifest-triangulation`
Capability / experiment: `CAP-011`, `EXP-006`
Status: STRONG experiment/capability evidence; no new repository promotion
Working score: **28/30** — A4 B5 C5 D5 E4 F5

## Question tested
The prior R20 run showed that notice-history completeness and attachment/resource completeness are independent. This run tested a more basic temporal-authority question on the same frozen family: if a downstream normalized surface reconstructs the full set of SAM action UUIDs, can it safely determine which action is current merely from its normalized ordering/grouping?

Fixture: SAM Notice ID / solicitation `FA524026Q0041` — 36 WG Vehicle Removal and Towing Services IDIQ (Andersen AFB, Guam).

## First-party current-action authority
The current first-party SAM page is:
- `https://sam.gov/opp/0f367577ad68477b947384888441974e/view`
- Updated Published Date: **Sep 17, 2026 05:21 pm AEST**
- History entries shown by SAM:
  - Sep 17, 2026 05:21 pm AEST — Updated
  - Sep 17, 2026 05:17 pm AEST — Updated
  - Sep 17, 2026 05:02 pm AEST — Updated
  - Sep 15, 2026 05:47 pm AEST — Original

The current page's history links point to the three predecessor action UUIDs:
- `cf21df787f6d480897b037d1af47aa7d`
- `a9d281564bc540ab8ef09af4c64c2a53`
- `838bdb200ad14374a300c9debd2a86cf`

Therefore, for this observation, the first-party current action is `0f367577ad68477b947384888441974e` and `cf21df...` is a predecessor.

Source: https://sam.gov/opp/0f367577ad68477b947384888441974e/view

## Two independent normalized/public mirrors select a different current action
### Abierto
Abierto says it derives the record from the **Contract Opportunities bulk extract, SAM.gov Data Services**. Its page reconstructs all four UUIDs under Publications:
1. `838bdb200ad14374a300c9debd2a86cf`
2. `0f367577ad68477b947384888441974e`
3. `a9d281564bc540ab8ef09af4c64c2a53`
4. `cf21df787f6d480897b037d1af47aa7d`

Yet the same page reports:
- `Publications: 4`
- `Latest notice: cf21df787f6d480897b037d1af47aa7d`

That disagrees with the first-party current page, which is `0f367...` and timestamps it at 05:21, later than the `cf21...` predecessor at 05:17.

Source: https://abierto.us/opportunities/fa524026q0041

### SAM Directory
A separate public SAM mirror also reconstructs a four-notice history but labels:
- `Notice ID cf21df787f6d480897b037d1af47aa7d`
- history entry 4 as `LATEST`

It therefore converges independently on the same non-current UUID selected by Abierto.

Source: https://sam.directory/opportunities/36-wg-vehicle-removal-and-towing-services-idiq-andersen-afb-guam-fa524026q0041

## Why this is materially different from R20
R20 established:
`history completeness != attachment completeness`.

R21 establishes an additional temporal invariant:
`history-set completeness != current-action correctness`.

A consumer can possess all four action UUIDs and still pick the wrong controlling/current action. This is more dangerous than merely omitting an attachment because the wrong current pointer can select the wrong description, deadline, attachment state, or amendment context while the UI still looks like a complete history.

## Official API boundary
GSA's official Get Opportunities Public API documentation states that its public API returns **only the latest active version** and directs users to SAM.gov Data Services for all versions. This supports keeping two authority paths separate:
- latest/current discovery from a source that explicitly asserts latest active state;
- historical reconstruction from all-version data.

A historical/bulk feed should not silently redefine `current` unless it has an authoritative ordering/currentness field whose semantics are validated.

Official source: https://open.gsa.gov/api/get-opportunities-public-api/

## Additional attachment-identity witness
Abierto exposes only one attachment on its current normalized page even though the first-party SAM page currently exposes eight rows. Its visible `Attachment 5 - Past Performance Questionnaire.docx` link points to the SAM resource download route:

`https://sam.gov/api/prod/opps/v3/opportunities/resources/files/ef47d7d89f6d4ba1acfcc6d864e0a53b/download`

This externally corroborates one stable SAM resource identifier (`ef47d7d89f6d4ba1acfcc6d864e0a53b`) for Attachment 5, but it also demonstrates why a normalized mirror cannot be used as the packet enumerator: it exposes only one of the eight current first-party rows. The mirror remains a challenger/corroborator, not authority.

## Raw manifest-body limitation
The public first-party resource-manifest URLs for all four actions were reached in this run with explicit `excludeDeleted=false`, but the available free non-interactive extraction path did not expose the JSON response bodies. Therefore the prior exact R20 questions remain unresolved:
- distinct `resourceId`s for the current and deleted 575 KB solicitation revisions are **NOT VERIFIED**;
- `UNION(all four first-party action manifests) - latest` for this family is **NOT VERIFIED**.

A source/read failure remains `UNRESOLVED`, never an empty manifest.

## Capability delta
`CAP-011` needs three independent temporal completeness/currentness receipts, not one history flag:
1. `history_set_complete` — all known action UUIDs accounted for;
2. `history_ordering_authoritative` — ordering comes from source-effective timestamps/sequence semantics, not list position;
3. `current_action_authoritative` — the selected controlling/current action is proven by a first-party latest/current assertion or equivalent authoritative currentness field.

Recommended non-green states:
- `history_set_complete_current_unknown`
- `history_set_complete_current_conflict`
- `history_ordering_ambiguous`
- `current_action_source_disagreement`

Only after current-action authority is resolved should attachment/resource completeness be evaluated for the controlling packet.

## Graph edge
Do not model:
`notice family -> ordered list of actions -> last item = current`.

Model instead:
`notice family -> action set`
plus independently observed edges:
- `ACTION_HAS_SOURCE_EFFECTIVE_TIME`
- `ACTION_PRECEDES / SUCCEEDS`
- `SOURCE_ASSERTS_CURRENT_ACTION`

A conflict between a normalized latest pointer and first-party current assertion is evidence, not a tie to be guessed away.

## Radar signal
Strengthens `RAD-008` qualitatively: temporal public authority requires **set membership, ordering, and currentness** as separate semantics. Version-complete data can still be temporally wrong.

## Experiment impact
Add the planted case:
`ALL_ACTION_UUIDS_PRESENT_BUT_NORMALIZED_LATEST_POINTER_WRONG`.

Expected behavior:
- emit `current_action_source_disagreement`;
- do not trust list order or mirror `LATEST` labels;
- resolve currentness from first-party source-effective timestamps/current assertion;
- preserve all observations without rewriting history;
- block `complete_public` until current action and packet are both resolved.

## Commercial impact
The CaptureBrief Solicitation Packet Integrity Audit can catch a more dangerous failure than a missing file: **a complete-looking four-action history can still analyze the wrong action as current.** That can propagate into stale amendment text, deadlines, required documents, and bid/no-bid logic.

This supports a buyer-facing distinction:
- “All public actions found.”
- “Current controlling action independently proven.”
- “Current and historical attachment inventories proven.”

## Negative knowledge
- Full action-set reconstruction does not prove correct ordering.
- List position does not prove source-effective chronology.
- A third-party `LATEST` label is not current-action authority.
- Two independent mirrors can repeat the same upstream normalization/order mistake.
- Bulk/history data and latest/current discovery are separate authority planes.
- Failed manifest extraction is unresolved, never zero resources.

## Cross-lane referral
**Data/provenance lane:** model `history_set_complete`, `history_ordering_authoritative`, and `current_action_authoritative` as separate receipts. Exact unanswered technical question: can the source-agnostic evidence envelope represent a complete set of versions while refusing to select a current version whenever first-party currentness and normalized-history ordering disagree?

## Strongest objection
Both mirrors may share the same underlying SAM bulk/Data Services semantics, so their agreement is not independent evidence that `cf21...` is correct; in fact that correlation is the point of the negative fixture. The first-party live page remains the current-action authority for this observation. This run does not establish the root cause inside SAM Data Services itself; it establishes that a consumer of normalized/all-version data can reconstruct the full action set and still select a non-current UUID.

## Next highest-value question
What exact field/ordering rule in the SAM Data Services Contract Opportunities bulk extract causes both normalized consumers to select `cf21df787f6d480897b037d1af47aa7d` while the live first-party current action is `0f367577ad68477b947384888441974e`, and can CaptureBrief derive a deterministic source-authoritative current-action rule that survives same-day multi-action updates?
