# CMS Transparency-in-Coverage Payer Rate Ledger

Provenance-first ingestion for the CMS Transparency in Coverage (TiC) payer machine-readable-file universe.

## Why this exists

The public TiC corpus is extraordinarily large. Some payer releases contain tens of thousands to hundreds of thousands of files and hundreds of terabytes of uncompressed JSON. A no-spend GitHub workflow should not pretend that copying all bytes into one repository or one Actions artifact is viable.

This subsystem separates two responsibilities:

1. **Universe inventory** — payer roots → public landing/listing/index pages → CMS table-of-contents files → plans → in-network / allowed-amount MRF URLs.
2. **Rate-content ingestion** — download a selected MRF once, hash exact source bytes, stream it without loading the file into memory, and normalize its provider/rate relationships into Parquet.

That gives PayerRecovery a complete discovery catalog while allowing content ingestion to be targeted by payer, plan, NPI/TIN, billing code, or recovery case.

## Discovery sources

The initial source universe is built from:

- a snapshotted public curated payer-source registry from `EndurantDevs/healthcare-mrf-api`;
- built-in fallback roots for UHC, Anthem/Elevance, Cigna, Aetna/CVS, Humana, Optum, and a bounded Centene/Fidelis acceptance TOC.

Third-party source registries are discovery seeds only. No rate or plan fact becomes evidence until the payer/CMS-format source itself is observed.

UHC has an explicit listing adapter for its public blobs API. Generic discovery handles CMS TOCs, directory JSON, JSON/HTML link pages, and direct MRF URLs. Dynamic portals that cannot be resolved without additional adapters remain explicit gaps.

## Provenance

Inventory records preserve:

- exact index/landing-page SHA-256 where bytes were downloaded;
- URL, HTTP status, content type and length;
- ETag / Last-Modified where available;
- discovery parent and method;
- reporting entity + schema version + `last_updated_on`;
- exact plan-to-file relationships from the CMS TOC.

Rate ingestion preserves:

- exact raw-file SHA-256;
- source URL and HTTP metadata;
- parser version and active filters;
- normalized provider references, TINs/NPIs, billing items, negotiated rates, provider bridges and negotiated prices;
- a manifest with every Parquet part and row count.

## Normalized rate model

The pipeline does not denormalize every price × provider cross-product.

Tables:

- `provider_references`
- `provider_groups`
- `provider_npis`
- `items`
- `rates`
- `rate_provider_refs`
- `prices`

This mirrors the CMS relationship model and prevents avoidable row explosion.

## Historical-date safety

TiC negotiated-price objects provide an `expiration_date`, but they do not provide a contractual effective-start date.

Therefore:

- `expiration_date` can support end-date evidence;
- the monthly payer snapshot and `last_updated_on` are observation/publication evidence;
- a current MRF cannot prove that the same negotiated rate applied before the first relevant snapshot;
- money-bearing recovery must still resolve the provider contract / amendment / claim context.

`resolve.py` fails closed for pre-snapshot service dates and returns `REQUIRES_CLAIM_CONTEXT` when multiple price semantics remain.

## Local use

```bash
cd production/cms_tic_ledger
python -m pip install -r requirements.txt
python -m unittest -v test_tic_ledger.py

# Inventory a deterministic source shard.
python inventory.py inventory \
  --out output/shard-0 \
  --db catalog.sqlite \
  --shard-count 4 \
  --shard-index 0

# Merge inventory shards.
python merge_catalog.py \
  --input-root downloaded \
  --db merged/catalog.sqlite

# Ingest one selected public rate file.
python rate_ingest.py \
  --catalog merged/catalog.sqlite \
  --out rate-output \
  --url 'https://example/..._in-network-rates.json.gz' \
  --billing-code 99213 \
  --max-gb 1

# Query normalized evidence.
python resolve.py \
  --catalog merged/catalog.sqlite \
  --normalized-root rate-output/normalized \
  --billing-code 99213 \
  --service-date 2026-09-01 \
  --npi 1234567890
```

## Scope

This is ingestion #1 in the requested dataset sequence. Do not start OpenEI/URDB ingestion until this lane has passed live inventory + real-MRF acceptance.
