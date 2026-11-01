# RETALLY Research Lab 14 — Mission 12: Published Freight Market Source Reconciliation

**October 11, 2026 public-source review. DRAFT / RESEARCH ONLY.** Stacked on the unmerged Mission 11 research branch. No production deployment, buyer/carrier outreach, paid data, real customer files, new scheduled task, or new laboratory.

## What changes and why it matters

Prior research established **18 unverified real-world pilot controls**, six proposed business experiments, and a public freight-source catalog. Those controls should remain in place, but they do not answer a basic marketing intelligence question: *Which publicly observed freight statistics legitimately justify researching a buyer segment?* Mission 12 adds the first offline, sourced **numerical contradiction and denominator audit** inside the same Lab 14.

Data **were manually transcribed from the publicly searchable Census CFS 2022 CF2200A01 table and June 26, 2025 Census press release**, not re-imported from a raw Census CSV. The [2022 original Census download directory](https://www2.census.gov/programs-surveys/cfs/data/2022/) lists \`CF2200A01.zip\` (164 KB). The original ZIP contents were **not downloaded or verified** for this mission; the checks are a bounded source-excerpt comparison, not independent full-data replication.

### Source register (all published Census/BTS material)

- [Census CF2200A01 — Origin Geography by Domestic Transportation Mode (2022 and 2017)](https://data.census.gov/table/CFSAREA2022.CF2200A01): June 26, 2025 publication; six specific 2022 rows manually reviewed, not the whole table.
- [Census June 26, 2025 CFS press release](https://www.census.gov/newsroom/press-releases/2025/cfs-shipments-of-goods.html): rounded national value/tonnage and truck-mode figures, manufacturing/wholesale headline estimates, and the South-region claim that requires reconciliation.
- [Official CFS 2022 original dataset directory](https://www2.census.gov/programs-surveys/cfs/data/2022/): confirms the presence of the ZIP, but not its uninspected content or checksum.
- [Census CF2200A01 methodology and table notes](https://data.census.gov/table/CFSAREA2022.CF2200A01): CFS is a sample of in-scope establishments, not a census of paid carrier invoices; estimated dollar values are **goods shipped**. The 2022 single-truck category includes customer pickup, which was not separately included in the 2017 truck definition.

All three source artifacts are 2025 publications observed in 2026. They share one CFS survey evidence family; they are not three statistically independent confirmations of a market forecast.

## Published table observations, not LTL billings

| Exact 2022 CF2200A01 source row | Value ($ million of goods) | Weight (thousand tons) |
| --- | ---: | ---: |
| United States / all modes | 17,996,782 | 12,169,793 |
| Single-mode truck incl. customer pickup | 13,222,965 | 8,293,501 |
| For-hire truck | 8,062,541 | 3,909,476 |
| Company-owned truck | 4,141,550 | 2,994,372 |
| Customer pickup | 1,018,874 | 1,389,653 |
| South Region / all modes | 6,689,859 | 4,919,551 |

**Arithmetic test:** 8,062,541 + 4,141,550 + 1,018,874 = 13,222,965 ($ million), and 3,909,476 + 2,994,372 + 1,389,653 = 8,293,501 (thousand tons). Derived shares from the detailed rows: truck accounts for **73.47% of value** and **68.15% of tonnage** across the CFS covered mode universe; for-hire truck is **44.80% of total shipped-goods value** and **60.97% of single-truck value**. The published press highlights of 73.5% and 68.1% are consistent at their stated rounding precision.

**Interpretation hold:** $8.06 trillion is value of commodities moving by for-hire truck, not the amount businesses paid for carrier invoices, not LTL freight spend, not errors found, not addressable freight-audit market and not RETALLY contingent fees. For-hire includes truckload/non-LTL business. The sample-frame and mode-definition changes also preclude unadjusted 2017-to-2022 comparisons.

## Discovered source discrepancy — not silently fixed

The Census [press release](https://www.census.gov/newsroom/press-releases/2025/cfs-shipments-of-goods.html) says the **South** shipped **1.9 billion tons (40.4%)** in 2022. The detailed [CF2200A01 source excerpt](https://data.census.gov/table/CFSAREA2022.CF2200A01) instead reports **4,919,551 thousand tons**, i.e. 4.919551 billion tons, corresponding to **40.42%** of the detailed U.S. total 12,169,793 thousand tons. Using the press release's 1.9 billion tons with that same U.S. denominator gives only **15.61%**, not 40.4%.

This is recorded as \`UNRESOLVED_FIRST_PARTY_PUBLICATION_CONTRADICTION\`: **the press South tonnage is quarantined from downstream analysis.** The detailed table's 4.92 billion tons is a separately published value, **not an authorized correction to the press release**. A future analyst must check the original full table, survey geography definitions and official publication revisions before promoting a reconciliation or republishing a revised press value. No official corrigendum has been established by this mission.

## Buyer research hypotheses (not rankings, customers, or findings)

- **Manufacturing:** the press release attributes 4.9 billion tons and $7.1 trillion of *shipped goods* to manufacturers. Test actual buyer-approved for-hire **LTL** paid invoice counts, carrier contracts, discount/exceptions and incidence of independently adjudicated errors. No conversion or recovery assumptions supplied.
- **Wholesale trade:** the press release attributes 4.1 billion tons and $8.1 trillion of goods to wholesalers. Test the actual split between parcel/LTL/TL/company-owned movement, paid invoices, audit provider lock-in and permission to inspect historical records before evaluating opportunity.
- **Warehousing/distribution auxiliaries:** part of the covered survey population, but no isolated warehouse shipment- or paid-invoice estimate comes from the reviewed headline. Inspect [GAS18 NAICS × mode × distance](https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html) with industry frame/quality terms before proposing a market figure.

They are research work items, **not a ranked prospect list**. Different establishments can ship the same goods through multiple transactions; the value of goods cannot be turned into paid freight expenditures by summing manufacturer and wholesale headlines. A permissions-and-representation-controlled invoice study remains necessary for any claimed recovery incidence, buyer demand or bill-level accuracy.

## Engineering

\`freight/research/CFS_2022_SOURCE_AUDIT_20261011.json\`: three directly attributed official-source records, six manually transcribed detailed rows, one press-release numerical claim set, three explicit buyer cohort hypotheses and three next-step Census table verifications. All are bounded metadata; no CSV, customer file or API credential.

\`freight/research_market_audit.py\`: fixed-source identity, mode code/unit/year, publication date, numerator/denominator validation, component conservation, Decimal-based share calculations, mandatory South conflict hold, 90-day source recheck flag, buyer research-only outputs, and deterministic JSON/HTML operator reports. No network actions or auto-corrections.

\`freight/test_research_market_audit.py\`: adversarial controls for swapped truck-mode buckets, thousand/million scaling, impossible implied shares, press-release contradictions, altered primary-source attribution, forged raw ZIP hash, survey-value-to-billing TAM laundering, fake customer evidence, malformed HTML, and old-versus-new mode-definition errors.

Existing Lab 14 director, Phase 4 Control Center and read-only Research Intelligence CI integrate the report. **The 14 original labs, six proposed study designs, 18 unmet pilot approval controls, and original 26 historical open findings remain unchanged.**

Run locally, from repository root using Python 3.11+:

\`\`\`bash
PYTHONPATH=. python -m pytest -q freight/test_research_market_audit.py
PYTHONPATH=. python -m freight.research_market_audit --as-of-date 2026-10-11 --out /tmp/retally-market-audit
# Read market_source_audit.json and market_source_audit.html
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control-center
\`\`\`

### Follow-on high-value action

Review the official **CF2200A18** (NAICS × mode × distance) and **CF2200A19** (NAICS × mode × shipment weight) tables under an explicit primary-source acquisition and data-quality plan. **Neither should be treated as LTL invoice or paid carrier rate data.** Only a subsequent independently authorized invoice corpus with contractual rate and payment proofs can establish second-look invoice error incidence or net recovery profitability.

**DO NOT MERGE, DEPLOY, CONTACT BUYERS/CARRIERS, IMPORT LIVE CUSTOMER MATERIAL, CHANGE EXISTING TASKS, OR PUBLISH UNVERIFIED PERFORMANCE CLAIMS.**
