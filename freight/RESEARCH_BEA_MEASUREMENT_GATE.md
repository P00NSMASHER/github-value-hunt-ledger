# RETALLY Research Lab 14 — Mission 30: BEA gross output versus value-added compatibility

**October 12, 2026 · INTERNAL RESEARCH ONLY · Draft stacked on Mission 29 PR #415.** Do not merge, deploy, change scheduled tasks, contact customers/carriers, access private invoices or issue marketing/performance claims. Original 14 research laboratories and 18 unmet customer-pilot controls are preserved.

## Finding 1 — incompatible economic measures are not a validation test

Mission 29's all-trucking 2017–2024 Census employer revenue divided by an annual BLS producer-price-index ratio produced an **illustrative +1.18% price-adjusted revenue proxy**.

The U.S. Bureau of Economic Analysis distinguishes **real gross output** from **real GDP (value added)**. Gross output captures industry sales, receipts and other output measures. Value added is gross output **minus intermediate inputs**. A real-GDP-by-industry chain-type quantity index is therefore different from a chain-type real gross-output index.

Official BEA references, directly opened and inspected by the Mission 30 GitHub source-probe job:
- https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables
- https://www.bea.gov/data/industries/gross-output-by-industry
- https://www.bea.gov/itable/gdp-by-industry

BEA source-page SHA-256 fingerprints from the probe:
- Definitions HTML: 6c98d1a73d978babf37b8a42df39482e23fc566feed500e4ad0f45ec1769c4fd.
- Gross-output overview HTML: 6f8b892fe5a36d00cd1d22a86f3d76bc812fd2398e7c2d45f2bda274d790cc01.

Neither first-party methods page contains source-authenticated 2017–2024 national NAICS 484 **real gross-output quantity** observations. The BEA real gross-output source must remain **HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED**. We do not assert that an API-key-protected or unpublished series was obtained.

## Finding 2 — 2026 BEA publication revisions changed the sign of GDP value-added growth

FRED/ALFRED distribute BEA-origin real GDP by industry (value added), not real gross output:

| 2017–2024 national NAICS 484 measure | Value in 2017 | Value in 2024 | Change |
| --- | ---: | ---: | ---: |
| BEA real GDP value-added index, September 2025 vintage (2017 = 100) | 100.000 | 101.406 | **+1.41%** |
| BEA real GDP value-added index, September 2026 revised vintage (2017 = 100) | 100.000 | 97.585 | **−2.42%** |
| Illustrative 2017-level BLS/PPI-adjusted Census employer gross-revenue proxy (Mission 29) | — | — | **+1.18%** |

The 2026 value-added quantity index reflects chained 2017-dollar real GDP values of **177,967 million (2017)** and **173,669 million (2024)**. The 2024 real GDP quantity index was revised **−3.821 index points** between the two BEA publication vintages. This is a material source-vintage warning; the older +1.41% value must not be treated as the current BEA estimate.

Source references:
- https://fred.stlouisfed.org/data/USTRUCKTRANQGSP — 2025-vintage index observed on FRED web.
- https://fred.stlouisfed.org/data/USTRUCKTRANRGSP — 2026 BEA-origin chained-dollar value-added, observed in a public web result.
- https://alfred.stlouisfed.org/series?seid=USTRUCKTRANQGSP — revised September 30, 2026 quantity index.

**Source honesty:** FRED original HTML and CSV HTTP endpoints TIMED OUT from GitHub Actions. These are BEA-origin values *web-observed through secondary Federal Reserve distributors*, **not** direct original BEA source bytes authenticated in this CI. The original BEA definitions pages *were* fetched successfully from the BEA domain. Neither source group provides an independently verified real gross-output quantity index for truck transportation.

The 3.60 percentage-point difference between +1.18% illustrative price-adjusted gross-revenue growth and −2.42% real GDP value-added growth is **NOT a model-validation error, confidence interval or an independent gross-output observation**. Value added subtracts intermediate inputs; these measures do not have interchangeable denominators or growth dynamics.

## Implementation

- Source catalog: freight/research/BEA_TRUCKING_MEASURE_COMPATIBILITY_M30_20261012.json. Git-blob-pinned BEA methodology originals, secondary FRED observed GDP value-added vintages, source/CI reachability flags, a nullable real gross-output source, and prohibited commercial assertions.
- Source and compatibility gate: freight/research_bea_measurement_gate.py. Calculates value-added vintage revisions using Decimal, locks unsupported BEA-gross-output comparisons, and offers explicit read-only BEA official HTML method-page verification. Semantic page validation prevents a changed website from silently becoming a valid source; a network problem is BLOCKED; a page that is reachable but no longer supplies required measurement definitions is a FAIL. No original numerical BEA gross-output quantity series is invented.
- Adversarial tests: freight/test_research_bea_measurement_gate.py. Cover false gross-output/value-added equivalence, stale September 2025 vintage, 2017 baseline, wrong BEA source URL, forged original values, unsupported paid invoice/recovery claims, HTML escaping, network and content-drift conditions.
- Existing research Lab 14: retains all previous Census/BLS reports and original 14-lab count, adds a clear operator measurement-source decision panel, and preserves all 18 independent unmet genuine customer-data pilot signoffs.
- CI: .github/workflows/retally-bea-measurement-gate.yml. Unscheduled PR/manual-only offline research regression suite plus exact-domain official BEA definitions fetch, JSON/HTML evidence receipts, no client files or raw publisher data uploaded.

Run from repository root (Python 3.11+):

    PYTHONPATH=. python -m pytest -q freight/test_research_bea_measurement_gate.py
    PYTHONPATH=. python -m freight.research_bea_measurement_gate --offline --as-of-date 2026-10-12 --out /tmp/retally-m30-offline
    PYTHONPATH=. python -m freight.research_bea_measurement_gate --fetch-bea-definitions --as-of-date 2026-10-12 --out /tmp/retally-m30-primary
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m30-control

**All 18 independent real-customer pilot requirements remain unmet.** Public GDP, Census revenues and BLS producer price indexes do not prove specific freight bills, rate-contract errors, customer approvals, refunds or RETALLY addressable recovery market. No public revenue/market claim is authorized.
