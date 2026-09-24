# Historical MNPI Research Corpus

This package is for **historical, already-public research and compliance analysis only**.

It does not ingest live confidential information and is not a trading feed.

## Step 1 — source registry

The source registry is the provenance gate for every later artifact.

Every source must include:

- stable `source_id`;
- source type;
- admissibility class;
- publisher;
- title;
- HTTPS source URL;
- publication date;
- SHA-256 of the exact retained artifact;
- timezone-aware retrieval timestamp;
- explicit confirmation that the source was already public;
- optional case/docket identifiers.

### Admissibility

**PRIMARY_PUBLIC_RECORD**

For already-public SEC, DOJ, court, or official FOIA artifacts. These may produce
candidate case/trade/publication-boundary facts in later stages, but those facts
will still require extraction review and exact source locators.

**PUBLISHED_RESEARCH_RECONSTRUCTION**

For peer-reviewed/public academic replication material. These remain explicitly
academic reconstructions and are never silently promoted to primary enforcement
facts.

**DISCOVERY_ONLY**

For secondary indexes, articles, catalogs, or lead-generation sources. They may
identify a primary source to retrieve, but they cannot establish a trade fact.

## Integrity

Each `SourceRecord` has a deterministic proof hash.

The full registry has its own order-independent registry hash. Duplicate artifacts,
conflicting source IDs, malformed hashes, non-HTTPS locations, naive timestamps,
or not-yet-public sources fail closed.

## Scope boundary

The constant `HISTORICAL_RESEARCH_COMPLIANCE_ONLY` is included in every record
and registry proof. A registry payload with a different usage scope is rejected.

## Tests

Run:

```bash
python -m unittest historical_mnpi.test_source_registry -v
```

Step 2 will retain raw public artifacts separately from normalized facts. No raw
source documents are downloaded by Step 1.


## Step 2 — raw artifact separation

Raw public source bytes are retained separately from every future normalized fact.

`LocalContentAddressedArtifactStore` accepts bytes only when:

- the source already exists in the Step-1 registry;
- the supplied source record's proof hash exactly matches that registered record;
- the source is confirmed already public;
- the exact bytes hash to the registered source SHA-256;
- acquisition/storage timestamps are timezone-aware and ordered;
- metadata such as filenames and media types passes validation before any write.

Artifacts are addressed as `sha256:<digest>` and stored under a content-addressed
layout. Reads re-check byte length and SHA-256. Existing objects are idempotent and
never overwritten with different content.

The local store reports
`APPLICATION_ENFORCED_APPEND_ONLY`. It does **not** claim the underlying
filesystem is provider-level WORM. `PROVIDER_VERIFIED_IMMUTABLE` requires a
separate provider attestation hash.

A `RawArtifactManifest` binds the exact source-registry hash to exactly one
retained artifact per registered source. The manifest contains hashes and custody
metadata only; source bytes are deliberately absent.

Future normalized records should use `SourceArtifactRef` to point to an exact
artifact and source location such as a page, paragraph, table, CSV row, JSON
pointer, text range, or archive member. Each reference pins both the Step-1
`SourceRecord.proof_hash` and the Step-2 `RawArtifactRecord.proof_hash`, so a
later metadata reclassification or custody-record change cannot silently alter
the provenance of a normalized fact.

Step 2 still performs no web retrieval and creates no normalized trade facts.


## Step 3 — canonical case layer

The case layer unifies multiple retained public artifacts around one historical
matter without turning case outcome into transaction truth.

A `HistoricalCase` contains:

- stable case identity and title;
- event type and information origin;
- proceeding status;
- named parties with explicit roles;
- issuers with optional historical CIK/ticker;
- exact proof-pinned raw-artifact references;
- optional complaint/opened and resolution dates.

Discovery-only sources cannot establish case content. Academic sources must remain
labeled `ACADEMIC_RECONSTRUCTION` and cannot masquerade as SEC/DOJ/court
artifacts.

Case proceeding status is deliberately separate from the fact status introduced
in Step 5. A settled or adjudicated case does not automatically prove every
individual allegation or transaction detail.


## Step 4 — sparse transaction schema

Historical transaction rows are deliberately sparse and provenance-bound.

A transaction must point to:

- an existing canonical case and exact case proof hash;
- a trader/party already present in that case;
- an issuer already present in that case;
- an exact retained artifact reference already linked to that case.

Trade timing may be represented as one exact timestamp, one date, or one date
range. The schema does not collapse ranges into guessed dates.

Price, quantity, profit, side, instrument, ticker, currency, exit data, and
option terms remain nullable/UNKNOWN when the public record does not establish
them. Numeric values are preserved as plain decimal strings rather than binary
floating-point values.

A transaction cannot be registered when its case proof, party, issuer, source
proof, artifact proof, or case-artifact relationship does not match.


## Step 5 — mandatory fact status

Every normalized historical transaction now requires an explicit `FactStatus`:

- `ALLEGED`
- `ADMITTED`
- `SETTLED_WITHOUT_ADMISSION`
- `FOUND_LIABLE`
- `CONVICTED`
- `COURT_ESTABLISHED`
- `ACADEMIC_RECONSTRUCTION`

The status is separately provenance-bound through `status_ref`. This matters
when the transaction details come from one artifact (for example a complaint
table) while the legal/factual status is established by another artifact (for
example a final judgment).

The verifier prevents status inflation:

- complaints/indictments can support allegations, not a `FOUND_LIABLE` label;
- liability requires a judgment;
- conviction requires a judgment or plea/statement artifact;
- court-established facts require court judgment/exhibit evidence;
- academic reconstructions must remain `ACADEMIC_RECONSTRUCTION`;
- non-academic legal statuses require a primary public record.

Case-level proceeding status remains separate and cannot automatically upgrade
the status of any individual transaction.


## Step 6 — information events and public-release boundaries

The event layer separates the historical information event from trade rows.

Each `InformationEvent` binds:

- one canonical case and exact case proof;
- one or more issuers already present in that case;
- an event type and historical information summary;
- a required public-release boundary;
- an optional private-information start boundary;
- optional tip/transfer boundaries.

Temporal precision is explicit: exact timestamp, date-only, or date range. Coarse
dates/ranges are not silently promoted to exact times.

Public-release boundaries require a primary public record linked to the case with
the `PUBLIC_RELEASE` artifact role. New primary source types cover public filings,
issuer press releases, and public regulatory releases.

Where both sides have exact timestamps (or both are date-only), chronology is
validated so the private-information boundary cannot follow the public release.
Cross-precision cases remain coarse rather than being guessed.


## Step 7 — source-specific candidate extractors

Extractors are deliberately **candidate-only**. They cannot create canonical
transactions/events or approve their own output.

Implemented adapters include:

- SEC HTML text extraction;
- SEC PDF page-text candidate extraction;
- DOJ/court page-text candidate extraction;
- academic CSV and ZIP/CSV extraction;
- a dedicated `hacked_earnings_jfe` `TimeOfFirstTrade.csv` adapter using the
  real public headers `PERMNO,SYMBOL,GVKEY,TimeOfFirstTrade`.

Each candidate preserves:

- exact source/artifact proof chain;
- source locator;
- extractor ID/version;
- raw excerpt hash;
- parsed field values and per-field parse state;
- warnings about important limitations.

PDF adapters consume separately supplied page text and explicitly mark it as
`PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION`; they do not OCR or claim visual
verification of the underlying PDF.

The hacked-earnings adapter explicitly marks its output as academic
reconstruction, retains the source's timezone ambiguity, and warns that
`TimeOfFirstTrade` is not complete trade economics.
