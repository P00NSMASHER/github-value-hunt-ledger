# RETALLY Research Lab 14 — Mission 22: The 2022 LTL industry-revenue discrepancy

**October 11, 2026 · INTERNAL RESEARCH ONLY · Draft stacked on Mission 21 PR #396.** This is an analytical source-verification upgrade to the original research Lab 14, not a new laboratory, customer audit, financial filing, or production launch.

## Numerical discrepancy: reconciled to Census publication rounding

**The old $68.411 billion and newer $65.688 billion estimates belong to two different published vintages of the Census Bureau's 2022 Services Annual Survey (SAS) 2017-NAICS estimates for employer-firm revenues in `484122` (general-freight long-distance less-than-truckload trucking).** They are not two different sets of identified paid carrier invoices or two independent studies.

The Census Bureau's [August 31, 2026 benchmark release](https://www.census.gov/data/tables/2022/econ/services/sas-naics.html) supplies revised public source workbooks:

| Official 2022 SAS source, national all-employer-firms, 2017 NAICS 484122 | Revenue (millions nominal USD) | Published 2022 CV |
| --- | ---: | ---: |
| [Earlier 2022 SAS, 2017-NAICS original workbook](https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/sas-22.xlsx), Table 2, rows 50–51 | **68,411** | 1.6% |
| [Revised benchmark 2022 SAS, released Aug 31 2026](https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/Table2.xlsx), Table 2, rows 48–49 | **65,688** | 0 (published raw CV) |
| [Original 2024 AIES historical release](https://www2.census.gov/programs-surveys/aies/data/2024/API_Datasets/AIESTIMESERIES.zip), 2022 historical 484122 | **65,688.461** | 0 (historical-series raw CV) |

The *old minus new* difference is **$2,723 million**, or a **3.98% decrease** in revised published employer-industry revenue relative to the earlier version. The AIES-linked 2022 historical source is **$0.461 million higher than the revised SAS**; rounding $65,688.461 million to the **nearest million** reproduces the revised SAS's $65,688 million. These series therefore reconcile to the revised SAS table's published precision.

**This closes the numeric/edition discrepancy**. The [Census SAS 2022 benchmarking methodology](https://www.census.gov/programs-surveys/sas/technical-documentation/methodology/benchmarkprocess22.html) establishes that the 2022 SAS time series was benchmarked to the final **2022 Economic Census** on a 2017-NAICS basis, revising estimates from 2018 onward while minimizing trend distortions. The [AIES linking methodology](https://www2.census.gov/programs-surveys/aies/technical-documentation/methodology/2023-aies-methodology.pdf) explains the use of the benchmarked 2022 legacy survey estimates to link newer AIES samples.

**Not established:** an independently calculated NAICS 484122 unbenchmarked survey estimate, the industry's exact carry-forward/linking ratio, a decomposition of every statistical revision, an independent sampling-significance test, or customer-specific freight-bill overcharge prevalence. The revised 2022 Census CV shown as `0` does **not** certify zero uncertainty or zero invoice errors.

## Source provenance pinned in code

The first bounded read-only GitHub Actions inspection independently retrieved the exact Census-hosted XLSX bytes:

| Archive | Compressed publisher workbook bytes | SHA-256 | Source table |
| --- | ---: | --- | --- |
| Revised Table2.xlsx | 128,635 | `cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac` | Sheet1, 839 rows; NAICS 484122 rows 48,49 |
| Earlier sas-22.xlsx | 515,901 | `4aa1efe9533fb3b16f32806af4f0b1bd5c72e92f2db024e559f891e03f0bc33a` | Sheet2, 839 rows; NAICS 484122 rows 50,51 |

Both Table 2 datasets identify `2022 Estimate` in column **F** and 2022 published coefficient of variation in column **P**. Exactly **two** eligible NAICS 484122 revenue rows exist in each source. One is the entire employer population across tax status; the other is the taxpaying subgroup. The identical figures in the two rows are **not independent source replications or proof of two separate samples**.

The other revised [Table1.xlsx](https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/Table1.xlsx) does **not** contain a 484122 row; it is a different, broader survey reporting table. Source quality checks must not manufacture the missing category in Table 1.

## Implemented research code and tests

1. **Pinned source evidence:** `freight/research/SAS_BENCHMARK_2022_EVIDENCE_20261011.json`, documenting two official XLSX SHA-256s, source row coordinates, 2017 NAICS, population/units, release dates, the AIES historical original 2022 value, and explicit disallowed commercial assertions.
2. **Original workbook reader:** `freight/research_sas_xlsx_probe.py`, bounded ZIP/XML read-only discovery without executing spreadsheets, macros or storing raw Census workbooks. Reads only fixed allowlisted Census public URLs. All source labels/rows remain untrusted until independently authenticated against pinned ZIP hashes.
3. **Fail-closed evidence engine:** `freight/research_sas_benchmark.py`, tests frozen manifest Git-blob identity, two source vintage ZIP byte SHA-256s/sizes, exact Table 2 title/year field, two distinct tax-status population rows, 484122 industry classification, revenue and published CV units, published-rounding consistency and pre-existing Mission 21 receipt. Produces `sas_2022_reconciliation.json` and `sas_2022_reconciliation.html`.
4. **Adversarial tests:** `freight/test_research_sas_benchmark.py`, including counterfeit ZIP/digests, wrong revenue units or tax status, Census CV metadata tampering, missing/duplicated NAICS rows, forged real customer claims, false audit/recovery market, and blocked vs manipulated-source distinctions.
5. **Existing Lab 14 integration:** adds a separate **offline-labeled** historical benchmark reconciliation panel in the Control Center, preserves the original 14-laboratory census, original 18 unmet human pilot requirements and historical research findings. The prior M21 snapshot remains valid for the knowledge available *then*; the new evidence extends that result rather than falsifying old data.
6. **Dedicated read-only CI:** `.github/workflows/retally-sas-benchmark.yml`, only PR/manual dispatch (no schedule). Runs offline regression suite and the original 14-lab operator, then a separate explicit two-source Census XLSX download/validation job. Only bounded JSON/HTML evidence receipts are retained; no raw spreadsheets are uploaded or committed.

### Evidence status policy

- **VERIFIED:** both original Census workbooks fetched, bytes and SHA-256 match the prior government fingerprints, exact 2022 NAICS 484122 cells are read twice per vintage, both publication revenue values match, and the AIES historical value reconciles within the declared nearest-million rounding rule.
- **BLOCKED:** Census HTTPS server is inaccessible or times out; the report explicitly records no newly authenticated source archives. Existing observed metadata are not promoted.
- **FAIL:** source ZIP bytes or checksum, row count, wrong NAICS, tax status, units, year, missing CV, revised estimate or header differ. Any changed source must be human-reviewed as a revised publisher version, not silently swapped in.

Run from repo root with Python 3.11 or later:

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_sas_benchmark.py
PYTHONPATH=. python -m freight.research_sas_benchmark --offline --as-of-date 2026-10-11 --out /tmp/retally-sas-offline
PYTHONPATH=. python -m freight.research_sas_benchmark --fetch-publisher-workbooks --as-of-date 2026-10-11 --out /tmp/retally-sas-source
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control
```

**No actual customer-paid LTL invoices, governing rate contracts, overcharge error rates, claim eligibility, recovered refunds, sales demand, commissions, buyer leads or RETALLY recoverable market size have been established. All 18 customer-pilot gates remain unmet. DO NOT MERGE, DEPLOY, PUBLISH BUSINESS PERFORMANCE CLAIMS, CONTACT CARRIERS/CUSTOMERS, ACQUIRE PRIVATE DOCUMENTS, OR MODIFY SCHEDULED TASKS.**
