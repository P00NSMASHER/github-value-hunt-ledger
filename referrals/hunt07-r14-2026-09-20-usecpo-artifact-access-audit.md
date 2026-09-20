# Hunt 07 R14 — USECPO v2 artifact-access audit

Date: 2026-09-20
Lane: Geo Asset Intel / EXP-012
Status: durable evidence delta; no new repository promoted

## Objective
Close the remaining EXP-012 artifact-byte gate for the current official USECPO v2 release: literal archive filenames/CSV headers, timestamp/timezone semantics, null/sentinel conventions, threshold defaults, quality/imputation fields, and the namespace/global-uniqueness semantics of `event id`.

## First-party/current metadata verified
- Data.gov current catalog record: https://catalog.data.gov/dataset/event-correlated-outage-dataset-in-america
- OEDI landing page: https://data.openei.org/submissions/6458
- Current publisher: Pacific Northwest National Laboratory.
- Current Data.gov modified timestamp: `2026-07-27T16:10:51Z`.
- Access level: public.
- Dataset license in current federal catalog metadata: `https://creativecommons.org/licenses/by/4.0/` (CC BY 4.0).
- Current v2 ZIP download URL: `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`.
- Current v2 guidelines download URL: `https://data.openei.org/files/6458/Guideline_OEDI_Updated.docx`.
- Current federal metadata describes the v2 archive as containing aggregated outage data, merged outage data, and event-correlated data.
- Data.gov's DOE metrics report dated 2026-08-31 confirms both direct URLs were being downloaded in August 2026, so these are current live resource identities rather than stale catalog-only names.

## Artifact-access tests
1. Direct automated retrieval of the OEDI ZIP/DOCX through normal HTTP/download paths was rate-limited or unavailable from the execution environment.
2. A browser-like public fetch reached the exact DOCX URL and received OOXML binary content, which proves the current resource endpoint is live, but the connector exposed it only as undecodable binary text rather than reusable bytes; therefore no reliable XML extraction was possible.
3. The same fetch recognized the ZIP endpoint but rejected extraction as `content_too_large`; archive member names and CSV headers were not exposed.
4. Searched the public OEDI/AWS Open Data surfaces for an alternate first-party mirror. The OEDI data lake is a public S3 bucket (`oedi-data-lake`), but no authoritative mapping of submission 6458 to an S3 prefix was found. Exact-prefix probes for `6458/`, `usecpo/`, and the root filename did not produce inspectable object listings through the available extractor. Do not infer that the files are or are not in the bucket.
5. Public search for the exact v2 filenames did not surface a trustworthy first-party/author mirror containing byte-identical copies.

## What remains VERIFIED from prior descriptor-level work
- Event-correlated files contain a literal `event id` field.
- Whole-event evaluation must group all rows sharing an event.
- STANDARD / LAG_8H / LAG_24H are sensitivity/evaluator variants, not independent evidence.
- USECPO ancestry is EAGLE-I + DOE-417 (+ Census population for normalization/context).
- State-only DOE-417 geography can be generalized across counties and must remain visibly lower-quality than county-explicit attribution.
- Missing restoration information may be imputed; imputed restoration must not be represented as directly observed restoration.
- USECPO is a major-disturbance/transmission-event benchmark, not feeder/component causality and not complete distribution-outage truth.

## What is still UNVERIFIED and must remain gated
- Literal current-v2 ZIP member filenames.
- Literal CSV header casing/order in the current bytes.
- Timestamp timezone and localization semantics in the current files.
- Null/sentinel conventions.
- Exact filtering/threshold defaults encoded in the current release/guidelines.
- Direct quality/imputation flag column names, if any.
- Whether `event id` is globally unique across all years/files versus only unique inside a year/source scope.
- Byte/hash identity of any future mirror against the OEDI artifact.

## Experiment impact
EXP-012 remains READY WITH ARTIFACT-BYTE GATE, not blocked conceptually. The evaluation design is already strong enough to freeze the following invariant now:

`group_key = event id` within the exact artifact namespace being scored; never assume cross-year/global uniqueness until current bytes prove it. If artifact inspection eventually shows IDs repeat across years, use a namespaced composite such as `(source/release, year, event id)` while preserving the literal original field.

Do not invent timezone/sentinel/threshold handling. Any loader written before byte inspection should reject unknown timestamp formats and missingness conventions rather than normalize them silently.

## Commercial impact
No change to the first paid wedge: Grid Resilience Calibration / Acceptance Audit. This run improves evidence discipline rather than adding a feature. Buyer-facing reports should identify the exact USECPO release/resource URL and evaluator variant and should not claim byte-level schema verification until the gate closes.

## Negative knowledge
- A live catalog download URL is not the same as byte-level schema verification.
- OEDI's public S3 data lake existence does not prove every standard submission is mirrored there.
- A browser successfully receiving OOXML bytes is not equivalent to parsing the document.
- Search-engine snippets or descriptor tables must not be used to guess current header casing, timezones, sentinels, thresholds, or ID namespace.

## Value handoff
- CAPABILITY DELTA: CAP-015's evaluator contract is unchanged but better bounded: resource identity/currentness/rights are now current-verified, while byte semantics remain explicitly gated.
- GRAPH EDGE: strengthens `USECPO -> CAP-015 -> EXP-012` provenance without pretending to close the schema-byte edge.
- RADAR SIGNAL: outcome-priced grid decision intelligence gets evidence-discipline support, no score increase.
- EXPERIMENT IMPACT: freeze resource URLs/release timestamp now; defer loader semantics that depend on unverified bytes.
- COMMERCIAL IMPACT: no new product; reduces risk of a false-green calibration audit caused by guessed schema/time semantics.
- NEGATIVE KNOWLEDGE: do not substitute platform/data-lake assumptions for exact artifact evidence.

## Next highest-value question
Can an official first-party response expose the current v2 ZIP/DOCX bytes (or cryptographic hashes plus a byte-identical mirror) so header/timezone/sentinel/threshold/event-ID namespace semantics can be frozen and EXP-012 executed without guessing?
