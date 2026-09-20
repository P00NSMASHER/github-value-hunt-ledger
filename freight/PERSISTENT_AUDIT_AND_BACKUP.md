# Freight Recovery — Persistent Audit and Backup/Restore Proof

Updated: 2026-09-20

This layer extends the v15.7 application audit chain into durable scoped
reference persistence and applies the recovery-proof rule that **backup existence
is not recovery proof**.

## Persistent audit store

`freight/audit_store.py` stores audit-chain records in SQLite with:
- buyer/business-unit scope chosen at repository construction;
- monotonic per-scope sequence;
- hash-chain verification before every append;
- immutable UPDATE/DELETE SQL triggers;
- transaction-serialized concurrent append;
- scope-bound reads and semantic summary.

This is a reference persistence boundary. It is not a hosted WORM log service,
external trusted timestamp, or proof of production database authorization.

## Semantic backup/restore drill

`freight/backup_restore.py`:
1. freezes the semantic summary of the audit + settlement stores;
2. uses SQLite's backup API for each store;
3. restores each backup into fresh database files;
4. reopens both stores in the same buyer/BU scope;
5. re-verifies the audit hash chain;
6. re-computes settlement realized/fee-eligible cents and row counts;
7. requires the complete semantic summary hash to match before the drill passes.

The resulting proof records backup/restore file SHA-256 plus source/restored
semantic hashes.

This is closer to **restore proof** than a backup-file checksum, but it still
does not prove cloud backup scheduling, geographic redundancy, RPO/RTO for a
deployed service, or an externally supervised disaster-recovery exercise.
