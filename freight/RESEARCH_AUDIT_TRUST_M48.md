# RETALLY existing Research Lab 14 — Mission 48: Persistent audit evidence trust

**October 13, 2026 · DRAFT / INTERNAL RESEARCH ONLY · stacked on M47 PR #444.** No merges, deployments, recurring task changes, customer data imports, carrier/bank contact, business registration or real payment activity.

## Critical persistent evidence gap

M42–47 guarded the **settlement** SQLite store against duplicate financial identifiers, time-inconsistent receipts, arbitrary source data, weakened triggers, deleted databases and silent file swaps. The **separate AuditStore** backing recovery claims and backup/restore evidence still had older behavior: sqlite3.connect(path) implicitly created a missing audit database, its initializer re-ran CREATE ... IF NOT EXISTS on every reopen, silently reconstructing deleted append-only/event-admission triggers, and ordinary count()/records()/head() could read a substituted database without binding the original file identity or verifying all requested chain fields in one pinned transaction.

This could produce false evidence of audit continuity even if the settlement file remained correctly protected. Mission 48 extends the real source-code trust boundary to **AuditStore**, rather than inventing another research lab or declaring the original 26 defects fixed.

## Source-level changes

- **freight/audit_store_schema_m48.sql:** extract the exact original AuditStore DDL, keeping stored SQL formatting. Source is frozen to Git blob SHA-1 **6eabc1b9d9dd25994d30a8fb3b418dbd7afdeab5**. Every approved change must be reviewed as a real database schema/migration change; re-hashing an altered local policy cannot silently bless it.
- **freight/audit_store_integrity_m48.py:** independent, read-only approved-source catalog verification of the original one audit table and **three immutable/admission triggers**, rejecting missing/replaced triggers, extra tables/views/indexes or changed table columns. In the same SQLite revision, examine the original application **hash chain**, typed audit events, sequential IDs, causal pointers, canonical UTC and SHA-256 event payload digest, across **ALL tenant histories on reopen**, or only the currently authenticated tenant on normal operations. Current local SHA records do not establish independently anchored or externally timestamped evidence.
- **freight/audit_store.py:** absolute path pinning, O_EXCL private exclusive first-time creation, symlink/orphan-WAL denial, SQLite mode=rw (never implicitly create deleted main files), local device+inode continuity before/after connection and event operations; **no auto-repair** of missing triggers or changes to unapproved existing journal modes. Each ordinary read runs schema + hash-chain verification and the requested query under a single pinned SQLite transaction. Every write validates pre- and post-mutation before COMMIT; DDL/event edits in a failed transaction roll back. Existing append behavior and tenant scoping are preserved.
- **freight/backup_restore.py:** original backup source must be a real pre-existing database opened through mode=ro, not implicit creation. Bind source device+inode both before and after SQLite backup; check original audit and settlement session identities before/after copying, and refuse damaged audit chain or invalid settlement semantics **before** creating a recovery drill claiming success.
- **freight/lab_audit_trust_boundary_m48.py:** thirteen fresh, disposable, fictional **current AuditStore** attacks covering removed immutable/admission triggers, no-op trigger replacements, injected indexes/new columns, altered audit event hash and sequence, forged typed event, deleted source/valid swaps and symlinks. All require passing original two-event fictional positive controls, followed by **65 exact read and 13 exact append denials**. A freshly reviewed new instance may deliberately accept a valid replacement but an existing source-bound session may not. No automatically closed original finding.
- **freight/test_lab_audit_trust_boundary_m48.py:** source/schema fidelity, exact row/DDL failure reason, rollback of bad DDL, two-tenant reopen across both chains, file deletion nonrecreation (including backup), legitimate reviewed replacement, symlink, concurrency, in-flight file replacement and malicious inputs.
- Existing Lab 14, M39 independent cross-lab verifier, Control Center and detailed internal HTML/JSON evidence now require thirteen negative probes while preserving all original 14 laboratories. A PR/manual-only dedicated GitHub Action runs all inherited financial/backup/recovery tests plus independently checks the pre-M48 original AuditStore source against identical fictional mutated SQLite fixtures.
- No live customer operations, database migration, tasks, deployment, external communication or financial side effects are authorized by this draft.

## Rehearsal coverage and limits

Original audit chains are **locally re-hashable**. If an actor with full file access rewrites *the entire history* with correctly sequenced and internally consistent hashes, current local validation alone cannot prove it was altered. An external immutable append-only anchor, independently trusted timestamp and real customer/legal authority remain separate requirements. Application review is not a bank or carrier event signature.

**All 26 historical RecoveryOS findings remain OPEN_UNVERIFIED; all 18 independent first-customer human approval controls remain unmet.** Simulated positive controls do not certify real customer refunds, fee accrual, privacy compliance, banking access, actual recovery money or published recovery/market claims.

### Local reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_audit_trust_boundary_m48.py freight/test_audit_store.py freight/test_backup_restore.py freight/test_settlement_store.py
    PYTHONPATH=. python -m freight.lab_audit_trust_boundary_m48 --as-of-date 2026-10-13 --out /tmp/retally-m48
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m48-control

**DRAFT / UNMERGED / NO LIVE DEPLOYMENT.** A broader audit storage migration is a separate reviewed operation; no customer legal consent is implied by local tests.
