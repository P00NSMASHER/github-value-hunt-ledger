# RETALLY Research Lab 14 — Mission 44: Persistent settlement semantic integrity

**October 13, 2026 · DRAFT / INTERNAL TESTING ONLY · stacked on M43 PR #437.** No merges, live deployment, cron/schedule changes, business registration, customer/provider messages, fund movement or use of private invoice data.

## Functional vulnerability and code-level correction

M41–M43 strengthened the **independent research verifier** for legacy/unconstrained SQLite and validated source-provenance and timeline checks. The actual persistent SettlementStore, however, used normal SQL constraints, append-only triggers and partial reopen checks but did not recheck complete historical settlement **monetary semantics** when reopening an existing database or exporting it for reporting. A privileged edit, imported database or failed restore can bypass INSERT-time guards while leaving the SQLite file structurally valid.

In particular, even with SQL integrity_check and foreign-key checks passing, an old database may have a valid-looking 500-cent current net that once represented 1300 cents against a signed 1000-cent claim, or a return/reversal that exceeds its own original receipt or allocation. Such data must not be exported as a valid read-only pilot report or backup proof without local structural revalidation.

M44 delivers a real source-code gate:

- **New freight/settlement_semantic_guard_m44.py:** validates *raw scoped source rows* and relational source identities for claims, credits, returns, allocation edges and reversals. Includes buyer/business-unit partition identity, unique source hashes, source-counterparty binding, exact eligible fee metadata, allowed workflow mode, source-currency/chronology, funding and return capacity, reversal caps and exact historic UTC claim-balance peaks. This does not verify separate original buyer/carrier signatures: consistency and authenticity are distinct.
- **freight/settlement_store.py:** entire file is checked **under one pinned read transaction at reopen**, before accepting the database; existing instances also re-audit the current scope under one transaction before returning each scoped report_snapshot_json. New explicit read-only assert_semantic_integrity() is available for report/backup gates.
- **freight/backup_restore.py:** the original backup/restore drill used independent SQLite connections and individual count/realized/fee calls that could observe different database revisions. Now it uses a **single semantically verified report_snapshot_json** for all settlement table counts, hash, realized cash and fee-eligible amounts. The backup drill refuses a corrupt original **before copying it**. Audit-store and settlement-store remain two separately stored databases, not a single atomic cross-file transaction; external provider signatures are not established.

## Eight actual persistent-store adversarial cases

All attack scenarios construct a real SettlementStore with a fictional positive control: one claim, two provider credits, two allocations, one return and reversal, resulting in **$5.00 fictional retained cash**. Each then deliberately bypasses local append-only/INSERT triggers **inside one disposable SQLite test directory**, simulating an illegally modified import or privileged broken restore, and requires rejection from **three independent consumer paths**: reopening, explicit current-store audit, and exporting a scoped read-only report.

| Test-only privileged edit | Required current persisted-file denial |
| --- | --- |
| Reduced provider receipt to 399 cents, original allocated 400 | ALLOCATION_CAPACITY_EXCEEDS_CREDIT |
| Increased provider return to 601 cents against 600-cent credit | RETURN_CAPACITY_EXCEEDS_CREDIT |
| Changed allocated fee-eligible cents to 399, original allocation 400 | ALLOCATION_FEE_ELIGIBILITY_DRIFT |
| Rewrote carrier payer after claim/credit linkage | ALLOCATION_CURRENCY_OR_COUNTERPARTY_DRIFT |
| Changed a reversal's return to reference the wrong original credit | REVERSAL_WRONG_ORIGINAL_RECEIPT |
| Increased original reversal to 601 cents against 600-cent allocation | REVERSAL_CAPACITY_EXCEEDS_ALLOCATION |
| Extra 900-cent credit/reversal hid a temporary 1300-cent balance on a 1000-cent claim, ending at apparently valid 500 | TRANSIENT_CLAIM_CAPACITY_EXCEEDED |
| Marked a claim fee-disqualified while leaving old fee-eligible rows | ALLOCATION_FEE_ELIGIBILITY_DRIFT |

**These tests validate *source-level financial structure*, not original financial event truth.** A privileged attacker who can rewrite all provider/source/account authority or separate signing history may still create a structurally consistent but false file; no local integrity validator alone can prevent that. Real first-customer evidence and independently guarded signatures remain mandatory.

## Comprehensive original-lab integration

- freight/lab_persistent_semantic_m44.py: eight real current-store disposable SQLite positive/negative probes; exact typed read/reopen/audit rejection; metadata-only internal HTML/JSON.
- freight/test_lab_persistent_semantic_m44.py: isolated positive and negative proof tests, transparent no-human-signoff, strict scope isolation, genuine corrupt-backup refusal before any backup file exists, single-revision backup metrics (no separate count/money reads), evil/malformed scenario rejection, no write on invalid input, HTML escaping.
- Existing Lab 14 in freight/lab_phase4_director.py now **requires all eight** source-level denials (with no additional lab). Cross-lab receipts in freight/lab_cross_lab_assurance_m39.py must match these eight positive/reopen/report checks and preserve all original findings.
- Existing Control Center adds a linked read-only persistent-source integrity panel, while preserving all earlier research and macroeconomic reports.
- .github/workflows/retally-persistent-semantic-m44.yml: PR/manual-only, broad inherited regressions including persistent pilot report, backup/restore and all existing 14 labs; separate independent job runs exactly the **same eight original test-only corrupted SQLite files** against the immediate pre-M44 SettlementStore source and the corrected reopen/report gate. No deploy and short-lived derived receipts.

### Local reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_persistent_semantic_m44.py freight/test_backup_restore.py freight/test_settlement_store.py freight/test_settlement_report.py
    PYTHONPATH=. python -m freight.lab_persistent_semantic_m44 --as-of-date 2026-10-13 --out /tmp/retally-m44
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m44-control

## Boundaries unchanged

**All 26 historical RecoveryOS findings remain OPEN_UNVERIFIED**, even those overlapping this protection. Neither an original archived vulnerable revision nor an authenticated real bank/carrier invoice has been reproduced in M44. **All 18 human first-customer pilot approval gates remain unmet.** The tests are fictional; they do not establish real customer refunds, business income, a serviceable freight recovery market, or publication permission. They do not register the business or modify hosted services.
