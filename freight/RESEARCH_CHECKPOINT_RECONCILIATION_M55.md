# RETALLY Research Lab 14 / Mission 55 — Signed checkpoint crash-gap reconciliation

**October 13, 2026 · DRAFT / INTERNAL SYNTHETIC ONLY · stacked on M54 PR #458.**
No merge, deploy, scheduled tasks, customer contact, bank/provider account access, payments, business registration or public recovery claims.

## Substantive source defect addressed

M53–54 require an independently signed prior high-water checkpoint inside the same SQLite write lock as technical review and witness nonce consumption. Once the local write commits, its successor digest remains UNSIGNED until an independent custodian attests and persists the new checkpoint. A crash between those actions leaves a legitimate one-commit gap that the original M53 verifier rejects generically as source mismatch. That is safe for admission but provides no fail-closed diagnostic to distinguish ordinary interrupted countersigning from forged, rewound or multiply changed review history.

Mission 55 adds an explicitly **read-only checkpoint reconciliation entrypoint** which can identify one provable local child of a signed external parent, return it only as PENDING_EXTERNAL_COUNTERSIGN, and *never* bypass the original M53/M54 one-time write gate or sign an external receipt.

### Actual functional changes

- **freight/recovery_checkpoint_m53.py:** extracts the original complete Ed25519 signature/authority/namespace/audience/UTC expiry check into a reusable helper. The original consuming validator still calls this exact logic followed by same-transaction source matching. Factors its exact canonical hash of all journal review rows, witness nonce rows and persistent M54 checkpoint mode into one implementation shared by the reconciliation proof.
- **freight/recovery_reconcile_m55.py:** verifies the previously signed, independently held source checkpoint against caller-supplied external public keys; opens an explicitly provisioned M52–54 SQLite journal under one read-only transaction, checks all original immutable schema/typed histories and pinned source file identity.
- If the full local journal equals the signed current checkpoint, the result is EXTERNAL_SIGNED_HEAD_MATCHES_LOCAL — still not customer restore authorization.
- If the journal is exactly one review ahead, mode CHECKPOINT_REQUIRED, and excluding **exactly one** review and its **two associated signed witness nonce rows** reproduces the exact full originally signed journal row image and mode, the result is ONE_UNSIGNED_SUCCESSOR_REQUIRES_EXTERNAL_COUNTERSIGN. It provides only an unsigned candidate digest, not a signed external receipt, not a restored service, and not permission for another review.
- Multiple unanchored reviews, forks, old signed ancestor mutations, journal rewind, legacy local-only writes, mode rollback, missing/replaced/symlinked source and bad external signers are rejected with typed errors. The result is read-only and preserves all four backup SQLite files.
- **freight/backup_restore.py:** adds the explicitly named wrapper inspect_signed_replay_checkpoint_reconciliation without changing the existing record/consume APIs.
- **freight/lab_checkpoint_reconciliation_m55.py** and **freight/test_lab_checkpoint_reconciliation_m55.py:** 18 isolated *actual* SQLite negatives. Every scenario starts from an independently signed current-head positive and an honest one-step unsigned successor PENDING positive. Tests cover second/third legitimate but unanchored reviews, overwritten ancestor rows, coherent same-sequence rewrite, journal file changes, untrusted or expired Ed25519 receipts, scope/context changes, source-byte preservation, safe HTML/JSON and no secret export.
- Additional test deliberately inserts one forged-looking but internally consistent request and two nonces using privileged SQL. M55 may classify it as a *candidate pending child* but **never approves it**; this prevents falsely claiming local state-prefix consistency is equivalent to authenticated human reviewer consent or external bank/carrier proof.
- Integrates exact M55 results into the **original Lab 14**, independent M39 cross-lab receipt verification and internal Control Center. No fifteenth lab, no historical defect closure, no real business activity. Dedicated PR/manual-only GitHub Actions regression checks all original M39–54 controls and compares predecessor M54 behavior to the explicit M55 diagnostic.

### Negative control matrix

| Attack | Required failure |
| --- | --- |
| Signed head two review generations behind | MULTIPLE_UNCOUNTERSIGNED_REVIEWS_OR_HISTORY_GAP |
| Old journal rows rewritten with unchanged count | SAME_SEQUENCE_JOURNAL_FORK_OR_MODE_ROLLBACK |
| Signed sequence ahead of rewound local journal | SIGNED_HISTORY_AHEAD_OF_CURRENT_JOURNAL |
| Locally valid extra review but older signed ancestor altered | NOT_AN_EXACT_ONE_REVIEW_SIGNED_SUCCESSOR |
| Legacy LOCAL_ONLY journal with one unanchored review | LOCAL_ONLY_UNCOUNTERSIGNED_REVIEW_NOT_ELIGIBLE |
| Privileged mode-only 54 to 0 reset | SAME_SEQUENCE_JOURNAL_FORK_OR_MODE_ROLLBACK |
| Forged checkpoint signature or changed custodian public key | INVALID_SIGNATURE |
| Missing independent trust root | TRUST_NOT_PROVISIONED |
| Wrong signed journal namespace or audience | NAMESPACE_MISMATCH / AUDIENCE_MISMATCH |
| Expired, future or unsigned checkpoint | EXPIRED_CHECKPOINT / FUTURE_CHECKPOINT / RECEIPT_MALFORMED |
| Malformed signed sequence type | INVALID_SIGNED_PAYLOAD |
| Main SQLite deleted/replaced/symlinked | SOURCE_FILE_MISSING / SOURCE_FILE_REPLACED / SOURCE_SYMLINK_REJECTED |

### Essential boundaries

**A provable one-step local child is not authentic original reviewer evidence.** An attacker with privileged SQL access can insert a coherent but fictional one-step child; that can at most appear as UNSIGNED/PENDING and requires separate independent custodian approval. The diagnostic does not issue, persist, forge or promote a countersignature, does not admit any new one-time request, and cannot solve the two-source SQLite and offsite custodian distributed atomic commit problem.

No independent external signer, real remotely nonrollbackable high-water service, legal customer consent, authenticated bank/carrier source, real recovered money, hosted deployment, business registration or scheduled tasks were activated.

**All original 26 RecoveryOS historical findings remain OPEN_UNVERIFIED and all 18 first-customer independent human approval gates unmet.** Local green tests do not certify commercial outcomes.

### Reproduce

    PYTHONPATH=. python -m pytest -q freight/test_lab_checkpoint_reconciliation_m55.py freight/test_lab_checkpoint_mode_m54.py freight/test_lab_replay_checkpoint_m53.py
    PYTHONPATH=. python -m freight.lab_checkpoint_reconciliation_m55 --as-of-date 2026-10-13 --out /tmp/retally-m55
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m55-control

**DRAFT / UNMERGED / NO LIVE DEPLOYMENT.**
