# RETALLY existing Research Lab 14 — Mission 54: one-way checkpoint mode and anti-downgrade

**October 13, 2026 · DRAFT / INTERNAL SYNTHETIC ONLY · stacked on M53 PR #455.**
No merge, customer access, bank/carrier contact, registration, money movement, production deploy, real restore or scheduled-task modification.

## Actual runtime authorization gap

M53 introduced independently signed replay-journal checkpoints verified under the same SQLite BEGIN IMMEDIATE lock as one-time technical request and nonce consumption. But its older, public M52 LOCAL_ONLY recording function remained callable **on that exact same journal** even after it had processed a properly checkpointed review. A second client could simply omit the externally signed checkpoint and write another valid-looking technical review before the successor state was signed externally. That silently invalidates the expected M53 high-water state and creates a downgrade from high-assurance review to legacy local-only, despite legitimate M51 signatures.

A manually privileged operator could also rewind an M52 journal's rows while preserving the original schema, and then use that same local-only route. M53 detected the rewind only in its separately named checkpointed API. M54 closes the **ordinary downgraded application path** once a journal has actually been elevated. It does not claim privileged SQLite header edits are impossible.

### Exact application changes

- **freight/recovery_mode_m54.py** — strict, versioned persisted SQLite header security policy, using PRAGMA user_version **0 = LOCAL_ONLY, 54 = CHECKPOINT_REQUIRED**. No auto-migration, added table, new customer data, extra delegated role or changes to M52's reviewed immutable trigger schema. Unsupported header versions fail closed; local-only clients may open/read an elevated journal but **may not consume any review or nonce without an independently signed checkpoint**.
- **freight/recovery_replay_m52.py** — validates the persisted security mode as part of every original journal consistency scan. Every M52 consume, regardless of caller, checks that mode AFTER acquiring its **BEGIN IMMEDIATE write lock and BEFORE inserting any review or nonce rows**. If mode is 54 and there is no signed M53 checkpoint, the operation rejects with exact M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE. Clients opened before the elevation see the same committed mode after the locking transaction.
- After the FIRST **valid M53 signed checkpoint** is verified under that lock and its original review/nonce rows are staged, M54 performs the **one-way 0→54 mode elevation INSIDE the same SQLite transaction**. If any validation fails, the request, both nonces and mode header are rolled back together. Reopened journals preserve the mode across WAL checkpoints and ordinary restarts.
- **freight/recovery_checkpoint_m53.py** — the complete, canonical signed journal-state hash now incorporates the security mode header and an M54-specific state domain. A custodian-held checkpoint signed over a strict journal becomes invalid if a privileged actor changes only the header from 54 to 0, even when **all review rows and trigger definitions stay unchanged**.
- **freight/test_lab_replay_checkpoint_m53.py** — inherited M53 regression was strengthened to confirm local M52 now refuses the ordinary downgrade on an elevated journal, while explicitly demonstrating a **never-upgraded legacy LOCAL_ONLY journal still admits privileged coherent row rollback**. This does not conceal unchanged local-only limitations.
- **.github/workflows/retally-signed-replay-checkpoint-m53.yml** — inherited historical differential pins **both** predecessor M52 application and predecessor replay-journal implementations, not the modern M54 class; the original M52 false admission is still proven against the actual prior source.
- The original 14-lab director, independent M39 cross-lab admission and existing Control Center now check the exact source results. **No new fifteenth lab.**

### Twelve disposable runtime downgrade attack classes

Every scenario first creates a fully valid *fictional* M50 dual-SQLite backup, ephemeral M51 technical Ed25519 reviewers, a separate local replay journal and an original M53 checkpointed review with an independently simulated (also ephemeral) custodian key. The normal first review must succeed, changing the journal header to mode 54. The following attempted review or checkpoint must fail with exact typed denial:

| Controlled scenario | Expected outcome |
| --- | --- |
| Fresh correctly signed local-only review | Downgrade denied |
| New client reopens same journal then uses legacy entrypoint | Downgrade denied |
| Client opened before first checkpoint tries legacy write after first | Downgrade denied |
| Replay original fully signed review without checkpoint | Downgrade denied |
| Same request with valid freshly signed nonces | Downgrade denied |
| Two distinct fresh, well-signed local-only reviews | Both denied |
| Direct legacy journal consume bypassing public wrapper | Downgrade denied |
| SQLite WAL checkpoint followed by reopened legacy client | Downgrade denied |
| Second independently checkpointed review then old legacy write | Downgrade denied |
| Unapproved SQLite mode header version 99 | Unsupported mode denied |
| Valid old externally signed pre-upgrade header=0 checkpoint | Stale state denied |
| Trusted externally signed strict checkpoint after privileged header reset | Signed-state mismatch denied |

Source backup files must be **byte-identical before/after** each rejected operation, and no failed operation may append a real customer approval or mutate the accepted review/nonce history.

### Additional concurrency / rollback checks

- **Six simultaneous, independently signed fresh local-only requests**, each through a distinct reopened SQLite client, are all denied on a previously elevated journal.
- An intentional exception inserted **after the security mode flips to 54 but BEFORE SQLite commit** rolls the header, review row and both nonces back to the original empty, local-only state. A valid original checkpointed retry can then succeed atomically.
- Legitimate freshly signed sequential M53 checkpointed requests still succeed when a real custodian is simulated re-signing each new successor state. Without that new signature, a prior checkpoint cannot silently cover a later journal generation.
- A privileged header edit 54→0 changes the externally signed M53 journal digest, so the strict independently checked path refuses it **even if every underlying journal row remains otherwise valid**.

### Limits and why this is NOT an external security certification

The one-way policy is enforced by *application code* over **local SQLite header user_version**. A privileged operator who can edit the header AND erase/restore all local historical rows or code can still defeat local-only checks. A different brand-new journal has no inherited external history. Local mode alone is **NOT a nonrollbackable remote trust anchor**. Independently provisioned signer/custodian keys and a separately safeguarded latest signed M53 checkpoint remain required for true rollback detection. None is deployed/provisioned by this synthetic mission, and M52 journals that have **never** been elevated remain LOCAL_ONLY and rollback-susceptible.

Neither successful technical signatures nor the local one-time journal establish real customer consent, legal commercial authority, a bank/carrier payment, actual freight recovery or production disaster-recovery readiness.

**All original 26 RecoveryOS historical findings remain OPEN_UNVERIFIED. All 18 human first-customer approval gates remain unmet.** No real receipts or recovered funds have been validated. No externally marketable error/recovery/TAM claims are authorized.

### Local reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_checkpoint_mode_m54.py freight/test_lab_replay_checkpoint_m53.py freight/test_lab_recovery_replay_m52.py
    PYTHONPATH=. python -m freight.lab_checkpoint_mode_m54 --as-of-date 2026-10-13 --out /tmp/retally-m54
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m54-control

**DRAFT / UNMERGED / UNDEPLOYED.**
