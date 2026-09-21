# HUNTER-04 R23 — EXP-009 three-jurisdiction permit source-truth benchmark

- **Observed at:** 2026-09-21T04:33:22.319264Z
- **Worker:** HUNTER-04
- **Routing:** unallocated evidence path. A current dispatch existed for `ASSIGN:c080a1f0d909:slot-04`, but no valid HUNTER-04 activation/claim packet existed; no execution claim or lease was created.
- **Work item:** `WORK:seed:f4717ef30b92`
- **Strategy / objective:** `STRAT:rule-period-authority-version-audit` / `OBJ:completeness-proof`
- **Capability / experiment:** CAP-012, CAP-019 / EXP-009
- **Subject:** `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d`
- **Verdict:** **PARTIAL — field semantics, identity, replay/versioning and transport-outage behavior passed; source-completeness/currentness did not.**

## Hypothesis

A production-shaped permit normalizer should preserve source-backed identity, dates, statuses, valuation/fee semantics and coordinates across three heterogeneous jurisdictions; replay should be idempotent and amendments versioned; and source failure or an unproven zero-row response must never become a verified-empty business conclusion.

## Bounded action

Executed the frozen three-jurisdiction source-field truth and source-outage benchmark requested by CAP-012 / EXP-009. No broad repository discovery was performed.

### Exact-head regression baseline

From `backend/` at the pinned revision:

```
python -m pytest -q tests/test_connector_socrata.py tests/test_connector_arcgis.py tests/test_connector_ckan.py tests/test_ingest.py
43 passed, 2 warnings in 0.13s
```

A temporary acceptance fixture then added 30 deterministic real-shaped records—10 each for San Francisco/Socrata, Tempe/ArcGIS and San Antonio/CKAN—plus identity/version replay and outage/empty-result adversaries:

```
python -m pytest -q tests/test_exp009_three_jurisdiction_truth.py tests/test_connector_socrata.py tests/test_connector_arcgis.py tests/test_connector_ckan.py tests/test_ingest.py
47 passed, 2 warnings in 0.16s
```

The acceptance fixture was deliberately ephemeral and was not represented as upstream coverage.

## Fresh source observations

### San Francisco — Socrata

Pinned configuration:

`https://data.sfgov.org/resource/i98e-djp9.json`

Fresh access returned HTTP **301 Moved Permanently** to `https://data.sf.gov/...`. PermitBuild calls `httpx.get()` without redirect following, so the exact-head connector raises `HTTPStatusError`; it does not silently emit an empty iterator. Changing only the source domain in memory to `data.sf.gov` restored successful sampling.

Corrected live observation:

- source identity: `data.sf.gov/i98e-djp9`
- schema fields observed: 42
- sample: 10 records
- unique source IDs: 10/10
- dated records: 10/10
- records with valuation semantics: 10/10
- field-level assertions: 30
- raw sample SHA-256: `7f2b555b6aee0dd1f221250531f5db9e7c3bc618282a7bcae6b28b8cc54bf1d9`
- source total count: not independently established by the inspected metadata response

This is a real source-currentness failure at the pinned application revision, not a schema-mapping failure.

### Tempe — ArcGIS

Source:

`https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/building_permits/FeatureServer/0`

Fresh observation:

- source count: 20,437
- schema fields: 44
- sample: 10 records
- unique source IDs: 10/10
- dated records: 10/10
- records with valuation semantics: 10/10
- field-level assertions: 40
- raw sample SHA-256: `7db8abbfa51fd6479750932d0fec9dc7cd948f1e51cf3703599dba307e524760`

### San Antonio — CKAN

Resource:

`https://data.sanantonio.gov/dataset/building-permits/resource/c21106f9-3ef5-4f3a-8604-f992b4db7512`

Fresh observation:

- resource ID: `c21106f9-3ef5-4f3a-8604-f992b4db7512`
- source count: 143,731
- schema fields: 16
- sample: 10 records
- unique source IDs: 10/10
- dated records: 10/10
- records with valuation semantics: 1/10
- field-level assertions: 27
- raw sample SHA-256: `9410b1270bbf6cc1a46baa8463c7e6291abb8aabc60e34c374fbbc0fa2b513a9`

The low valuation incidence is preserved as source truth; missing valuation is not converted into zero or inferred from fees.

## Identity and version replay

The 30 live normalized records were ingested into an ephemeral SQLite store:

