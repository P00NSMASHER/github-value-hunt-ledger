# RETALLY Research Lab 14 — Mission 18: Census AIES LTL carrier revenue

**Internal research only; October 11, 2026.** Stacked on Mission 17 draft PR #388. Not a new lab, production change, public marketing claim, real invoice audit, sales outreach, or permission to claim recoveries.

## New empirical evidence

The Census Bureau released the complete **2024 Annual Integrated Economic Survey (AIES)** dataset on September 3, 2026. The Census-origin series, republished through FRED and last updated September 10, 2026, measure employer-establishment industry revenue under 2017 NAICS classifications. Survey values are nominal and subject to sampling and nonsampling error.

| Industry (Census / FRED) | 2022 revenue ($1,000) | 2023 revenue ($1,000) | 2024 revenue ($1,000) |
| --- | ---: | ---: | ---: |
| NAICS 484122, long-distance general-freight less-than-truckload | 65,688,461 | 64,651,167 | **65,096,292** |
| NAICS 484121, long-distance general-freight truckload | 172,717,339 | 163,025,116 | 161,329,027 |
| NAICS 484, all truck transportation | 423,270,958 | 406,651,010 | 402,827,246 |

The specific **2024 LTL employer-industry revenue** estimate is **$65.096292 billion**, displayed as $65.096 billion. This NAICS child industry accounted for **16.16%** of the broader 2024 truck transportation industry revenue; its nominal 2024 revenue rose **0.69%** versus 2023 and declined **0.90%** versus 2022. These are industry subset shares and annual business revenue changes, **NOT** shares of invoices audited, freight bills paid, errors, recoveries, carriers eligible for claims or buyers reachable by RETALLY.

### Official sources and distribution provenance

- Census announcement, published September 3, 2026: https://www.census.gov/newsroom/press-releases/2026/2024-aies-data-release.html
- Census documentation and API guidance: https://www.census.gov/data/developers/data-sets/aies.html
- FRED/Census NAICS 484122 annual series: https://fred.stlouisfed.org/data/AIES484122RCT00US
- FRED/Census NAICS 484121 annual series: https://fred.stlouisfed.org/data/AIES484121RCT00US
- FRED/Census NAICS 484 annual series: https://fred.stlouisfed.org/data/AIES484RCT00US
- NAICS definition: https://data.census.gov/profile/484122_-_General_freight_trucking%2C_long-distance%2C_less_than_truckload?codeset=naics~484122&g=010XX00US

All three FRED series come from a single Census AIES origin; they are not independently sampled studies. The U.S. Census industry universe covers employer businesses and the NAICS 484122 code excludes some broader shipment services called LTL in everyday usage.

### Conflict with historical 2022 Services Annual Survey

FRED's legacy Census Services Annual Survey source https://fred.stlouisfed.org/data/REVEF484122ALLEST reports $68,411 **million** for 2022. The AIES current historical 2022 value above is $65,688.461 **million**. They are *different published series*; their difference is not an observed billing error, and the evidence does not establish a single explanation for the gap. Do not replace AIES 2022 with legacy SAS, splice trend rates or count these as independent studies.

### Incompatible CFS and AIES populations

The earlier Mission 17 verified two **2022 Census Commodity Flow Survey** A18/A19 original ZIP archives against exact hashes and all selected 60 for-hire goods-value/weight observations. CFS tracks commodity value shipped by industry of origin. Its mode 111 includes truckload and LTL; its 4931 tabulation includes NAICS 484 truck transportation. The AIES 484122 subset instead tracks long-distance general-freight carrier industry revenue. The units, population, year, and meaning differ.

Never divide or multiply CFS goods value by AIES establishment revenue to produce customer freight spending, invoice counts, rate levels, LTL-wide market size or recovery opportunity.

## Implementation

1. Source inventory: freight/research/AIES_LTL_CARRIER_REVENUE_20261011.json, nine exact annual revenue observations, FRED/Census source URLs, legacy SAS quarantine and explicit false commercial-evidence flags.
2. Analysis and report: freight/research_ltl_revenue_bridge.py validates a frozen source Git blob, checks units/years/source identity/lineage and generates a read-only JSON/HTML report with Decimal calculations.
3. Optional independent distributor check: the command line --verify-fred-csv downloads only three allowlisted FRED public CSV series when explicitly invoked, checks source values, duplicates, year coverage and recent changes, and records hashes. This is NOT an original Census API replay, publisher digital signature or independent freight audit.
4. Adversarial tests: freight/test_research_ltl_revenue_bridge.py rejects fraudulent source substitutions, source-unit changes, fabricated invoice results, false rights/approval flags, future timestamps, legacy survey splicing, corrupt CSVs and HTML script injection. It also tests independent **blocked-network** and **mismatched-source** outcomes: a FRED network timeout is recorded as BLOCKED and cannot yield a verified source receipt; a successfully downloaded but altered Census-origin figure is a test FAIL.
5. Existing Lab 14: validates new research in the existing lab director and links a separate report in the original operator Control Center. Laboratory count stays fourteen.
6. CI: .github/workflows/retally-aies-ltl-revenue.yml runs offline falsification plus a separate optional FRED CSV source job for PRs and explicit manual dispatch only. There is no cron or background process.

Run from the repo root with Python 3.11 or newer:

    PYTHONPATH=. python -m pytest -q freight/test_research_ltl_revenue_bridge.py
    PYTHONPATH=. python -m freight.research_ltl_revenue_bridge --as-of-date 2026-10-11 --out /tmp/retally-aies-evidence
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-operator

Optional fixed-source verification (only when intentionally requested):

    PYTHONPATH=. python -m freight.research_ltl_revenue_bridge --verify-fred-csv --as-of-date 2026-10-11 --out /tmp/retally-fred-evidence

## Decision boundaries

**Established research context:** One bounded Census-origin industry revenue snapshot with NAICS subset arithmetic, relevant source dates and traceable FRED links. This is closer to transportation service revenue than the CFS dollar value of commodities.

**Still NOT independently evidenced:** Actual customer-paid LTL invoice population; carrier/shipper contract coverage; invoice overcharge prevalence; claim legality; refunds and cash collection; buyer intent; RETALLY addressable, serviceable, or recoverable markets. The eighteen genuine human/real-document pilot approvals in Mission 11 remain unverified.

**DO NOT MERGE OR DEPLOY, CREATE SCHEDULES, IMPORT CUSTOMER DOCUMENTS, CONTACT BUYERS/CARRIERS, PUBLISH PERFORMANCE CLAIMS, OR TAKE ANY FINANCIAL ACTION.**

## Source network status (Mission 18 execution)

An initial GitHub Actions attempt to retrieve the allowlisted FRED graph CSV failed on an HTTPS response read timeout after 20 seconds. The offline source snapshot, tests and existing 14-lab operator build succeeded independently. The subsequent hardening commits ensure a transient unavailable FRED endpoint is **explicitly labeled BLOCKED_EXTERNAL_FRED_CSV_UNREACHABLE_NOT_VERIFIED** with no CSV download digests. The block does not promote external data freshness or override the observed Census/FRED figures. If the endpoint serves a parseable CSV that disagrees with the frozen series, the source QA still **fails** instead of silently accepting drift.

The independent source-family limitation remains: a FRED CSV download, even if successful, verifies a publisher-distributed time-series rendering, not Census-original AIES API bytes or a legally authorized customer freight invoice.
