# RETALLY Research Lab 14 / Mission 46 — Approved-Schema Drift Protection

**October 13, 2026 · DRAFT / INTERNAL ONLY · stacked on M45 PR #440.**
No merge, deployment, background task, customer data import, carrier/bank access, actual payments or externally published performance claims.

## Material security problem addressed

M44/45 validate persistent SQLite **row values, financial relationships and one-revision money operations**. Yet a privileged editor or botched restore could silently remove an INSERT-time capacity or append-only trigger while leaving all existing rows **financially consistent**. The old semantic scan would pass. Worse, SettlementStore's initializer ran CREATE ... IF NOT EXISTS unconditionally on **pre-existing files**, silently recreating missing triggers and masking the historical modification instead of demanding review.

A correct first-customer readiness gate must detect and preserve evidence of database schema tampering *before* accepting money reads, writes, reporting, backup or reopening, even when source balances remain plausible.

### Production-shaped source-code improvements (draft only)

- **freight/settlement_schema_guard_m46.py:** read-only, strict SQLite schema-catalog contract. Derives approved definitions from first-party freight/settlement_schema.sql using an independent disposable in-memory SQLite engine; pins the exact original committed Git blob SHA1 **85585df4b382a421b55c477649ac9ab3a7573b2f**. It requires **six reviewed tables, thirty reviewed triggers, four reviewed indexes** with exact SQLite-parsed SQL definitions. Rejects missing/extra/modified tables, triggers, indexes and views, including no-op replacement trigger bodies. Names/SQL are not emitted in errors or saved artifacts. Future approved schema changes require explicit review and migration; a hostile operator controlling the whole repository is outside this local trust boundary.
- **freight/settlement_semantic_guard_m44.py:** after the existing precise monetary/value validation completes, verifies the exact reviewed schema **in the same SQLite revision**. This ordering preserves the earlier M44 monetary error precedence when corrupt rows and missing triggers coexist. It blocks a clean ledger whose protective SQL has been removed.
- **freight/settlement_store.py:** an existing SQLite file is *never silently repaired* with first-party CREATE ... IF NOT EXISTS statements at opening. Truly new files receive the approved schema once; reopened files must pass the source, scope, schema and financial checks unchanged. A legacy unscoped/incomplete file is blocked, not migrated implicitly. Inherited M45 read and pre/post-write wrappers automatically inherit the new schema fence, including write-transaction rollback when a trigger is dropped.

## Ten actual isolated schema-drift attacks

Run each against a brand-new existing SettlementStore containing a passing, fully synthetic $5 current net settlement:

| Attack | Required denial |
| --- | --- |
| Remove allocation receipt-capacity trigger | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Remove allocation immutability trigger | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Replace immutability trigger with no-op body under original name | M46_SQLITE_DEFINITION_CHANGED |
| Remove frozen-claim source admission trigger | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Remove reversal counter-capacity trigger | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Remove automatic allocation review lock | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Remove reviewed allocation index | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Inject unreviewed index | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Inject unreviewed view | M46_SQLITE_CATALOG_OBJECTS_CHANGED |
| Add unreviewed allocation-table column | M46_SQLITE_DEFINITION_CHANGED |

Each mutation changes **DDL only** on a temporary SQLite file; no signed financial source row is changed. The original M45 row semantic check alone would accept the untouched money balances. M46 requires exact denials on seven already-open read paths (cash, fee, residuals, count, report, semantic audit), one ordinary write, and one reopen. **10 × (7+1+1) = 90 controlled denials**. Every denied operation must leave the damaged file unchanged rather than quietly re-creating missing protective triggers.

### Extra independent attack tests

- An explicitly staged trigger drop and new financial event during one M45 write **must roll back the entire SQLite transaction**, including the dropped trigger itself.
- A clean Tenant A cannot ignore globally removed SQLite protections even if all account rows appear valid; money rows remain tenant-scoped but schema contracts protect the entire file.
- Frozen original schema source modifications fail closed without updating the approved policy; no hidden migrate-on-open.
- Pre-existing empty or incomplete SQLite is not initialized as if it were new. New genuinely empty paths still initialize successfully.
- M44/M45 malformed financial rows still fail for their original exact financial reason before M46 catalog denial, preserving existing negative-test evidence.
- Malicious scenario names, HTML content and expired/invalid research dates cannot alter customer databases, issue public claims or create success artifacts.
- Dedicated GitHub Actions PR/manual workflow compares a pinned original **pre-M46 M45 source** with M46 against identical disposable DDL-only changes, proving that old stores accepted them before M46 and current guarded stores refuse them, without activating any hosted connection. Short-lived metadata-only CI artifacts; no SQL, source database or test signing keys uploaded.

## Reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_schema_integrity_m46.py freight/test_lab_atomic_financial_m45.py freight/test_lab_persistent_semantic_m44.py freight/test_settlement_store.py
    PYTHONPATH=. python -m freight.lab_schema_integrity_m46 --as-of-date 2026-10-13 --out /tmp/retally-m46
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m46-control

## Boundaries preserved

No new research lab is created: M46 strengthens **existing Lab 14**, the cross-lab M39 acceptance gate and its Control Center. A passing local test or GitHub Action **cannot establish original customer invoice source validity, bank receipt identity, real monetary recovery, legal customer permission or external audit/marketing authorization**. It is not hostile-administrator-proof when an attacker can rewrite both repository policy and code.

**All 26 original RecoveryOS historical findings remain OPEN_UNVERIFIED; all 18 independent first-customer human approval requirements remain unmet.** No business registration, live customer contact, new automated schedule, production merge/deploy or payments.
