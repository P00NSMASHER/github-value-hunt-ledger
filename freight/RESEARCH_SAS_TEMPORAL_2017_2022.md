# RETALLY Lab 14 Mission 24 — 2017–2022 trucking Census revenue revisions

INTERNAL RESEARCH / DRAFT. October 11, 2026. Stacked on Mission 23 draft PR #398. Does not deploy, merge, publish financial performance claims, contact buyers or carriers, read customer files, or change any schedules.

## Source-backed research finding

Census revised its 2022 Services Annual Survey (SAS) time-series estimates using 2022 Economic Census benchmarks. The two official Census original and revised Table 2 workbooks report the same 2017 national employer-revenue baseline for all three trucking categories, then lower estimates in every year 2018–2022. All amounts here are **millions of nominal U.S. dollars**, not paid freight invoices.

| NAICS | Year | Older SAS | Aug 2026 SAS | Revised minus old | Percent revision |
| --- | ---: | ---: | ---: | ---: | ---: |
| 484 all truck transportation | 2017 | 290,532 | 290,532 | 0 | 0.00% |
| 484 | 2018 | 313,809 | 310,688 | −3,121 | −0.99% |
| 484 | 2019 | 320,817 | 314,044 | −6,773 | −2.11% |
| 484 | 2020 | 318,602 | 308,131 | −10,471 | −3.29% |
| 484 | 2021 | 376,903 | 361,243 | −15,660 | −4.15% |
| 484 | 2022 | 445,509 | 423,271 | −22,238 | −4.99% |
| 484121 long-distance truckload | 2017 | 112,441 | 112,441 | 0 | 0.00% |
| 484121 | 2018 | 124,337 | 122,875 | −1,462 | −1.18% |
| 484121 | 2019 | 124,566 | 121,331 | −3,235 | −2.60% |
| 484121 | 2020 | 126,768 | 121,752 | −5,016 | −3.96% |
| 484121 | 2021 | 152,753 | 145,249 | −7,504 | −4.91% |
| 484121 | 2022 | 183,482 | 172,717 | −10,765 | −5.87% |
| 484122 long-distance LTL | 2017 | 46,192 | 46,192 | 0 | 0.00% |
| 484122 | 2018 | 49,982 | 49,584 | −398 | −0.80% |
| 484122 | 2019 | 51,897 | 51,037 | −860 | −1.66% |
| 484122 | 2020 | 50,515 | 49,186 | −1,329 | −2.63% |
| 484122 | 2021 | 60,003 | 58,035 | −1,968 | −3.28% |
| 484122 | 2022 | 68,411 | 65,688 | −2,723 | −3.98% |

### Effect on historical growth claims

2017–2022 cumulative nominal industry revenue changes depend on the **publication vintage**: all trucking +53.34% old vs +45.69% revised; truckload +63.18% vs +53.61%; LTL +48.10% vs +42.21%. The 2017 anchor was unchanged in all three industries; all 15 peer-year estimates after 2017 were reduced. The absolute difference between old and revised revenue increased each year for all three industry series.

These are **publication revisions**, not experimental treatment effects or observations of inflation-adjusted real activity. Claims about LTL cost savings, billing errors, recoverable overpayments or actual carrier freight invoices are not supported.

## Primary source files

The publisher URLs below were retrieved directly from the official U.S. Census Bureau host. Source checks require complete byte sizes and SHA-256 fingerprints, not just matching cells.

- Old Census SAS 2022 workbook, 2017 NAICS Table 2 worksheet 2, https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/sas-22.xlsx . Size 515,901 bytes, SHA-256 4aa1efe9533fb3b16f32806af4f0b1bd5c72e92f2db024e559f891e03f0bc33a.
- Revised August 2026 SAS 2022 workbook, 2017 NAICS Table 2 worksheet 1, https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/Table2.xlsx . Size 128,635 bytes, SHA-256 cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac.
- Publisher release: https://www.census.gov/data/tables/2022/econ/services/sas-naics.html
- Census benchmarking methodology: https://www.census.gov/programs-surveys/sas/technical-documentation/methodology/benchmarkprocess22.html

The original Table 2 shows 2017 in column K, 2018 in J, 2019 in I, 2020 in H, 2021 in G, 2022 in F. Only national employer-firm, all-establishments, 2017 NAICS revenue observations are compared. The federal-income-tax subset provides a separate source quality check of the same publication cells; the two tax statuses are **not two independent samples**. The NAICS 484 industry is the parent of 484121 and 484122, so those values cannot be added as separate market categories.

For three categories across six years and two publication vintages, there are **36 distinct industry-year-vintage revenue amounts**. Counting both separate tax-status source rows yields **72 original source cell instances** to validate, not 72 independent surveys.

## Implementation and control boundaries

- freight/research/SAS_TEMPORAL_2017_2022_20261011.json: pinned source registry, exact observed 36 revenue figures, source row addresses, units, original file hashes and explicit prohibited commercial inferences.
- freight/research_sas_temporal.py: Decimal comparison engine, original Census ZIP/XML source reader reusing the prior safety path, 72 source-cell validation, original SHA/source row controls and deterministic read-only JSON/HTML reports.
- freight/test_research_sas_temporal.py: adversarial tests against swapped years, wrong NAICS, tampered files, missing years or tax rows, false inflation correction, market-size claims, customer/pilot promotions, HTML injection and blocked-versus-failed source states.
- freight/lab_phase4_director.py and freight/lab_phase4_control_center.py: add an offline-labeled research panel and preserve existing Lab 14 negative probes. The lab count remains fourteen.
- .github/workflows/retally-sas-temporal.yml: PR/manual-only source verification; separate offline and original government-file replay jobs, with short-retention JSON+HTML evidence artifacts only. No downloaded government XLSX stored in repository or CI artifacts, no scheduled tasks.

Verification states: VERIFIED only if both original publisher ZIP byte fingerprints match and 72 original source cells pass; BLOCKED if the publisher is inaccessible and no new authenticity is claimed; FAIL when available source bytes or cells contradict pinned observations.

Run under Python 3.11+ from repository root:

    PYTHONPATH=. python -m pytest -q freight/test_research_sas_temporal.py
    PYTHONPATH=. python -m freight.research_sas_temporal --offline --as-of-date 2026-10-11 --out /tmp/retally-sas-historical
    PYTHONPATH=. python -m freight.research_sas_temporal --fetch-originals --as-of-date 2026-10-11 --out /tmp/retally-sas-primary
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control-center

All 18 external human/real-data pilot requirements remain unmet. No verified client invoices, independently adjudicated carrier billing errors, real cash refunds, buyer-demand study, or RETALLY recovery market estimate are supplied by Census industry statistics.

DO NOT MERGE OR DEPLOY, TOUCH SCHEDULED TASKS, CONTACT BUYERS/CARRIERS, IMPORT CUSTOMER FILES, MAKE PAYMENTS, OR PUBLISH PERFORMANCE CLAIMS.
