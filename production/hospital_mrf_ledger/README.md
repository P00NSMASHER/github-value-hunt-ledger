# Hospital Price Transparency MRF Ledger

Provenance-first ingestion for the CMS Hospital Price Transparency machine-readable-file universe.

## Pinned authority

- CMS technical guide: `CMSgov/hospital-price-transparency`
- Pinned revision: `5333564a710f80d7740180b9ffab8dbdcba9b502`
- Current JSON schema: `documentation/JSON/schemas/V3.0.0_Hospital_price_transparency_schema.json`
- Schema blob SHA in the CMS repository: `11043f073ab24e638c91bde1b8bcf73e4733b296`
- Data dictionary: v3.0, effective 2026-01-01; CMS enforcement began 2026-04-01.

The ledger records the authority version used for each validation/extraction run. Older v2.x files may still exist on the public web; they are not silently interpreted as v3.0.

## Discovery model

CMS requires the selected public MRF host domain to expose `/cms-hpt.txt`.
The TXT file provides repeated records containing:

- `location-name`
- `source-page-url`
- `mrf-url`
- contact fields

This subsystem stores the location/source/MRF relationships but deliberately does **not** persist contact names or email addresses.

Input is a reviewed seed list of hospital/homepage or MRF-host domains. The crawler derives the root host, fetches `cms-hpt.txt`, snapshots and hashes it, and catalogs every direct MRF URL found.

A missing or inaccessible TXT file is coverage debt, not evidence that the hospital has no MRF.

## National discovery registries

The live crawler is supplemented by two pinned GitHub registries, kept as separate
evidence classes rather than silently promoted to first-party observations:

- **2026 current tracker** — `anthonyisnotadev/cms-hpt-tracker` pinned at
  `27c08db25896d765845f9ff6827da7f96ee66b04`. The importer uses the public
  compliance CSV plus CMS-roster-derived identity fields. It deliberately discards
  phone values and does not import pointer contact names/emails.
- **2022 historical registry** — `TPAFS/transparency-data` pinned at
  `8baae985b3d08380305c93091ad815e4cf57b83f`. Its hospital MRF URL catalog is
  preserved as historical discovery evidence with its original status/date fields.

Direct `cms-hpt.txt` snapshots remain the strongest discovery evidence in this
subsystem. Registry claims are useful for national coverage, gap-filling and
historical comparison, but do not overwrite a contradictory direct observation.

## Evidence layers

1. CMS schema authority receipt: exact CMS repo revision/path/blob SHA.
2. Hospital root TXT snapshot: requested/final URL, HTTP metadata, SHA-256, immutable small blob.
3. MRF observation: direct URL, byte hash, content type/format, CMS version, hospital identity and Type-2 NPI metadata.
4. Targeted charge extraction: requested billing codes and optional payer/plan filters only.
5. Benchmark export: public hospital rates remain context/benchmark evidence unless independent contract/claim authority proves applicability.

## Run

    python -m pip install -r requirements.txt
    python -m unittest discover -v -p 'test_*.py'

Catalog reviewed source domains:

    python catalog.py --sources sources.json --out output --db hospital_mrf.sqlite

Fetch and inspect discovered MRFs up to a bounded byte ceiling:

    python catalog.py --sources sources.json --out output --db hospital_mrf.sqlite \
      --fetch-mrfs --max-mrf-bytes 2147483648

Targeted extraction:

    python extract_targeted.py --db output/hospital_mrf.sqlite \
      --mrf-url 'https://hospital.example/file.json' \
      --billing-code 99214 --billing-code 27447 \
      --payer 'Example Payer' --output targeted.json

Quality summary:

    python quality.py --db output/hospital_mrf.sqlite --json

Benchmark export:

    python export_benchmarks.py --db output/hospital_mrf.sqlite --output hospital_benchmark.csv

## Parser scope

Implemented:

- JSON v3-style files: streaming targeted extraction using `ijson`.
- CSV tall: first-row general headers / second-row values / third-row charge headers.
- gzip-compressed JSON/CSV based on URL/content encoding.

Fail closed:

- CSV wide targeted extraction is catalogued but not interpreted by this subsystem.
- malformed/ambiguous TXT blocks do not create guessed MRF URLs.
- unsupported schema versions remain explicit.
- zero/missing values are not converted into prices.

## 2026 fields preserved

The normalized ledger includes, when present:

- hospital/location/address/license identity;
- Type-2 organizational NPI values;
- attestation confirmation;
- gross and discounted-cash prices;
- payer/plan;
- dollar / percentage / algorithm negotiated charge;
- methodology;
- de-identified minimum / maximum;
- allowed-amount median / 10th / 90th percentiles and count;
- setting, modifiers, billing/account code/type;
- source locator and exact MRF SHA-256.

## RecoveryWorks authority boundary

Hospital Price Transparency MRFs are **benchmark/context evidence by default**.

A public hospital MRF does not prove that a specific claim, provider, patient, plan, network, modifier, site of service, contract amendment or service date is governed by the disclosed amount.

Therefore benchmark exports set:

- `Benchmark_Only=true`
- `Verified_Controlling_Rate=false`
- `Verified_Claim_Applicability=false`

No public hospital MRF row is permitted to create asserted or realized recovery dollars without independent authority.
