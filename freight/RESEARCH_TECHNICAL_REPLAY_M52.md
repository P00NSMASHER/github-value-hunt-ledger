# RETALLY Research Lab 14 / Mission 52 — Durable technical review replay barrier

**October 13, 2026 · DRAFT / INTERNAL SYNTHETIC ONLY · stacked on M51 PR #451.** No merge, deployment, external identity/signing service, customer data, bank/carrier contact, business registration, scheduled task, real payment or production restore.

## Significant open issue carried forward from M51

M51 introduced explicit **Ed25519 dual technical review** requiring independently provisioned public keys, two different reviewer roles, precise original/restored financial receipts, signed request and audience, UTC expiry and a fully valid M49/M50 recovery source. That verification was **stateless**. During the signature validity window, the same previously reviewed request could be presented again and accepted, or individual Ed25519 witness nonces could be reused across separately signed requests. A review decision must not be counted repeatedly merely because its signatures remain valid.

Mission 52 builds an **explicit durable, local technical-review replay journal** without granting production restore activation. It creates no customer account and does not claim a real independent trust service exists.

### Real application changes

- **freight/recovery_replay_m52.py:** a separate explicitly managed TechnicalReviewReplayLedger, stored **outside** the recovery bundle in its own SQLite file. It does not auto-create a missing existing journal, overwrite an old one, follow direct symlinks, silently accept a replaced path or repair a weakened schema. New file creation requires explicit create=True, uses an O_EXCL exclusive regular-file create, and requires an existing approved schema with two tables and four append-only triggers on all reopen/read/write operations.
- The journal uses a SQLite **BEGIN IMMEDIATE** transaction and UNIQUE constraints to record exactly one global restore-request ID and **two globally unique signed witness nonces**. It also stores only the scoped original manifest/proof fingerprints, intended audience, role/signing-key fingerprints, canonical signed-payload digests and a typed technical-only decision. No private keys, full signatures, customer invoices, source SQLite file content or decrypted bank/carrier credentials are stored.
- Strict integrity verification is performed under the same transaction before and after appending request/nonces. Missing/altered review rows, missing nonce entries, substituted trigger bodies, extra objects, corrupted request metadata and inconsistent role/key counts cause exact fail-closed denials. If anything fails after partially inserting rows, SQLite rolls back the **entire request and both nonce claims**. A concurrent second caller must lose to the globally unique already-consumed review request/nonce; no race between separate Python processes can claim the same ID in the same persistent SQLite file.
- **freight/backup_restore.py:** new explicit record_witnessed_recovery_review operation. It first runs the full original M49/M50 source integrity gate and **both authentic M51 signature verifications**, rejects a replay journal located inside the backup folder, then consumes the request and two signed nonces. Normal verify_backup_bundle and read-only verify_witnessed_recovery_bundle retain existing behavior. Recording a technical review is NOT restoration, customer consent or a legal/financial approval.

### Fourteen genuine current-code adversarial cases

Every scenario starts with a fresh fictional four-SQLite recovery bundle, two in-memory Ed25519 signing keys, and a separately provisioned local replay SQLite file. One original valid dual-signer technical review is **successfully consumed first**. The following replay or source tamper must fail for its exact reason with all four original recovery SQLite files unchanged.

| Fake or broken review request | Expected exact denial |
| --- | --- |
| Same signed request presented twice | REQUEST_ALREADY_CONSUMED |
| Same request after reopening durable journal | REQUEST_ALREADY_CONSUMED |
| Same request freshly signed with different nonces | REQUEST_ALREADY_CONSUMED |
| Same request through a separate journal client | REQUEST_ALREADY_CONSUMED |
| New signed request reuses operator nonce | WITNESS_NONCE_ALREADY_CONSUMED |
| New signed request reuses independent reviewer nonce | WITNESS_NONCE_ALREADY_CONSUMED |
| Remove request-immutability trigger | SQLITE_REPLAY_SCHEMA_DRIFT |
| Replace nonce immutability trigger with noop body | SQLITE_REPLAY_SCHEMA_DRIFT |
| Insert unapproved SQLite schema object | SQLITE_REPLAY_SCHEMA_DRIFT |
| Corrupt durable review timestamp, then restore original trigger | PERSISTED_TECHNICAL_RECEIPT_TAMPERED |
| Delete exactly one used nonce, then restore original trigger | PERSISTED_TECHNICAL_RECEIPT_TAMPERED |
| Delete original replay ledger main file | SOURCE_FILE_MISSING |
| Atomically substitute another completely valid empty replay ledger | SOURCE_FILE_REPLACED |
| Replace pinned journal path with SQLite symlink | SOURCE_SYMLINK_REJECTED |

### Independent concurrency and rollback controls

- **Six simultaneous legitimate contenders** present identical valid two-key proofs through separately constructed journal clients. Exactly one must succeed, all other attempts are denied as consumed, and the reopened journal holds one review and two nonces (not six approvals).
- A test-only failure inserted **after** staging the review row and two nonces must roll back the entire transaction; the next original valid request remains usable. This guards against partial written approvals.
- A distinct properly signed request with two truly new nonces succeeds without granting activation, while a new signed request that recycles one nonce is denied globally.
- Corrupt source SQLite or a bad M51 Ed25519 signature fails **before any nonce is consumed**. The bad bundle cannot bypass financial validation with a durable ledger.
- The local journal itself must be intentionally provisioned, cannot be placed inside the backed-up bundle, never follows a symlink or silently recreates a missing former source, never adopts a changed trigger on reopen, and never upgrades its own records to CUSTOMER_APPROVED.
- Original Lab 14 plus M39 independent 14-lab receipt acceptance and Control Center now require all fourteen source/nonce negative proofs while preserving the original 14-lab census.

### Real deployment limitations — explicitly unresolved

A locally stored SQLite journal is **not an independently trusted distributed nonce store or an external immutable log**. If separate replicas use unshared journals, the same signed request can still be presented to each. A privileged attacker may restore the journal to an earlier generation, rewrite a fully consistent local history, change the code or compromise the trusted operator key registry. Preventing that requires an independently protected, consistently shared, persistent replay service with external anchoring and real custodian setup. This proposal **does not connect one**, claim end-to-end replay-proof production, or introduce actual real operator keys.

Two valid technical witness signatures and one locally consumed request do **not** independently prove real customer/legal consent, a bank or carrier receipt, a synchronized ACID backup, actual recovery money or permission to activate a restore. Full real-world performance and scale are not benchmarked.

**All 26 historically indexed RecoveryOS findings remain OPEN_UNVERIFIED and all 18 human first-customer pilot approval controls unmet.** No actual customer contact, registration, production deployment, scheduled task change or real funds are authorized.

### Reproduce

    PYTHONPATH=. python -m pytest -q freight/test_lab_recovery_replay_m52.py freight/test_lab_recovery_witness_m51.py freight/test_lab_recovery_admission_m50.py
    PYTHONPATH=. python -m freight.lab_recovery_replay_m52 --as-of-date 2026-10-13 --out /tmp/retally-m52
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m52-control

**DRAFT / UNMERGED / UNDEPLOYED.** This is a synthetic test-verified LOCAL replay barrier, not a customer-approved recovery service.
