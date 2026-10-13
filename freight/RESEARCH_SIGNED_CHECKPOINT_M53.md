# RETALLY existing Research Lab 14 — Mission 53: Signed off-journal replay checkpoints

**October 13, 2026. DRAFT / internal, fictional research only.** Stacked on M52 PR #453. Do not merge or deploy, register the business, access a real customer/provider/bank account, alter scheduled tasks, or move money.

## Security problem

M52 atomically consumes a signed technical review and two nonce IDs in one separately provisioned local SQLite journal. However, its internally consistent SQLite history can be reverted to an older generation **without changing the main-file inode, restoring no-op/removed triggers, or leaving invalid accounting rows**. The original M52 verifier then considers previously used request IDs and nonces unused and can accept an identical still-valid M51 Ed25519 signed review. Local uniqueness constraints cannot establish a **monotonic externally trusted replay history** when privileged restoration or coherent edits to the journal are possible.

## What the current code actually changes

- **freight/recovery_checkpoint_m53.py** — a strict, read-only Ed25519 checkpoint validator. The signed payload binds all local journal review and nonce rows in canonical order (SHA-256), number of consumed reviews, a logical journal namespace, intended audience, exact authority and checkpoint IDs, issued/expiry times and a domain-separated purpose. The signer public key must be **supplied independently by the caller**, never loaded from the recovery bundle or replay database. A valid signature is insufficient when the signed state and actual rows differ; an unprovisioned custodian, wrong authority, bad timestamp, expired checkpoint, forged key and altered complete journal SHA are rejected with typed errors.
- **freight/recovery_replay_m52.py** — retains the existing **local-only** M52 entrypoint and adds a strongly separated optional signed-checkpoint mode to its actual BEGIN IMMEDIATE write transaction. It checks the complete outside-signed journal state **inside the same lock** that guards restore-request/nonce admission, then inserts the original M52 one-time records, checks all local invariants, and returns only an **unsigned successor state proposal** (sequence and local SHA). It does not forge, sign, publish, or persist an external checkpoint.
- **freight/backup_restore.py** — adds a separately named higher-assurance record_checkpointed_witnessed_recovery_review function. Before checking any signed journal checkpoint, it still executes M49/M50 validation of the real published backup/restore SQLite files and both original independently provisioned M51 technical signatures. It requires an explicit caller-provided signed external checkpoint, custodian trust key, namespace and audience, and a journal held outside the bundle. A successful call records only technical review evidence, not actual restore activation.
- **freight/lab_replay_checkpoint_m53.py** — 19 reproducible fictional test-only source manipulations, including two complete same-inode replay journal rollbacks, four coherent row rewrites with the original SQL trigger definitions restored, replay of a genuine older checkpoint, a correctly signed false state digest or sequence, forged/counterfeit independent signing keys, absent trust, wrong namespace/audience, expired/stale/future/long-lived and missing signatures.
- **freight/test_lab_replay_checkpoint_m53.py** — direct technical positive and negative proofs on actual SQLite and ephemeral Ed25519 keys; a deliberately **demonstrated M52 predecessor bypass** on an old internally consistent journal, independent M53 denial of identical journal state, six simultaneous reviewer requests with one allowed successor and five failed stale-checkpoint claims, a second and third correctly signed successor review, safe crash-gap behavior when a new checkpoint was not obtained, signed-source prerequisite, invalid trust and malformed signed payload rejection, no customer data/artifact leakage.
- M53 remains a strengthening of **the existing original Lab 14**, its independent M39 receipt verification, and the Control Center. No fifteenth lab or historic-issue closure is created. A dedicated PR/manual-only GitHub Action runs all inherited M39–M52 source/backup/authorization regressions, all fourteen original labs and an independent source comparison pinned to the actual pre-M53 M52 commit.

## Non-negotiable external boundaries

**No actual off-journal signing service, separately safeguarded public-key registry, remotely retained latest checkpoint, or durable nonrollbackable store has been provisioned.** The 19 positive controls use **temporary synthetic keys in memory**, and an attacker who controls the caller's trust context can bypass them. A signed digest on its own is not a third-party time source or bank/customer attestation.

M53 is an **explicit stricter entrypoint**; the pre-existing M52 local-only entrypoint is **still vulnerable to rollback** and must not be used as proof of rollback protection. Even the new path cannot commit a local review and update an external checkpoint atomically. After a successful local consume it reports the successor digest as **UNSIGNED**. A real custodian must separately sign and retain the new state before another higher-assurance review; an interruption in that external step intentionally blocks subsequent checkpointed operations pending manual reconciliation.

These local tests do not establish real customer consent, recovered bank funds, carrier authority, legal business formation, independently confirmed historical source events, durable external signing custody, or production disaster-recovery readiness. **All 26 original RecoveryOS historical findings remain OPEN_UNVERIFIED and all 18 independent human first-customer approval gates remain unmet**. Zero customer activation, true external revenue, commercial authorization or published empirical recovery claim is approved.

### Reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_replay_checkpoint_m53.py freight/test_lab_recovery_replay_m52.py freight/test_lab_recovery_witness_m51.py
    PYTHONPATH=. python -m freight.lab_replay_checkpoint_m53 --as-of-date 2026-10-13 --out /tmp/retally-m53
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m53-control

**DRAFT / UNMERGED / NO LIVE DEPLOYMENT.**
