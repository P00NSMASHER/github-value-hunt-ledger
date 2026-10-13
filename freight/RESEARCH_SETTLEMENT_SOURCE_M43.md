# RETALLY Research Lab 14 — Mission 43
## Settlement chronology, provenance and fee-integrity hardening

**October 13, 2026 · DRAFT / INTERNAL ONLY · stacked on M42 PR #436.** No production release, customer access, bank or carrier communication, cron, business registration, or marketing publication.

### Source-level corrections

The independent read-only verifier in freight/lab_assurance.py may consume imported settlement SQLite without SettlementStore constraints. M42 rejected repeated allocation, counter and reversal row IDs. A malicious import could still contain distinct IDs for the same economic edge, ill-formed source hashes, noncanonical fee eligibility or temporally impossible cash balances. The former verifier checked final NET claim balances but not every intermediary allocation/reversal transition.

M43 makes the verifier fail closed before recognizing financial results:

- **Monetary chronology:** Reject reversal records dated before their allocation. Replay all positive allocation and negative reversal movements in UTC order. Reject intermediate negative balances or values above the signed original claim, even if a subsequent reversal brings the final net back within the cap. Same-time uncertainty is treated conservatively (positive movements first).
- **Economic edge identity:** Refuse a repeated (claim_id,event_id) allocation or repeated (counter_id,allocation_id) reversal when local row IDs differ. Preserve original receipt overcapacity denial for repeated events that also exceed their separately signed source amount.
- **Provenance uniqueness:** Enforce scoped claim, credit and counter source-hash uniqueness, aligned with SettlementStore, and 64-character lowercase SHA-256 shape when reading unconstrained imports. A hash is not publisher authentication.
- **Fee semantics:** Mode must be AUTO or REVIEW; eligible cents equal allocated cents for a non-disqualified claim and zero for an expressly disqualified claim. The frozen fee_disqualified flag must be a typed SQLite integer 0 or 1. Return amounts must be positive exact integer cents.

### Twelve direct current-verifier synthetic attacks

| Scenario | Exact rejection |
| --- | --- |
| Unknown allocation mode | INVALID_ALLOCATION_MODE |
| Forged allocation fee eligibility | ALLOCATION_FEE_ELIGIBILITY_MISMATCH |
| Null / untyped fee-disqualification flag | INVALID_FEE_DISQUALIFICATION_FLAG |
| Reversal before source allocation | REVERSAL_PREDATES_ALLOCATION |
| Peak claim balance 1300 against signed 1000, later returns to 500 | TRANSIENT_CLAIM_CAPACITY_EXCEEDED |
| Same claim + credit split 200+200 under different allocation IDs | DUPLICATE_CLAIM_EVENT_ALLOCATION |
| Same return + allocation split 499+1 under different reversal IDs | DUPLICATE_COUNTER_ALLOCATION_REVERSAL |
| Two claim records sharing source hash | DUPLICATE_CLAIM_SOURCE |
| Two provider credits sharing source hash | DUPLICATE_CREDIT_SOURCE |
| Two returns sharing source hash | DUPLICATE_RETURN_SOURCE |
| Fake-signed negative return with no allocation | INVALID_COUNTER_CENTS |
| Fake-signed invalid provenance SHA-256 | INVALID_SOURCE_HASH |

Each negative scenario has a passing known-good fictional $5 recovered / $1 earned-fee control, and mutates only a new disposable SQLite file. A pass requires precisely the expected typed denial. This is NOT bank/carrier evidence. Positive controls also test correctly disqualified no-fee claims and legitimate later replacement receipts after reversals, which must not be denied solely for exceeding the lifetime gross allocation cap.

### Changes

- freight/lab_assurance.py — genuine source-verifier fee, provenance and timeline safeguards.
- freight/lab_settlement_source_m43.py — 12 fixed source-level adversarial fixtures with internal JSON/HTML output.
- freight/test_lab_settlement_source_m43.py — exact denial, false acceptance, wrong-denial, positive controls, timestamp and no-write-on-invalid-input tests.
- freight/lab_phase4_director.py — existing Lab 14 now depends on every positive/negative M43 result.
- freight/lab_cross_lab_assurance_m39.py and its test — require M43 exact-count and proof receipt bounds.
- freight/lab_phase4_control_center.py — source-provenance and monetary-timeline panel and metadata-only report.
- .github/workflows/retally-settlement-source-m43.yml — PR/manual-only exact-head CI, inherited tests, independent old/new source behavioral challenge and no cron/deploy.

### Reproduce locally

    PYTHONPATH=. python -m pytest -q freight/test_lab_settlement_source_m43.py freight/test_lab_assurance.py freight/test_lab_phase4_director.py
    PYTHONPATH=. python -m freight.lab_settlement_source_m43 --as-of-date 2026-10-13 --out /tmp/retally-m43
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m43-control

**All 26 historically indexed RecoveryOS defects remain OPEN_UNVERIFIED, and all 18 separate human first-customer pilot approvals remain unmet.** M43 validates current-source behavior only, not archived vulnerable source revisions, real signed buyer/carrier/bank funds, external publication rights or customer invoice error rates. A SHA or passing CI check is not third-party attestation.
