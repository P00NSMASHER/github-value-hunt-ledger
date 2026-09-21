# Hunt 05 R22 — SAM bulk currentness boundary

Date: 2026-09-20
Lane: Gov Evidence / CaptureBrief
Status: STRONG CAP-011 / EXP-006 evidence; no new MASTER repository promotion

## Best new finding

### Complete SAM bulk history cannot source-authoritatively select the controlling current action

Live fixture: `FA524026Q0041`.

The first-party SAM opportunity page currently resolves to action UUID `0f367577ad68477b947384888441974e` and shows **Updated Published Date 2026-09-17 05:21 PM AEST**. Its history shows four actions: 2026-09-17 05:21, 05:17, 05:02, plus the 2026-09-15 original.

Source: https://sam.gov/opp/0f367577ad68477b947384888441974e/view

By contrast, Abierto — which explicitly says it reads SAM.gov Data Services Contract Opportunities bulk rows rather than the website and keeps each notice row verbatim — reconstructs all four action UUIDs but reports `cf21df787f6d480897b037d1af47aa7d` as the **Latest notice**. Its publication list contains:

- `838bdb200ad14374a300c9debd2a86cf` — 2026-09-15
- `0f367577ad68477b947384888441974e` — 2026-09-17
- `a9d281564bc540ab8ef09af4c64c2a53` — 2026-09-17
- `cf21df787f6d480897b037d1af47aa7d` — 2026-09-17

Source: https://abierto.us/opportunities/fa524026q0041
Data-method source: https://abierto.us/data

Abierto states that SAM issues a new notice ID for each revision and lists every active revision as its own bulk row. It groups notices sharing a solicitation number. The page was rebuilt from the Contract Opportunities bulk extract and still selects `cf21...` despite the first-party SAM current action being `0f367...`.

## Why the bulk plane is structurally insufficient for currentness

The Contract Opportunities full CSV has 47 columns. An independently inspected parser/header lists:

`NoticeId, Title, Sol#, Department/Ind.Agency, CGAC, Sub-Tier, FPDS Code, Office, AAC Code, PostedDate, Type, BaseType, ArchiveType, ArchiveDate, SetASideCode, SetASide, ResponseDeadLine, NaicsCode, ClassificationCode, Pop*, Active, Award*, contacts, OrganizationType, State, City, ZipCode, CountryCode, AdditionalInfoLink, Link, Description`.

Critically, that schema does **not** expose an authoritative `latest/current` flag, `modifiedDate`, `createdDate`, or an explicit source sequence for same-family revisions.

Independent code/header evidence:
- `SirLord/Gov-Contract-Finder@9654eab06f6bcc01f0d89f733cd0a15802a85031`, `app.py`
- https://github.com/SirLord/Gov-Contract-Finder/blob/9654eab06f6bcc01f0d89f733cd0a15802a85031/app.py

`JonGerhardson/federal-agent@5674ce02df97f9f7fef88e5dc33c08ea82cefb22` independently documents the same file as **active notices only**, a **current-state snapshot, not a time series**, with 47 columns and useful fields including `NoticeId`, `PostedDate`, `Link`, but no authoritative current-revision field. Its loader preserves columns as-is and writes SHA-256/Last-Modified provenance manifests.

Evidence:
- `federal-procurement/references/file_extracts.md`
- `federal-procurement/scripts/file_extracts.py`
- https://github.com/JonGerhardson/federal-agent/tree/5674ce02df97f9f7fef88e5dc33c08ea82cefb22

This means a downstream consumer can have **every active revision row** and still lack enough source semantics to prove which tied/same-day row is controlling. A row-order, last-row, lexical, day-granularity, or normalized `PostedDate` tie-break is not source authority. I did not obtain Abierto's private selection code, so the exact implementation tie-break is **UNVERIFIED**; the important verified result is that the bulk schema itself does not carry a trustworthy currentness primitive.

## First-party authority surfaces clarify the split

GSA's official Get Opportunities Public API documentation states that it **only provides the latest active version of the opportunity**, while users should go to Data Services to view all versions.

Source: https://open.gsa.gov/api/get-opportunities-public-api/

Therefore the two first-party planes have different authority roles:

- **Public Opportunities API / live SAM current view:** current/latest-active assertion.
- **Data Services bulk:** broad version/member rows for history/current-state bulk processing, but not sufficient by itself to prove same-family currentness.

