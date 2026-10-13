# RETALLY existing Research Lab 14 — Mission 45
## Transactional money read/write integrity, corrupted-source rollback, and pinned concurrency

**October 13, 2026 · DRAFT / INTERNAL SYNTHETIC ONLY · stacked on Mission 44 PR #438.** No merge, deployment, customer invoice ingestion, provider contact, business registration, production credentials, real cash, scheduled tasks, or external marketing.

### Significant functional defect corrected

M44 hardened persistent SettlementStore's **opening, explicit semantic audit, and report snapshot** against privileged edits to a valid SQLite file. However, *already-open* stores still exposed unguarded financial **realized_cents(), fee_eligible_cents(), claim_residual(), event_residual() and count()** and accepted application operations through the normal private _write() transaction wrapper without revalidating the modified source. Consequently a damaged file could be rejected as an export, yet yield numeric balance data or accept additional new ledger events without independent semantic verification.

M45 closes that discrepancy directly in **freight/settlement_store.py**, not merely in a demonstration report:

1. **Every standard read** now begins one SQLite read transaction, runs the M44 semantic audit on that same buyer/business-unit scope and database revision, and uses the exact same revision for the requested cash/fee/residual/count SELECTs. The central read wrapper replaces nested per-report BEGIN statements; explicit reporting and audit still fail closed, and concurrent newer writes do not silently splice two revisions into a single numeric result.
2. **Every standard write** now runs the same semantic audit immediately after acquiring BEGIN IMMEDIATE and **again after the requested operation, before COMMIT**. Existing typed SQLite/value errors and busy/locked retries are preserved. A damaged source that was edited after object construction cannot accept a new write; a write operation that itself creates inconsistent source data is entirely rolled back, including SQLite DDL/trigger changes staged inside the transaction.
3. **Tenant scope is preserved:** ordinary existing-instance reads and writes audit the authenticated tenant/business-unit scope; reopening an entire persistent SQLite file still reviews *all* tenants. A malicious change to Tenant B must never leak identifiers into Tenant A reports. Local semantic agreement remains distinct from authentic buyer/carrier/bank authority.
4. **No new lab:** new tests and source gates run inside original Research Lab 14, existing 14-lab integration and M39 receipt acceptance, without altering any of the original historical finding statuses.

### Eight real source mutations × six operational paths

Existing M44 laboratory cases are **reused**, not simulated anew with looser fake checks:

- Credit reduced below the already-allocated amount.
- Carrier return greater than signed original credit.
- Allocation's eligible-fee metadata changed after approval.
- Credit payer changed after claim binding.
- Return relinked to a different provider credit.
- Reversal exceeds its original allocation.
- Claim temporarily exceeds its signed amount and later nets back into range.
- Claim marked fee-disqualified without updating old fee-eligible rows.

Each case first validates five legitimate fictional source read APIs with **$5 retained recovery / $5 fee-eligible allocation**. Each corruption is then applied only to a *new disposable SQLite file* through intentionally test-only direct SQL, and the **same already-open store** must reject all five read paths and a new write attempt with the precise M44 source error code. Hence M45 requires **40 typed read denials and 8 typed write denials (48 total)**. Every rejected action must leave the source file unmodified beyond the deliberate test-only corruption.

### Independent positive and concurrency tests

- A correctly signed fictional new receipt and an exact replay remain permitted and idempotent.
- A test-only write stages a fee metadata edit and trigger drop *after* M45 preflight; post-write semantic verification must reject it and roll back **both** the changed rows and the dropped trigger. Similarly, an invalid provider-return amount cannot commit.
- One pinned read revision is tested with a legitimate **external writer committing between the audit and the requested count**. The first read sees the originally audited table snapshot; the next new read sees the committed new event. No false transaction-mixed financial counters.
- An already-open Tenant A can read its own clean data even if Tenant B's source rows are corrupted, while reopened whole-file review remains blocked on Tenant B. No customer ID or invoice/source bytes are emitted in M45 report artifacts.
- A cross-branch independent differential uses the **pinned exact M44 source** (commit d824939dfbe9fb3ed87927809af1b4c13898fde3), not a moving HEAD^, to show that an already-open M44 store could return monetary values and append an unrelated event from all eight damaged files whereas the new M45 runtime rejects each.
- Broad regression suite: settlement store, real local financial proof, original 14 research labs, M39–M44, persistent pilot report, backup/restore and all prior source-publication/human approval boundaries. PR/manual-only; derived test artifacts retained for 14 days.

### Reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_atomic_financial_m45.py freight/test_lab_persistent_semantic_m44.py freight/test_settlement_store.py freight/test_backup_restore.py
    PYTHONPATH=. python -m freight.lab_atomic_financial_m45 --as-of-date 2026-10-13 --out /tmp/retally-m45
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m45-control

### Hard limits

M45 guarantees a bounded **local structural/reconciliation** check for current-version SQLite operations, not protection from an operator who can rewrite both source file and independently controlled credentials/code. Semantic consistency cannot establish real invoice error rates, carrier authority, funds received, privacy/legal permission, security certification or actual customer validation. Full-load performance has **not** been benchmarked: customer-scale deployment requires resource sizing and concurrency soak tests.

**All original 26 RecoveryOS historical defects remain OPEN_UNVERIFIED, with 0 automatically closed. All 18 real human first-customer approval gates remain unmet. Zero real cash or external recovery/market-size publication is authorized.** No production writes or real customer activity was performed by M45.
