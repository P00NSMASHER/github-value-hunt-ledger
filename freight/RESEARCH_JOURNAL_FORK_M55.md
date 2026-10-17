# RETALLY Research Lab 14 / M55 — checkpoint journal-instance fork binding

**Internal synthetic research · draft only · October 13, 2026.**

M53/M54 bind an Ed25519 checkpoint to all review rows, nonce rows, and the checkpoint-required mode. However, two independently created local SQLite journals can have *identical rows and mode*. The same signed checkpoint could then be reused against a new journal, bypassing the intended one-journal review history.

**Source change:** `freight/recovery_checkpoint_m53.py` now incorporates a hash of the main SQLite file's local absolute path, device and inode into the already signed complete journal-state SHA. The strict checkpointed path compares this fingerprint while holding the same SQLite write transaction as request/nonce consumption. Copies, new empty journals, and a byte-identical journal swapped into the same path cannot reuse a checkpoint signed for the original local file. Reopening the original journal without replacing it remains supported.

**Regression evidence:** `freight/test_lab_journal_fork_m55.py` tests the actual SQLite backup/copy path, same-path replacement with a newly opened handle, copied empty-journal replay, positive same-inode reopening, and strict technical-only output. All are fictional with ephemeral keys; no customer restore or real signing authority is created. The Repository Release Gate discovers the test, and the dedicated M55 workflow also runs the complete M39–M54 source/lab regression set.

**Limits:** Local inode/device/path is NOT a globally unique, cryptographically authenticated or nonrollbackable journal identity. A privileged attacker controlling filesystem identity or signing trust, inode reuse, migrations, and cloned hosts can still defeat or invalidate this defense. Legitimate relocation or restoration requires independently approved re-anchoring; this implementation deliberately fails closed rather than automatically transferring a signature. No external custodian, distributed nonce store or atomic remote checkpoint service has been provisioned. The legacy LOCAL_ONLY path is not made secure by this change.

**All 26 original historical findings remain OPEN_UNVERIFIED; all 18 independent human first-customer approval gates remain unmet.** No business registration, real customer/bank/carrier approval, money movement, production deployment or scheduled task change.

**DRAFT / UNMERGED / UNDEPLOYED.**

## October 17 integration with the independent crash-gap M55 branch

This candidate unifies the **independent** draft research strands #459 and #460:
the exact off-journal Ed25519 signed predecessor/one unsigned successor diagnosis
and the physical journal-instance binding for copied/replaced SQLite files.
Neither is a production recovery authority. The branches remain untouched.

The one canonical `digest_journal_rows(...,local_journal_identity_sha256=...)`
now includes the absolute canonical path, device and inode identity in
BOTH the live signed-head hash and the reconstructed predecessor hash.
The reconciler must compare a signed ancestor **for this same journal
instance**. Merely copying the same rows and consuming a new unsigned
technical review cannot be labeled as an eligible pending descendant.

Independent cross-branch negative controls: copied identical signed head
is denied, and copied one-step unsigned successor is denied, while the
original unchanged file can reopen and a true one-step child is held as
`ONE_UNSIGNED_SUCCESSOR_REQUIRES_EXTERNAL_COUNTERSIGN` without
issuing a signature or bypassing the consuming write gate.

This is review-only integration. All 26 original historical findings
remain OPEN_UNVERIFIED and all 18 independent human/customer release
conditions remain unmet. No customer, claim, payment, legal authorization,
remote custodian or production deployment was added. Exact-head CI is required.
