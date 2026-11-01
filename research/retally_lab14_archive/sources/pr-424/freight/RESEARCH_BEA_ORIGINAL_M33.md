# RETALLY Research Lab 14 — Mission 33: Original BEA gross-output workbook authenticated

**October 12, 2026 · DRAFT, INTERNAL RESEARCH ONLY · stacked on Mission 32 PR #422.** Do not merge, deploy, create or edit scheduled tasks, import private customer files, contact customers/carriers, pay for data, collect money or make external recovery claims. All original 14 labs and 18 independent unmet real-customer pilot controls remain intact.

## Answer: The original BEA source is publicly downloadable without API registration

The previous M32 BEA Table 16, NAICS 484 annual real gross-output quantity index was verified from **DBnomics**, a redistribution of BEA's statistical output. The missing evidence was independent original BEA first-party numeric data, rather than another redistributor.

The **U.S. Bureau of Economic Analysis original publisher** directly serves the GDP-by-industry gross-output workbook here:

**https://apps.bea.gov/industry/Release/XLS/GDPxInd/GrossOutput.xlsx**

A first-party original-source GitHub Actions GET retrieved this workbook with:
- HTTP **200**, URL remaining the official apps.bea.gov host; proper XLSX content type.
- **506,819 bytes**, SHA-256 **a5a88e808bd88c5b48d7c1f572acb4d9b113d0d753828ed8b45d8800c1eb1f46**.
- An XLSX ZIP archive with **13 official worksheets**, including Contents and annual/quarterly original tables TGO101, TGO103, TGO104, TGO105, TGO106 and TGO107.
- Publisher heading **Bureau of Economic Analysis** and **Data published September 30, 2026**.
- **TGO103-A**, publisher heading **Chain-Type Quantity Indexes for Gross Output by Industry**, units **[2017=100]**, annual 1997–2025.
- **Publisher industry line 44, actual worksheet row 52, Truck transportation**, broadly equivalent to Table 16 NAICS 484.

This source provides the exact primary BEA real gross-output annual measures M32 could only authenticate as redistributor-held. Official interactive table access remains https://apps.bea.gov/iTable/?reqid=1603&step=2&Categories=GDPxInd&isURI=1 , while BEA’s open-data catalog provides the interactive entry and a separately registered API.

The **BEA API request with an inactive UserID still returned HTTP 200 with APIErrorCode 1, Invalid API UserId** in an earlier job. This remains historically true. But **API registration is not needed to download the public original XLSX**. No BEA API key, terms-submission form, subscription, credential or private dataset access was created.

### Original publisher Table 16 / TGO103-A source values, NAICS 484

| Year | Real gross-output quantity index (2017=100) |
| ---: | ---: |
| 2017 | **100.000** |
| 2018 | 102.952 |
| 2019 | 102.398 |
| 2020 | 103.678 |
| 2021 | 109.538 |
| 2022 | 108.519 |
| 2023 | 107.307 |
| 2024 | **108.047** |

**2017–2024 real gross output rose 8.05%.** Every original BEA index exactly matches the previously redistributor-verified DBnomics 484-A source. This is first-party-vs-redistributor **value reconciliation**, not two independent economic surveys.

### Source-internal sanity check: quantity × price = nominal

The same original BEA workbook has three additional official annual, same-population original sheets:
- **TGO104-A** — Chain-Type Price Indexes for Gross Output by Industry (2017=100).
- **TGO105-A** — Gross Output by Industry (millions of current dollars).
- **TGO106-A** — Real Gross Output by Industry (millions of chained 2017 dollars).

The key 2017/2024 values for trucking industry NAICS 484 are:

| BEA official table | 2017 | 2024 | 2017–2024 change |
| --- | ---: | ---: | ---: |
| TGO103-A gross output real quantity index | 100.000 | 108.047 | **+8.05%** |
| TGO104-A gross output price index | 100.000 | 137.494 | **+37.49%** |
| TGO105-A nominal gross output, $million | 367,154 | 545,435 | **+48.56%** |
| TGO106-A real gross output, chained 2017 $million | 367,154 | 396,699 | **+8.05%** |

Over all eight annual observations, the reconstructed nominal gross output from 2017 nominal dollars times 2017-referenced source price and quantity indices agrees with BEA's reported current-dollar gross output **within the tolerance required for the source's three-decimal published index rounding**. The chained-dollar values likewise reconcile with the indexed quantities, allowing for separately rounded BEA output-dollar figures.

