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
