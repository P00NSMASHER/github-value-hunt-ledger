# RETALLY Research Lab 14 — Mission 15: Source-Grounded Industry Comparison

**Date:** October 11, 2026. **Research-only draft**, stacked on Mission 14 PR #379. No merger, deployment, outside contact, paid data, real customer invoice intake, scheduled task changes or new Lab 15.

## Executive result

RETALLY can make a **limited, reproducible quantitative comparison of the Census 2022 goods shipped from manufacturing, wholesale, and warehousing establishments**. It **cannot infer buyer LTL invoice spending, industry-specific for-hire mode mix, recoverable overcharges, market size or buyers likely to sign** from those rows. The original A18/A19 archives were inspected by a read-only browser in Mission 14; GitHub CI remains offline and tests only static source receipts and synthetic adversarial mutations. The original ZIPs were not copied to this repository, and their contents were not rerun in CI.

Published primary-source references:
- [Census 2022 CF2200A18 NAICS × mode × distance ZIP](https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A18.zip)
- [Census 2022 CF2200A19 NAICS × mode × shipment weight ZIP](https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A19.zip)
- [Census 2022 CF2200A01 geography × mode ZIP](https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A01.zip)
- [Census final CFS 2022 source index](https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html)

These are **2022 survey estimates published in 2025**, not 2026 spending forecasts. A18/A19 observations derive from the **same 2022 CFS statistical source family**, not two independent measures of buyer demand.

## Quantitative comparison — five real published direct totals

The unit of the table below is **all domestic transportation modes**, national **origin-establishment NAICS** within CFS's coverage. Census \`VAL\` is **USD millions of goods shipped**, and \`TON\` is **thousands of tons**. Figures were directly matched in both A18 total distance (\`SHIPDIST=001\`) and A19 total weight (\`SHIPWT=01\`) at the same NAICS/mode.

| Industry (origin NAICS) | 2022 goods value ($m) | 2022 weight (thousand tons) | Share of survey's U.S. goods value | Goods value per ton (not a freight rate) |
| --- | ---: | ---: | ---: | ---: |
| Manufacturing (31-33) | 7,073,495 | 4,949,955 | 39.30% | $1,429.00 |
| Wholesale trade (42) | 8,094,350 | 4,115,279 | 44.98% | $1,966.90 |
| Warehousing/storage (4931) | 1,347,716 | 305,651 | 7.49% | $4,409.33 |

