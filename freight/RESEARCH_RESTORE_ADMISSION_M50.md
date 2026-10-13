# RETALLY Research Lab 14 — Mission 50: Read-only published recovery admission

**October 13, 2026 · DRAFT / INTERNAL SYNTHETIC ONLY · stacked on M49 PR #448.**
No merge, deployment, new cron tasks, business registration, customer communication, carrier/bank access, actual cash movement or public empirical claims.

## High-impact defect in the original restore verification boundary

Mission 49 prevented racing source snapshots and incomplete dual-ledger bundle publication by staging the four original/restore SQLite images, checking original source hashes and stamping a final local completion marker. The public-facing verification entrypoint, however, primarily checked **the four raw file SHA values against a separately supplied result and a self-rehashable JSON marker**. It did NOT independently open the actual published file bytes and confirm that the files still contained the approved audit schema and valid hash history, the approved settlement ledger and monetary relationships, the same **all-tenant source generations** as the completion marker, and the specific buyer/business-unit money and chain evidence that the result purported to certify.

An actor with file-level write access could alter the audit chain, remove an append-only trigger, corrupt original credit payer identities or replace a valid restored source; then recompute the local (unkeyed) SHA fields, result proof and completion marker. The predecessor M49 check would still accept these **locally self-consistent receipts**, despite the underlying source records being invalid or belonging to another version or scope.

M50 extends **the actual M49 verify_backup_bundle entrypoint** to inspect the published data. It does NOT claim that local hashes become independent cryptographic authentication or that any real customer payment has been validated.

### Source-level changes

- **freight/restore_admission_m50.py:** read-only SQLite recovery candidate inspector invoked by verify_backup_bundle after the existing SHA/marker gates, preserving previous typed errors and public result type. It reads every original backup and restored image through SQLite URI **mode=ro** and PRAGMA query_only, with one transaction per file.
- For each image it performs SQLite integrity_check, foreign_key_check, and the actual **M48 independent AuditStore schema/hash-chain verifier** or **M44–M46 independent settlement monetary/schema verifier**, explicitly covering **all tenants**, not only the requested scope.
- From the same pinned read transaction, it computes a canonical all-tenant logical content digest for each SQLite source. The two backups and the two restores must ALL equal the original frozen pair in the completion marker. This catches a valid but **wrong-generation restored database** or an out-of-scope ledger addition even when its raw SHA is correctly rebound.
- It reconstructs the existing M49 **scope-specific semantic result** from the actual recovered audit and settlement rows: chain sequence/count/head; source invoice/credit/allocation/reversal tables; real-valued integer cents only; realized money and fee eligible totals; buyer/business-unit identity. Both restored and original scoped summary digests must match the supplied output and each other.
- The completion marker must be a real file (not a symlink), state the **same semantic and byte hashes** as the typed result rather than only a matching proof_hash, and preserve correct labels that the files are **not a single atomic dual-SQLite transaction** and **not human-authorized customer banking evidence**.
- No SQLite data or original invoice bytes are published in reports. During validation, all four source database byte hashes are checked before and after the read-only scans to catch incidental changes. This is a bounded local check, not a hardened hostile-filesystem race-proof API or a third-party trusted anchor.

### Thirteen independent negative tests (all receipts locally recalculated)

| Deliberately invalid published source | M50 denial |
| --- | --- |
| Audit backup missing immutable trigger | SQLITE_SOURCE_OR_SEMANTICS_INVALID |
| Audit backup event altered but original DDL restored | SQLITE_SOURCE_OR_SEMANTICS_INVALID |
| Settlement backup missing funding-capacity trigger | SQLITE_SOURCE_OR_SEMANTICS_INVALID |
| Settlement backup payer altered but original trigger restored | SQLITE_SOURCE_OR_SEMANTICS_INVALID |
| Later valid audit event added only to the backed-up source | BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH |
| Later valid audit event added only to the restored audit image | RESTORE_ALL_TENANT_SOURCE_GENERATION_MISMATCH |
| Later valid provider credit added only to the backed-up settlement file | BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH |
| Later valid provider credit added only to the restored settlement image | RESTORE_ALL_TENANT_SOURCE_GENERATION_MISMATCH |
| Manifest’s source semantic hash no longer matches supplied result | MANIFEST_SOURCE_RECEIPT_FIELDS_NOT_BOUND |
| Manifest falsely claims human first-customer approvals | FALSE_RESTORE_PROVENANCE_OR_HUMAN_APPROVAL |
| Manifest recomputed with false original all-tenant logical SHA | BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH |
| Report rebound to different buyer/business-unit scope | SCOPED_AUDIT_OR_SETTLEMENT_RECEIPT_MISMATCH |
| Completion marker replaced by symlink to a valid-looking marker | UNTRUSTED_BUNDLE_OR_COMPLETION_MARKER_SYMLINK |

Each attack starts with a completely accepted fictional M49 dual-SQLite backup, reopens and changes **the actual published files or marker**, and then recomputes all mutable local output file SHA, report proof_hash and completion SHA. Its last check requires that the predecessor's *same shallow hash conditions* would still pass; the hardened M50 verifier must reject the source for its exact new reason **without modifying any database bytes**.

The full independent GitHub CI additionally loads **the original pinned pre-M50 M49 verification code** and proves that each invalid (but locally rehashed) bundle was accepted by the actual predecessor before the corrected M50 source denied it.

### Existing research integration and limits

- Existing Lab 14 and independent M39 cross-lab acceptance now require 13/13 known-good synthetic bundles and 13/13 exact corrupted-restoration denials. No fifteenth lab created.
- The internal Control Center gets independent JSON/HTML derived metadata. CI runs the inherited audit/settlement schemas, previous M39–M49 negative controls, actual backups and all original 14 labs; PR/manual-only workflow, no cron and no hosted deployment.
- A malicious operator who can alter **all four backups, marker, scoped result, code and source history coherently** can still manufacture an internally consistent new history; M50 has no externally anchored log or independent bank signature. Two SQLite database files remain separately versioned with no shared ACID commit and customer-scale performance is not benchmarked.

**All 26 original historical RecoveryOS findings remain OPEN_UNVERIFIED; all 18 independent human first-customer approval gates unmet; no real bank/carrier/customer funds or actual recovery income shown.** External recovery rate, TAM, ROI and real-customer publication claims remain disallowed.

### Local reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_recovery_admission_m50.py freight/test_lab_dual_ledger_backup_m49.py freight/test_backup_restore.py
    PYTHONPATH=. python -m freight.lab_recovery_admission_m50 --as-of-date 2026-10-13 --out /tmp/retally-m50
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m50-control

**DRAFT / UNMERGED / NO LIVE DEPLOYMENT.**
