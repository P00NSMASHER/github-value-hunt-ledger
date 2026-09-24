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