Denominator: Census national covered goods value \`17,996,782\` ($m), separately checked against M12. National all-industry for-hire truck \`VAL=8,062,541\` ($m), i.e. **44.80% of total goods value**, but it **cannot be applied to those industries as an assumed LTL mode fraction**. Within-sector \`DMODE=111\` totals have **not been separately reproduced with flags/coefficients** in this mission. They remain **null**, as do freight-spend, billing-error, buyer acquisition and revenue fields.

**Avoid adding these sectors as a 'unique freight market':** origin industries, supply-chain re-shipment, nested NAICS, aggregate modes, weight buckets and distance buckets can overlap or represent different analytical slices. Percentages above use the same national survey-covered goods denominator, not RETALLY's serviceable market.

## Quality warnings, not freight errors

The full A18/A19 archive's original source-field flags were inspected in Mission 14 and stored as pinned, browser-observed metadata.

| Census table | S-value cells | Z-value cells | Value cells flagged S or Z | Weight cells flagged S or Z |
| --- | ---: | ---: | ---: | ---: |
| A18 (7,312 rows) | 1,839 | 43 | 25.74% | 31.74% |
| A19 (6,782 rows) | 2,063 | 91 | 31.76% | 34.03% |

\`S\` means an estimate fails Census publication quality criteria, while \`Z\` is a reported rounded-to-zero designation, **not proof of exact zero**. Those percentages describe the **proportion of published cross-tabular cells carrying quality flags**, not the proportion of freight bills containing errors, nor the quality/precision of the three direct unflagged industry totals. Census coefficients of variation for each sector remain unreviewed; no invented statistical significance or population ranking is inferred.

## Buyer-facing falsification design

**Manufacturing (31-33):** Investigate whether a genuinely consented manufacturer spends materially on independently contracted, paid LTL transport. A large shipped-goods value can reflect valuable merchandise or own-account and truckload shipping rather than LTL billing complexity. A fair permissioned historical bill sample with negative controls could disprove the hypothesis.

**Wholesale (42):** Research whether wholesale accounts have accessible, independently reconcilable LTL bills and authority to authorize external audits. Goods can change ownership and ship again across the supply chain. An analysis confined to parcel/TL accounts or self-reported errors would bias the result.

**Warehousing/storage (4931):** Determine whether operators *own or pay* the freight invoice instead of handling goods on someone else's behalf. Without an authorized payer, carrier-specific contracts and separately verified cash ledgers, no commercially recoverable freight audit cohort is established.

These are **three research questions in a convenient order**, not a top-three ranking of target buyers or a recommendation to contact them.

## Required independent evidence before stronger claims

1. Reproduce direct \`NAICS2017 in {31-33,42,4931}\` × \`DMODE=111\` rows from the original A18/A19 DAT archives, including \`VAL_F\`, \`TON_F\`, CV and CV flags. There is **no legitimate formula** to create industry for-hire shares from the national 44.80% figure.
2. Inspect nonoverlapping distance \`SHIPDIST 02..10\` and weight \`SHIPWT 02..10\` strata for each sector, handling suppression and any rounding residual. Never label middle-weight for-hire truck shipments as definitively LTL.
3. Complete the already-defined **18 still-unmet buyer-pilot data rights, security, sampling and independent review requirements** from Mission 11 before seeking actual invoice/payments data.
4. Validate real paid freight spend, issuer/payer rights, controlling historical contracts, independently adjudicated billing differences, and fees actually collected. No real-world recoveries have yet been proven.

## Engineering delivered

- \`freight/research/CFS_INDUSTRY_COMPARISON_PLAN_20261011.json\`: source lineage, exact prospective NAICS cohorts, research questions, alternatives, falsification criteria, four held proof gates, and expressly prohibited claims.
- \`freight/research_industry_comparison.py\`: offline, deterministic, Decimal-derived USD/ton and numerator/denominator checks against the existing **M12** source audit and **M14** original archive receipt. Reports no industry-specific for-hire, LTL, recovery revenue or marketing results if not actually observed.
- \`freight/test_research_industry_comparison.py\`: adversarial regression tests for inappropriate denominators, false primary-source hashes, corrupted sector values, quality-flag tampering, NAICS 4931 mislabeling, invented paid freight, false source independence, unapproved pilot status, HTML escaping, source-date backdating and reproducibility.
- Existing Lab 14 director, operator Control Center, and read-only GitHub workflow include \`cfs_industry_comparison.json\` and \`cfs_industry_comparison.html\` artifacts. All previous labs and scheduled tasks remain untouched.

Run offline (Python 3.11+):

\`\`\`bash
PYTHONPATH=. python -m pytest -q freight/test_research_industry_comparison.py
PYTHONPATH=. python -m freight.research_industry_comparison \
  --as-of-date 2026-10-11 --out /tmp/retally-cfs-sector-research
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control
\`\`\`

A useful next research task is obtaining **actual independently sourced sector × for-hire direct rows** with quality flags, while keeping every commercial inference blocked. As of this mission, the read-only external browser has insufficient credits; **no unverified extra original-source rows were invented**.

**DO NOT MERGE OR DEPLOY WITHOUT REVIEW. DO NOT ASK FOR CUSTOMER FILES, CONTACT CARRIERS, PURCHASE DATA, CHANGE SCHEDULED TASKS OR PUBLISH PERFORMANCE CLAIMS.**
