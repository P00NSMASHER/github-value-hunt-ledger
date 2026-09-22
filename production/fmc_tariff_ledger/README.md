# FMC Tariff Rule Ledger

Provenance-first crawler for the Federal Maritime Commission tariff-location directory.

## What it builds

The subsystem enumerates **current and all-history** FMC locations for:

- VOCCs
- OTI/NVOCCs
- marine terminal operators
- conferences

For every directory location it can reach, it:

1. preserves the exact response bytes in a content-addressed blob store;
2. computes SHA-256;
3. extracts text from HTML, PDF, CSV/text, and XLSX;
4. discovers linked tariff/rate/rule/history artifacts;
5. records source version and effective dates where present;
6. parses money, percentages, free-time quantities, named rule families, and generic `RULE` / `ITEM` sections;
7. materializes a carrier × rule × effective-date ledger in SQLite;
8. records fetch, parse, authentication, shared-publisher-resolution, and unsupported-format failures instead of silently dropping them.

The data model deliberately separates **evidence** from **applicability**. A public tariff entry is not automatically the governing agreement for a customer shipment. FreightRecovery must still resolve the contract/rate-confirmation/tariff precedence hierarchy before asserting a dollar recovery.

## Production entrypoint

Use **`run.py`** for production runs. It composes the core storage/parser contract in `crawler.py`, the publisher-aware discovery layer in `crawler_v2.py`, multi-currency monetary extraction, and raw FMC-directory snapshot preservation.

`publisher_adapters.py` currently recognizes shared publisher families including AP Tariffs, RateWave, DPI, BOTE, Descartes, DMS, Paramount, Tariff Data Systems, ETM, First Bay, Glenrate, ACE, CargoSphere, Blue/Lalandia, and eTariff.

Important behavior:

- shared publisher landing pages are snapshotted but are **not** attributed as carrier rules;
- AP Tariffs gets organization-number-addressable tariff/rule seeds;
- RateWave carrier-directory links are followed only when the carrier name matches;
- login/auth pages are retained as evidence of an unresolved source, never bypassed;
- an unresolved shared-publisher entity gets a durable `EntityTariffNotResolved` error.

## Ledger view

`carrier_rule_effective_ledger` exposes:

- FMC entity class
- organization number
- legal / trade name
- directory tariff location
- exact evidence URL
- source SHA-256
- fetch timestamp
- effective-from / effective-to
- tariff/revision identifier
- normalized rule type
- monetary or quantity value
- unit / currency
- confidence
- evidence locator and excerpt

## Rule coverage

Named rule families currently include demurrage, detention, free time, storage,
THC/terminal handling, wharfage, dockage, documentation/BOL fees, fuel/bunker
surcharges, chassis, reefer, hazardous/DG, congestion, security/ISPS, seals,
equipment, inland haulage, CFS, minimum charge, late fees, general freight rates,
and effective/revision clauses.

The v2 parser also preserves every detected `RULE <number>` or `ITEM <number>`
section as `rule:<number>`, including money, percentage, and free-time values found
inside it. This prevents the commercial ontology from silently discarding an
important but previously unknown tariff rule.

Every normalized value retains an evidence locator/excerpt so review can reject false
matches.

## Run locally

```bash
cd production/fmc_tariff_ledger
python -m pip install -r requirements.txt
python -m unittest -v test_crawler.py test_crawler_v2.py

# Inspect the full FMC directory inventory without crawling carrier sites.
python run.py enumerate --format csv > fmc_tariff_locations.csv

# Full crawl.
python run.py crawl \
  --out .fmc_tariff_ledger \
  --db ledger.sqlite \
  --workers 8 \
  --max-depth 3 \
  --max-pages-per-location 100

python run.py summary --db .fmc_tariff_ledger/ledger.sqlite
```

## Sharding

The directory is large enough that production runs should be sharded:

```bash
python run.py crawl --shard-count 12 --shard-index 0 --out output/shard-00
python run.py crawl --shard-count 12 --shard-index 1 --out output/shard-01
# ...
```

Assignment is deterministic from entity class + FMC organization number + tariff URL,
so shards are disjoint and stable.

Merge completed shard databases:

```bash
python run.py merge \
  --input-root ./downloaded-shards \
  --db merged/fmc_tariff_ledger.sqlite
```

When archiving merged output, preserve the content-addressed `blobs/` directories
alongside the merged database. The SQLite rows intentionally point to raw evidence
rather than embedding potentially large PDFs/pages in the database.

## Snapshot semantics

A snapshot is identified by tariff location + requested URL + SHA-256. Re-running
against a persistent data directory adds a new version only when bytes change; earlier
versions remain intact. Historical tariff PDFs/pages linked by the publisher/carrier
are captured during the same crawl.

“Every version” therefore means **every version discoverable from the FMC location,
its public history/index links, and implemented publisher adapters**. It does not
pretend that an unlinked or authentication-gated historical revision was collected.
Those gaps remain first-class unresolved records until an authorized source or
publisher-specific adapter supplies the bytes.

## Evidence rules

- Raw bytes are immutable and content-addressed.
- No normalized term exists without its source snapshot hash and evidence excerpt.
- Failed fetches/parses/resolution attempts are durable data.
- Generic publisher pages cannot create carrier-specific money/rule terms.
- Authentication is not bypassed.
- The crawler never treats a heuristic amount extraction as customer entitlement.
- Downstream money-bearing recovery defaults to $0 when agreement identity,
  precedence, effective date, or source authority remains unresolved.

## Manual GitHub workflow

`.github/workflows/fmc-tariff-ledger.yml` is intentionally `workflow_dispatch`
only. Running the exhaustive crawl can consume substantial network, compute, and
artifact storage, so it is never started automatically by a commit or schedule.
