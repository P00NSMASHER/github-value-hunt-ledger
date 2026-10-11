# RETALLY Research Lab 14 — Mission 16: For-Hire Mode Evidence, Original Source Replay

**Status:** Draft, research-only; October 11, 2026. Stacked on Mission 15's unmerged branch. Extends existing Lab 14, not a new Lab 16. No customer invoice ingestion, paid datasets, production deployment, carrier contact, financial action, or scheduled task changes.

## The analytical gap

Missions 12–15 analyzed the original U.S. Census 2022 Commodity Flow Survey and verified national **all-mode** shipped-goods figures for manufacturing (NAICS 31–33), wholesale (42) and warehousing/storage (4931). The 2022 industry-specific **for-hire truck** (\`DMODE=111\`) statistics, however, had *not* been independently reproduced from the actual A18 and A19 data rows. Applying the U.S. national for-hire share of goods value (44.80%) to every industry would fabricate mode exposure and is forbidden.

The objective is to create a **deterministic way to replay the exact original source bytes** and, only where each cell survives Census flag and cross-table checks, calculate descriptive for-hire mode shares and selected shipment-distribution fractions.

This mission implements that path without pretending the original ZIP bytes were available to this CI job. Web search and Census documentation were inspected; the Census API presently requires an API key. This run's separate direct source-download attempt failed due the working container's network resolution and the previously connected read-only browser had exhausted credits. **No unverified new for-hire values were invented.**

## Official public source and original fingerprints

- [2022 CF2200A18 — NAICS × mode × shipment distance](https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A18.zip), 93,390 bytes, browser-observed SHA-256 \`a18ce071599457572177dd56f8a6174594d1018da9b9024476c4e9832a357bf5\`, \`CF2200A18.dat\`, 7,312 rows, distance **total=001**.
- [2022 CF2200A19 — NAICS × mode × shipment weight](https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A19.zip), 107,682 bytes, browser-observed SHA-256 \`fe3085d23a3c76704a0d86d9213bb38d3d341b2c228990a5ebf40b6b3f1b661d\`, \`CF2200A19.dat\`, 6,782 rows, weight **total=01**.
- [Census CFS API 2022 variable definitions](https://api.census.gov/data/2022/cfsarea/variables.html) and [Census CFS API guidance](https://www.census.gov/data/developers/data-sets/cfs.html) (API key required for queries).

All source measurements are **goods shipped** (\`VAL\`: USD millions of commodity value; \`TON\`: thousand tons). They are **not carrier freight invoices, LTL spend, cost per ton, cash refunds, eligible contingency fees, addressable market or verified buyer demand**.

## Selection and safeguards

A locally supplied archive is evaluated with the existing Mission 13 hardened ZIP/DAT parser. It must match the original exact pinned **byte length and SHA-256**, file member, required columns and full original row count. It is parsed offline; there is no automatic download.

Accepted unique keys for the requested analysis:
- \`#GEOTYPE=01\`, \`ST=00\`, \`GEO_ID=0100000US\`, \`YEAR=2022\`.
- \`NAICS2017=31-33\`, \`42\`, or \`4931\`, at separate nonoverlapping rows.
- \`DMODE=00\` all-mode denominator and \`DMODE=111\` for-hire truck numerator; **never** use mode 11 truck total or mix parcel/truckload/LTL.
- A18 \`SHIPDIST=001\` total; A19 \`SHIPWT=01\` total. Exclude their total rows when evaluating the nonoverlapping bucket codes 02–10.

The extractor checks **12 direct total rows across both files** (three NAICS × two modes × two independent table dimensions). A18 and A19 numeric values and suppression flags must match at identical source grain. All-mode denominators must agree with the already observed Mission 14 national totals; unsupported for-hire values exceeding all-modes are rejected.

Census flags are never numeric zero:
- \`S\`: estimate unsuitable under Census publication standards; hold numerical inferences.
- \`Z\`: rounds to zero; do not treat as literal exact zero.
- \`VAL_S\` / \`TON_S\` and their \`_F\` flags: a CV unavailable or flagged \`S\` remains unavailable. Even a recorded CV is **not** a valid confidence interval for a ratio without covariance.
- Missing/incompatible strata, duplicates and totals outside the possible Census rounding tolerance result in explicit **HOLD** states, not inferred percent shares.

Two optional descriptive *goods-value* shares are computed **only when every nonoverlapping bucket of a distribution is usable** and the complete bucket sum reconciles with its own for-hire total:
- A18 distance buckets 02, 03, 04 correspond to less than 250 miles.
- A19 shipment-weight buckets 05, 06, 07 correspond to 500–9,999 pounds.

These are dimensions of **observed goods shipment value, not transport prices**. Being in the 500–9,999 lb bucket does **not** independently establish a less-than-truckload carrier movement.

## Implementation

- \`freight/research/CFS_FORHIRE_REPLAY_PLAN_20261011.json\` pins the two original archive identities, byte hashes, mode and NAICS selections, geographic scope, units and four outstanding human/source evidence steps.
- \`freight/research_cfs_forhire.py\` provides **offline, bounded replay and reconciliation**, with original-byte-only scope labels and a no-network readiness report when the original ZIPs have not been supplied.
- \`freight/test_research_cfs_forhire.py\` provides **29 adversarial tests**, creating wholly fictional ZIP/DAT contents for unit testing. Fake ZIPs cannot pass as original Census releases.
- Existing Lab 14 director negative probes, Phase 4 Control Center and GitHub Research Intelligence CI generate \`cfs_forhire_replay.json\` and \`cfs_forhire_replay.html\`. Tests run with no internet or customer source data.

Local commands for a separately obtained and inspected **actual original ZIP pair** (keep bytes outside GitHub):

\`\`\`bash
PYTHONPATH=. python -m pytest -q freight/test_research_cfs_forhire.py

PYTHONPATH=. python -m freight.research_cfs_forhire \
  --a18-zip /path/to/CF2200A18.zip \
  --a19-zip /path/to/CF2200A19.zip \
  --as-of-date 2026-10-11 \
  --out /tmp/retally-forhire-original-source-review

# Without original files, the same CLI creates an honest blocked report:
PYTHONPATH=. python -m freight.research_cfs_forhire \
  --as-of-date 2026-10-11 --out /tmp/retally-forhire-pending
\`\`\`

The offline original-byte replay pathway must never be mistaken for **legal customer permissions, independently validated carrier claims, real paid LTL invoices, verified overcharge rates or recovery revenue**. The Mission 11 pilot's 18 outside approvals remain unverified. No original source files or personal customer data have been committed.

## Next empirical research

Run the extractor against the original byte-identical public A18/A19 ZIP pair. Review flagged sector-specific totals, then decide which bucket compositions are legitimately publishable **as survey statistics**; validate real LTL invoice activity only through a separate approved customer data program. No buyer or business ranking is implied by Census survey goods value.

**DO NOT MERGE, DEPLOY, CONTACT BUYERS/CARRIERS, CHANGE SCHEDULED TASKS, OR PUBLISH UNVERIFIED COMMERCIAL PERFORMANCE.**
