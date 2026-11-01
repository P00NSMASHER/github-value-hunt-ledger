# Freight Recovery Laboratories 11–14: synthetic engineering release

**Status:** `PASS_SYNTHETIC_ONLY` (2026-10-07). Product-owner release review remains required.

This is a reproducible offline workbench built from an existing frozen *fictional* million-invoice freight fixture, not an authorized real customer population. Full synthetic artifacts are separately downloadable and deliberately not checked into the public GitHub repo.

## Four independent scenario engines

| Number | Specialty | Synthetic cases | Recorded events |
|---|---|---:|---:|
| 11 | Reliability/failover/idempotent message handling | 1,000,000 | 5,542,014 |
| 12 | Fraud/evidence/financial-control gating | 1,000,000 | 4,011,424 |
| 13 | Counterfactual freight cost savings | 1,000,000 | 5,000,000 |
| 14 | Procurement/competitive-evidence requirements | 1,000,000 | 5,000,000 |
| **Total** | | **4,000,000** | **19,553,438** |

Each lab covers 36 deliberately designed scenario families, all six freight modes, and 648 family/mode/synthetic-truth combinations. The generator is resumable and deterministic.

## Independently executed checks

- Independent verifier (not importing the case generator): **4,000,000** fictional cases / **19,553,438** events, zero observed structural/business-rule mismatches.
- Original frozen fictional source SHA256: `7c670a91a1a411480b35d054b821f483744267b9c07acda9fe974d910888ed81`.
- Full synthetic manifest SHA256: `18fec04fe52ce5ab9b0840a1d21ef20494f1d10a61781941b8bfede9fe5bf70e`.
- Compressed data shards checked with SHA256: **160/160**.
- Rehashed falsified synthetic money/savings/claim events rejected: **100,000 / 100,000**. These are test mutations, not real fraud detections.
- Offline Python regression suite: **169/169 passing**, zero skips with the frozen source installed. The portable toolkit transparently skips the one full-source test if the optional source download is missing.
- Standalone offline control room: desktop/mobile headless Chromium interactions passed; no runtime JS errors or external requests.
- Read-only localhost SQLite search: **4,000,000** rows, database integrity check passed. An index on lab/decision/index fixed the identified slow query. Entire database is intentionally not published as a huge blob, because the code can regenerate it.
- Independent release checks: **20/20 passed**, recorded in `reports/RELEASE_GATE.json` inside the separate portable toolkit.
- Packaging: portable toolkit, frozen fictional source ZIP and 16 small archive parts (4 per lab). Every ZIP CRC and SHA256 was checked; cross-platform installer rejects path traversal, symlink entries and ZIP hash mismatches. Manifest `DOWNLOAD_MANIFEST.json` is delivered with the downloads.

## Product-code evidence in this PR

`freight/labs11_14.py` implements the synthetic engine. `freight/test_labs11_14.py` enumerates 144 scenario families. `freight/test_labs11_14_actual_domain.py` executes pre-existing RecoveryOS Python objects (`AuditStore`, `PaymentOrchestrator`, the frozen `accuracy_benchmark`, and `competitive_matrix`) on fictional inputs.

The dedicated GitHub workflow is read-only, pull-request/dispatch-only, and pins third-party actions to immutable commit hashes. Existing commercial-contract, release and public-site checks are unchanged and were green at the previous exact head. Do not interpret this as a deployed RecoveryOS end-to-end test.

## Recorded model-only amounts: not revenue

- Lab 11: 611,409 simulated exactly-one successful commits out of a designed heterogeneous workload. **No hosted p95 latency or cloud SLO measured.**
- Lab 12: 860,871 scripted fraud-review holds. **No observed third-party fraud catch rate, bank transfer or chargeback.**
- Lab 13: $58,556,630.13 summed *artificial* potential net savings over 1M hypothetical tactic evaluations. This is **NOT** a forecast, realized customer savings, recoverable overpayment or merchant revenue. **Real savings verified: $0.**
- Lab 14: 805,000 synthetic unsupported-or-external-proof-needed buyer requirements. Competitor evidence is dated vendor-public information; no independent competitor testing or verified wins.

## Not tested or proved

No real buyer authorization, customer evidence, live app load, independent security certification, pen test, multi-tenant cloud isolation, actual claims/cash, actual savings, named ERP integrations, or real market demand. A simulated 100% integrity/rejection rate has no basis for production reliability/safety claims. The freight source and generated identities are all fictional.

**Governance:** Maintain PR draft. Do not deploy, merge, email contacts, contact carriers, purchase services, send funds or release confidential customer data. No scheduled tasks were modified.
