# RETALLY Research Lab 14 — Mission 17: Original Census Archive Replay

**Date:** October 11, 2026 · **DRAFT / INTERNAL EVIDENCE ONLY** · **Stacked on Mission 16 PR #385**.

## Research question

Can the 60 Census-format selected observations previously copied from a public GitHub mirror be reproduced exactly from publisher-hosted **2022 Census Commodity Flow Survey** A18 and A19 original archive bytes, including quality flags and coefficients of variation?

This is a source-integrity question, **not** LTL revenue market sizing, freight billing error prevalence, customer recovery validation or marketing approval.

Official publisher pages:
- [Census original downloadable ZIP directory](https://www2.census.gov/programs-surveys/cfs/data/2022/)
- [Census 2022 Final CFS tables](https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html)
- [Official A18 definitions and NAICS 484-with-4931 footnote](https://data.census.gov/table/CFSAREA2022.CF2200A18)
- [Official A19 table](https://data.census.gov/table/CFSAREA2022.CF2200A19)

## What the verifier does — and does not do

1. Reads only `CF2200A18.zip` and `CF2200A19.zip`. The CLI defaults to no network and requires two explicit local files. The optional `--fetch-official` mode allows exactly two HTTPS GETs to fixed government URLs and rejects redirects, oversized downloads, wrong archive SHA-256s and sizes.
2. Rejects unsafe ZIP members, encrypted or oversized archives, invalid data headers, mismatched whole-file row counts and incorrect member byte lengths using existing Lab 14 archive-verifier protections.
3. Requires **exact prior-browser-observed archive SHA-256 values**, then independently compares 60 records by 2022 national `NAICS2017 × DMODE=111 × SHIPDIST/SHIPWT` keys. Checks values, weights, Census quality/suppression flags, per-cell CVs and stratum/mode labels. Duplicate/missing source rows or one differing cell fail closed.
4. Emits `cfs_primary_replay.json` and `cfs_primary_replay.html`, with an evidence receipt checksum, source ZIP and extracted member SHA-256, counts and clearly bounded claims. It does not publish raw source ZIPs in the repository or action artifacts.
5. A **separate, unscheduled PR workflow** runs offline adversarial tests before trying exact official downloads. A clean unit-test job is *not* proof of official archive access. Only a successful `verify-original-census-zips` job with the generated source receipt establishes selected row replay in that CI run. A failed or missing job means **NOT VERIFIED**, not an implied success.

Original archive hashes are carried forward from earlier browser observation; they are not a government digital signature. Matching them plus fixed HTTPS acquisition and selected-row checks does **not** establish that the **entire** GitHub mirror is byte-identical, that the Census statistical samples are independent, or that the Census 2022 survey measures contemporary 2026 markets.

**Source population correction:** Census A18 footnote CF1 groups truck transportation NAICS **484** with reported **4931**. Captive warehouse auxiliaries are in-scope; this reported grouping is not a pure public warehousing segment.

## Independent local reproduction

From repository root under Python 3.11+ (only after legitimately obtaining the two original official ZIPs):

```bash
PYTHONPATH=. python -m unittest freight.test_research_cfs_primary_replay -v

PYTHONPATH=. python -m freight.research_cfs_primary_replay \
  --from-local \
  --zip-a18 /absolute/path/CF2200A18.zip \
  --zip-a19 /absolute/path/CF2200A19.zip \
  --as-of-date 2026-10-11 \
  --out /tmp/retally-cfs-replay
```

The explicit online mode used only in the isolated PR action (not background or a scheduled task):

```bash
PYTHONPATH=. python -m freight.research_cfs_primary_replay \
  --fetch-official --as-of-date 2026-10-11 \
  --out /tmp/retally-cfs-replay
```

**No physical invoices, customer/carrier records or contracts are accepted by this program.**

## Decision policy

- **PASS:** Both original ZIP hashes/sizes and all 60 selected source cells match. Mark *only* those selected published CFS figures as reproduced against the source ZIPs in the specific run.
- **BLOCKED:** Network access, HTTP or government-host retrieval failure. No original source replay claim. Preserve M16's third-party-mirror qualification; retry only on explicit CI workflow execution.
- **FAIL:** Any missing table, unexpectedly changed byte hash/size, member/header mismatch, duplicated source row, altered suppressed cell or CV. Do not promote new results, investigate source version/lineage and keep original internal receipt as unverified.
- **NEVER AUTHORIZED BY PASS:** LTL-only market size or 2026 freight spend estimates; carrier-rate validity; customer demand; recovery percentage or dollars; client eligibility; automatic prospect outreach; billing claims; commercial publication.

This mission adds no new lab, no customer-data import, no production deployment, no schedule and no merge. It does not modify M16's frozen evidence or silently replace its prior mirror provenance report. The M17 CI artifact is deliberately separate and ephemeral.
