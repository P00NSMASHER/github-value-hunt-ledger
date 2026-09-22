# TiC Payer MRF Ledger

Provenance-first ingestion for the CMS Transparency-in-Coverage machine-readable-file universe.

## Scope

This subsystem catalogs the payer MRF universe before attempting to materialize every negotiated price.

The first layer is:

    payer/source
      -> manifest/index snapshot + SHA-256
      -> plan identity
      -> in-network / allowed-amount file URL
      -> content metadata / history
      -> targeted provider + code extraction
      -> benchmark evidence

The current source registry combines:

- historical GitHub-hosted URL/size catalogs from DoltHub's TiC research;
- current UnitedHealthcare blob discovery;
- current Optum blob discovery;
- current Humana file listing;
- Aetna/CVS metadata endpoints across known brands;
- public Blue Cross NC index-link discovery;
- public Anthem/Elevance index-link discovery.

The source registry is intentionally extensible. Missing payers are an ingestion gap, not evidence that no data exists.

## Provenance model

Every fetched source catalog, API response, metadata response, or parsed index receives requested/final URL, observation timestamp, HTTP status, content type, byte count, SHA-256, ETag/Last-Modified when supplied, parser status, and an immutable content-addressed blob when within the configured snapshot size.

Large index files can be streamed and hashed without duplicating their bytes into the artifact. Their URL, hash, headers, byte count, parser status, plan mappings, and discovered child files remain in the ledger.

## Universe catalog

catalog.py builds sources, source_snapshots, mrf_files, plans, file_plan_links, and durable ingestion_errors.

Run:

    python -m pip install -r requirements.txt
    python catalog.py --out output --db tic_mrf.sqlite --parse-indexes --max-indexes 25

The summary reports unique file URLs, file types, payer/source coverage, known aggregate content length, unresolved paths, and failure classes.

## Targeted negotiated-rate extraction

Do not materialize every price just to answer a provider-specific recovery question.

extract_targeted.py downloads a selected in-network file once, SHA-256 hashes it, skips unrelated billing-code objects early, captures provider-group IDs referenced by requested codes, scans provider references, keeps only groups containing requested NPIs, and removes candidate rate rows for all other groups.

Example:

    python extract_targeted.py --db output/tic_mrf.sqlite \
      --url 'https://payer.example/rates.json.gz' \
      --billing-code 99214 --billing-code 27447 \
      --npi 1234567890 --output targeted.json

Normalized rows are exposed through payer_rate_benchmark_ledger.

## RecoveryWorks authority boundary

TiC negotiated rates are benchmark/context evidence by default.

The public MRF does not by itself prove that a specific provider claim is governed by that rate. The provider's actual agreement, amendment, plan/network applicability, modifier/POS rules, and service-date authority still need to be resolved.

export_benchmarks.py therefore emits Benchmark_Only=true and Verified_Controlling_Rate=false, and intentionally does not emit the controlling-rate CSV accepted by recoveryworks.branches.payer_csv.

This prevents public-price data from creating validated recovery dollars without contract authority.

## Historical coverage

The first ingestion uses public SQLite catalogs committed in dolthub/data-analysis for UnitedHealthcare, Aetna/CVS, Blue Cross NC, Empire BlueCross, Kaiser Permanente, and Optum. Those catalogs are preserved and hashed as historical discovery evidence. They are not assumed to represent current files.

## Current limitations

- Aetna metadata can expose file identity without a directly usable URL. Those rows are stored as mrf+unresolved://..., not guessed.
- JavaScript-heavy payer search pages may yield zero index links to a simple HTTP client. That is coverage debt, not absence of data.
- Targeted extraction expects current CMS-style inline provider_groups. Nonstandard remote provider-reference implementations are fail-closed.
- A public TiC rate is not automatically the client's governing contract.

## Tests

    python -m unittest discover -v -p 'test_*.py'
