# Hunt 07 r22 — USECPO extracted-member surface + downstream grain hazard

**Date:** 2026-09-20  
**Lane:** NODE 07 — Geo Asset Intel  
**Status:** WATCH / evaluator-provenance + semantic-grain evidence  
**Score:** 23/30 (A4 B4 C4 D4 E4 F3)

## Finding

A different public repository, `Resilient-Supply-Chain/open-supply-chain-control-tower`, at pinned revision `d0691e25ee1760cc0c0b5258761c12f8add0a9cb`, contains extracted 2022/2023 USECPO event-correlated CSVs as ordinary Git blobs and actively consumes them in outage-risk / conditional-impact notebooks. This is **not** the `brayo003/...` repository audited in r21; r21 remains correct that the earlier pinned mirror had only an archive-level Git LFS pointer and no extracted outage tree.

At this revision the 2023 extracted member appears in two model-data locations but both paths point to the same Git blob:

- `Asset_Data_Team/risk_model/eaglei_outage/eaglei_outages_with_events_2023.csv`
- `Asset_Data_Team/conditional_impact_prediction_model/raw_data/eaglei_outages_with_events_2023.csv`
- exact size: **12,452,488 bytes**
- Git blob SHA-1: **`35ac9310f2ee3ec0eb12cd5a786d08f8e5181a95`**

The actual blob was inspected beyond README. Its literal 14-column header is:

`event_id,state_event,Datetime Event Began,Datetime Restoration,Event Type,fips,state,county,start_time,duration,end_time,min_customers,max_customers,mean_customers`

Visible timestamp strings use `YYYY-MM-DD HH:MM:SS` with no explicit timezone suffix/offset. That is a representation fact only; it does **not** establish timezone semantics.

The repository independently cites the PNNL/OpenEI Event-Correlated Outage Dataset (`https://data.openei.org/submissions/6458`) in `paper.bib`; its README labels the copied EAGLE-I/USECPO files as outage source data; and its notebooks load the 2022/2023 files directly. This is therefore an active downstream consumer, not merely an orphaned copied filename.

## Downstream grain hazard verified in code

The strongest new evidence is not a new outage oracle; it is a concrete example of how a real downstream consumer can aggregate the flat event-correlated rows unsafely.

`Asset_Data_Team/conditional_impact_prediction_model/data_cleaning.ipynb` performs:

`impact_agg = impact_filtered.groupby(["start_date", "county"]).sum().reset_index()`

and then renames `mean_customers` to `total_customers`.

The README describes this target as daily affected customers derived by summing outage-row mean customer counts. The risk-model notebook separately filters California severe-weather events before constructing county/day labels.

This matters because r19 already established that USECPO event-correlated rows are not a safe additive fact table: event attribution can multiply county outage spells, and exact-row deduplication alone does not solve many-to-many spell↔event fan-out. This repository therefore provides a live implementation example of the exact downstream aggregation pattern CAP-015 / EXP-012 must avoid. It should **not** be used as ground truth for outage burden without canonical spell deduplication.

## Timestamp / missingness observations

For the inspected mirrored 2023 blob:

- timestamp representation visibly uses `YYYY-MM-DD HH:MM:SS`;
- visible timestamps have no explicit timezone suffix/offset;
- full-resource text searches did not find the common tokens `NaN`, `None`, `,nan,`, `,,`, `""`, or `+00:00`.

These observations are deliberately narrow. They do **not** establish:

- intended first-party timezone semantics;
- all-year/all-variant missingness behavior;
- that absence of an offset implies UTC;
- that the mirrored member is byte-identical to a member of the currently served first-party OEDI ZIP.

## Provenance boundary

Current first-party federal metadata identifies PNNL's `Outage Dataset v2.zip` at `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`, under CC BY 4.0. The first-party archive's SHA-256 remains unverified in this lane.

Previously established external expected archive identity remains:

- SHA-256: `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`
- size: `31,260,449` bytes
- external archive witness count: 2

