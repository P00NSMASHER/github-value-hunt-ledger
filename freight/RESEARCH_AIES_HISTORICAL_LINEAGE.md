# RETALLY Research Lab 14 — Mission 20: Historical AIES source lineage

**October 11, 2026 · DRAFT / INTERNAL RESEARCH ONLY.** This extends the existing Lab 14, stacked on Mission 19 [PR #391](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/391); it does not add a laboratory, merge/deploy changes, contact prospects/carriers, ingest customer documents, authorize recoveries, create scheduled tasks, or close the 18 outstanding pilot approvals.

## Question and evidence distinction

Mission 19 authenticated the Census Bureau's original **2024 AIES00BASIC.zip** archive and its national 2024 NAICS trucking revenue values. Mission 18's earlier FRED/Census-origin series also showed 2022 and 2023 observations. **The older observations have unequal provenance**. The Census states that the AIES historical series carries forward information from **legacy surveys** and the first annual AIES collected the 2023 reference period. Therefore an older FRED historical value must not be labeled an independent original 2022 AIES survey observation or stitched into a statistically verified 2022–2024 growth forecast.

Primary Census [AIES historical series methodology](https://www.census.gov/data/developers/data-sets/aiestimeseries.html), [2023 AIES API overview](https://www.census.gov/data/developers/data-sets/aies.2023.html), and [2024 AIES publication](https://www.census.gov/data/tables/2024/econ/aies/2024-aies-tables.html).

## Actual official publisher archive reconnaissance

The initial read-only, publisher-hosted GitHub Actions retrieval observed the following distinct **2023 Census** archive distributions. Both source references resolve under the original Census HTTPS host:

| Census original archive | ZIP bytes | Original ZIP SHA-256 | Original DAT bytes | DATA rows | NAICS field |
|---|---:|---|---:|---:|---|
| [AIESBASIC2023.zip](https://www2.census.gov/programs-surveys/aies/data/2023/API_Datasets/AIESBASIC2023.zip) | 819,756 | `7da68855e995342d9039c3c2f146eee72f079eabcd9a9620e34c3596d2e4ce9e` | 5,987,194 | 13,512 | NAICS2017 |
| [AIESBASICTIMESERIES.zip](https://www2.census.gov/programs-surveys/aies/data/2023/API_Datasets/AIESBASICTIMESERIES.zip) | 846,487 | `5e69e6a025ec25398321242b170c384b57e45bce522cdadd843ec39e13dffb69` | 6,936,210 | 13,512 | NAICS |

The publicly indexed **2024/API_Datasets/AIESBASICTIMESERIES.zip** candidate returned HTTP **404** in the initial bounded CI inspection; no 2024 historical archive was manufactured from that broken path. Instead, the verified 2024 **AIES00BASIC.zip** from Mission 19 is independently re-read in the *new* original-source mission.

The 2023 published and historical files are **two dissemination forms of a single Census population, not independent economic surveys**.

### Exact 2023 original source observations

The national, all-employer-establishments source rows (NAICS, TYPOP=00, TAXSTAT=00, 2023) agree between both original 2023 releases, with blank original Census suppression/quality flags.

| NAICS | National employer establishment industry | Revenue ($1,000 nominal USD) | Census revenue CV |
|---|---|---:|---:|
| 484 | Truck transportation | 406,651,010 | 0.6% |
| 484121 | General freight trucking, long-distance, truckload | 163,025,116 | 1.1% |
| 484122 | General freight trucking, long-distance, **less than truckload** | **64,651,167** | **0.9%** |

These numbers exactly match the corresponding **2023 FRED/Census-origin estimates** pinned in Mission 18. Census revenue coefficient of variation is an uncertainty measure about the industry's survey estimate, not an invoice error rate. No independent statistical significance or covariance adjustment is inferred from 2023 and 2024 CV values.

## Year-by-year provenance rules

| Year | LTL NAICS 484122 ($1,000) | Primary-source status in Mission 20 |
|---|---:|---|
| 2022 | 65,688,461 | **HOLD:** Mission 18 FRED historical/legacy-built series; no directly comparable 2022 original AIES reference-year archive replay |
| 2023 | **64,651,167** | Original publisher AIESBASIC2023 + AIESBASICTIMESERIES 2023 records subject to exact ZIP integrity checks |
| 2024 | **65,096,292** | Mission 19 original 2024 AIES00BASIC archive; replayed again with Mission 20's 2023 archives |

**Descriptive 2023→2024 nominal change: +0.69%.** This is **not** inflation-adjusted, statistically significant, or evidence of market expansion, margin, recoverable billings or customer willingness to pay. Mission 20 deliberately disallows a claimed 2022–2024 CAGR sourced by treating 2022 legacy-data construction as the same independent live survey vintage.

## Engineering

- `freight/research/AIES_HISTORICAL_LINEAGE_20261011.json`: closed, pinned Census archive version/byte/source records, three national 2023 cells, original published CV values, duplicate-lineage declaration, explicit 2022 primary-source hold and commercial evidence guards.
- `freight/research_aies_historical_lineage.py`: deterministic offline snapshot and **opt-in** HTTPS original-source replay. Checks exact archive ZIP lengths/hashes, safe member sets, DAT sizes, 13,512-row publication grain, required headers, 2023 geography/establishment/NAICS keys, selected revenue/CV/flags; independently invokes Mission 19 original Census 2024 ZIP verification in the **same run**. Emits status-graded `aies_historical_lineage.json` and `aies_historical_lineage.html`, each bound to evidence receipts.
- `freight/test_research_aies_historical_lineage.py`: adversarial tests for false 2022 original source certification, wrong year/geography/units, missing/duplicate 2023 source rows, Census suppression, CV corruption, forged source hash, unsafe output and blocked-vs-mismatched network source conditions.
- Existing **Lab 14** negative source checks and operator Control Center include the new research while preserving the original 14-lab count and 18 human pilot requirements.
- `.github/workflows/retally-aies-historical-lineage.yml`: PR/manual-only read-only CI, no schedule; offline adversarial suite, original three-archive Census HTTPS replay, bounded JSON/HTML evidence retention (not raw government archives or customer records). Network error is explicitly BLOCKED with no new proof. A successful network download that disagrees with pinned original records **fails CI**.

## Reproduce

From repository root, Python 3.11+:

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_aies_historical_lineage.py
PYTHONPATH=. python -m freight.research_aies_historical_lineage \
  --offline --as-of-date 2026-10-11 --out /tmp/retally-aies-historical-offline

# Explicit original-government-source replay; not a background schedule
PYTHONPATH=. python -m freight.research_aies_historical_lineage \
  --fetch-originals --as-of-date 2026-10-11 \
  --out /tmp/retally-aies-historical-original
```

An optional exact local replay accepts the three original ZIP files in 2023 basic, 2023 historical, and 2024 basic order. Neither mode imports customer or carrier invoices.

## Commercial evidence boundary

Still unverified: actual annual shipper **paid LTL invoice spend**, carrier or broker billing error prevalence, contractual rates and past payments, refund receipts, independent adjudicated overpayments, third-party reuse rights, reachable buyers, or RETALLY's addressable/collectable recovery TAM. 2023 and 2024 public survey revenue are valuable industry context but are **not** customer invoice volume, customer-level market size or audit recoveries.

**Do not merge, deploy, alter scheduled tasks, start outreach, file carrier claims, access customer data, make investment or financial transactions, or publish revenue/recovery claims.**
