# Hunt 05 R20 — FA524026Q0041: notice-history completeness is not attachment completeness

Date: 2026-09-20
Lane: Node 05 — Gov Evidence
Strategy: `STRAT:first-party-history-manifest-triangulation`
Capability / experiment: `CAP-011`, `EXP-006`
Status: STRONG experiment/capability evidence; no new repository promotion
Working score: **28/30** — A4 B5 C5 D5 E4 F5

## Question tested
Across the four historical actions for SAM Notice ID `FA524026Q0041`, can notice/action history or a normalized document inventory stand in for attachment-level packet authority? The prior specific target was to determine whether the current/deleted same-family solicitation revisions have distinct SAM `resourceId`s and whether `UNION(historical action manifests)` contains objects absent from the latest deletion-inclusive manifest.

## First-party action chain verified
Current SAM opportunity:
- Notice ID: `FA524026Q0041`
- Current action: `0f367577ad68477b947384888441974e`
- Public page: https://sam.gov/opp/0f367577ad68477b947384888441974e/view

The current SAM page's public History links expose the three predecessor action UUIDs:
1. `838bdb200ad14374a300c9debd2a86cf` — original, Sep 15 2026 05:47 pm AEST
2. `a9d281564bc540ab8ef09af4c64c2a53` — updated, Sep 17 2026 05:02 pm AEST
3. `cf21df787f6d480897b037d1af47aa7d` — updated, Sep 17 2026 05:17 pm AEST
4. `0f367577ad68477b947384888441974e` — latest/current, Sep 17 2026 05:21 pm AEST

Public action URLs:
- https://sam.gov/opp/838bdb200ad14374a300c9debd2a86cf/view
- https://sam.gov/opp/a9d281564bc540ab8ef09af4c64c2a53/view
- https://sam.gov/opp/cf21df787f6d480897b037d1af47aa7d/view
- https://sam.gov/opp/0f367577ad68477b947384888441974e/view

All four public action pages resolved during this run.

## First-party current attachment state
The current first-party SAM page exposes **8 attachment rows**:
1. `Solicitation - FA524026Q0041 Rev 1 (17SEP26).pdf` — 575 KB — Public — Sep 17 2026
2. `Solicitation - FA524026Q0041 Rev 1.pdf` — **Deleted** — 575 KB — Public — Sep 17 2026
3. `Questions and Answers FA524026Q0041 - 36 WG Vehicle Removal and Towing Services IDIQ.pdf` — 97 KB — Public — Sep 17 2026
4. `Attachment 1 - PWS 36 WG Vehicle Removal and Towing Services IDIQ (10 AUG 26).pdf` — 226 KB — Public — Sep 15 2026
5. `Attachment 2 - Price List.xlsx` — 34 KB — Public — Sep 15 2026
6. `Attachment 3 - Wage Determination 2015-5693 Rev29 (27AUG26).pdf` — 512 KB — Public — Sep 15 2026
7. `Attachment 4 - Past Performance Fact Sheet.docx` — 49 KB — Public — Sep 15 2026
8. `Attachment 5 - Past Performance Questionnaire.docx` — 50 KB — Public — Sep 15 2026

The description separately says Amendment 0001's purpose was to provide Government responses to industry questions and an amended solicitation.

### Verified implication
The current authoritative UI itself distinguishes a current revised solicitation from a deleted predecessor. A packet model that flattens this family to one human-readable solicitation filename loses state that SAM presently exposes.

## Independent temporal corroboration / negative comparator
A public third-party SAM mirror preserved the four-notice history but exposed a **6-document current inventory** consisting only of the Q&A plus Attachments 1–5. Its original Sep 15 notice snapshot exposed a different **6-document inventory** consisting of the original solicitation plus Attachments 1–5.

Original mirror snapshot:
- https://sam.directory/opportunities/36-wg-vehicle-removal-and-towing-services-idiq-andersen-afb-guam-fa524026q0041/notices/838bdb200ad14374a300c9debd2a86cf
- Documents shown: original `Solicitation_-_FA524026Q0041.pdf` + Attachments 1–5.

Current mirror family page:
- https://sam.directory/opportunities/36-wg-vehicle-removal-and-towing-services-idiq-andersen-afb-guam-fa524026q0041
- Notice history shown: 4
- Documents shown: Q&A + Attachments 1–5.

The current first-party SAM page, by contrast, exposes 8 rows and retains both the current revised solicitation and a deleted predecessor. Therefore a normalized opportunity/history surface can preserve the action count while still losing attachment-state evidence.

### Evidence discipline
The mirror is **not** authoritative and this finding does not prove that SAM Data Services itself omits these attachment objects. It is retained only as an independent negative comparator demonstrating that `notice_history_complete` and `attachment_inventory_complete` must be separate assertions.

