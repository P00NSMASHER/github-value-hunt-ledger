# RETALLY Existing Research Lab 14 — Mission 13: Official Census Source Bytes

**Status:** research-only, October 11, 2026, stacked on unmerged Mission 12. No 15th lab, automatic web crawler, customer data, bank access, business deployment, scheduled task changes, carrier contact, claims or market performance publication.

## What materially changed

Mission 12 reconciled six *published, manually transcribed* table excerpts. Mission 13 obtained the **original public Census CF2200A01 ZIP** through a **read-only cloud browser** and inspected the contained raw bytes. That source inspection found that the archive contains **pipe-delimited \`CF2200A01.dat\`**, not a CSV file, as well as \`CF2200A01_FIELDS.txt\` and \`CF2200A01_README.txt\`.

This branch contains a bounded browser-observed source-receipt JSON, not the original ZIP contents. It also implements a separate offline, hostile-input-resistant ZIP/DAT/CSV parser that can independently match those six cells when the same ZIP is supplied locally. Routine GitHub CI does **not** fetch Census pages and does **not** claim to have performed that local replay.

### Source details

- **Original**: https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A01.zip
- **Government data listing**: https://www2.census.gov/programs-surveys/cfs/data/2022/
- **2022 A01 table and notes**: https://data.census.gov/table/CFSAREA2022.CF2200A01
- **2025 Census press release**: https://www.census.gov/newsroom/press-releases/2025/cfs-shipments-of-goods.html
- **Browser observed source size**: **167,855 bytes**, shown as 164K in the government directory.
- **Browser-reported SHA-256 of downloaded ZIP**: \`15d90f1e64c5b3fb86c5f619a32350f9c60256cc3eaaa48838115fc70f7d6499\`.
- **Recorded source schema**: \`#GEOTYPE|ST|GEO_ID|GEO_LABEL|GEO_ID_F|DMODE|DMODE_LABEL|DMODE_F|YEAR|VAL|VAL_F|...|TON|TON_F|...\`
- **Measurements**: \`VAL\` denotes shipped-goods value in **USD millions**; \`TON\` denotes shipment weight in **thousands of tons**. Neither represents carrier freight invoices.

The source was downloaded and inspected in a read-only remote browser during this mission. **The original bytes were not materialized to our local container, not copied to GitHub, and not fetched within CI.** The observed SHA is a useful reproducible fingerprint but not a digitally signed publisher attestation.

### Primary-source row verification

| GEOTYPE / GEO_ID / DMODE (2022) | Value, $ million of goods | Tonnage, 1,000 tons |
| --- | ---: | ---: |
| 01 / 0100000US / 00 (United States, all modes) | 17,996,782 | 12,169,793 |
| 01 / 0100000US / 11 (U.S., truck incl. pickup) | 13,222,965 | 8,293,501 |
| 01 / 0100000US / 111 (for-hire) | 8,062,541 | 3,909,476 |
| 01 / 0100000US / 112 (company-owned) | 4,141,550 | 2,994,372 |
| 01 / 0100000US / 113 (customer pick-up) | 1,018,874 | 1,389,653 |
| 11 / 0200000US3 / 00 (South region, all modes) | 6,689,859 | 4,919,551 |

All six extracted \`VAL_F\` and \`TON_F\` fields were blank (not suppressed). \`DMODE_F=n\` documents the revised 2022 truck definition; \`DMODE_F=o\` identifies newly tabulated customer pick-up. The 2022 for-hire, company-owned and customer-pickup rows have \`VALPCHG_F=N\` and \`TONPCHG_F=N\`, indicating the change-from-2017 figures are unavailable/non-comparable. **The numeric zero placeholders beside \`N\` must never be interpreted as a measured 0% change.**

This matters for market claims: if RETALLY treated the new pickup bucket or an \`N\`-flagged 2017 comparison as observed data, its freight-mode addressable-market calculations could be materially wrong.

### South discrepancy reproduced from raw source

The original A01 \`CF2200A01.dat\` row for South shows \`TON=4,919,551\`, or **4.919551 billion tons**. U.S. \`TON=12,169,793\` gives **40.4243%**, consistent with the press release’s **40.4%**.

However, the [Census press release](https://www.census.gov/newsroom/press-releases/2025/cfs-shipments-of-goods.html) describes South as **1.9 billion tons (40.4%)**. The raw detailed table supports the percentage and **does not support** the 1.9-billion-ton figure. The press release's $6.7T South shipment value agrees with the original \`VAL=6,689,859\` ($ million) at rounded precision.

**Status remains:** \`UNRESOLVED_FIRST_PARTY_PUBLICATION_CONTRADICTION\`. The original tabulated data corroborates the discrepancy; it does **not** authorize RETALLY to silently edit Census press-release prose or claim an official corrigendum.

## Code and integrity safeguards

- \`freight/research/CFS_A01_REMOTE_SOURCE_RECEIPT_20261011.json\`: browser-observed original archive fingerprint, actual pipe-DAT member names, Census geographies and mode codes, six source records and exact footnote/comparability flags, with limits clearly stated.
- \`freight/research/CFS_A01_LOCAL_REPLAY_MAPPING_20261011.json\`: source field names \`GEO_ID/DMODE/YEAR/VAL/TON\`, source footnote and comparability columns, and six frozen row identity selectors.
- \`freight/research_cfs_archive_verifier.py\`: offline local ZIP introspection and real-format DAT parser. Restricts archive members, decompression, duplicate names and columns, encoding, row counts, absolute and traversal paths, encrypted entries, symlinks and ratio bombs. Checks original archive size and SHA against the independently observed browser receipt before a non-synthetic local verification. Never contacts the network.
- \`freight/test_research_cfs_archive_verifier.py\`: synthetic ZIP/DAT hostile-input regression tests and independent source-receipt consistency checks. A synthetic archive with the correct six values cannot impersonate the official ZIP because its binary SHA does not match the source fingerprint.
- Existing Lab 14 director, Phase 4 Control Center, and Research Intelligence CI export an explicit **browser-observed / CI offline-replay-pending** status. Other historical labs and findings remain untouched.

### Reproducible local operator commands

If a reviewed operator independently obtains the official ZIP, keep it outside GitHub and run:

\`\`\`bash
PYTHONPATH=. python -m freight.research_cfs_archive_verifier \
  --zip /path/to/CF2200A01.zip --inspect \
  --as-of-date 2026-10-11 --out /tmp/cfs-a01-inspection

PYTHONPATH=. python -m freight.research_cfs_archive_verifier \
  --zip /path/to/CF2200A01.zip \
  --mapping freight/research/CFS_A01_LOCAL_REPLAY_MAPPING_20261011.json \
  --verify --as-of-date 2026-10-11 --out /tmp/cfs-a01-verified

PYTHONPATH=. python -m pytest -q freight/test_research_cfs_archive_verifier.py
\`\`\`

If original bytes, SHA, ZIP structure, column names, selected row IDs, flags or any integer estimate differ from the reviewed receipt, verification fails closed for additional human review. The parser does not change the CFS dataset, replace a signed source, resolve the press release editorial dispute, or grant data processing/marketing rights.

### The commercial interpretation boundary

The $8.06T for-hire figure remains **value of goods transported**, not paid freight spend, LTL-only billings, audit error rates, buyer demand, net recoverable cash, contracted contingency fee, or RETALLY revenue. No actual freight invoices were received or analyzed. The 18 pilot human evidence/authorization requirements remain unverified. **No release or customer-facing use is authorized by this work.**

### Follow-up research

The official directory also lists \`CF2200A18.zip\` and \`CF2200A19.zip\` for NAICS × mode × distance and NAICS × mode × shipment weight. A future mission can similarly inspect the originals and incorporate sampling error/suppression metadata before developing vertical research hypotheses. Public survey statistics remain distinct from customer-authorized invoice truth.

**DO NOT MERGE OR DEPLOY WITHOUT REVIEW. DO NOT TOUCH EXISTING SCHEDULED TASKS.**
