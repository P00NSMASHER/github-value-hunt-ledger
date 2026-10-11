# RETALLY Research Lab 14 — Mission 16: For-Hire Trucking, Shipment Patterns & Corrected NAICS Scope

**Internal source-backed research · October 11, 2026 · draft stacked on Mission 15 #380.** No Lab 16 was added. This is an upgrade to the existing research Lab **14**, not a production change, externally validated customer result, prospect targeting, paid freight spend estimate, or claim-filing permission.

## Important correction to prior research

The original [Census 2022 CFS A18](https://data.census.gov/table/CFSAREA2022.CF2200A18) and its [2022 methodology](https://www2.census.gov/programs-surveys/cfs/technical-documentation/methodology/2022%20Commodity%20Flow%20Survey%20Methodology.pdf) explicitly say **NAICS 484 (truck transportation) is grouped with NAICS 4931 for tabulation**. The warehouse segment within the CFS frame covers **captive auxiliary warehouses supporting a single company**; warehouse operators providing public/commercial services are excluded. Therefore the previously described **$1.348T reported 4931 category is NOT $1.348T of pure warehousing shipments** and cannot be used as a warehousing-only opportunity estimate. The prior M15 report now carries the corrected combined 4931/484 label.

Likewise, \`DMODE=111\` is **for-hire truck**, including truckload and LTL. The CFS distance metric reflects **great-circle distance**, not actual road miles; shipment weight brackets do **not** identify LTL service type. Shipping-goods value is not freight spending, annual carrier invoices, pricing, billing errors, or cash overpayments.

## Actual recovered public data and provenance hierarchy

The read-only browser inspection from M14 separately recorded the official 2022 Census ZIP fingerprints (A18: \`a18ce071599457572177dd56f8a6174594d1018da9b9024476c4e9832a357bf5\`, A19: \`fe3085d23a3c76704a0d86d9213bb38d3d341b2c228990a5ebf40b6b3f1b661d\`). In this mission, original Census host ZIP bytes could not be reacquired by the local tool; Browser Use had insufficient credits. No false assertion of local original ZIP replay is made.

A [public GitHub mirror](https://github.com/noobifyLol/CAD_AI/tree/master/outputs/phase2b_healthcare_tam_som/cfs_raw) includes text-extracted \`CF2200A18.dat\` and \`CF2200A19.dat\`. The mirror's complete file lengths and row counts match the earlier original inspection: A18 **1,040,806 bytes / 7,312 rows**, A19 **1,017,567 bytes / 6,782 rows**. Original official observations, previously verified national/industry total rows, and the two mirror files' NAICS 111 total values, weights and CVs match exactly. Mirrored raw Git blobs are pinned separately:
- [A18 mirror raw](https://raw.githubusercontent.com/noobifyLol/CAD_AI/master/outputs/phase2b_healthcare_tam_som/cfs_raw/CF2200A18/CF2200A18.dat): Git blob SHA \`5e80c8e9a9242fbf776ed141abaf22e6cd16a5e4\`.
- [A19 mirror raw](https://raw.githubusercontent.com/noobifyLol/CAD_AI/master/outputs/phase2b_healthcare_tam_som/cfs_raw/CF2200A19/CF2200A19.dat): Git blob SHA \`c781c71eab0898d7939a0eba60966b9bedafebd7\`.

**Provenance qualification:** Git mirror blob SHA is not the official original ZIP SHA; matching row values/size does not cryptographically prove that every mirror bucket row equals the publisher-hosted archive. We captured and tested selected Census-format public records but do **not** label them publisher-authenticated, a new independent survey, or a proven Census correction. Official primary-source ZIP rehash remains a review step.

## Previously missing for-hire source rows

These are the 2022 **national NAICS × mode 111 TOTAL** rows. The A18 \`SHIPDIST=001\` and A19 \`SHIPWT=01\` values, flags and CVs agree. All six selected \`VAL_F\`/\`TON_F\` total fields are unflagged.

| Census source reporting category | For-hire goods value ($m) | For-hire / all-mode goods value | For-hire weight (thousand tons) | For-hire / all-mode weight | Published value/weight CV |
| --- | ---: | ---: | ---: | ---: | --- |
| Manufacturing \`31-33\` | 3,799,845 | 53.72% | 1,740,594 | 35.16% | 1.8% / 2.3% |
| Wholesale \`42\` | 3,341,533 | 41.28% | 1,348,938 | 32.78% | 3.2% / 5.3% |
| Combined \`4931/484\` reporting category | 635,089 | 47.12% | 140,628 | 46.01% | 7.5% / 9.8% |

Each within-category share uses the direct **same-NAICS all-mode** goods value/weight denominator from M14/M15. It is not a count of LTL shippers, shipments or freight invoices. The **full Census survey source is the same across A18 and A19**—those are two marginal views, not independent experiments.

### One-dimensional shipped-goods patterns

The following percentages are **shares of each category's for-hire shipped-goods value**, not route counts, transport spending, carrier price or real LTL volume.

| Census category | For-hire goods value in shipments with GCD less than 250 miles (A18) | For-hire goods value in shipments weighing 500–9,999 lbs (A19) |
| --- | ---: | ---: |
| Manufacturing \`31-33\` | 40.09% | 30.51% |
| Wholesale \`42\` | 61.71% | 31.48% |
| Reported \`4931/484\` grouping | 58.75% | 33.68% |

**Do not multiply those percentages to infer shipments that satisfy both conditions.** A18 and A19 are separate marginal distributions; their *joint* distance × shipment-weight structure is not present. Individual CVs are observed on the source, but covariance for grouped bins is not. Combined-bin sampling error or statistical significance has not been established. Short great-circle distances do not imply efficient actual delivery routes. Shipment weight alone does not classify a movement as LTL.

### Suppression and rounding rules

Most of the selected category mode/bucket values are unflagged, but:
- In A18, combined \`4931/484\` **distance bucket 09** has \`TON=0\`, \`TON_F=S\`. This is a quality-suppressed tonnage cell, **not an observed zero tons**.
- In A19, combined \`4931/484\` **weight bucket 10** has both \`VAL_F=S\` and \`TON_F=S\` alongside numeric zero placeholders. **Do not derive hidden value/weight by subtracting visible buckets from the total.**
- In otherwise unflagged buckets, values may differ from published totals by a few reporting units due to rounding. The verifier allows only a bounded number of units of rounding discrepancy and never silently fabricates a suppressed residual.

The five-year vintage and industry definitions apply to **2022**, not current October 2026 market conditions.

## Engineering delivered

1. \`freight/research/CFS_FORHIRE_NAICS_BUCKETS_20261011.json\`: **60 directly selected A18/A19 Census-format national records**, covering three industry categories × \`DMODE=111\` × ten distance/weight strata × two tables. Preserves raw integer published value and tonnage, \`VAL_F\`/\`TON_F\` and CV flags, actual Census bucket labels, original Census hashes and separate GitHub mirror blob hashes.
2. \`freight/research_cfs_mode_hierarchy.py\`: offline, deterministic source validator and analysis engine; frozen JSON Git blob receipt, source/member/version guards, fixed keys, Census S/Z suppression holds, cross-table totals/CV equality, same-NAICS denominators, Great Circle and weight-marginal warnings, no unsupported LTL billing or recovery calculation. Generates \`cfs_forhire_industry.json\` and \`cfs_forhire_industry.html\`.
3. \`freight/test_research_cfs_mode_hierarchy.py\`: adversarial tests for tampered original/mirror SHA, changed mode, duplicate/missing bucket, suppression CV/placeholder laundering, wrong scope of 4931, prior-market tampering, fictitious LTL market figures, unsafe HTML, source chronology, invalid rounding, and incorrect joint-distribution inferences.
4. Existing Lab 14 negative probes, Control Center and GitHub Research Intelligence workflow extended to run offline, retain the new reports and preserve the existing 14-lab census. The earlier M15 dashboard label is corrected to identify the 4931/484 combined table category.

From repository root under Python 3.11 or later:

\`\`\`bash
PYTHONPATH=. python -m pytest -q freight/test_research_cfs_mode_hierarchy.py
PYTHONPATH=. python -m freight.research_cfs_mode_hierarchy \
  --as-of-date 2026-10-11 --out /tmp/retally-cfs-mode-qa
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control
\`\`\`

### Remaining controls

Real invoice ownership, LTL-only paid invoices, customer consent, governing rate contracts, independently adjudicated billing errors, recovered cash and actual fee collection remain **unverified**. The 18 existing Mission 11 pilot controls have not been completed or bypassed.

**DO NOT MERGE, DEPLOY, CONTACT BUYERS/CARRIERS, IMPORT CUSTOMER DOCUMENTS, MODIFY SCHEDULED TASKS, OR PUBLISH CUSTOMER/REVENUE CLAIMS.**