## Official API boundary
GSA's public Get Opportunities API documentation explicitly states that the API returns only the latest active version and directs users to Data Services for all versions. The same API exposes `resourceLinks`, but latest-version discovery and historical-version reconstruction remain separate planes.

Official documentation:
- https://open.gsa.gov/api/get-opportunities-public-api/

This reinforces the architectural rule already planted by EXP-006: no single latest-row or normalized-history view proves packet completeness.

## Exact resource-ID question: unresolved in this run
The public SAM resource-manifest URL pattern for each action is:
`https://sam.gov/api/prod/opps/v3/opportunities/{ACTION_UUID}/resources?excludeDeleted=false&withScanResult=false`

The free public-web tools available in this run could reach these URLs but did not expose the JSON response body. Interactive/metered browsing was not used because the run is non-interactive and spending money is not authorized. Therefore:
- distinct `resourceId` values for the current and deleted solicitation revisions are **NOT VERIFIED** in this run;
- `UNION(all four action manifests) - latest` for this family is **NOT VERIFIED** in this run;
- no claim is made that the two equal-size 575 KB rows are different bytes merely because they have different presentation labels/states.

This is a bounded unresolved edge, not a reason to discard the fixture.

## Capability delta
`CAP-011` should represent two separate completeness dimensions:
1. **NOTICE/ACTION HISTORY COMPLETENESS** — every action/version in the family is accounted for;
2. **ATTACHMENT/RESOURCE COMPLETENESS** — source objects, deletion/access state and observation-time history are accounted for.

A source can satisfy (1) while failing (2).

Recommended packet state model:
- `history_complete_attachment_unknown`
- `history_complete_attachment_partial`
- `history_complete_attachment_complete`
- `history_partial_attachment_unknown`

These should remain independent from semantic reference closure and artifact-byte availability already identified in prior EXP-006 work.

## Graph edge
`SAM notice family -> action UUID history` **does not imply** `complete attachment inventory`.

Required independent edge:
`action UUID -> manifest observation -> resourceId/source-state rows`.

Only the latter can support attachment-level completeness claims.

## Radar signal
Strengthens `RAD-008` qualitatively: machine-readable public authority is multi-plane. A history surface may correctly preserve source versions while a document index loses tombstones or controlling files.

## Experiment impact
Add/retain the planted case:
`NOTICE_HISTORY_COMPLETE_BUT_ATTACHMENT_ENUMERATOR_INCOMPLETE`.

Expected behavior:
- do not emit `complete_public`;
- preserve first-party action UUIDs;
- compare normalized/bulk/mirror enumerators only as secondary challengers;
- require per-action first-party manifest observations before attachment completeness.

For `FA524026Q0041`, the next exact test remains:
1. query all four action manifests with explicit `excludeDeleted=false`;
2. record each `resourceId`, presentation name, deleted/access/file state and observation time;
3. compute `UNION(history) - latest`;
4. test whether the current and deleted solicitation rows have distinct `resourceId`s;
5. preserve failure/shape-unavailable as unresolved rather than absence.

## Commercial impact
The CaptureBrief **Solicitation Packet Integrity Audit** can differentiate itself by reporting two independent statements:
- “We reconstructed all public notice actions.”
- “We proved the attachment/resource inventory for those actions.”

Many procurement tools implicitly collapse those into one. This fixture shows why that is unsafe: a user can see a complete-looking four-action history while a normalized document list omits solicitation-state evidence still present on the first-party SAM page.

## Negative knowledge
- Complete notice history is not attachment completeness.
- A normalized document list is not a tombstone ledger.
- Equal filename/size or adjacent labels do not establish source-object identity.
- Third-party mirrors are useful falsifiers/corroborators, not authoritative completeness sources.
- Failure to retrieve a manifest body is `UNRESOLVED`, never `zero resources`.

## Cross-lane referral
**Data/provenance lane:** model `history_completeness` and `attachment_completeness` as separate typed receipts. Exact unanswered question: can a source-agnostic evidence envelope enforce that a version-complete family remains non-green until every successful action has an independently observed manifest or an explicit source-unavailable state?

## Strongest objection
The new finding proves a real mismatch between the first-party current attachment state and a third-party normalized document inventory, but it does **not** yet prove resource-level loss inside SAM's own historical manifest plane. The exact resource-ID/union test remains the decisive source-level follow-up.

## Next highest-value question
Across the four action UUIDs for `FA524026Q0041`, do explicit deletion-inclusive first-party manifests prove distinct resource IDs for the current and deleted solicitation revisions, and does their historical union contain any resource absent from the latest manifest?
