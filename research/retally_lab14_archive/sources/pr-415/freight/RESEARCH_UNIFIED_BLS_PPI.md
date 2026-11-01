# RETALLY Research Lab 14 — Mission 29: Unified Original BLS Producer Price Evidence

**October 12, 2026. Internal draft research only.** Stacked on Mission 28 draft PR #413. No merge, production deployment, scheduled monitoring, customer/carrier contact, payment or public recovery claim. All fourteen existing laboratories and all eighteen genuine customer-pilot human signoffs remain outstanding.

## One current BLS source view

Missions 26–28 document a sequence of historically accurate source discoveries. Mission 26 originally tried the short FRED alias PCU484484 against BLS, which returned Series does not exist. Mission 27 captured the visible FRED distributor table, but its direct FRED HTTP downloads timed out. Mission 28 corrected the original BLS-native NAICS 484 source ID to PCU484---484--- and independently authenticated 96 monthly records. Earlier reports remain in the archive and should not be described as current source blockers.

Mission 29 authenticates **all three legitimate native BLS price series in ONE original BLS API v2 POST**, across every month of 2017–2024:

- 484 all trucking: PCU484---484---
- 484121 long-distance general freight truckload: PCU484121484121
- 484122 long-distance general freight less-than-truckload: PCU484122484122

The initial direct-BLS three-source discovery succeeded in [GitHub Actions run #38274002011](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/38274002011): 96/96 months in each of the three native series, **288/288 total**, with REQUEST_SUCCEEDED and no BLS error message. Raw BLS v2 response SHA-256: 5418c6633ceb41e44c25935b7de543293f00006510a7ec452a23e6db6a0ad80e. Subsequent verification checks the 288 month/series/value facts rather than requiring the raw API JSON formatting to remain unchanged.

Original-source definitions and methods:
- https://www.bls.gov/ppi/overview.htm
- https://www.bls.gov/ppi/data-retrieval-guide/
- https://www.bls.gov/developers/api_signature_v2.htm
- https://www.bls.gov/developers/api_faqs.htm

**BLS PPI measures seller-side producer output-price change**, not consumer freight invoice payment amounts, billing errors, actual transaction prices, cargo tonnage or freight output volume.

## Source-verified Census nominal industry revenue with descriptive PPI ratios

The original 2017–2024 Census employer revenue series was separately publisher-authenticated in Mission 25. Mission 29's BLS job does **not** redownload original Census archives; it consumes the pinned, previously validated Census analysis.

For each industry and year, calculate a 12-month arithmetic mean of the not-seasonally-adjusted BLS industry index. Then multiply the nominal Census employer revenue by the 2017 annual-mean industry PPI divided by that year's annual mean.

| 2017 NAICS industry | Census nominal 2017–2024 change | Illustrative annual-average PPI-adjusted revenue proxy |
| --- | ---: | ---: |
| 484 parent truck transportation | +38.65% | **+1.18%** |
| 484121 long-distance truckload | +43.48% | **+2.82%** |
| 484122 long-distance LTL | +40.93% | **−1.89%** |

These **do not measure official BEA/BLS real output or physical freight volumes**. Census employer revenue populations and BLS net-output index composition/weights are not proven identical. NAICS 484 **includes both children**; these are not three independent samples or additive markets. Statistical uncertainty and true customer-level freight billing errors have not been measured.

### Important methodological sensitivity

Substituting December 2017 and December 2024 endpoint price ratios for annual-average BLS PPI ratios creates different illustrative adjusted figures:

| Industry | Annual-average adjusted proxy | December-endpoint alternative (NOT annual compatible) | Difference |
| --- | ---: | ---: | ---: |
| 484 | +1.18% | +4.75% | +3.57 percentage points |
| 484121 | +2.82% | +8.87% | +6.06 points |
| 484122 | −1.89% | +1.60% | +3.49 points |

**The LTL proxy changes sign**. This is a *sensitivity warning*, not contradictory independent measurements or a statistical confidence interval. December prices are not an appropriate substitute for annual-mean prices when trying to adjust full-year revenue. The annual-average method remains an illustrative proxy, not official real freight output.

## Implementation

The closed, Git-blob-pinned source policy lives at freight/research/BLS_TRUCKING_UNIFIED_SOURCE_POLICY_M29_20261012.json. The executable evidence module freight/research_unified_blspci.py reuses the prior immutable first-party source catalogs for all three BLS industry series and M25 Census source years. It verifies a single original BLS v2 response of 288 calendar-month observations (eight years, three series), correct native IDs, unique months, final/no-preliminary values, original numeric agreement, and provenance. A network outage records BLOCKED with zero newly authenticated records. Source bytes that are available but contain discrepant values cause a FAIL requiring review.

The adversarial tests live at freight/test_research_unified_blspci.py and cover identity/address mistakes, incomplete months, duplicate source records, source revisions, invalid year/source units, unauthorized real-output and customer-money claims, and the LTL method sign-flip trap. The existing Lab 14 director and Control Center now include a **single current** BLS series evidence report and explicitly label prior M26/M27 source-status text as historical. No previous audit records are rewritten and the laboratory count remains fourteen.

The unscheduled PR/manual-only workflow at .github/workflows/retally-unified-bls-ppi.yml separately runs offline full research regression tests and a fresh, bounded original BLS v2 API three-industry check. Only JSON/HTML evidence receipts are retained for 14 days. No downloaded raw BLS data or private customer information is stored.

### Reproduction

From repository root using Python 3.11+:

    PYTHONPATH=. python -m pytest -q freight/test_research_unified_blspci.py
    PYTHONPATH=. python -m freight.research_unified_blspci --offline --as-of-date 2026-10-12 --out /tmp/retally-m29-offline
    PYTHONPATH=. python -m freight.research_unified_blspci --fetch-original --as-of-date 2026-10-12 --out /tmp/retally-m29-live
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m29-control

**All eighteen independent real-customer pilot evidence gates remain unmet.** No paid customer invoices, contract-approved charges, adjudicated overpayments, recovered refunds, approved buyer contacts or recoverable market TAM are established by public BLS/Census prices. DO NOT MERGE, DEPLOY, CHANGE SCHEDULES, CONTACT CARRIERS/CUSTOMERS, ACCESS PRIVATE DOCUMENTS, OR PUBLISH RECOVERY OR OFFICIAL REAL-FREIGHT-OUTPUT CLAIMS.
