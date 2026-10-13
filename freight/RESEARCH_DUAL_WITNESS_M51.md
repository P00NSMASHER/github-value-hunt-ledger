# RETALLY Research Lab 14 — Mission 51: Off-bundle dual technical recovery witnesses

**October 13, 2026 · DRAFT / INTERNAL SYNTHETIC ONLY · stacked on M50 PR #449.**
No merge, deployment, real customer data, registrar filing, scheduled task, bank credentials, provider contact or money movement.

## Why the previous local verification was insufficient for restore authorization

M49/M50 now guarantee strong *local* checks for an original dual-SQLite backup: verified audit trails and source schema, financial amount/counterparty consistency, four independently reopened SQLite images, same all-tenant content generation, receipt hashes and completion marker. Those checks are essential but **every hash and manifest is stored with the backup and can be recomputed by an actor controlling all its files**. This is a local integrity check, not an authorization by a distinct human or an independently trusted source.

Mission 51 introduces a separate **fail-closed technical witness gate for future recovery review**. It leaves the original M50 local-only function available for normal post-backup structural validation, and explicitly requires two review signatures **in addition** whenever a caller seeks independently witnessed technical restore clearance. This work does not perform or authorize a production restore.

## Real source-level changes

- **freight/recovery_witness_m51.py:** strict Ed25519 signature verification with domain-separated canonical signed payloads. The *caller* must provide an out-of-bundle preapproved trust registry; the verifier never trusts a key embedded in the recovery bundle or discovered from its directories. Two distinct trusted public keys and two distinct roles — **RECOVERY_OPERATOR** and **INDEPENDENT_SECURITY_REVIEWER** — are required. Same key in both roles, duplicate signer, duplicate nonce, unregistered signer, changed role or malformed key is refused.
- Signatures bind the **exact validated M49/M50 manifest SHA**, scoped financial proof, buyer and business-unit, individual restore-request ID, intended audience, issue time, expiry and explicit purpose. Ed25519 signing bytes have an M51-specific domain prefix. Unsupported fields, extra fake customer approvals, noncanonical UTC, another restore request, another audience, stale, expired, future-dated or overly long validity and modified signature bytes all fail with precise typed denials.
- **freight/backup_restore.py:** new explicit function verify_witnessed_recovery_bundle first executes the COMPLETE original M49/M50 local-file verification, then calls the external public-key technical witness verifier. A valid witness CANNOT override corrupted SQLite, broken physical checks, misplaced scope or mutated source receipts. With no trusted registry or no two signatures, the new technical review fails closed. No private key or witness payload is written to disk by the verifier.
- Critically, a successful M51 verification returns **technical review only**, never full_customer_restore_activation_authorized. Two Ed25519 signatures do NOT independently prove the real people behind keys, owner/customer consent, legal business readiness, carrier/bank authority, actual recovered customer funds, a shared two-file ACID transaction or satisfaction of first-customer human controls.
- Ed25519 **private keys are created solely in memory during synthetic CI**, never committed, uploaded or configured as real operational signing credentials. A real externally controlled trust registry and independent operators must be provisioned through a separate approved operational process.

## Twenty-two executable test-only threats

Every scenario first creates a valid, fictional M50 four-SQLite backup and two independent ephemeral Ed25519 signatures, which correctly pass the new technical review while yielding **no production activation**. The original M50 local source verifier also continues to pass. The attack then tampers with the technical authorization context, not the customer data, and the new gate must deny it exactly.

| Negative scenario | Required denial |
| --- | --- |
| No witnesses, or only one witness | MISSING_TWO_DISTINCT_WITNESSES |
| No externally provisioned trusted keys | TRUST_REGISTRY_NOT_PROVISIONED |
| Unregistered signer identity | UNKNOWN_EXTERNAL_WITNESS_KEY |
| Same signer reused | DUPLICATE_ROLE_OR_SIGNER |
| Two separate keys claiming the same role | DUPLICATE_ROLE_OR_SIGNER |
| Same public key assigned to both roles | DUPLICATE_PUBLIC_KEY_ACROSS_WITNESSES |
| Signature produced by an untrusted private key | SIGNATURE_NOT_VALID |
| Malformed or non-base64 signature | INVALID_SIGNATURE_ENCODING |
| Signature bound to a different bundle's SHA | MANIFEST_OR_FINANCIAL_RECEIPT_REBOUND |
| Signature bound to another scoped money receipt | MANIFEST_OR_FINANCIAL_RECEIPT_REBOUND |
| Correct signature with wrong customer scope | WRONG_RECOVERY_BUYER_SCOPE |
| Signed request replayed for another restore | RESTORE_REQUEST_REPLAY_OR_MISMATCH |
| Different system/audience using identical receipt | WITNESS_AUDIENCE_MISMATCH |
| Expired, stale, or future-dated signature | EXPIRED_WITNESS / STALE_WITNESS / FUTURE_DATED_WITNESS |
| Signed expiry longer than one day | INVALID_WITNESS_LIFETIME |
| Reused nonce across two roles | DUPLICATE_RECEIPT_NONCE |
| Added fake real-customer approval field | INVALID_RECEIPT_FIELDS |
| Role substitution without trust-policy authority | WITNESS_ROLE_MISMATCH |
| Unreviewed/malformed trusted public key | TRUST_REGISTRY_INVALID |

Additional regression tests cover actual published SQLite tampering **even with two valid signatures**, schema-unknown/extra JSON fields, read-only behavior, strict context input, replay after expiry, distinct signing keys, valid correct signatures, no private-key leakage, reporting honesty and negative mocks.

## Original research integration and CI

- **freight/lab_recovery_witness_m51.py** and **freight/test_lab_recovery_witness_m51.py** run the original source-verifying API with synthetic keys, rather than only asserting a generated report.
- Existing **Research Lab 14**, **M39 independent cross-lab admission** and the internal Control Center now require the twenty-two actual positive/negative technical witness results; no fifteenth lab and no original historical finding closure.
- Dedicated PR/manual-only workflow tests all previous M39–M50 financial/source/audit/backup obligations and new signed request scenarios. A separate pinned M50 source comparator confirms that the former local-only recovery checker accepted every otherwise-healthy bundle without requiring a distinct witness. The new technical gate denies the same fake/missing technical witness claims. All CI artifacts contain metadata-only JSON/HTML, no SQLite files or signing private keys.
- The existing task/schedule list, business incorporation decision, customer access, live services and financial accounts are unchanged.

## Key security limitations

A caller that **accepts public keys supplied by the same party who controls the backup** defeats this gate. Real public keys must be pinned by an independently trusted process. This test suite **does not connect a real trust registry or create any real witness authority**. M51 does NOT implement a durable nonce-spent ledger, prevent the same signed request being re-presented within its valid lifetime, prevent hostile code changes, or establish source authenticity. It does not resolve the original absence of a shared atomic transaction across two SQLite files.

**All 26 historical RecoveryOS findings remain OPEN_UNVERIFIED and all 18 independent first-customer human approvals remain unmet.** No real customer recovered cash, ROI, freight error rates, publication permission or production activation is established.

### Reproduce

    PYTHONPATH=. python -m pytest -q freight/test_lab_recovery_witness_m51.py freight/test_lab_recovery_admission_m50.py freight/test_backup_restore.py
    PYTHONPATH=. python -m freight.lab_recovery_witness_m51 --as-of-date 2026-10-13 --out /tmp/retally-m51
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m51-control

**DRAFT / UNMERGED / UNDEPLOYED.** This is a prerequisite for a future externally witnessed restore review, not permission to restore a real customer's database.
