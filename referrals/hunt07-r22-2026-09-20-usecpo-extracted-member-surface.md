# Hunt 07 r22 — USECPO extracted member surface / raw-grain verification

**Date:** 2026-09-20  
**Lane:** NODE 07 — Geo Asset Intel  
**Status:** WATCH / evaluator-provenance + semantic-grain evidence  
**Score:** 23/30 (A4 B4 C4 D4 E4 F3)

## Finding

A second public repository, `Resilient-Supply-Chain/open-supply-chain-control-tower`, at pinned revision `d0691e25ee1760cc0c0b5258761c12f8add0a9cb`, contains extracted USECPO event-correlated CSV files as ordinary Git blobs. This is a different repository from the `brayo003/...` mirror audited in r21. The r21 correction therefore remains valid: that earlier pinned mirror had only an archive-level Git LFS pointer and no extracted outage tree.

This new repository materially advances the member-level evidence gate because the actual 2023 standard event-correlated member was inspected beyond README:

- path: `outage_data/Outage_Dataset/eaglei_outages_with_events_2023.csv`
- exact byte size: **12,452,488**
- Git blob SHA-1: **`35ac9310f2ee3ec0eb12cd5a786d08f8e5181a95`**
- literal header: `fips_code,county,state_name,start_time,end_time,duration,min_customers,max_customers,mean_customers,year,outage_event,event_type,event_id,event_name`

The repository also explicitly cites the PNNL/OpenEI Event-Correlated Outage Dataset in `paper.bib` with `https://data.openei.org/submissions/6458`, and notebooks load the 2022/2023 `eaglei_outages_with_events_*.csv` files for analysis. This is therefore not merely an orphaned filename found by tree search.

## Direct raw-row semantic test

The beginning of the actual 2023 CSV contains the same Rockbridge County, Virginia outage spell repeated under the same `event_id=2023-36` with multiple event-type/event-name representations:

- `2023-11-21 02:45:00` → `2023-11-21 03:44:59`, event type `Severe Weather, Transmission Interruption`
- the same county/start/end/customer spell, event type `Transmission Interruption`
- the same county/start/end/customer spell, event type `Severe Weather`

This is direct byte-level evidence from an externally hosted extracted member that the flat `with_events` table can multiply one outage spell across event-attribution rows. It independently strengthens r19's rule that additive outage burden must be computed at unique county-spell grain `(fips,start_time,end_time)` with a separate spell↔event bridge rather than summing flat event-correlated rows.

## Timestamp / missingness observations

Visible timestamp strings use the literal form `YYYY-MM-DD HH:MM:SS`; the inspected values contain **no explicit timezone suffix or offset**. A full-resource text search of this mirrored 2023 member found no occurrences of the common representations `NaN`, `None`, `,nan,`, `,,`, `""`, or `+00:00`.

These observations are deliberately narrow. They do **not** establish:

- the intended first-party timezone semantics;
- that all years/variants lack nulls;
- that absence of an offset means UTC;
- that the mirrored member is byte-identical to a member of the currently served first-party OEDI ZIP.

## Provenance boundary

Current first-party federal metadata still identifies PNNL's `Outage Dataset v2.zip` at `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`, under CC BY 4.0. The first-party archive's SHA-256 remains unverified in this lane.

Previously established external expected archive identity remains:

- SHA-256: `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`
- size: `31,260,449` bytes
- external archive witness count: 2

The newly inspected extracted member is **not yet cryptographically bound** to that expected archive. This run establishes a member-level external surface, not first-party authority and not archive-membership proof.

## Evidence labels

- **VERIFIED_EXTERNAL_MEMBER:** actual 2023 member content inspected from pinned Git blob.
- **VERIFIED:** literal 14-column header, byte size, Git blob SHA-1, and raw repeated-attribution rows.
- **VERIFIED:** repository provenance citation points to PNNL/OpenEI submission 6458; notebooks consume 2022/2023 event CSVs.
- **UNVERIFIED:** member SHA-256.
- **UNVERIFIED:** member-to-expected-archive byte identity / ZIP membership.
- **UNVERIFIED:** current first-party OEDI ZIP SHA-256.
- **UNVERIFIED:** source timezone meaning and all-year/all-variant null semantics.

## Capability delta

CAP-015 should distinguish **archive receipt**, **member receipt**, **semantic grain**, and **first-party authority**. This run supplies an externally verified literal member schema plus direct raw evidence of attribution multiplicity.

## Graph edge

`Resilient-Supply-Chain/open-supply-chain-control-tower@d0691e25...` **STRENGTHENS** the r19 grain correction and EXP-012 evaluator design, while remaining subordinate to first-party USECPO authority.

## Radar signal

Proof-carrying prospective evaluators increasingly require artifact-level and member-level receipts plus semantic-grain identity, not merely a dataset URL or enclosing archive hash.

## Experiment impact

EXP-012 can now freeze the externally witnessed 2023 literal header and demonstrate why flat-row aggregation is invalid. It still must fail closed on first-party/archive-member identity and timezone semantics before production scoring.

Recommended evaluator receipt fields:

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

## Commercial impact

This reduces the risk that a Grid Resilience Calibration / Acceptance Audit double-counts outage burden while appearing reproducible. It advances evaluator implementation without weakening the authority gate.

## Negative knowledge

1. A member exposed by a public mirror is not first-party authority.
2. Literal timestamps without offsets do not reveal timezone meaning.
3. One year's lack of obvious null tokens does not establish cross-year missingness semantics.
4. A Git blob SHA-1/size does not prove membership in an externally hash-pinned ZIP.
5. The r21 correction remains valid for the separate `brayo003/...` repository; evidence from this new repository must not be retroactively attributed to that mirror.

## Cross-agent referral

**To:** EXP-012 / CAP-015 integrator.  
**Question:** Can the hash-matching expected USECPO archive be retrieved and its central directory/member digests used to bind this externally inspected 2023 member to the expected archive, while keeping current first-party OEDI digest equality as a separate authority gate?

## Next action

Retrieve either the current first-party OEDI archive or a byte-identical archive matching `44557bae...910fe7`; inspect the ZIP central directory; compute member SHA-256/CRC for `eaglei_outages_with_events_2023.csv`; compare it with the pinned external member; then inspect exact raw member bytes for null/timestamp representations. Do not infer timezone semantics unless authoritative documentation or first-party metadata states them.