# RETALLY Research Lab 14 — Mission 34: BEA vs Census Nominal Industry Denominators

**October 12, 2026 · DRAFT / INTERNAL RESEARCH.** Stacked on Mission 33 draft [PR #424](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/424). No merge, deployment, schedule modifications, private customer/carrier records, outreach, commercial performance claims, fees or money movement. Original 14 laboratories and all 18 unmet independent real-customer pilot conditions are preserved.

## Why this comparison matters

Earlier missions authenticated two **different** national trucking NAICS 484 industry measurements:
- **BEA gross output**, as published in the official September 30, 2026 first-party [GrossOutput.xlsx](https://apps.bea.gov/industry/Release/XLS/GDPxInd/GrossOutput.xlsx), \`TGO105-A\`, annual current-dollar **millions**, trucking line 44. BEA's gross output is broader industry production/sales activity and can include inter-industry and intermediate activity.
- **Census employer-industry revenue**, from the original benchmarked revised **2017–2021 Services Annual Survey** and the historical **2022–2024 AIES linked series** for NAICS 484. The 2022 AIES history is legacy-linked, not independently fielded in 2022; the separate 2024 AIES Basic file corroborates the same survey's figures, not a new independent customer-audit population.

Both values are nominal U.S. dollar millions for an NAICS 484 label, but **equal classification labels and nominal units are insufficient to prove equal economic coverage, matching weights, common populations or a direct subset relationship**.

A BEA-minus-Census dollar gap is *not* a list of missing paid freight invoices; it is not an invoice-billing error estimate, rate-contract discrepancy, legally recoverable cash, client serviceable market or RETALLY revenue.

## Exact 2017–2024 source comparison

| Year | BEA nominal gross output ($million) | Census employer revenue ($million) | Arithmetic difference ($million) | Census/BEA numeric ratio* |
| --- | ---: | ---: | ---: | ---: |
| 2017 | 367,154 | 290,532.000 | **76,622.000** | 79.13% |
| 2018 | 401,324 | 310,688.000 | 90,636.000 | 77.42% |
| 2019 | 409,425 | 314,044.000 | 95,381.000 | 76.70% |
| 2020 | 413,595 | 308,131.000 | 105,464.000 | 74.50% |
| 2021 | 490,334 | 361,243.000 | 129,091.000 | 73.67% |
| 2022 | 577,292 | 423,270.958 | 154,021.042 | 73.32% |
| 2023 | 546,993 | 406,651.010 | 140,341.990 | 74.34% |
| 2024 | **545,435** | **402,827.246** | **142,607.754** | **73.85%** |

*The Census/BEA ratio is descriptive arithmetic between different measurement definitions. **It is NOT a verified percentage of auditable freight invoices or even a proven subgroup coverage fraction.**

From 2017 to 2024, BEA nominal gross output rose **48.56%**, Census employer revenue rose **38.65%**, a **9.91-percentage-point nominal growth-rate difference**. The Census-to-BEA numeric ratio fell from **79.13% to 73.85%** (−5.28 percentage points), and the dollar difference increased by **$65,985.754 million** to **$142,607.754 million**. This is **not a recoverable-freight market**, and no causal decomposition of the changing ratio is claimed.

### Producer-price source mismatch guard

The same BEA original workbook contains trucking \`TGO104-A\` gross-output producer **price indexes** (2017=100): 2024 **137.494**, a **+37.49%** change. The separately first-party-verified BLS NAICS 484 **net-output Producer Price Index** \`PCU484---484---\`, measured by 12-month annual means, rose **+37.04%** from 2017 to 2024. The difference is **0.45 percentage points**. Numerical similarity does **not** imply they share the same price universe, weights, service mix or gross-output denominator.

Mission 29's illustrative Census nominal revenue adjusted by BLS price mean produces **+1.18%**; official BEA **real gross output** from \`TGO103-A\` rose **+8.05%**, and BLS **real sectoral output** rose **+4.02%**. Those measure different real economic concepts. They are not additive, and their numeric differences are not independently validated causal model errors or recoverable cash.

## Source and security boundaries

- First-party original BEA GrossOutput.xlsx, SHA-256 \`a5a88e808bd88c5b48d7c1f572acb4d9b113d0d753828ed8b45d8800c1eb1f46\`, original 506,819 bytes, source-year rows \`TGO105-A\` and \`TGO104-A\`; Mission 33 [PR #424](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/424).
- Original Census revised SAS Table2, SHA-256 \`cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac\`; original Census 2024 AIES historical series ZIP \`1487da6e619f2e9701635a7f6ad2ab282302d75921e33797060866142c0d94a4\`, and original 2024 AIES Basic ZIP \`39c4235026672e7bffdbc36292ed976726df368f2ca435219aef1c84e8e4faa6\`; Mission 25 original source lineage, not customer invoice sources.
- Original BLS public API v2, \`PCU484---484---\`, 96 months 2017–2024, first-party verified in the Mission 29 source suite; original M26–28 alias investigations retained as history.

**BEA gross output does not verify that the Census revenue values are a subset.** The difference can involve coverage and conceptual measurement choices, and needs independent official methodology crosswalk evidence before any causal allocation. Do not imply that the difference was discovered in carrier billings, client paid invoices, pricing disputes or legal recovery.

## Engineering

- \`freight/research/TRUCKING_MEASURE_DENOMINATOR_M34_20261012.json\`: immutably pinned original source-family roles and Git catalog hashes, eight annual Census/BEA nominal measures, strict published dollar/growth checkpoints, BLS-versus-BEA output price distinction and closed commercial claim vetoes.
- \`freight/research_economic_denominator_m34.py\`: deterministic Decimal reconciliation, source NAICS/year/unit and original catalog checks, pure eight-year comparison, one internal HTML/JSON report. Offline status explicitly claims **zero** original downloads this run. A separate \`--verify-original-receipts\` path reads source-replay JSON outputs generated **within the same CI job** by the original M33 BEA XLSX, M25 Census three-archive and M29 BLS API scripts. It checks exact source status, original BEA XLSX SHA-256 and 32 cells, all three Census archive SHA-256s and expected 2017–2024 revenue, and 288 original BLS monthly observations and source IDs; only then may the combined receipt say **three first-party families freshly replayed**. One network block yields a partial-source hold, and changed origin/values fail rather than silently pass.
- \`freight/test_research_economic_denominator_m34.py\`: adversarial field/ratio/NAICS/source-ID/units checks, corrupt original evidence receipts, forged BEA 32 cells, missing Census original ZIP proofs, truncated BLS months, forbidden false paid-customer/overcharge/TAM promotion and modified source-year lineage. Synthetic fixture receipts in unit tests are **never original web downloads**.
- Existing Lab 14 director and read-only Control Center: a source-status card and eight-year report within original **Lab 14**, not a fifteenth lab. Original M25/M29/M33 reports retained.
- \`.github/workflows/retally-economic-denominator-m34.yml\`: PR/manual-only, unscheduled. Offline M18–33 source/lab regressions and source policy tests, followed by three exact original publisher replay scripts and combined receipt validation. Stores derived JSON and HTML attestation only, not raw source files or private carrier invoices; no cron, deployments or payments.

From repository root (Python 3.11+):

    PYTHONPATH=. python -m pytest -q freight/test_research_economic_denominator_m34.py
    PYTHONPATH=. python -m freight.research_economic_denominator_m34 --offline --as-of-date 2026-10-12 --out /tmp/retally-m34-offline

No 2024 $142.608 billion industry-measure gap can be promoted to **recoverable freight TAM**. No customer invoices, contract/rate evidence, adjudicated overcharges, refunds, paid contingency fees, buyer-intent observations or customer authorization were produced. All 18 independent human data-owner pilot requirements remain unmet.

**DO NOT MERGE OR DEPLOY, CHANGE SCHEDULES, CONTACT OUTSIDE PEOPLE, IMPORT PRIVATE DOCUMENTS, MOVE FUNDS OR MAKE UNVERIFIED RECOVERY-MARKET CLAIMS.**
