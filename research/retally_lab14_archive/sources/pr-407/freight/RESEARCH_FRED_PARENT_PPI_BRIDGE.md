# RETALLY Research Lab 14 — Mission 27: FRED/BLS parent trucking PPI provenance

**October 12, 2026 · Draft internal research, stacked on Mission 26 PR #406.** No merge, production release, scheduled checks, customer/carrier outreach, private documents, external recovery claims or money actions. All 14 labs remain intact, with 18 independent real-customer pilot controls unmet.

## Problem: Parent producer price index in FRED but not BLS original API

Mission 26's direct BLS Public Data API v1 original request for PCU484484, the all-trucking NAICS 484 producer price index, returned **Series does not exist for Series PCU484484**. Both children, PCU484121484121 truckload and PCU484122484122 LTL, returned 96 monthly observations and were verified directly in BLS API from 2017 to 2024.

The [Federal Reserve Bank of St. Louis FRED](https://fred.stlouisfed.org/series/PCU484484) separately publishes **PCU484484** as a BLS-origin industry producer price series. Its [public monthly data table](https://fred.stlouisfed.org/data/PCU484484) displays **not-seasonally-adjusted, December 2003=100** BLS-origin values, and was last updated September 10, 2026. It includes all 96 months of 2017–2024.

**Critical evidence distinction:** The public FRED web table is visible, but an independent GitHub runner **could not download FRED's publisher bytes**. The exact page and its public CSV alternative both timed out in the [initial Mission 27 CI reconnaissance](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/38252235304). This is **web-observed distributor data, NOT fresh publisher-HTTP-verified data**, and **NOT direct original BLS API verification**. The root cause of the BLS API series lookup discrepancy is unknown; [BLS documentation](https://www.bls.gov/developers/api_FAQs.htm) recommends checking series IDs for a series-not-found error.

## Candidate 2017–2024 price adjustment, explicitly provisional

The frozen 96-month FRED public-table snapshot yields these simple arithmetic means and descriptive revenue comparisons:

| Measure | Result |
| --- | ---: |
| Public FRED all-trucking 2017 annual-average PPI | **134.3583** |
| Public FRED all-trucking 2024 annual-average PPI | **184.1238** |
| Public FRED all-trucking PPI 2017–2024 change | **+37.04%** |
| Census all-trucking nominal employer-industry revenue 2017–2024 change (M25) | **+38.65%** |
| **Provisional price-adjusted all-trucking revenue proxy change** | **+1.18%** |

The adjustment formula uses Census employer revenue at each year times the 2017 annual PPI mean divided by that year's annual PPI mean. Original 2017 Census nominal revenue was $290,532 million; original 2024 Census nominal revenue was $402,827.246 million. With the web-observed BLS-origin FRED index, the *illustrative, provisional* 2024 revenue at the 2017 producer index level is $293,949.981 million. The initial 2017 base is $290,532 million; their ratio yields +1.18%.

None of this establishes official Census or BLS real output, adjusted GDP, freight tonnage, demand for freight shipping, paid client freight invoice values, contractual overcharge prevalence, refunds, fee collections, or RETALLY recoverable TAM. BLS producer output index population and composition may differ from employer revenue, producer price index weights can shift, and annual means are equal-weighted across months rather than revenue-weighted.

## Separate source confidence grades

| Source | NAICS scope | Confidence and source replay |
| --- | --- | --- |
| Original BLS API v1, Mission 26 | 484121 truckload, 484122 LTL | **Previously verified: 192/192 original BLS months**, not replayed by Mission 27's parent module |
| FRED public table, BLS-origin | 484 all trucking | **Observed public webpage, fresh GitHub FRED HTTP download BLOCKED** |
| BLS original API v1 | 484 all trucking | **Not verified: series ID rejected** |
| Census SAS/AIES publisher files, Mission 25 | 484 parent and both children | **Previously authenticated original Census nominal revenue figures** |

Previously directly verified M26 child industry PPI-based revenue proxies were **+2.82% long-distance truckload** and **−1.89% long-distance LTL** over 2017–2024. These are separately qualified and do not imply that the parent all-trucking PPI is their average or a legitimate composite of only those two subsets.

The parent +1.18% proxy has a *lower provenance level* than the direct-BLS-verified child proxies. All these proxies are illustrative—not official real freight volume or a commercial customer market estimate.

## Engineering implementation

- freight/research/FRED_PARENT_484_PPI_2017_2024_20261012.json pins the exact 96 public FRED webpage-observed monthly index values, date and series metadata, original BLS API rejection, latest GitHub-runner FRED timeouts, original web source URLs, and explicit non-commercial evidence guards.
- freight/research_fred_parent_ppi.py verifies the catalog's Git blob hash, validates monthly values and provenance, and computes annual PPI means and the all-trucking price-adjusted *candidate* from M25 published Census revenue. The public-table snapshot is always labeled not freshly authenticated. A fixed allowlisted HTTPS GET attempts to read the original FRED public table under bounded resource limits; successful complete source matches can be marked **FRED HTTP distributor verified, not direct BLS**, while timeouts are **BLOCKED** and available-but-drifted source values **FAIL** rather than silently passing.
- freight/test_research_fred_parent_ppi.py tests a complete synthetic 96-month HTML source table, missing/duplicate/altered months, wrong producer series metadata or index units, altered provenance catalog, unauthorized commercial invoice/TAM claims, publisher network outages versus data mismatches, document escaping and the unchanged 18 real customer control requirements. Synthetic HTML fixtures are not proof of source origin.
- The existing Lab 14 director and read-only Control Center gain a separate visibly provisional parent source panel while preserving Mission 26's **direct BLS v1 NAICS 484 source hold** and original 14 laboratory count.
- .github/workflows/retally-fred-parent-ppi.yml is PR-triggered/manual-only with offline source-regression tests followed by a separate FRED publisher-access job. It stores only internal JSON/HTML reproducibility receipts for 14 days; no raw FRED page, client document, or user secret is committed. No schedule or deployment is created.

Reproduction, from the repository root under Python 3.11+:

    PYTHONPATH=. python -m pytest -q freight/test_research_fred_parent_ppi.py
    PYTHONPATH=. python -m freight.research_fred_parent_ppi --offline --as-of-date 2026-10-12 --out /tmp/retally-m27-offline
    PYTHONPATH=. python -m freight.research_fred_parent_ppi --fetch-fred --as-of-date 2026-10-12 --out /tmp/retally-m27-fred
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m27-control

**There is no direct original BLS NAICS 484 source proof and no FRED publisher byte replay from the observed GitHub runner.** These gaps remain open until a fresh authorized source verification works. The 18 independent real-customer pilot evidence approvals remain unmet.

**DO NOT MERGE, DEPLOY, CONTACT BUYERS OR CARRIERS, IMPORT PRIVATE DOCUMENTS, CHANGE ANY SCHEDULED TASK OR PUBLICLY ASSERT INVOICE ERRORS, REAL FREIGHT OUTPUT OR RECOVERABLE FEES.**
