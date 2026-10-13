# RETALLY Research Lab 14 — Mission 49: Two-ledger backup stability and completion integrity

**October 13, 2026 · DRAFT / INTERNAL SYNTHETIC ONLY · stacked on M48 PR #447.** No merge, production deployment, customers, bank/carrier access, financial transactions, business formation or new scheduled tasks.

## Actual original-code vulnerability

M44–48 now protect persistent **settlement** and **audit** source files against read/write corruption, weakened triggers, swapped databases, and event-chain tampering. Yet the shared backup/restore drill in freight/backup_restore.py copied the two independent SQLite files **sequentially**, then reused a source summary captured before the copy. A writer could update the audit or settlement ledger between the two copies, leaving a mixed-history recovery bundle with an unreliable single “proof of restored operations.” If restore verification or file copying failed, the drill could leave a plausible-looking *partial* set of final backup files in the output directory. Earlier backup code would also unlink/recreate existing target SQLite paths, risking an old verified backup.

Mission 49 implements a real transactional-publication **best-effort stability gate**. It does **NOT** pretend two independent SQLite files have a shared atomic commit clock. The artifact remains strictly offline/local evidence.

### Functional changes

- **freight/backup_restore.py**
  - An original audit summary (chain verification, sequence count and chain head) and all original settlement totals are taken from independently pinned SQLite read revisions.
  - A closed allowlist of actual audit and settlement tables is fingerprinted for **ALL tenants**, not just the currently logged-in buyer/business unit. Each per-file hash is computed under one SQLite read transaction, using sorted canonical rows rather than unreliable raw WAL/page bytes.
  - The source audit/settlement pair is fingerprinted before copying; the **backups, their independent restores, and the original sources again after both restores** must all match the original all-tenant logical contents and scoped operational semantics. A concurrent mutation anywhere in this observable window refuses the entire attempt.
  - SQLite backup sources are opened **mode=ro**, tied to direct-file device/inode identity, so missing originals cannot be silently recreated by ordinary sqlite3.connect.
  - The entire candidate bundle lives first in a **private temporary staging directory** under the destination's parent. Existing final backup files are never unlinked/overwritten. All four SQLite artifacts are published by exclusive create (hard link), with a digest-bound local **capture.complete.json published LAST**. The completion marker is required for verification; a partial directory without the marker is never accepted.
  - A failed publication removes **only files created by that attempt**; an unrelated preexisting customer backup stays byte-identical. Missing/bad marker, altered saved SQLite, forged length-only proof and falsely claimed externally attested revenue all fail local verification.
  - A logically complete but self-rehashed local manifest is still NOT independent third-party provenance. A process crash during publish can leave partial files without a completion marker, which must be treated as incomplete, not an accepted bundle.
- **freight/audit_store.py** — semantic_summary now gathers verified original chain, count and head from **one pinned SQLite read transaction**, instead of separate verify()/count()/head() operations vulnerable to a concurrent append between reads.
- **freight/lab_dual_ledger_backup_m49.py** — nine distinct test-only attacks on actual current AuditStore + SettlementStore backup code, each with a passing complete fictional two-ledger positive first and then a precise fail-closed negative.
- **freight/test_lab_dual_ledger_backup_m49.py** — real concurrent audit and settlement appends between copies, other-tenant data changing after a snapshot, preexisting-output protections, source deletion, partial hard-link publish failure, corrupt manifest/file proof, malicious output symlink and scope input, plus fail-before-file creation.
- M49 results are integrated into **existing Research Lab 14**, the M39 structural cross-lab verifier, and the internal Control Center with separate JSON/HTML evidence. No new lab is created.
- A dedicated PR/manual-only GitHub Actions workflow runs the original 14-lab settlement and audit suites, preserves human first-customer evidence gates, and performs a separate differential experiment using the **exact pre-M49 M48 backup_restore.py** to reproduce mixed or partial source acceptance while verifying the new code fails safely. No cron, deployment, live secrets, or external data access.

### Nine isolated adversarial cases

| Synthetic attack | Expected denial |
| --- | --- |
| Audit ledger appended after the audit copy, before settlement copy | M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE |
| Settlement ledger appended immediately after its copy | M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE |
| An unrelated tenant's audit events change during capture | M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE |
| An unrelated tenant's settlement events change during capture | M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE |
| Existing output backup file would be overwritten | M49_EXISTING_BACKUP_ARTIFACT_MUST_NOT_BE_OVERWRITTEN |
| Independent SQLite restore raises before completion | M49_TEST_ONLY_RESTORE_INTERRUPTED |
| Third exclusive final artifact publication fails after two copies | M49_TEST_ONLY_BUNDLE_PUBLICATION_INTERRUPTED |
| Audit main file deleted before SQLite backup opens source | M47_SQLITE_SOURCE_FILE_MISSING |
| Settlement main file deleted before SQLite backup opens source | M47_SQLITE_SOURCE_FILE_MISSING |

**Positive controls:** nine independent fully verified fictional backup bundles with four real SQLite files, matching source/restore financial semantics, and a final manifest. All nine negative cases must fail with their *exact* bounded reason and leave **zero misleading completed backup bundles**. Scenarios testing other-tenant changes must fail even though the requesting tenant's scoped money summary remains unchanged.

### Operational limitations and first-customer readiness

Two independent SQLite WAL databases **do not have one distributed ACID snapshot**. A malicious writer capable of changing and reversing all source content within the observational window could bypass pre/post comparison. Treat this as a conservative stable-window check plus completed-bundle marker, NOT a guarantee of perfect cross-store synchronization or real disaster-recovery readiness.

No underlying original carrier/buyer invoice source, bank payment, externally immutable audit head, or third-party timestamp is authenticated. **All 26 original historical RecoveryOS defects remain OPEN_UNVERIFIED**, and **all 18 separately required human first-customer approval gates remain unmet**. There is **zero real recovered customer cash**, no externally publishable win-rate/TAM data, no customer contact, no formation/registration, no scheduled tasks and no production deployment.

### Reproduce

    PYTHONPATH=. python -m pytest -q freight/test_lab_dual_ledger_backup_m49.py freight/test_backup_restore.py freight/test_lab_audit_trust_boundary_m48.py freight/test_settlement_report.py
    PYTHONPATH=. python -m freight.lab_dual_ledger_backup_m49 --as-of-date 2026-10-13 --out /tmp/retally-m49
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m49-control

A completed bundle may be locally reverified via freight.backup_restore.verify_backup_bundle; a directory containing only SQLite files without the final manifest is **never an approved recovery bundle**.

**DRAFT / UNMERGED / NO LIVE DEPLOYMENT.**
