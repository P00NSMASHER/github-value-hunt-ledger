# RETALLY Research Lab 14 — Mission 14: Original Census Industry-Mode Source Integrity

**October 11, 2026. Internal research only.** Stacked on unmerged Mission 13. This does **not** create Lab 15, a product feature, an external data intake endpoint, a commercial market-size projection, or a release.

## Source inspection and provenance

The following original public U.S. Census Bureau Commodity Flow Survey 2022 ZIP archives were downloaded and inspected **in a read-only cloud browser**. No Census source ZIP was copied into this GitHub branch, and the GitHub CI workflow does **not** fetch government websites.

| Public table / original ZIP | ZIP bytes | Browser-observed SHA-256 | Original DAT records |
| --- | ---: | --- | ---: |
| [CF2200A18 — NAICS × mode × distance](https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A18.zip) | 93,390 | \`a18ce071599457572177dd56f8a6174594d1018da9b9024476c4e9832a357bf5\` | 7,312 |
| [CF2200A19 — NAICS × mode × shipment weight](https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A19.zip) | 107,682 | \`fe3085d23a3c76704a0d86d9213bb38d3d341b2c228990a5ebf40b6b3f1b661d\` | 6,782 |

Original public directories and method notes: [Census 2022 downloads](https://www2.census.gov/programs-surveys/cfs/data/2022/), [Census CFS 2022 published tables](https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html), [A18 interactive](https://data.census.gov/table/CFSAREA2022.CF2200A18), [A19 interactive](https://data.census.gov/table/CFSAREA2022.CF2200A19). Tables were released June 26, 2025; the data describe shipments from establishments in CFS's survey universe during **2022**. Source date, observation date, quality and definitional limitations must not be conflated with current market activity.

The actual members are pipe-delimited \`CF2200A18.dat\` and \`CF2200A19.dat\`, alongside each archive's \`_FIELDS.txt\` and \`_README.txt\`. Their header starts \`#GEOTYPE\`. A18 includes \`NAICS2017\`, \`DMODE\`, \`SHIPDIST\`, \`YEAR\`, \`VAL\`, \`TON\`, \`VAL_F\`, \`TON_F\`, \`VAL_S\`, \`TON_S\`. A19 replaces the distance axis with \`SHIPWT\` and has an additional \`AVGMILE\` field. \`VAL\` is the estimated **value of shipped goods in USD millions**; \`TON\` is estimated weight in **thousand tons**.

### Direct national source facts — not nested sums

The original source rows for \`GEOTYPE=01\`, \`GEO_ID=0100000US\`, \`YEAR=2022\`, \`DMODE=00\` (all modes) or \`111\` (for-hire truck) and **total** distance \`SHIPDIST=001\` (A18) versus **total** weight \`SHIPWT=01\` (A19) were directly compared in both archives:

| Source NAICS and mode | Goods value ($ million) | Weight (1,000 tons) |
| --- | ---: | ---: |
| All industries \`00\`, all modes \`00\` | 17,996,782 | 12,169,793 |
| All industries \`00\`, for-hire truck \`111\` | 8,062,541 | 3,909,476 |
| Manufacturing \`31-33\`, all modes \`00\` | 7,073,495 | 4,949,955 |
| Wholesale trade \`42\`, all modes \`00\` | 8,094,350 | 4,115,279 |
| Warehousing & storage \`4931\`, all modes \`00\` | 1,347,716 | 305,651 |

This is **not** an addition across industries. NAICS has parent and child categories (e.g. 31-33 and 311); modes have parent/child groups (e.g. truck 11 and for-hire 111); weight and distance are separate partitions with total rows. Summing these indiscriminately causes double counting. The two archives include the same **50 NAICS codes** and **21 mode codes**. A01 includes mode \`134\` (Multiple Waterways), absent from A18/A19; no claim that all mode-code catalogs are identical.

There is **no separate NAICS category called “distribution”** in these files; related coverage is under wholesale \`42\` (including \`423\`, \`424\`) and warehousing/storage \`4931\`. This does **not** establish who pays individual carrier bills, whether shipments are LTL, or whether RETALLY can serve them.

### Critical quality and suppression findings

| Table and metric | Unflagged | \`S\` | \`Z\` |
| --- | ---: | ---: | ---: |
| A18 goods value \`VAL_F\` | 5,430 | 1,839 | 43 |
| A18 shipment weight \`TON_F\` | 4,991 | 2,224 | 97 |
| A19 goods value \`VAL_F\` | 4,628 | 2,063 | 91 |
| A19 shipment weight \`TON_F\` | 4,474 | 1,956 | 352 |

The flags sum to each table's full row count independently. **\`S\`** means an estimate does not meet Census publication standards due to sampling variability, poor response quality or other issues. **\`Z\`** means the estimate rounds to zero, *not* a demonstrated exact physical zero. In the selected national for-hire cell for NAICS \`45431\`, \`TON=0\` appears with \`TON_F=S\` and must not count as measured zero tonnage. \`X\` and \`N\` were not observed in A18/A19 value/weight flags. Blank \`VAL_F\`/\`TON_F\` fields alone do not establish small uncertainty: coefficients of variation (\`VAL_S\`, \`TON_S\`) and their companion flags still require review.

This source-led numerical QA **does not establish** customer LTL invoice spend, recoverable overcharges, cash savings, buyer demand, subscription willingness, retention, fees or freight audit total addressable market.

## Implemented and safeguarded

- \`freight/research/CFS_A18_A19_INDUSTRY_RECEIPT_20261011.json\`: pinned public URL, version, exact ZIP hash/size, .dat header, row counts, dimension codes and quality-flag census, five directly observed totals, and three **unverified** buyer-segment research hypotheses.
- \`freight/research_cfs_industry_quality.py\`: read-only offline CFS archive inspector, using the existing Mission 13 hardened ZIP and pipe-DAT parsing logic rather than recreating it. The local original-file path must exactly match independently recorded Census ZIP hashes. Validates row/cross-tab uniqueness, source year, NAICS/mode/stratum IDs, value/ton flags, missing CVs, suppression and units. **\`S\` and \`Z\` never turn silently into measured zero.**
- \`freight/test_research_cfs_industry_quality.py\`: all source parsing CI tests use **synthetic mock DAT/ZIP bytes**; the full original archives are *not* replayed in routine CI.
- New JSON/HTML source-integrity report linked from the existing Lab 14 operator Control Center and included as a read-only GitHub Actions artifact.

### Local operator usage

With a separately and legally sourced local copy of an original public ZIP (do not commit the file):

\`\`\`bash
PYTHONPATH=. python -m freight.research_cfs_industry_quality \
  --table CF2200A18 --zip /path/to/CF2200A18.zip \
  --as-of-date 2026-10-11 --out /tmp/retally-a18

PYTHONPATH=. python -m freight.research_cfs_industry_quality \
  --table CF2200A19 --zip /path/to/CF2200A19.zip \
  --as-of-date 2026-10-11 --out /tmp/retally-a19

PYTHONPATH=. python -m pytest -q freight/test_research_cfs_industry_quality.py
\`\`\`

In default CI mode, the report truthfully says original bytes were **observed through the read-only browser but not replayed inside the CI worker**; publisher digital signature and customer invoice truth remain unknown. Source version/suppression/NAICS drift causes a hard failure in a purported verified local replay.

### Next specific evidence gap

Continue with independent NAICS-level **actual paid for-hire LTL invoice counts** obtained under the 18 still-unmet buyer pilot approvals. Official Census shipment value is not a substitute. All **14** original labs and prior **26** historical findings remain unchanged, unmerged review workflow preserved.

**DO NOT MERGE/DEPLOY, BUY DATA, CONTACT CARRIERS/BUYERS, INGEST PRIVATE CUSTOMER FILES, CHANGE SCHEDULED TASKS OR PUBLISH OVERCHARGE PERFORMANCE CLAIMS.**
