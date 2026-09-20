# Hunt 07 R19 — USECPO grain / event-identity audit

Date: 2026-09-20
Lane: Node 07 — Geo Asset Intel
Related: CAP-015, EXP-012, Grid / Infrastructure Decision Assurance

## Result
A current downstream implementation that downloaded the official OEDI `Outage_Dataset_R1.zip` on/around 2026-09-01 exposes two evaluator defects that materially change EXP-012 design. Repository: `Jaskeeratr/grid-reliability-analytics@24e59a7318db3560b6547ff9b79416119abf6ecb`.

The project lands the literal `eaglei_outages_with_events_<YYYY>.csv` family for 2014–2023 without parsing/deduplication first, then computes expected counts independently in pandas and SQL Server. Its pinned source and generated expected-results agree on 526,165 raw rows.

## Finding 1 — `event_id` is not globally unique
The audit reports 663 distinct `event_id` strings but 2,953 distinct events under the natural key `(event_id, Datetime Event Began, Datetime Restoration, Event Type)`. 498 of 663 `event_id` strings recur across years. Example: `Arkansas-0` refers to a 2014 fuel-supply emergency and a 2019 severe-weather event.

EXP-012 correction: never use bare `event_id` as the cross-year partition key. Use a release-bound composite event key at minimum `(source_year, event_id)`; preferably preserve the full audited natural key `(event_id, event_began, event_restored, raw_event_type)` plus source year/file provenance. Then group every row attached to that composite event into one split.

This supersedes any earlier shorthand that treated literal `event id` alone as globally unique across the 2014–2023 evaluator.

## Finding 2 — flat event-correlated rows are unsafe for additive outage metrics
The audit reports:
- 526,165 source rows.
- 308,615 rows participate in exact full-row duplicate groups.
- 273,291 are surplus exact copies removed by keeping one representative.
- 252,874 source rows survive exact-copy quarantine.
- Those survivors collapse to 168,858 unique county outage spells at grain `(fips, start_time, end_time)`.
- 22.75% of county outage spells map to more than one DOE-417 event; maximum observed fan-out is 34 events for one spell.
- A naive `SUM(mean_customers * duration)` over all source rows yields 21,478,985,822 customer-hours versus 2,529,006,494 at one-spell grain: 8.49x inflation. Exact duplicate removal alone reduces the naive total to 5,889,173,102; the remaining inflation is event↔spell fan-out/grain duplication.

EXP-012 correction: model observed outage burden at one county-spell grain and attach DOE-417 events through a many-to-many bridge. Never calculate additive customer-hours directly from the flat `with_events` rows. Event-level outcome aggregation must deduplicate spells before summing.

## Evidence inspected beyond README
- `python/load_raw.py`: literal 14-column source header list; loads `eaglei_outages_with_events_YYYY.csv` as text with source file/line provenance and no cleanup; warns unless total rows = 526,165.
- `python/expected_counts.py`: independent pandas oracle; defines source columns, event natural key, spell grain, duplicate surplus, event/spell bridge count, and audited-vs-naive customer-hours.
- `sql/05_dim.sql`: enforces unique event key `(event_id, event_began, event_restored, cause_key)` and documents cross-year event-id reuse.
- `sql/06_fact.sql`: enforces unique spell grain, quarantines duplicate rows, and creates a distinct spell↔event bridge; comments document 22.75% multi-event spells and max fan-out 34.
- `sql/02_stg.sql`: parses all four time columns into timezone-naive `DATETIME2(0)` using style 120 and converts blank text to NULL at the raw-loader boundary. This establishes the downstream implementation's assumed timestamp representation but is not first-party proof of timezone semantics.
- Commit `24e59a7318db3560b6547ff9b79416119abf6ecb` (2026-09-16) narrows overstated claims after review and records that the core 526,165-row and 8.49x results were reproduced. Treat this as repository-history evidence, not independent first-party authority.

## First-party / provenance boundary
Current first-party Data.gov/OEDI metadata still identifies PNNL's `Outage_Dataset_R1.zip` as the current v2 resource at the exact same URL and CC BY 4.0, and August 2026 DOE download metrics show that exact URL actively served downloads. However, the first-party ZIP SHA-256 remains unavailable through the accessible metadata and direct binary inspection is still blocked in this runtime.

Therefore:
- `external_manifest_expected_sha256 = 44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`
- `first_party_digest = UNKNOWN`
- `external_vs_first_party_digest_status = UNKNOWN`
- downstream grain/identity audit = strong secondary evidence, not a substitute for first-party byte identity.

## Score
`Jaskeeratr/grid-reliability-analytics@24e59a7...` as an EXP-012 evaluator-QA component: A4 B5 C5 D5 E5 F4 = **28/30**.

Why high: it reveals two false-green failure modes that can change evaluated outage burden by an order of magnitude and can leak unrelated events across temporal splits. Why not a production authority: it is a downstream analysis, not the OEDI publisher; repo public-license grant was not established during this run, though the user's standing repository authorization applies to repository-owned material and the OEDI source itself is CC BY 4.0.

## Capability delta
CAP-015 must bind a prediction evaluator not only to source release/hash and whole-event grouping, but also to **globally stable event identity and additive outcome grain**. A later outcome dataset can be cryptographically pinned yet still give a false score if duplicated rows or many-to-many attribution are aggregated at the wrong grain.

## Graph edge
`Jaskeeratr/grid-reliability-analytics@24e59a7...` -> CHALLENGES prior bare-`event_id` grouping assumption -> STRENGTHENS CAP-015 -> sharpens EXP-012.

## Radar signal
Strengthens RAD-005 / proof-carrying prospective prediction evidence: evaluator receipts need semantic grain/identity contracts in addition to artifact hashes. No numeric radar-score increase; this is stronger correctness evidence, not adoption acceleration.

## Experiment impact
Before EXP-012 scores any policy:
1. verify first-party OEDI bytes/digest;
2. build composite event identity, never bare `event_id` across years;
3. form one unique county-outage-spell table keyed by `(fips, start_time, end_time)`;
4. form a distinct spell↔event bridge;
5. whole-event block using composite event identity;
6. calculate additive outage burden once per unique spell;
7. keep STANDARD/8H/24H as sensitivity variants, not independent validators;
8. preserve source year/file and evaluator release/hash in every result receipt.

## Commercial impact
The proposed Grid Resilience Calibration / Acceptance Audit becomes more defensible. Without this correction, a buyer-facing report could overstate customer-hours materially or leak unrelated cross-year events into the same identity. This is a correctness/moat improvement, not new revenue evidence.

## Negative knowledge
- Bare `event_id` is not a global event key across 2014–2023.
- Flat event-correlated rows are not safe additive fact grain.
- Exact-row dedupe alone is insufficient; event↔spell many-to-many fan-out still inflates additive metrics.
- A source hash proves byte identity, not semantic grain correctness.
- Downstream timestamp parsing into timezone-naive `DATETIME2(0)` does not establish first-party timezone semantics.

## Next highest-value action
Obtain/hash the current first-party OEDI ZIP against `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`; on MATCH, byte-inspect central-directory filenames and literal raw timestamp/null semantics, then freeze a composite-event + unique-spell EXP-012 manifest before running any historical score.