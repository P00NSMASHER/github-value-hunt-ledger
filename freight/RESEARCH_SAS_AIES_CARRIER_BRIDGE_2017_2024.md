# RETALLY Research Lab 14 — Mission 25: Census 2017–2024 original-source revenue bridge

**October 12, 2026 · DRAFT / INTERNAL RESEARCH ONLY.** Stacked on the unmerged [Mission 24 PR #401](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/401). The original fourteen research laboratories and all eighteen unmet human customer-pilot evidence controls remain in force. No production release, outside outreach, scheduled task changes, customer data import or revenue/recovery market claims.

## Executive finding and intended use

The original Census sources now support one **source-versioned descriptive** eight-year employer-industry revenue chart for three overlapping 2017 NAICS trucking categories. Census expressly published its September 10, 2026 AIES historical series to maintain continuity with predecessor annual business surveys; that does not turn the prior estimates into independent fielded AIES samples.

Original Census methodology and release:
- https://www.census.gov/newsroom/press-releases/2026/aies-time-series-data.html — historical AIES release Sept. 10, 2026
- https://www.census.gov/data/developers/data-sets/aiestimeseries.html — Census AIES time series definition
- https://www.census.gov/data/tables/2022/econ/services/sas-naics.html — benchmarked SAS released Aug. 31, 2026
- https://www.census.gov/data/tables/2024/econ/aies/2024-aies-tables.html — original 2024 Census AIES basic figures

The bridge uses **2017–2021 revised SAS** as the annual published pre-AIES source, and **2022–2024 2024-AIES historical statistics** (linked through predecessor surveys). The overlapping **2022** SAS and AIES historical values must reconcile to SAS's nearest one-million-dollar reporting precision. An independently published 2024 AIES Basic file checks each final-year Census industry cell. This is a consistency/source integrity proof across publisher distributions — **not** three statistically independent business samples.

### Eight-year industry results

| NAICS 2017 | 2017 benchmarked SAS revenue | 2022 linked AIES historical revenue | 2024 AIES revenue | 2017–2024 nominal change |
| --- | ---: | ---: | ---: | ---: |
| 484 — all truck transportation | $290.532B | $423.270958B | $402.827246B | **+38.65%** |
| 484121 — long-distance general freight truckload | $112.441B | $172.717339B | $161.329027B | **+43.48%** |
| 484122 — long-distance general freight LTL | $46.192B | $65.688461B | $65.096292B | **+40.93%** |

For 2022 specifically, revised SAS (millions USD) and original AIES historical (millions USD) show published-unit residuals:
- NAICS 484: SAS 423,271; AIES 423,270.958; AIES minus SAS **−0.042 million**.
- NAICS 484121: SAS 172,717; AIES 172,717.339; AIES minus SAS **+0.339 million**.
- NAICS 484122: SAS 65,688; AIES 65,688.461; AIES minus SAS **+0.461 million**.

All three are within ±0.5 million and round exactly to published SAS values. The historical 2022 survey observation is **legacy-linked**, **not** an independently fielded AIES survey in reference year 2022. Published historical 2022 CV of zero must not be read as zero uncertainty.

The **2022–2023 long-distance LTL nominal industry revenue change is −1.58%**, and **2023–2024 +0.69%**. The 2017–2024 +40.93% is **descriptive nominal carrier-establishment revenue growth**, not inflation-adjusted real freight demand, customer-paid LTL invoices, rate errors, carrier rebates, demand for a recovery service, or monetizable opportunity.

### Parent-child overlap and historical vintage pitfalls

NAICS **484 includes both 484121 and 484122**, so adding the three rows double-counts child industries. The new engine rejects original but **older, pre-benchmark** 2022 SAS as a valid handoff; Mission 24 proved the old SAS revenue estimates were revised in 2018–2022. A 2022 handoff must therefore use the **August 2026-benchmarked** SAS vintage. Even consistent original data do not provide a statistical test of year-to-year change, buyer need or a freight-audit market size.

## Source proofs

Three U.S. Census Bureau original publisher archives are SHA-pinned and independently replayed by the mission's opt-in CI:

1. Revised 2022 SAS Table 2 (2017–2022), https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/Table2.xlsx . **128,635 bytes**, SHA-256 **cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac**. Table 2, 839 source rows, three NAICS × six years × two tax-status rows = **36** original source cell instances used.
2. 2024 AIES historical source (2022–2024), https://www2.census.gov/programs-surveys/aies/data/2024/API_Datasets/AIESTIMESERIES.zip . **771,290 bytes**, SHA-256 **1487da6e619f2e9701635a7f6ad2ab282302d75921e33797060866142c0d94a4**. Original 23,448 source rows; the strict national NAICS 484/484121/484122 × 2022–2024 selector checks **nine** unflagged revenue cells plus source CV.
3. Original Census 2024 AIES Basic source (2024), https://www2.census.gov/programs-surveys/aies/data/2024/AIES00BASIC.zip . **340,551 bytes**, SHA-256 **39c4235026672e7bffdbc36292ed976726df368f2ca435219aef1c84e8e4faa6**. Original 8,802 data rows; three unflagged national 2024 NAICS revenue cells.

Original-source totals: **48 selected original source cell instances** (36 SAS including both tax populations, nine historical AIES, three AIES Basic). The final stitched display contains **24 distinct NAICS-year values** (three industries × eight years), not 48 independent research samples. Government-hosted ZIP hashes represent observed technical reproducibility, not a government digital-signature audit.

## Files and test boundaries

- freight/research/SAS_AIES_CARRIER_BRIDGE_2017_2024_20261012.json: immutable source archive identity and exact industry/year values, official units, 2022 overlap and unsupported business claims.
- freight/research_sas_aies_bridge.py: source-controlled offline and explicit original-publisher replay modes. Reuses prior source verifiers so changed Census XLSX/ZIP contents, NAICS, tax status, units, false 2022 source handoffs, suppression flags, wrong 2024 basic numbers or signature claims **fail closed**. Reports a SHA-bound JSON and readable HTML including each year's source ID and asterisks identifying 2022 legacy linkage.
- freight/test_research_sas_aies_bridge.py: synthetic adversarial cases for obsolete series substitution, wrong year/source units, source tampering, added/removed industries, 2022 rounding mismatch, 2024 original AIES conflict, false paid invoices/recoverable TAM, network-only source blocking and malformed HTML/source names.
- Existing freight/lab_phase4_director.py and freight/lab_phase4_control_center.py: one additional research module/panel **within original Lab 14**, keeping the lab count at fourteen. Offline report visibly distinguishes earlier pinned public source observations from a fresh Census byte replay.
- .github/workflows/retally-sas-aies-bridge.yml: PR/manual-only offline tests, intact Lab 14 Control Center and isolated original-source verification; retains **only internal JSON/HTML reproducibility receipts** for 14 days, never private records or downloaded government archives. No cron.

Reproduce (Python 3.11+, repository root):

    PYTHONPATH=. python -m pytest -q freight/test_research_sas_aies_bridge.py
    PYTHONPATH=. python -m freight.research_sas_aies_bridge --offline --as-of-date 2026-10-12 --out /tmp/retally-m25-offline
    PYTHONPATH=. python -m freight.research_sas_aies_bridge --fetch-originals --as-of-date 2026-10-12 --out /tmp/retally-m25-originals
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m25-operator

**Strict source statuses:** VERIFIED only when all three original publisher archives and 48 source cells are independently reproduced in that same run; BLOCKED when publisher network is inaccessible and no new source receipt is credited; FAIL when available original bytes or source records disagree with earlier pinned observations. Passing offline tests never constitutes publisher verification.

**No real paid customer freight invoices, lawfully recoverable overcharges, paid carrier claim proofs, collections, external customers or market size are established. All 18 independent human/data-owner pilot requirements remain unmet. DO NOT MERGE, DEPLOY, CHANGE SCHEDULES, CONTACT BUYERS/CARRIERS, IMPORT PRIVATE DOCUMENTS OR ISSUE RECOVERY CLAIMS.**