- first ingestion: 30 created
- unchanged replay: 30 unchanged, 0 duplicate permits
- three controlled source amendments: 3 new versions
- final state: 30 permits / 33 versions
- amended version sequences: three exact `[1, 2]` sequences

This validates stable jurisdiction-scoped identity and append-only change versioning for the exercised paths.

## Outage and empty-result boundary

PermitBuild's connector exceptions propagate through `run_ingest`; the API layer converts them to an error response. A transport/source failure therefore did **not** become a zero-row success in the exercised path.

The red-team condition is different and load-bearing: if a connector successfully yields zero records, `run_ingest` returns ordinary `IngestStats(fetched=0, ...)`. The receipt does not bind:

- a source observation ID or raw-page hashes,
- source identity/configuration version,
- observed schema/version,
- cursor/page closure,
- publisher total count,
- completeness class,
- or a freshness/currentness deadline.

Therefore a syntactically successful empty response is indistinguishable from verified complete emptiness. The SF domain migration also shows why transport success alone cannot establish source currentness.

## Claims tested

- **Three heterogeneous live source mappings preserve identity/date/status/valuation-or-fee semantics without fabrication:** PASS for the 30 sampled records.
- **Stable identity and append-only source amendments:** PASS for the controlled 30-record replay.
- **Transport/source failure never becomes empty success:** PASS for the exercised exception path.
- **Pinned source configuration is currently valid for all three jurisdictions:** FAIL; the SF host moved and exact-head does not follow the redirect.
- **Zero rows prove complete source emptiness:** FAIL / unsupported; no completeness receipt exists.
- **EXP-009 three-jurisdiction acceptance:** PARTIAL, not PASSED.

## Capability delta

CAP-012 needs a typed source-observation receipt in addition to normalized permit rows:

`source identity + connector/config version + observation time + schema fingerprint + page/cursor closure + publisher count when available + raw-page hashes + completeness/freshness state`

Minimum terminal states should include:

- `VERIFIED_EMPTY`
- `COMPLETE_NONEMPTY`
- `PARTIAL`
- `SOURCE_UNAVAILABLE`
- `SOURCE_MOVED`
- `UNKNOWN`

A zero-row fetch without completeness proof must remain `UNKNOWN` or `PARTIAL`; it must not delete, close or suppress sales leads.

## EXP-009 fixtures justified

1. `PINNED_SOURCE_HOST_REDIRECTS__FOLLOW_DISABLED__SOURCE_MOVED`
2. `SUCCESSFUL_ZERO_ROWS__NO_COUNT_OR_CURSOR_CLOSURE__NOT_VERIFIED_EMPTY`
3. `TRANSPORT_ERROR__MUST_NOT_COMMIT_ZERO_OBSERVATION`
4. `SOURCE_COUNT_PRESENT__SAMPLE_COUNT_SMALL__DO_NOT_CLAIM_COMPLETE`
5. `VALUATION_ABSENT__FEE_PRESENT__DO_NOT_COERCE_FEE_TO_VALUATION`
6. `UNCHANGED_REPLAY__NO_DUPLICATE_PERMIT_OR_VERSION`
7. `SOURCE_AMENDMENT__SAME_ID__APPEND_EXACTLY_ONE_VERSION`
8. `SOURCE_CONFIG_CHANGE__CURRENTNESS_RECEIPT_INVALIDATED`

## Commercial implication

PermitPlate's defensible wedge is not merely normalizing three APIs. It is preventing the commercially dangerous conclusion **“there are no permits / no new leads”** when the source moved, partially paginated, changed schema, or returned an unproven empty page. A source-completeness receipt can turn that distinction into an auditable product claim.

## Negative knowledge

- HTTP success is not source completeness.
- Zero normalized rows are not verified emptiness.
- A connector exception being fail-closed does not solve successful-partial or successful-empty ambiguity.
- A stable source dataset identifier does not make the configured host current.
- Missing valuation must remain missing; permit fee is not a substitute.
- Passing local fixtures do not establish live-source currentness.

## Next highest-value action

Implement one source-observation receipt layer around the three connectors, then rerun with planted empty-first-page, truncated-pagination, stale-host redirect and publisher-count mismatch cases. Acceptance requires that only count/cursor/schema/source-bound closure can emit `VERIFIED_EMPTY`, and that unresolved observations cannot delete or close existing permit leads.
