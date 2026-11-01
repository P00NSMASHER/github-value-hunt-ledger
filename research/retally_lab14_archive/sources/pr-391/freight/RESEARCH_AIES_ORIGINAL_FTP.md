# RETALLY Research Lab 14 — Mission 19: Original Census AIES Revenue Attestation

**October 11, 2026 · Internal research only · Draft stacked on Mission 18 PR #390.** Upgrades the existing fourteen laboratories, not a new laboratory, real customer study, source endorsement or authority to publish commercial claims.

## Why verify the original publisher archive?

Mission 18 captured 2024 AIES long-distance LTL employer-industry revenue from Census-origin FRED series. The independent live FRED CSV check timed out and was correctly marked source unavailable.

The Census Bureau makes its own complete 2024 AIES00BASIC summary table available as a public HTTPS ZIP, without needing an API key.

Original source: https://www2.census.gov/programs-surveys/aies/data/2024/AIES00BASIC.zip
Publisher directory: https://www2.census.gov/programs-surveys/aies/data/2024/
Publication overview: https://www.census.gov/data/tables/2024/econ/aies/2024-aies-tables.html

In the first read-only GitHub Actions inspection of the original publisher archive, the file had **340,551 ZIP bytes** and SHA-256 **39c4235026672e7bffdbc36292ed976726df368f2ca435219aef1c84e8e4faa6**.

Archive members: AIES00BASIC.dat (1,859,064 bytes uncompressed, 8,802 source data rows, 35 source fields), AIES00BASIC_FIELDS.txt and AIES00BASIC_README.txt. Original ZIP hashes are reproducibility proofs of the observed publisher download, **not** government digital signatures or certifications of all Census publications.

## Exact 2024 revenue cells

Selection requires 2024, Census 2017 NAICS, U.S. national geography, type of operation and tax status both All establishments, original unsuppressed published value and CV cells.

| 2017 NAICS | Census employer-industry | 2024 revenue ($1,000 nominal USD) |
| --- | --- | ---: |
| 484 | All truck transportation | 402,827,246 |
| 484121 | Long-distance general-freight truckload | 161,329,027 |
| 484122 | Long-distance general-freight less-than-truckload | **65,096,292** |

The original Census 484122 data row includes published revenue coefficient of variation of **0.9%**. This is a measure of sampling variability, **not** an invoice error rate. NAICS 484122 is a specific subset of long-distance general-freight LTL, not all LTL freight spending, not real customer-paid invoices, and not a RETALLY recovery market. Survey estimates can contain sampling and nonsampling error.

## Implementation

The new freight/research_aies_original_ftp.py validates a fixed Census government ZIP from explicit HTTPS retrieval or an approved local copy. It uses the existing bounded ZIP archive reader, strictly authenticates observed original ZIP size/SHA, exact member names, original DAT row/header census, three national industry grain keys, all value and coefficient-of-variation quality flags, and the frozen Mission 18 expected annual totals. It never silently replaces an old revenue estimate with a new or incompatible Census measurement.

The new freight/test_research_aies_original_ftp.py covers synthetic original-file tampering, forged and rehashed test ZIPs, missing/duplicate records, false year/geography/NAICS classification, value discrepancies, suppressed quality, unexpected income or customer data, source URLs, and HTML injection. Source HTTP timeouts record a definitive BLOCKED status; a successfully retrieved but altered ZIP raises FAIL.

The existing Lab 14 continues to run with fourteen modules and eighteen outstanding genuine customer pilot controls. A new pull-request-only workflow executes adversarial tests, repeats the original publisher ZIP verification in an isolated CI job and saves only read-only JSON/HTML evidence receipts for 14 days—**not** raw Census ZIPs or customer records.

## Source-state policy

**VERIFIED:** The previous original archive SHA and size match, exact original data member matches, 8,802 original records parse, and three specified Census industry rows are source-checked including flags and CVs. Only reference year 2024 can be upgraded to primary original-source replay.

**BLOCKED:** FTP network is unreachable; no source hash or original-source result is credited, even when offline unit tests pass.

**FAIL:** ZIP size/hash changed, member or field schema differs, population changes, data value differs from observed M18 baseline, flags are altered, ZIP path traversal is present or any source data quality rule fails.

2022 and 2023 historical FRED observations are not independently authenticated just because the 2024 FTP archive matches. Legacy 2022 Services Annual Survey remains a separate and incompatible series. The 2022 Commodity Flow Survey goods-value population is also different from AIES carrier-establishment revenue.

## Reproduction

Run from repository root using Python 3.11 or newer:

    PYTHONPATH=. python -m pytest -q freight/test_research_aies_original_ftp.py
    PYTHONPATH=. python -m freight.research_aies_original_ftp --fetch-official --as-of-date 2026-10-11 --out /tmp/retally-m19

Or supply an original local Census archive explicitly:

    PYTHONPATH=. python -m freight.research_aies_original_ftp --from-local /path/to/AIES00BASIC.zip --as-of-date 2026-10-11 --out /tmp/retally-m19-local

Both forms produce aies_primary_source.json and aies_primary_source.html, including the source-state, source ZIP/DAT SHA-256, and a bounded link to Mission 18's independent research receipt.

**NO merge, deployment, customer data ingestion, real paid invoice assessment, carrier filing, market recovery claim, sales contact, financial action or scheduled-task changes are authorized.** All eighteen independent customer pilot requirements remain unmet.