These are **source-internal consistency checks**, not a second independent survey and not actual customer-paid freight invoices.

## Comparison with other economic statistics — still distinct quantities

| 2017–2024 NAICS 484 industry measure | Reported descriptive change | Evidence grade |
| --- | ---: | --- |
| **BEA real gross output** | **+8.05%** | **Original BEA numeric XLSX publisher download directly verified** |
| **BLS real sectoral output** | **+4.02%** | Original BLS API verified in M31; excludes certain intra-industry shipments |
| **Illustrative Census nominal industry revenue / BLS PPI** | **+1.18%** | Source-verified Census/BLS inputs but unofficial annual price adjustment |

The BEA original source resolves **provenance**, not **methodological incompatibility**: gross output includes intermediate sales; BLS sectoral output is constructed with selected within-sector shipment exclusions; simple Census employer revenue divided by a BLS net-output industry price index may cover different services and establishments. Their differences do **not** constitute statistical model errors, causal findings, confidence intervals, shipment tonnage, freight invoices, carrier errors, recoverable cash or RETALLY's serviceable audit market.

NAICS 484 includes both long-distance TL 484121 and LTL 484122. The parent series is not a separate additive source of recoverable invoices.

## Implementation and verification policy

- Original primary source registry: **freight/research/BEA_ORIGINAL_ACCESS_M33_20261012.json**, Git-blob-pinned with direct official XLSX SHA, bytes, official source sheet/row/industry/units/vintage, **32 original source cells** from four official tables (four sheets × eight years), earlier API UserID failure as historical metadata, DBnomics matching numbers and 18 unmet customer-pilot holds.
- Source verifier: **freight/research_bea_original_m33.py**, read-only fixed allowlisted BEA HTTPS URL, full original XLSX byte count/SHA, exactly 13 expected worksheets, exact official annual headings, publisher/industry/date metadata, eight contiguous year header columns, industry row 52/line 44, unique source industry row, four 2017–2024 table values, price×quantity-to-nominal and chained-dollar checks using Decimal. If original bytes or values change, source validation **FAILS closed** for human vintage review; a network outage returns **BLOCKED** and zero new source years. Offline reports never pretend a fresh publisher download.
- Adversarial tests: **freight/test_research_bea_original_m33.py** use generated synthetic XLSX fixtures solely to verify the parser. They reject false BEA publisher document identities, stale date, wrong NAICS/industry, shifted year columns, altered prices/quantities, bad annual values/units, forged digest and invoice/refund/TAM promotions. **Synthetic workbooks are not counted as authentic first-party source replays.**
- Original Lab 14 director and read-only Control Center now show the **new primary BEA source grade**, the nominal/price/quantity original accounting reconciliation and an explicitly historical M32 DBnomics-source card. All earlier source receipts remain intact; original 14-lab count and 18 independent real customer pilot approvals are unchanged.
- **.github/workflows/retally-bea-original-m33.yml**: PR/manual-only original source SHA/32-cell replay in a dedicated job, and separate M18–32 regressions plus original fourteen-lab run. Only derived JSON/HTML source receipts are retained for 14 days; no original XLSX or private customer invoices are committed or uploaded. No cron, deployment or payment action.

### Reproduce from repository root (Python 3.11+, openpyxl 3.1.5)

    PYTHONPATH=. python -m pytest -q freight/test_research_bea_original_m33.py
    PYTHONPATH=. python -m freight.research_bea_original_m33 --offline --as-of-date 2026-10-12 --out /tmp/retally-m33-offline
    PYTHONPATH=. python -m freight.research_bea_original_m33 --fetch-original --as-of-date 2026-10-12 --out /tmp/retally-m33-first-party
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m33-control

**No actual paid customer invoices, governing freight contract rates, independently adjudicated overcharges, real cash refunds, buyer demand, or addressable freight-audit market size are demonstrated by these public government statistics. All eighteen real-customer pilot approvals remain unmet. NO MERGE, DEPLOY, SCHEDULE CHANGES, CUSTOMER/CARRIER OUTREACH, PRIVATE RECORD IMPORT OR UNVERIFIED COMMERCIAL RECOVERY CLAIMS.**
