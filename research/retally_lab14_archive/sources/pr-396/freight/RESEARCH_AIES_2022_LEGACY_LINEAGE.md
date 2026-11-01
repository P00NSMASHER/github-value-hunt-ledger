# RETALLY Research Lab 14 — Mission 21: 2022 Census historical revenue source reconciliation

**DRAFT / INTERNAL RESEARCH · October 11, 2026.** Stacked on Mission 20 PR #393. No new lab, production merge, scheduled task, customer data, outreach, carrier filing, or marketing claim. The 18 real-customer pilot approvals remain unmet.

## Discovery: the actual 2024 AIES historical ZIP

The Census Bureau's 2024 archive directory lists **AIESTIMESERIES.zip**, published September 10, 2026. Mission 20's attempted `AIESBASICTIMESERIES.zip` location returned 404. A read-only GitHub Actions source inspection obtained the genuine, different publisher file:

- Government original: https://www2.census.gov/programs-surveys/aies/data/2024/API_Datasets/AIESTIMESERIES.zip
- Parent Census directory: https://www2.census.gov/programs-surveys/aies/data/2024/API_Datasets/
- Full original ZIP: **771,290 bytes**, SHA-256 **1487da6e619f2e9701635a7f6ad2ab282302d75921e33797060866142c0d94a4**
- Original DAT: `AIESTIMESERIES.dat`, **6,800,762 bytes**, SHA-256 **a8053af22913f1872a10a5d386a602d7a3bbecfdd4441727b8a70ecde4235648**
- Total published DATA records: **23,448**, **89 fields**. Separate original FIELDS and README documents included.

This original Census archive contains **nine eligible 2017 NAICS 484/484121/484122 × 2022/2023/2024 national employer-establishment revenue cells**. Values are in **thousands of nominal U.S. dollars**, not dollar-denominated freight invoices or paid overcharges.

| Reference year | NAICS 484 total trucking ($1,000) | NAICS 484121 long-distance TL ($1,000) | NAICS 484122 long-distance LTL ($1,000) | LTL source CV raw |
|---|---:|---:|---:|---|
| 2022 | 423,270,958 | 172,717,339 | **65,688,461** | `0` |
| 2023 | 406,651,010 | 163,025,116 | **64,651,167** | `.9` |
| 2024 | 402,827,246 | 161,329,027 | **65,096,292** | `.9` |

All nine match Mission 18's frozen Census/FRED historical observations. This authenticates the **published 2022 historical-series number as a Census source record**. It does **not** mean a standalone 2022 AIES field survey was collected.

## Why 2022 is not directly comparable to independent AIES fielding

The Census Bureau's [2023 AIES methodology](https://www2.census.gov/programs-surveys/aies/technical-documentation/methodology/2023-aies-methodology.pdf) describes **sample linking using carry-forward factors** derived from Census-adjusted 2022 legacy survey revenues and new AIES sample estimates. For most industries, the factor links the 2022/2023 new sample to the prior survey and benchmarks to the 2022 Economic Census. Later [AIES historical documentation](https://www.census.gov/data/developers/data-sets/aiestimeseries.html) confirms the time series incorporates legacy survey data. Therefore **2022 historical source VERIFIED** is different from **2022 direct independent AIES field survey VERIFIED**, which is **false**.

The Census historical 2022 cells have `RCPT_TOT_CV=0` (published raw value) and empty quality flags. We deliberately do **not** interpret that as zero sampling variability, perfect accuracy, zero carrier invoice errors, or any confidence interval. The original source does not provide sufficient variance and survey-linkage information for such conclusions.

### Legacy 2022 Services Annual Survey discrepancy

The older FRED-distributed Census SAS series [REVEF484122ALLEST](https://fred.stlouisfed.org/data/REVEF484122ALLEST) reported **$68,411 million** for reference year 2022. The newly original-Census-replayed AIES historical series reports **$65,688.461 million** for the same named NAICS category. The numeric difference is **$2,722.539 million**.

The Census [latest 2022 SAS benchmark page](https://www.census.gov/data/tables/2022/econ/services/sas-naics.html) shows an updated **August 31, 2026 2017-NAICS benchmark release** separate from older SAS tables, and the AIES methodology documents sample linkage. These facts make survey vintage/benchmarking a material *candidate explanation*, but this mission **does not authenticate the exact newer 2022 SAS table cell** or calculate an industry-specific carry-forward factor. Therefore the **exact cause of the $2.722539B gap remains unresolved** rather than asserting it is due to a specific adjustment.

Legacy SAS series and Census 2024 AIES historical series are two publisher vintages and cannot be treated as independent real invoice observations, averaged for a single market, or used to infer revenue lost to invoice billing errors.

## Engineering changes

- `freight/research/AIES_2022_LEGACY_LINEAGE_20261011.json`: fixed Census publisher ZIP+DAT checksums, 9 exact national/NAICS/source unit/CV records, 2022 survey vintage flags, unresolved SAS benchmark comparison and false commercial claims.
- `freight/research_aies_2022_lineage.py`: read-only offline mode or explicit original ZIP GET/local replay; reuses existing bounded ZIP parser, verifies original checksums, unique eligible cells, source quality/suppression flags, all original rows and field count. Emits `aies_2022_lineage.json` and `aies_2022_lineage.html`.
- `freight/test_research_aies_2022_lineage.py`: adversarial coverage for corrupted/hijacked ZIP, wrong years/NAICS/units, suppressed flags, fraudulent CV significance, mismatched estimates, fabricated 2022 AIES field survey or adjudicated SAS causal explanation, false invoices/recovery market and explicit unavailable-source status.
- Original **Lab 14 director/Control Center**: adds a separate offline historical publisher context report and negative probes. Prior Mission 20 continues to hold a **separately fielded 2022 AIES survey**, not the now-replayable Census-published legacy-linked historical statistic.
- `.github/workflows/retally-aies-2022-lineage.yml`: PR/manual-only tests and live direct Census publisher ZIP replay in separate jobs, preserving only attestation receipts, **not raw ZIP source files** or customer data. An HTTP outage produces **BLOCKED** with zero credited source rows; a changed ZIP value/hash is a **FAIL**.

## Reproducibility

From repository root (Python 3.11+):

    PYTHONPATH=. python -m pytest -q freight/test_research_aies_2022_lineage.py
    PYTHONPATH=. python -m freight.research_aies_2022_lineage --offline --as-of-date 2026-10-11 --out /tmp/retally-m21-offline
    PYTHONPATH=. python -m freight.research_aies_2022_lineage --fetch-original --as-of-date 2026-10-11 --out /tmp/retally-m21-primary
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m21-operator

**No customer-paid invoices, contract authority, error rates, refunds, collectible fees, buyers or recoverable market have been verified.** All 18 actual customer-pilot evidence controls remain unapproved. Do not merge, deploy, schedule, import customer records, contact anyone or publish financial/recovery claims.
