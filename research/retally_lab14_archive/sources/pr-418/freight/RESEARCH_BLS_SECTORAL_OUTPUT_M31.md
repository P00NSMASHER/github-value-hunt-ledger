# RETALLY Research Lab 14 — Mission 31: Original BLS Real Sectoral Output

**October 12, 2026 · DRAFT, INTERNAL RESEARCH ONLY · stacked on Mission 30 PR #417.** No merge, deployment, scheduled task changes, private customer data, outside contacts or commercial recovery claims. All 14 existing laboratories and 18 unmet real-customer pilot requirements remain.

## Result: Official BLS real sectoral output now source-verified; BEA gross output still unverified

Mission 30 established that BEA GDP by industry is **value added** (gross output minus intermediate inputs) and is not the same as the official **real gross-output quantity index**. An original BEA real gross-output time series for trucking NAICS 484 has **not been authenticated** in this project.

Mission 31 found a separate original government output index published by the **Bureau of Labor Statistics Industry Productivity** program. BLS real sectoral output is adjusted for changes in inventory and the removal of intra-industry shipments. It is **not BEA real gross output**, GDP/value added, shipment tonnage or customer freight invoices.

Original methodological references:
- https://www.bls.gov/opub/hom/opt/calculation.htm — definition and Törnqvist index construction for real sectoral output.
- https://www.bls.gov/k12/productivity-101/content/how-is-productivity-measured/output.htm — output, sales and intra-industry shipment exclusions.
- https://www.bls.gov/help/hlpforma.htm — BLS original industry-productivity series IDs pad abbreviated NAICS industries with underscores.
- https://www.bls.gov/productivity/tables/ — original BLS downloadable tables (current detailed industry XLSX returned HTTP 403 specifically to the GitHub runner).

### Direct original BLS API source discovery

A BLS v2 POST using the shorter **FRED-distributed aliases** returned HTTP 200 but reported "Series does not exist" for each requested series. This is a source identifier issue rather than a lack of published output data. The **native BLS industry productivity IDs include underscores** for shorter industry codes. Repeating a single original BLS API v2 POST, years 2017–2024, with the correct native IDs returned a successful original publisher response and all **24 annual source observations**:

| Industry | Native BLS IPU series ID | 2017 index | 2024 index | 2017–2024 output index change |
| --- | --- | ---: | ---: | ---: |
| Truck transportation, NAICS **484** | IPUIN484___T010000000 | 100.000 | **104.019** | **+4.02%** |
| General freight trucking, NAICS **4841** | IPUIN4841__T010000000 | 100.000 | **105.912** | **+5.91%** |
| General freight long-distance, NAICS **48412** | IPUIN48412_T010000000 | 100.000 | **102.984** | **+2.98%** |

Each of the three series contains **eight distinct annual A01 indices**, 2017 through 2024 inclusive. The initial correct-native-ID original BLS source response contained **2,340 bytes**, SHA-256 **3596212ab4c68346613a76bd62777550b83aac2f4251fea7371ba5e3077dfd6e**; see [Mission 31 original source investigation](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/38286326777). Subsequent runs check the original values semantically rather than insisting the API's JSON byte format never changes.

**Scope and double-counting:** NAICS 484 already contains 4841, and 4841 contains 48412. Long-distance combined general freight **48412** includes both truckload **484121** and less-than-truckload **484122**. It is NOT a direct six-digit LTL quantity index, nor a truckload quantity index, and these industry output series are NOT additive independent markets.

## Official BLS quantity index vs. Mission 29 illustrative proxy

| 2017–2024 parent NAICS 484 output-related measurement | Reported change | Provenance |
| --- | ---: | --- |
| **Official BLS real sectoral output** | **+4.02%** | Original BLS Industry Productivity API (NAICS 484) |
| Mission 29 **illustrative** Census-employer-revenue/BLS producer-price adjustment | **+1.18%** | Earlier original Census and BLS PPI publisher sources, with a simpler annual deflator |
| Descriptive difference | **2.84 percentage points** | **NOT** an authenticated forecast error, real gross-output difference, confidence interval or freight invoice billing-error rate |
| Direct original BEA real gross output, NAICS 484 | Unavailable | Original industry quantity series remains **NOT AUTHENTICATED** |

The original BLS real sectoral output is a different statistical measure: adjusted for intra-industry/intra-sector shipments, compiled using sales and price data, and may share some source inputs with both Census and BLS PPI. The 2.84-point gap documents a **measurement-method difference**, not an independent randomized-survey contradiction, failure of a formal model, or an error in real customer invoicing.

M29's six-digit TL/LTL adjusted revenue proxies remain separate, and cannot be validated by BLS's combined five-digit NAICS 48412 output index.

## Original BEA source-access limitation is unchanged

An unauthenticated BEA GDPbyIndustry API request, without an active user API key, returned **APIErrorCode 4: This UserId is not active. Please activate it and try again.** Mission 31 did not create an account, ask the user for credentials, or claim that a direct BEA gross-output quantity table was obtained. The optional BLS detailed-industry XLSX retrieval returned **HTTP 403** in the GitHub runner; this also does not establish that the data are unavailable, as the original BLS IPU v2 source succeeded independently.

## Engineering and validation

- Source catalog: freight/research/BLS_SECTORAL_OUTPUT_M31_20261012.json. Pinned Git blob of three BLS annual 2017–2024 index histories, official native IDs, BEA original-source holds, nested industry/NAICS distinctions and prohibited customer/recovery assertions.
- Engine: freight/research_bls_sectoral_output_m31.py. Exact original BLS v2 API POST for 3 native series and eight years, strict 24 annual A01 rows and no preliminary/suppressed flags, Decimal source comparison, explicit OFFLINE/ORIGINAL VERIFIED/NETWORK BLOCKED/CONTENT FAIL. Emits derived JSON and HTML only and preserves M29/M30 source governance.
- Tests: freight/test_research_bls_sectoral_output_m31.py. Adversarial identifier/alias checks, missing/duplicate years, wrong annual period, source drift, corrupt decimals and footnotes, false BEA output comparisons and customer-money claims.
- Lab integration: existing freight/lab_phase4_director.py and freight/lab_phase4_control_center.py contain a new independently labeled measurement-source report within the original 14 laboratories; 18 real-pilot evidence gates remain blocked.
- Workflow: .github/workflows/retally-bls-sectoral-output-m31.yml is pull-request/manual only. Offline original research regressions and a separate read-only first-party BLS v2 source replay produce short-retention internal JSON/HTML receipts. Raw BLS payloads, private records, keys and original spreadsheets are not uploaded.

Run from repository root, Python 3.11 or later:

    PYTHONPATH=. python -m pytest -q freight/test_research_bls_sectoral_output_m31.py
    PYTHONPATH=. python -m freight.research_bls_sectoral_output_m31 --offline --as-of-date 2026-10-12 --out /tmp/retally-m31-offline
    PYTHONPATH=. python -m freight.research_bls_sectoral_output_m31 --fetch-original --as-of-date 2026-10-12 --out /tmp/retally-m31-primary
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m31-control

**No actual paid customer freight invoices, governing rate contracts, independent billing errors, real cash refunds, buyer-demand proof or recoverable-market dollars have been established. All 18 independent human/data-owner pilot conditions remain unmet. NO MERGE, DEPLOY, SCHEDULE CHANGE, PUBLIC RECOVERY CLAIM, CUSTOMER PRIVATE DATA ACCESS OR CARRIER/BUYER OUTREACH.**
