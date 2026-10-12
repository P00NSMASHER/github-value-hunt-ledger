# RETALLY Research Lab 14 — Mission 28: Correct Native BLS Trucker PPI Series

**October 12, 2026 — Internal research only. Draft stacked on Mission 27 PR #407.** No merge, deployment, scheduled task changes, customer data, outreach, financial operations or publication of commercial claims. All original 14 research labs and the 18 unmet human pilot approvals remain.

## Confirmed root cause

The native Bureau of Labor Statistics producer price industry-subsector series for all truck transportation (NAICS 484) is **PCU484---484---**, while FRED redistributes the corresponding source under the shortened alias **PCU484484**. They are not interchangeable BLS API identifiers.

The official BLS downloadable PC series catalog, located at https://download.bls.gov/pub/time.series/pc/pc.series , publishes:
- series_id: PCU484---484---
- industry_code and product_code: 484---
- seasonal: U (not seasonally adjusted)
- base_date: 200312 (December 2003 = 100)

Missions 26–27 queried the FRED alias against original BLS API v1, obtaining the per-series diagnostic Series does not exist. Mission 28 also proved that the alias fails via BLS API v2 POST and GET, and v1 GET: HTTP 200 alone is NOT a valid source result. The BLS bulk series catalog and current bulk source returned HTTP 403 specifically to the GitHub runner; this is no evidence that the BLS series was discontinued or lacks data.

Replacing the alias with the **correct native PCU484---484---** in an official BLS API v2 POST, with startyear 2017/endyear 2024, returned HTTP 200, REQUEST_SUCCEEDED, empty message array and **96 genuine BLS monthly index observations** (12 per year in all eight years).

The source response was 8,483 bytes, original response SHA-256 **3668395c29966ca90ff6ee8ff5ae4f575e1cea27bd500fdaec65505eb8595880** in the first successful native-code probe. BLS API v1/v2 GET also accepted the correct native ID but without explicit eight-year parameters did not return the full earlier history. Thus the reproducible workflow uses **one exact v2 POST**, not the short-window GET.

The original BLS numerical values for all 96 months agree with the earlier FRED public monthly table, even when harmless decimal presentation differs, such as 132.5 versus 132.500. M27's old FRED HTTP timeout remains a historically true source limitation in M27's prior report; Mission 28 supplies a new, **stronger direct-BLS-original-source** evidence path without retroactively claiming that M27 fetched FRED bytes.

## Qualified price-index-adjusted Census revenue comparison

| NAICS 484 all trucking | 2017 | 2024 | Descriptive change |
| --- | ---: | ---: | ---: |
| BLS original industry producer price index, mean of 12 monthly levels | 134.3583 | 184.1238 | +37.04% |
| Source-verified Census nominal employer revenue, USD millions | 290,532.000 | 402,827.246 | +38.65% |
| Illustrative 2017 industry-PPI-level adjusted revenue proxy, USD millions | 290,532.000 | 293,949.981 | +1.18% |

**This adjusted number is NOT official real freight output, inflation-adjusted GDP, shipping tonnage, freight moves, carrier overcharge rate, collectable refunds, observed demand for audits or RETALLY recoverable TAM.** Census employer revenues and BLS net producer output price coverage may differ in service mix, scope and weights. Twelve equally-weighted monthly PPI levels do not amount to a published BLS real output statistic. No statistical variance or causal inference is offered. Parent 484 contains both 484121 and 484122; adding overlapping sectors or indexes is prohibited.

Mission 26 had already independently authenticated child BLS original index series, supporting separately qualified **+2.82% truckload** and **−1.89% LTL** 2017–2024 illustrative proxies. They remain child-industry figures, not separate components to average into the parent.

## Implementation and source-integrity controls

- freight/research/BLS_PARENT_ORIGIN_M28_20261012.json: pinned original BLS native identifier, its official series catalog metadata, previous FRED alias and Git blob, exact historical 96 monthly index levels and economic/commerce exclusions.
- freight/research_bls_parent_origin.py: strict original BLS API v2 source read-only POST, exact native series ID, date/period and preliminary-footnote checks; require 96 unique months with source values matching the source register. New returned data contradicting the pinned values triggers FAIL instead of silent normalization. Network unreachability triggers BLOCKED, not verified. Produces JSON and HTML receipts.
- freight/test_research_bls_parent_origin.py: synthetic adversarial test cases for the FRED alias, API status/message semantics, wrong year scope, missing/duplicate months, annual M13 substitution, numeric source tamper, preliminary flags, source catalog modification, source-signature forgery and inappropriate freight refund/real-output claims.
- freight/lab_phase4_director.py and freight/lab_phase4_control_center.py: append one source-provenance report to existing Lab 14, preserving all fourteen lab modules and 18 unapproved genuine customer pilot requirements. Previous M27 source status stays intact.
- .github/workflows/retally-bls-parent-origin.yml: unscheduled pull-request/manual CI. Runs adversarial historical research regressions and a separate original native-BLS v2 96-month HTTP replay, retaining only derived internal JSON/HTML receipt files for 14 days. No raw BLS payload, private invoice or carrier data committed or uploaded.

### Reproduce from repo root (Python 3.11+)

    PYTHONPATH=. python -m pytest -q freight/test_research_bls_parent_origin.py
    PYTHONPATH=. python -m freight.research_bls_parent_origin --offline --as-of-date 2026-10-12 --out /tmp/retally-m28-offline
    PYTHONPATH=. python -m freight.research_bls_parent_origin --fetch-bls-native --as-of-date 2026-10-12 --out /tmp/retally-m28-original
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m28-control

**No paid real-world LTL invoices, correct governing rate-contract checks, independent audited overcharges, actual money recovered, customer consent, approved independent buyers or market TAM has been established. All 18 pilot requirements remain unmet. DO NOT MERGE, DEPLOY, CONTACT CARRIERS/BUYERS, IMPORT CUSTOMER FILES, ADD SCHEDULES, MAKE PAYMENTS OR PUBLISH RECOVERY CLAIMS.**
