# RETALLY Research Lab 14 / Mission 47 — Persistent SQLite File Continuity

**October 13, 2026 · DRAFT / INTERNAL TESTING ONLY · stacked on M46 PR #442.** No merge, production deployment, tasks/cron changes, customer contact, payments, public marketing or business registration.

## Meaningful source-level issue resolved

M39–M46 added independent structural evidence, verified financial chronology, atomic money reads/writes and exact SQLite schema/trigger policy. But Python's original sqlite3.connect(path) defaults to **creating a new file when the main database path is missing**. An already-open SettlementStore also retained only the filename, not which actual database file it had reviewed. A deleted, renamed or **valid replacement SQLite** at the same path could be silently opened on later money reads and writes. Even when the replacement itself contains valid financial records and thirty intact SQL triggers, it is **not automatically the audited original**. A previously nonzero account could appear zero after an empty but valid database was substituted.

### M47 durable continuity upgrade

- **freight/settlement_file_identity_m47.py:** verify direct file type and local device/inode tuple on all operations, reject missing/symlink/directory/replacement without revealing tenant names or path text. New paths are opened using **exclusive O_CREAT|O_EXCL** and private file mode (0600 on POSIX); a late file-creation race never overwrites an existing file. Reject apparent first-time creation if a stale/orphaned **-wal, -shm or -journal** companion suggests a deleted original. This is an operational safety check, not a cryptographically signed source identity.
- **freight/settlement_store.py:** convert supplied path to absolute location once, preserving the original database despite later working-directory changes. **Every actual SQLite connect uses URI mode=rw**, never sqlite3's default implicit-create mode. Connections check file type and pinned identity **before and after opening**. M45 money/report reads re-check after the requested SELECT under one SQLite snapshot. M45 writes verify file identity before and after the transaction, including before commit, in addition to source/financial/schema invariants. A path swap during a write causes rollback before success is reported.
- First-time requested creation remains supported, but a pre-existing incomplete file must satisfy all M46 schema and M44 semantic invariants without automatic repair. Genuine explicit operator recovery can use a **new SettlementStore instance** after the replaced file has been separately reviewed; an existing session **cannot silently adopt the replacement**.
- SQLite still offers standard concurrency: legitimate writes by a second instance to the SAME file/device/inode succeed and become visible on later read snapshots. This does NOT provide a hostile-kernel race-proof open, guarantee against in-place rewriting, authenticate source data, prevent a compromised operator changing code, or amount to an external bank signer.

### Eight disposable old-session path substitutions

| Mutation | Required exact denial |
| --- | --- |
| Delete original database main file | M47_SQLITE_SOURCE_FILE_MISSING |
| Rename original main file away | M47_SQLITE_SOURCE_FILE_MISSING |
| Atomically replace with equivalent valid SQLite backup | M47_SQLITE_SOURCE_FILE_REPLACED |
| Replace with legitimate empty SQLite (simulated silent reset) | M47_SQLITE_SOURCE_FILE_REPLACED |
| Replace with separately valid other-tenant SQLite | M47_SQLITE_SOURCE_FILE_REPLACED |
| Substitute symlink to a valid SQLite file | M47_SQLITE_SOURCE_SYMLINK_REJECTED |
| Substitute dangling symlink | M47_SQLITE_SOURCE_SYMLINK_REJECTED |
| Substitute a directory at the original file path | M47_SQLITE_SOURCE_NOT_REGULAR_FILE |

Each attack starts from a real persistently opened test-only SettlementStore with **five passing known-good fictional cash/residual/count positive controls**. The disposable source path is altered, with all attempted operations against the **already-open** store required to refuse the replacement: **seven read/report/audit APIs plus one write**. That yields **56 typed read denials, 8 typed write denials (64 total)**. Rejected operations may NOT create an empty replacement database, repair the damage, overwrite alternate valid source, or convert the original ledger to zero.

### Independent adversarial acceptance

The new M47 unit suite also covers:

- A deleted main file never gets recreated by reads, writes or reports.
- Positive explicit adoption of an operator-reviewed valid replacement through a NEW SettlementStore session. Old session still refuses it.
- Creation race with a second writer, verifying existing sentinel bytes are not truncated.
- Orphan WAL sidecars are not mistaken for a new file.
- Initial direct symlinks (valid and dangling) refused before SQLite follows them.
- An absolute source location survives changes in process working directory.
- File identity switched in the middle of a pinned money read or a write transaction refuses to report success.
- Two valid separate sessions writing new events to the original SAME SQLite file still work normally.
- Closed-set attack inputs, derived JSON/HTML escaping, scope disclaimers and fail-before-output rules.
- Exact-head dedicated GitHub Actions CI: full inherited financial and original 14-lab regression; second job loads **pinned pre-M47 M46 source** to demonstrate that former already-open instances accepted valid file swaps (including a misleading zero-balance substitute) which M47 blocks. It separately validates no automatic creation after deletion and normal new/open behavior. PR/manual only, no cron, no live deployment and short-lived metadata-only artifacts.

### Reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_file_continuity_m47.py freight/test_lab_schema_integrity_m46.py freight/test_lab_atomic_financial_m45.py freight/test_backup_restore.py
    PYTHONPATH=. python -m freight.lab_file_continuity_m47 --as-of-date 2026-10-13 --out /tmp/retally-m47
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m47-control

## Trust boundary

This is **local database-file continuity**, not the verification of original outside invoice, bank, carrier or customer events. A malicious process with privilege to modify both code and storage, including changing file content *in place*, can still produce structurally consistent but false results. Filesystem races with privileged attackers are not fully eliminated in CPython's separate stat/open interface; do not claim otherwise. Real production recovery requires access controls, monitored restores and independent source signing.

The original **26 historical RecoveryOS findings remain OPEN_UNVERIFIED**, the **18 real first-customer human pilot gates remain unmet**, and zero external money recovered, customer validation, empirical recovery/market-size claim or provider authority has been independently shown. **No deployment, registration, schedule modification or customer action** is included in this draft.
