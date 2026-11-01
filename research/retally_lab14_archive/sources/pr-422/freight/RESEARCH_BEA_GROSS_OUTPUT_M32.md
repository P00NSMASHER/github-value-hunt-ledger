# RETALLY Research Lab 14 — Mission 32: BEA Table 16 real gross output

**October 12, 2026. DRAFT / INTERNAL RESEARCH.** Stacked on Mission 31 PR #418. Do not merge, deploy, change schedules, import customer data, contact buyers/carriers or publish recovery claims. Preserve the original 14 labs and all 18 independent human pilot approval controls.

## Verified source discovery and scope

The official [BEA guide](https://www.bea.gov/resources/guide-interactive-gdp-industry-accounts-tables) identifies **GDPbyIndustry Table 16: Chain-Type Quantity Indexes for Gross Output by Industry**. The series missing from Mission 30's independent BEA-source analysis is annual national **NAICS 484, Truck transportation**, indexed to **2017 = 100**, coded **484-A**.

The data are available from [DBnomics](https://db.nomics.world/BEA/GDPbyIndustry-16/484-A), which **redistributes BEA data**. The September 30, 2026 BEA industry release was indexed by DBnomics on **October 1, 2026**. The direct DBnomics API address is:

https://api.db.nomics.world/v22/series/BEA/GDPbyIndustry-16/484-A?observations=1

The independent original-redistributor HTTP probe returned status 200, one correct BEA Table 16 annual industry-484 series, 29 historical years (1997–2025), and the required eight years 2017–2024. Original DBnomics JSON was 6,077 bytes, SHA-256 **291bc055352e57bcc79047e0a5208f54d19deb62a61fb652d5330753cb385d8a**.

**Provenance limitation:** A DBnomics source replay is NOT an authenticated original BEA numerical-file or BEA API replay. Original BEA access was previously denied because a BEA API UserID was inactive; no key was created and no official BEA 484 numerical file was downloaded here. The report carries an explicit original-publisher hold even after redistributor evidence succeeds.

## Annual real gross-output quantity observations

| Year | BEA Table 16 gross-output index for NAICS 484 |
| --- | ---: |
| 2017 | 100.000 |
| 2018 | 102.952 |
| 2019 | 102.398 |
| 2020 | 103.678 |
| 2021 | 109.538 |
| 2022 | 108.519 |
| 2023 | 107.307 |
| 2024 | **108.047** |

From 2017 to 2024, this **real gross-output quantity index rose 8.05%**.

## Three measures are conceptually distinct

| 2017–2024 national truck transportation (484) | Descriptive change | Source |
| --- | ---: | --- |
| BEA real gross output, GDPbyIndustry-16 | **+8.05%** | BEA-origin data through **DBnomics**, secondary HTTP verified |
| BLS official real sectoral output | **+4.02%** | Direct original BLS Industry Productivity API (Mission 31) |
| Census employer nominal revenue divided by BLS annual-average PPI | **+1.18%** | **Illustrative** price-adjusted calculation (Mission 29) |

BEA real gross output differs from GDP/value added because value added subtracts intermediate inputs. BLS sectoral output excludes certain intra-industry transactions, so it is not equivalent to BEA real gross output. Census employer revenue and BLS net-output price-index coverage may differ from BEA's gross-output population, composition and aggregation weights.

The BEA index is **4.03 percentage points higher than BLS sectoral output** and **6.87 percentage points higher than the price-adjusted revenue proxy**. Those differences are descriptive, NOT measured forecast errors, inferential confidence intervals, independently randomized samples, actual freight volume, carrier invoice billing errors, cash refunds, RETALLY total addressable recovery market or customer demand.

Parent NAICS **484 includes both long-distance truckload 484121 and LTL 484122**. The BEA index is for the parent trucking industry, not a direct recovered-billing market for either child category. Parent/child revenues and indexes cannot be treated as additive disjoint markets.

## Engineering and reproducibility

- Source registry: **freight/research/BEA_GROSS_OUTPUT_M32_20261012.json**. Git-blob-frozen BEA Table 16/484-A identity, eight original published values, DBnomics October 1 data vintage, original BEA direct-source hold and commercial-claim vetoes.
- Evidence engine: **freight/research_bea_gross_output_m32.py**. Bounded allowlisted DBnomics API read-only fetch, strict one-series/full-year/2017=100/NAICS 484/current vintage/value-quality checks, pinned original M29–M31 lineages and deterministic Decimal arithmetic. Distinct OFFLINE, SECONDARY VERIFIED, network BLOCKED and changed-source FAIL statuses. Generates internal JSON/HTML, never claims BEA-original verification.
- Tests: **freight/test_research_bea_gross_output_m32.py**. Adversarial year/dataset/metric/NAICS/vintage/duplicate/quality/claim/timeout cases with explicit original BEA source hold.
- Original Lab 14 director and Control Center: additional source-graded research panel, without changing the lab count or undoing earlier M30's historically valid no-direct-original-BEA status.
- **.github/workflows/retally-bea-gross-output-m32.yml** is PR/manual-only, with no scheduled tasks. Full previous regression and original 14-lab execution before separately replaying the redistributor's HTTPS source. It retains only internal JSON/HTML receipts for 14 days; no raw source files or customer data.

Reproduce from repository root with Python 3.11+:

    PYTHONPATH=. python -m pytest -q freight/test_research_bea_gross_output_m32.py
    PYTHONPATH=. python -m freight.research_bea_gross_output_m32 --offline --as-of-date 2026-10-12 --out /tmp/retally-m32-offline
    PYTHONPATH=. python -m freight.research_bea_gross_output_m32 --fetch-secondary --as-of-date 2026-10-12 --out /tmp/retally-m32-distributor
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m32-control

**No real paid customer invoices, governing LTL rate contracts, independently validated overcharges, actual cash refunds, interested buyers or recoverable-market amounts have been observed. All 18 real customer pilot approvals remain unmet. No merge/deployment, private customer imports, scheduled checks, outreach, money actions or public recovery statements.**