The separate Opportunity Management history specification is even more explicit internally: history objects have `latest`, `postedDate`, `modifiedDate`, and `createdDate`; that is precisely the class of source-effective metadata absent from the 47-column public bulk CSV. This management surface requires authorization and should not be treated as the public product dependency.

Source: https://open.gsa.gov/api/opportunities-api/

## Capability delta

CAP-011 should enforce **three independent receipts**:

1. `HISTORY_SET_RECEIPT` — which action/notice UUIDs were observed for the family.
2. `CURRENT_ACTION_RECEIPT` — the first-party source assertion identifying the current/latest-active action at observation time.
3. `ACTION_ORDER_RECEIPT` — source-backed effective chronology when exact ordering is required.

`HISTORY_SET_COMPLETE` must never imply either of the other two.

Recommended state machine:

- bulk gives full member set but no current pointer -> `HISTORY_SET_COMPLETE / CURRENT_UNKNOWN`
- bulk-derived pointer agrees with fresh first-party current assertion -> `CURRENT_VERIFIED`, citing the first-party receipt
- bulk/mirror pointer disagrees with first-party current assertion -> `CURRENT_ACTION_SOURCE_DISAGREEMENT`; first-party current assertion controls buyer-facing analysis, disagreement remains visible
- first-party current surface unavailable -> fail closed to `CURRENT_UNKNOWN`; do not promote a bulk tie-break to authority

## Experiment impact — EXP-006

Add/retain this planted real-world case:

`ALL_ACTION_UUIDS_PRESENT_BUT_BULK_SCHEMA_LACKS_AUTHORITATIVE_CURRENTNESS`

Expected behavior:
- identify all four action UUIDs;
- observe current action separately from first-party latest-active/live source;
- refuse to choose current solely from list order, UUID order, same-day `PostedDate`, or mirror `LATEST` labels;
- preserve the disagreement receipt;
- only after current action is resolved proceed to current packet/resource completeness.

A useful synthetic negative should deliberately shuffle three same-day revision rows while keeping every row/field intact. Any algorithm whose result changes under row permutation has proven it is deriving currentness from non-authoritative ordering.

## Commercial impact

CaptureBrief can turn this into a concrete buyer-visible distinction:

> **All amendments found** is not the same claim as **controlling amendment proven**.

That is a defensible Packet Integrity feature because a competitor can correctly ingest every SAM bulk row and still analyze the wrong revision if it guesses currentness from row/date ordering.

## Candidate note — JonGerhardson/federal-agent

- Exact revision: `5674ce02df97f9f7fef88e5dc33c08ea82cefb22`
- Status: WATCH / useful source-observation component, not currentness authority
- Score: 22/30 (A3 B3 C4 D3 E4 F5)
- Value: public no-key SAM bulk ingestion, exact-column preservation, SHA-256 + Last-Modified provenance, explicit current-state-snapshot warning.
- Limitation: does not provide authoritative intra-family latest/current selection; bulk source itself lacks that field.
- Rights: inspect repository license before direct reuse if needed; this run used it as implementation/evidence reference only.

## Radar signal

RAD-008 strengthened qualitatively, no numeric score change: **set membership, currentness, and chronology are different public-authority claims even when they concern the same versioned government object.**

## Negative knowledge

- Do not infer current action from bulk row order.
- Do not infer current action from lexical UUID order.
- Do not infer current action from a day-level posted-date tie.
- Do not accept a normalized mirror's `LATEST` label as source authority.
- Do not treat a complete action set as proof of temporal correctness.
- Do not use the keyed latest-active API as the history source; it intentionally returns only latest active.

## Cross-lane referral

Provenance/data lane: model `HISTORY_SET`, `CURRENT_ASSERTION`, and `ORDERING` as independent typed evidence objects. Exact unanswered technical question: can the common evidence envelope bind a first-party current-pointer receipt to a bulk-history snapshot while retaining disagreement and source observation times without mutating historical membership?

## Next highest-value question

Across the remaining frozen EXP-006 solicitation families with multiple same-day revisions, how often would a row-order/day-date/lexical current-selection rule disagree with the first-party latest-active/current assertion, and can one deterministic `CURRENT_ACTION_RECEIPT` contract cover active, cancelled, archived, and inactive families without guessing?