# CMS Transparency-in-Coverage Payer MRF Ingestion

Provenance-first ingestion for the public payer machine-readable-file universe.

This is dataset **#1** in the current ingestion sequence.

## Two-stage strategy

The national TiC corpus is too large for a blind download-everything approach. Individual files can be tens or hundreds of gigabytes and the aggregate monthly corpus is enormous.

1. **Universe catalog** — discover payer/index/file URLs, snapshot discovery sources, hash source bytes, retain plan relationships and HTTP metadata.
2. **Selective full normalization** — explicitly download chosen immutable MRFs, hash the bytes, and stream them into queryable provider/rate tables.

A cataloged URL is not treated as a verified rate source until the referenced file itself has been downloaded and hashed.

## Initial source registry

The checked-in source registry currently seeds:

- UnitedHealthcare / Optum public Azure MRF container
- Aetna / CVS Health public metadata endpoint
- Cigna public TiC landing page
- Elevance / Anthem public MRF landing page
- Aetna public TiC landing page
- Humana discovery seed

New payer sources can be added in `sources.json` without changing the parser.

Supported resolver types:

- `azure_blob_container` — paginate a public Azure container listing for the current monthly prefix.
- `metadata_json` — parse a public metadata document containing `files[]`.
- `html_links` — snapshot a public landing page and discover MRF/index links.
- `direct_index` — snapshot and stream a CMS Table-of-Contents file directly.

After discovery, `--expand-indexes` downloads cataloged CMS index files and streams `reporting_structure[]` into plans and referenced in-network/OON files.

Unresolved dynamic landing pages remain durable errors. They are never interpreted as evidence that a payer has no files.

## Evidence model

Every fetched discovery source or selected full MRF is content-addressed at:

`blobs/sha256/<first-two>/<sha256>`

The SQLite ledger retains requested/final URL, observation time, response type, byte count, SHA-256, ETag and Last-Modified where available.

Catalog entries retain payer/source family, file kind, plan/issuer/sponsor identity, content length, HTTP metadata and lineage to the hashed source observation.

## Normalized in-network model

`provider_groups` -> `provider_entities` (TIN, business name, NPI)

`negotiated_rates` <-> `rate_provider_groups`

A negotiated price is stored once and linked to every referenced provider group. This avoids multiplying the same price row by the number of provider references.

Rate evidence retains billing code/type/version, FFS/bundle/capitation arrangement, negotiated type and amount, expiration date, professional/institutional class, setting, service/POS codes, modifiers, structural locator and immutable source hash.

## Normalized out-of-network model

`allowed_amounts` retains billing code/type/version, TIN, billing class, service/POS codes, modifiers, historical allowed amount, billed charge, provider NPI and source locator.

No member or patient identifiers are used or expected.

## Run tests

```bash
cd production/tic_payer_mrf
python -m pip install -r requirements.txt
python -m unittest -v test_ingest.py
```

## Catalog the public source graph

```bash
python ingest.py catalog \
  --out output \
  --db ledger.sqlite \
  --expand-indexes \
  --probe \
  --workers 8
```

Summary:

```bash
python ingest.py summary --db output/ledger.sqlite
```

## Normalize a selected full MRF

```bash
python ingest.py normalize \
  'https://example/..._in-network-rates.json.gz' \
  --out output \
  --db ledger.sqlite \
  --kind in-network-rates \
  --codes 99213,99214,27447
```

Omit `--codes` only when a full-file normalization is deliberate; output can become extremely large.

## RecoveryWorks authority rule

The existing PayerRecovery branch expects verified effective-dated rates. Public TiC data is corroborating/benchmark evidence by default, not automatically the customer's controlling contract.

Recommended authority hierarchy:

customer contract / fee schedule
-> payer-specific amendment or payment policy where applicable
-> exact TiC provider/plan rate as corroboration
-> broader TiC market benchmark
-> Medicare/reference schedule.

Unresolved provider identity, plan identity or authority stays review-only and contributes **$0 asserted recovery**.

## Scale controls

- catalog before full download
- streaming JSON with `ijson`
- immutable content-addressed evidence
- separate rate/provider link table to avoid rate-row explosion
- optional billing-code filters
- explicit index byte limits
- explicit Azure listing page limits
- no automatic full-MRF downloads
- public source failures retained as errors