The newly inspected 2023 Git blob is **not yet cryptographically bound** to that expected archive. This run establishes an external member surface and a downstream implementation hazard, not first-party authority and not archive-membership proof.

## Evidence labels

- **VERIFIED_EXTERNAL_MEMBER:** actual 2023 CSV content inspected from pinned Git blob.
- **VERIFIED:** exact member paths, 12,452,488-byte size, Git blob SHA-1, and literal 14-column header.
- **VERIFIED:** repository citation points to PNNL/OpenEI submission 6458; notebooks consume 2022/2023 event CSVs.
- **IMPLEMENTED:** downstream notebook groups filtered flat outage rows by `(start_date, county)`, sums numeric columns, and renames summed `mean_customers` to `total_customers`.
- **UNVERIFIED:** member SHA-256.
- **UNVERIFIED:** member-to-expected-archive byte identity / ZIP membership.
- **UNVERIFIED:** current first-party OEDI ZIP SHA-256.
- **UNVERIFIED:** source timezone meaning and all-year/all-variant null semantics.

## Capability delta

CAP-015 should distinguish **archive receipt**, **member receipt**, **semantic grain**, **downstream transform**, and **first-party authority**. This run supplies a literal externally witnessed member schema plus a concrete downstream implementation of the aggregation hazard r19 warned about.

## Graph edge

`Resilient-Supply-Chain/open-supply-chain-control-tower@d0691e25...` **STRENGTHENS** r19's semantic-grain correction and **CHALLENGES** naive county/day aggregation for EXP-012. It remains subordinate to first-party USECPO authority.

## Radar signal

Proof-carrying evaluators require not only artifact/member receipts but transform receipts: a correct source can still produce a false evaluator when a downstream pipeline sums rows at the wrong grain.

## Experiment impact

EXP-012 should preserve the literal source/member fields, derive a canonical county outage-spell fact table before additive metrics, retain a separate many-to-many spell↔event bridge, and record the transform that turns raw rows into the scored outcome. A simple county/day `.sum()` over event-correlated rows is explicitly disallowed.

Recommended receipt fields:

- `archive_expected_sha256`
- `archive_first_party_sha256`
- `member_surface_source`
- `member_git_blob_sha1`
- `member_size`
- `member_header`
- `member_to_archive_binding_status = UNKNOWN | MATCH | MISMATCH`
- `timestamp_representation`
- `timezone_semantics = UNKNOWN | VERIFIED`
- `semantic_grain = county_outage_spell`
- `outcome_transform_id`
- `outcome_transform_hash`

## Commercial impact

This reduces the risk that a Grid Resilience Calibration / Acceptance Audit produces inflated interruption burden or trains on a distorted target while appearing reproducible. It also suggests a sellable QA wedge: **outage-evaluator lineage / grain audit** for teams consuming public reliability datasets.

## Negative knowledge

1. A member exposed by a public mirror is not first-party authority.
2. Literal timestamps without offsets do not reveal timezone meaning.
3. One year's lack of obvious null tokens does not establish cross-year missingness semantics.
4. A Git blob SHA-1/size does not prove membership in an externally hash-pinned ZIP.
5. Correct source files do not guarantee correct outcome labels; downstream aggregation is part of evaluator provenance.
6. The r21 correction remains valid for the separate `brayo003/...` repository; evidence from this repository must not be retroactively attributed to that mirror.

## Cross-agent referral

**To:** EXP-012 / CAP-015 integrator.  
**Question:** Can the hash-matching expected USECPO archive be retrieved and its central directory/member digests used to bind this externally inspected 2023 member to the expected archive, while the evaluator transform is rebuilt at unique-spell grain and current first-party OEDI digest equality remains a separate authority gate?

## Next action

Retrieve either the current first-party OEDI archive or a byte-identical archive matching `44557bae...910fe7`; inspect the ZIP central directory; hash the relevant 2023 member; compare it with the pinned external member; then implement/test a unique-spell transform and quantify how much the repository's naive county/day sum differs on the same input. Do not infer timezone semantics unless authoritative documentation or first-party metadata states them.