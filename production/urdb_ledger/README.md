# OpenEI URDB Ledger

Provenance-first Utility Rate Database ingestion for UtilityRecovery.

## Evidence layers

1. Official current bulk — exact bytes from https://apps.openei.org/USURDB/download/usurdb.csv.gz, SHA-256 hashed and stored content-addressed.
2. Current operational normalization — generated from those exact official bytes in the same run: tariff metadata, energy/demand tiers, flat-demand month mapping and run-length encoded TOU schedules.
3. Monthly normalized release history — exact urdb-for-ai data artifacts pinned by Git commit SHA, with their own SHA-256 hashes.
4. Tariff revision graph — supersedes and derived superseded_by relationships, with cycle detection and chain roots.

Current UtilityRecovery logic must still determine that a tariff applies to the customer account/service class. Dataset presence is not account-level authority.

## Outputs

- urdb.sqlite
- current/rates.parquet
- current/energy_rates.parquet
- current/demand_rates.parquet
- current/flat_demand_months.parquet
- current/schedules.parquet
- current/metadata.json
- content-addressed raw/release artifacts under blobs/sha256/
- summary.json

The SQLite ledger includes release metadata, source-file hashes, per-release tariff observations, current tariffs, and version-chain edges.

## Resolve an effective tariff

Exact label:

    python resolve.py --db output/urdb.sqlite --service-date 2026-09-01 --label TARIFF_LABEL

Utility/name lookup:

    python resolve.py --db output/urdb.sqlite --service-date 2026-09-01 --utility "Example Utility" --name "General Service"

Overlapping candidates fail closed as AMBIGUOUS_TARIFF; undated records do not get silently selected.

## Run

    python -m pip install -r requirements.txt
    python -m unittest discover -v -p 'test_*.py'
    python ingest.py --out output --db urdb.sqlite

## UtilityRecovery boundary

URDB is a high-value tariff/rate source, but a public database record is not by itself proof that a specific account was enrolled on that tariff. Account documents, service class and service period still control recovery validation.
